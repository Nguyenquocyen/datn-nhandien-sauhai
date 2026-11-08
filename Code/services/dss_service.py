"""AHP/KNN decision-support services for RICE PEST AI."""

from __future__ import annotations

import math
import re
from collections.abc import Mapping, Sequence
from decimal import Decimal
from numbers import Real
from typing import Any

import numpy as np
import pandas as pd
from fastapi import HTTPException
from sklearn.neighbors import NearestNeighbors
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import GiaiPhapSinhHoc, SauHai, SauHaiGiaiPhap


class DSSService:
    """Tính mật độ, xếp hạng AHP và truy xuất ca tương đồng bằng KNN."""

    _RI_TABLE = {1: 0.0, 2: 0.0, 3: 0.58, 4: 0.90, 5: 1.12, 6: 1.24}
    _CRITERIA_NAMES = (
        "mat_do",
        "chi_phi",
        "thoi_gian_hieu_qua",
        "an_toan_moi_truong",
    )
    _CRITERIA_LABELS = (
        "Mật độ lây lan",
        "Chi phí",
        "Thời gian tác dụng",
        "An toàn sinh thái",
    )
    _PAIRWISE_INDEXES = (
        (0, 1),
        (0, 2),
        (0, 3),
        (1, 2),
        (1, 3),
        (2, 3),
    )
    _PAIRWISE_LABELS = (
        "Mật độ ↔ Chi phí",
        "Mật độ ↔ Thời gian",
        "Mật độ ↔ An toàn",
        "Chi phí ↔ Thời gian",
        "Chi phí ↔ An toàn",
        "Thời gian ↔ An toàn",
    )

    def calculate_pairwise_ahp(
        self,
        comparisons: Sequence[float],
        ma_lop_yolo: str,
        db: Session,
    ) -> dict[str, Any]:
        """Tính AHP và xếp hạng giải pháp phù hợp với loài sâu đã nhận diện."""
        if len(comparisons) != len(self._PAIRWISE_INDEXES):
            raise ValueError("AHP cần đúng 6 giá trị so sánh.")

        values = np.asarray(comparisons, dtype=float)
        if not np.all(np.isfinite(values)) or np.any((values < (1.0 / 9.0)) | (values > 9)):
            raise ValueError("Mỗi giá trị AHP phải nằm trong khoảng từ 1/9 đến 9.")

        matrix = np.ones((4, 4), dtype=float)
        for value, (row, column) in zip(values, self._PAIRWISE_INDEXES, strict=True):
            matrix[row, column] = value
            matrix[column, row] = 1.0 / value

        column_totals = matrix.sum(axis=0)
        normalized_matrix = matrix / column_totals
        weights = normalized_matrix.mean(axis=1)
        lambda_max = float(np.mean((matrix @ weights) / weights))
        consistency_index = (lambda_max - 4.0) / 3.0
        consistency_ratio = consistency_index / 0.90

        if consistency_ratio > 0.1:
            pair_errors = np.asarray(
                [
                    abs(matrix[row, column] - weights[row] / weights[column])
                    for row, column in self._PAIRWISE_INDEXES
                ],
                dtype=float,
            )
            worst_pair_position = int(np.argmax(pair_errors))
            conflict_pair = self._PAIRWISE_INDEXES[worst_pair_position]
            left_criterion, right_criterion = (
                self._CRITERIA_LABELS[index] for index in conflict_pair
            )
            error_message = (
                f"Đánh giá mâu thuẫn (CR={consistency_ratio:.3f}). "
                f"Cặp {left_criterion} và {right_criterion} lệch nhiều nhất "
                "so với tỷ lệ trọng số lý tưởng."
            )
            suggestion_text = (
                f"Có vẻ đánh giá giữa {left_criterion} và {right_criterion} "
                "đang hơi mâu thuẫn với các câu còn lại. "
                "Bác thử điều chỉnh lại thanh trượt này nhé!"
            )
            raise HTTPException(
                status_code=400,
                detail={
                    "error_message": error_message,
                    "conflict_pair_index": list(conflict_pair),
                    "suggestion_text": suggestion_text,
                },
            )

        solutions = db.scalars(
            select(GiaiPhapSinhHoc)
            .join(
                SauHaiGiaiPhap,
                SauHaiGiaiPhap.MaGiaiPhap == GiaiPhapSinhHoc.MaGiaiPhap,
            )
            .join(SauHai, SauHai.MaSauHai == SauHaiGiaiPhap.MaSauHai)
            .where(SauHai.MaLopYOLO == ma_lop_yolo)
        ).unique().all()
        if not solutions:
            raise HTTPException(
                status_code=404,
                detail=f"Chưa có giải pháp IPM phù hợp với loài sâu '{ma_lop_yolo}'.",
            )

        score_columns = (
            "score_mat_do",
            "score_chi_phi",
            "score_thoi_gian",
            "score_an_toan",
        )
        for solution in solutions:
            if any(getattr(solution, column) is None for column in score_columns):
                raise HTTPException(
                    status_code=503,
                    detail=(
                        f"Giải pháp '{solution.TenGiaiPhap}' chưa có đủ điểm chuyên gia AHP."
                    ),
                )

        score_matrix = np.asarray(
            [
                [float(getattr(solution, column)) for column in score_columns]
                for solution in solutions
            ],
            dtype=float,
        )
        if not np.all(np.isfinite(score_matrix)) or np.any(score_matrix <= 0):
            raise HTTPException(
                status_code=503,
                detail="Các giải pháp phù hợp phải có điểm chuyên gia AHP dương và hợp lệ.",
            )

        # AHP cấp phương án: tỷ lệ điểm chuyên gia tạo thành ma trận
        # so sánh cặp nhất quán cho từng tiêu chí.
        alternative_weights = np.empty_like(score_matrix)
        alternative_matrices: list[list[list[float]]] = []
        for criterion_index in range(score_matrix.shape[1]):
            criterion_scores = score_matrix[:, criterion_index]
            alternative_matrix = criterion_scores[:, None] / criterion_scores[None, :]
            column_totals = alternative_matrix.sum(axis=0)
            normalized_matrix = alternative_matrix / column_totals
            alternative_weights[:, criterion_index] = normalized_matrix.mean(axis=1)
            alternative_matrices.append(alternative_matrix.tolist())

        final_scores = alternative_weights @ weights
        final_scores /= final_scores.sum()
        ranking = []
        for solution_index, solution in enumerate(solutions):
            scores = score_matrix[solution_index]
            ranking.append(
                {
                    "id": solution.MaGiaiPhap,
                    "name": solution.TenGiaiPhap,
                    "scores": {
                        criterion: round(float(score), 6)
                        for criterion, score in zip(
                            self._CRITERIA_NAMES, scores, strict=True
                        )
                    },
                    "alternative_weights": {
                        criterion: round(float(weight), 6)
                        for criterion, weight in zip(
                            self._CRITERIA_NAMES,
                            alternative_weights[solution_index],
                            strict=True,
                        )
                    },
                    "mo_ta": solution.mo_ta,
                    "cach_su_dung": solution.cach_su_dung,
                    "luu_y_khi_dung": solution.luu_y_khi_dung,
                    "co_so_khoa_hoc": solution.co_so_khoa_hoc,
                    "weighted_score": round(float(final_scores[solution_index]), 6),
                }
            )
        ranking.sort(key=lambda item: item["weighted_score"], reverse=True)
        for rank, solution in enumerate(ranking, start=1):
            solution["rank"] = rank

        return {
            "cr": round(float(consistency_ratio), 6),
            "ci": round(float(consistency_index), 6),
            "lambda_max": round(lambda_max, 6),
            "weights": {
                criterion: round(float(weight), 6)
                for criterion, weight in zip(
                    self._CRITERIA_NAMES, weights, strict=True
                )
            },
            "matrix": matrix.tolist(),
            "alternative_matrices": alternative_matrices,
            "alternative_weight_matrix": alternative_weights.tolist(),
            "ranking": ranking,
        }

    def calculate_ahp_ranking(
        self,
        ma_tran_json: Any,
        danh_sach_giai_phap: Sequence[Any],
        *,
        total_bounding_boxes: int = 0,
        quy_mo_dien_tich: Any = None,
    ) -> dict[str, Any]:
        """Tính AHP 4 tiêu chí; không xếp hạng nếu thiếu diện tích hoặc không có sâu."""
        density = self.calculate_density(total_bounding_boxes, quy_mo_dien_tich)
        if density["severity"] == "Không phát hiện":
            return {
                **density,
                "trong_so": None,
                "consistency_index": None,
                "consistency_ratio": None,
                "xep_hang": [],
                "giai_thich_top_1": "Không phát hiện đối tượng sâu hại nên không xếp hạng giải pháp.",
            }
        if not danh_sach_giai_phap:
            return {
                **density,
                "trong_so": None,
                "consistency_index": None,
                "consistency_ratio": None,
                "xep_hang": [],
                "giai_thich_top_1": "Không có phương án phù hợp trong cơ sở dữ liệu.",
            }

        matrix = self._parse_matrix(ma_tran_json)
        if len(matrix) != 4:
            raise ValueError("Ma trận AHP phải có kích thước 4x4.")
        weights = self._calculate_weights(matrix)
        consistency_index, consistency_ratio = self._consistency(matrix, weights)
        if consistency_ratio > 0.1:
            raise ValueError(
                f"Ma trận AHP không nhất quán: CR={consistency_ratio:.6f}, yêu cầu CR <= 0.1."
            )

        criteria_values = self._build_criteria_values(
            danh_sach_giai_phap, density["value"]
        )
        normalized = [
            self._normalize_criteria(criteria_values[index], index)
            for index in range(4)
        ]
        ranked: list[dict[str, Any]] = []
        for item_index, item in enumerate(danh_sach_giai_phap):
            criterion_scores = {
                name: round(normalized[index][item_index], 6)
                for index, name in enumerate(self._CRITERIA_NAMES)
            }
            score = sum(
                weights[index] * normalized[index][item_index] for index in range(4)
            )
            ranked.append(
                {
                    "ma_giai_phap": self._read(item, "MaGiaiPhap"),
                    "ten_giai_phap": self._read(item, "TenGiaiPhap"),
                    "diem_hieu_qua": self._as_float(
                        self._read(item, "DiemHieuQua", 0), "DiemHieuQua"
                    ),
                    "diem_tieu_chi": criterion_scores,
                    "diem_ahp": round(score, 6),
                }
            )
        ranked.sort(key=lambda item: item["diem_ahp"], reverse=True)
        for rank, item in enumerate(ranked, 1):
            item["xep_hang"] = rank
        top = ranked[0]
        explanation = (
            f"Chọn phương án {top.get('ten_giai_phap') or top.get('ma_giai_phap')} "
            f"vì đạt điểm AHP cao nhất ({top['diem_ahp']:.6f}) "
            "theo bốn tiêu chí mật độ, chi phí, thời gian hiệu quả và an toàn môi trường."
        )
        return {
            **density,
            "trong_so": self._criteria_weights(weights),
            "consistency_index": round(consistency_index, 6),
            "consistency_ratio": round(consistency_ratio, 6),
            "xep_hang": ranked,
            "giai_thich_top_1": explanation,
        }

    def calculate_density(
        self, total_bounding_boxes: int, quy_mo_dien_tich: Any
    ) -> dict[str, Any]:
        if isinstance(total_bounding_boxes, bool) or not isinstance(
            total_bounding_boxes, int
        ) or total_bounding_boxes < 0:
            raise ValueError("Tổng số Bounding Box phải là số nguyên không âm.")
        if total_bounding_boxes == 0:
            return {
                "mat_do": None,
                "value": None,
                "canh_bao": "Không phát hiện",
                "severity": "Không phát hiện",
                "don_vi": "đối tượng/đơn vị diện tích",
            }
        area = self._parse_area(quy_mo_dien_tich)
        density = total_bounding_boxes / area
        severity = "Nhẹ" if density <= 1 else "Trung bình" if density <= 3 else "Nặng"
        return {
            "mat_do": round(density, 6),
            "value": round(density, 6),
            "canh_bao": severity,
            "severity": severity,
            "don_vi": "đối tượng/đơn vị diện tích",
        }

    def find_similar_cases(
        self,
        current_env: Mapping[str, Any] | Any,
        historical_data: Sequence[Mapping[str, Any] | Any],
        *,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """Chuẩn hóa bối cảnh và tìm ba ca lịch sử gần nhất bằng KNN."""
        if not historical_data:
            return []
        categorical_fields = ("GiaiDoanLua", "MuaVu", "ma_lop_yolo")
        numeric_fields = ("NhietDo", "DoAm", "MatDo")
        fields = categorical_fields
        if any(self._read(current_env, field) in (None, "") for field in fields):
            raise ValueError("KNN cần đủ GiaiDoanLua, MuaVu và ma_lop_yolo.")

        def feature_row(item: Mapping[str, Any] | Any) -> dict[str, Any]:
            return {
                field: self._categorical_value(self._read(item, field))
                for field in categorical_fields
            } | {
                field: self._as_float(self._read(item, field), field)
                for field in numeric_fields
            }

        history_rows = [feature_row(item) for item in historical_data]
        current_row = feature_row(current_env)
        preprocessor = ColumnTransformer(
            transformers=[
                ("numeric", StandardScaler(), list(numeric_fields)),
                (
                    "categorical",
                    self._make_encoder(),
                    list(categorical_fields),
                ),
            ]
        )
        pipeline = Pipeline(
            steps=[
                ("preprocessor", preprocessor),
                ("knn", NearestNeighbors(n_neighbors=min(3, len(history_rows)), metric="euclidean")),
            ]
        )
        history_frame = pd.DataFrame(history_rows)
        current_frame = pd.DataFrame([current_row])
        pipeline.fit(history_frame)
        distances, indices = pipeline.named_steps["knn"].kneighbors(
            pipeline.named_steps["preprocessor"].transform(current_frame)
        )
        results = []
        for distance, index in zip(distances[0], indices[0], strict=True):
            item = historical_data[int(index)]
            similarity = 1 / (1 + float(distance))
            density_labels = {1.0: "Thấp", 2.0: "Trung bình", 3.0: "Cao"}
            results.append(
                {
                    "ma_lich_su": self._read(item, "MaLichSu"),
                    "ma_sau_hai": self._read(item, "MaSauHai"),
                    "ma_lop_yolo": self._read(item, "ma_lop_yolo"),
                    "giai_doan_lua": self._read(item, "GiaiDoanLua"),
                    "mua_vu": self._read(item, "MuaVu"),
                    "vung_mien": self._read(item, "VungMien"),
                    "nhiet_do": self._read(item, "NhietDo"),
                    "do_am": self._read(item, "DoAm"),
                    "mat_do": self._read(item, "MatDo"),
                    "mat_do_nhan": density_labels.get(
                        float(self._read(item, "MatDo", 0)), "Không xác định"
                    ),
                    "ma_giai_phap_da_chon": self._read(item, "MaGiaiPhapDaChon"),
                    "giai_phap": self._read(item, "ten_giai_phap"),
                    "ten_giai_phap": self._read(item, "ten_giai_phap"),
                    "diem_hieu_qua": self._read(item, "DiemHieuQua"),
                    "diem_hieu_qua_thuc_te": self._read(item, "DiemHieuQua"),
                    "nguon_trich_dan": self._read(item, "NguonTrichDan"),
                    "ghi_chu_trich_dan": self._read(item, "GhiChuTrichDan"),
                    "ket_qua": self._read(item, "KetQua"),
                    "khoang_cach": round(float(distance), 6),
                    "do_tuong_dong": round(similarity, 6),
                    "similarity": f"{similarity * 100:.1f}%",
                    "hieu_qua": f"{float(self._read(item, 'DiemHieuQua', 0)):.1f}%",
                }
            )
        return results

    @staticmethod
    def _make_encoder() -> OneHotEncoder:
        try:
            return OneHotEncoder(handle_unknown="ignore", sparse_output=False)
        except TypeError:
            return OneHotEncoder(handle_unknown="ignore", sparse=False)

    def _build_criteria_values(
        self, solutions: Sequence[Any], density: float
    ) -> list[list[float]]:
        return [
            [density] * len(solutions),
            [
                self._as_float(
                    self._read(item, "ChiPhiMoiHecta", self._read(item, "ChiPhi", 0)),
                    "ChiPhiMoiHecta",
                )
                for item in solutions
            ],
            [
                self._as_float(self._read(item, "SoNgayHieuQua", 0), "SoNgayHieuQua")
                for item in solutions
            ],
            [
                self._as_float(
                    self._read(
                        item,
                        "DiemAnToanMoiTruong",
                        self._read(item, "DiemAnToan", 0),
                    ),
                    "DiemAnToanMoiTruong",
                )
                for item in solutions
            ],
        ]

    @staticmethod
    def _normalize_criteria(values: list[float], index: int) -> list[float]:
        low, high = min(values), max(values)
        if high == low:
            return [1.0] * len(values)
        normalized = [(value - low) / (high - low) for value in values]
        if index == 1:
            normalized = [1.0 - value for value in normalized]
        return normalized

    def _parse_matrix(self, value: Any) -> list[list[float]]:
        if isinstance(value, Mapping):
            value = value.get("matrix", value.get("ma_tran"))
        if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
            raise ValueError("MaTranSoSanh_JSON phải là ma trận số.")
        matrix = [
            [self._as_float(cell, "MaTranSoSanh_JSON") for cell in row]
            for row in value
        ]
        size = len(matrix)
        if size == 0 or any(len(row) != size for row in matrix):
            raise ValueError("Ma trận AHP phải vuông và không rỗng.")
        for index in range(size):
            if matrix[index][index] != 1:
                raise ValueError("Đường chéo ma trận AHP phải bằng 1.")
            for other in range(index + 1, size):
                if not math.isclose(
                    matrix[index][other] * matrix[other][index], 1, rel_tol=1e-5
                ):
                    raise ValueError("Ma trận AHP phải đối nghịch nghịch đảo.")
        return matrix

    @staticmethod
    def _calculate_weights(matrix: list[list[float]]) -> list[float]:
        means = [math.prod(row) ** (1 / len(row)) for row in matrix]
        total = sum(means)
        return [mean / total for mean in means]

    def _consistency(
        self, matrix: list[list[float]], weights: list[float]
    ) -> tuple[float, float]:
        size = len(matrix)
        if size <= 2:
            return 0.0, 0.0
        weighted = [
            sum(matrix[row][col] * weights[col] for col in range(size))
            for row in range(size)
        ]
        lambda_max = sum(weighted[i] / weights[i] for i in range(size)) / size
        consistency_index = (lambda_max - size) / (size - 1)
        random_index = self._RI_TABLE.get(size)
        if random_index is None:
            raise ValueError("Chỉ hỗ trợ ma trận AHP tối đa 6x6.")
        return consistency_index, consistency_index / random_index

    def _criteria_weights(self, weights: list[float]) -> dict[str, float]:
        return {
            name: round(weights[index], 6)
            for index, name in enumerate(self._CRITERIA_NAMES)
        }

    @staticmethod
    def _parse_area(value: Any) -> float:
        if isinstance(value, (Real, Decimal)) and not isinstance(value, bool):
            area = float(value)
        elif isinstance(value, str):
            match = re.search(r"\d+(?:[.,]\d+)?", value)
            area = float(match.group(0).replace(",", ".")) if match else 0
        else:
            area = 0
        if area <= 0:
            raise ValueError("QuyMoDienTich phải là số dương.")
        return area

    @staticmethod
    def _read(source: Mapping[str, Any] | Any, key: str, default: Any = None) -> Any:
        return source.get(key, default) if isinstance(source, Mapping) else getattr(source, key, default)

    @staticmethod
    def _categorical_value(value: Any) -> Any:
        return getattr(value, "value", value)

    @staticmethod
    def _as_float(value: Any, field_name: str) -> float:
        if isinstance(value, bool) or not isinstance(value, (Real, Decimal)):
            raise ValueError(f"{field_name} phải là số.")
        return float(value)
