"""Service chạy nhận diện sâu hại bằng YOLO."""

from __future__ import annotations

import os
import uuid
from collections import Counter
from io import BytesIO
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image
import torch  # Đã thêm: Thư viện lõi để quản lý GPU


class YoloService:
    """Nạp mô hình YOLO và xử lý ảnh nhận diện sâu hại."""

    MAX_IMAGE_BYTES = 5 * 1024 * 1024
    INFERENCE_IMAGE_SIZE = 640
    ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}
    LABEL_ALIASES = {
        "0": "rice_leaf_roller",
        "rice_leaf_roller": "rice_leaf_roller",
        "rice_leaf_folder": "rice_leaf_roller",
        "cnaphalocrocis_medinalis": "rice_leaf_roller",
        "1": "brown_planthopper",
        "2": "yellow_rice_borer",
        "3": "asiatic_rice_borer",
        "4": "rice_leaf_caterpillar",
        "5": "rice_shell_pest",
        "6": "rice_gall_midge",
        "7": "grain_spreader_thrips",
        "8": "rice_stem_maggot",
        "rice_leaf_caterpillar": "rice_leaf_caterpillar",
        "marasmia_patnalis": "rice_leaf_caterpillar",
        "parnara_guttata": "rice_leaf_caterpillar",
        "paddy_stem_maggot": "rice_stem_maggot",
        "rice_stem_maggot": "rice_stem_maggot",
        "steneotarsonemus_spinki": "rice_stem_maggot",
        "panicle_rice_mite": "rice_stem_maggot",
        "asiatic_rice_borer": "asiatic_rice_borer",
        "chilo_suppressalis": "asiatic_rice_borer",
        "striped_stem_borer": "asiatic_rice_borer",
        "yellow_rice_borer": "yellow_rice_borer",
        "scirpophaga_incertulas": "yellow_rice_borer",
        "stem_borer": "yellow_rice_borer",
        "rice_gall_midge": "rice_gall_midge",
        "orseolia_oryzae": "rice_gall_midge",
        "brown_planthopper": "brown_planthopper",
        "brown_plant_hopper": "brown_planthopper",
        "nilaparvata_lugens": "brown_planthopper",
        "grain_spreader_thrips": "grain_spreader_thrips",
        "rice_thrips": "grain_spreader_thrips",
        "stenchaetothrips_biformis": "grain_spreader_thrips",
        "rice_shell_pest": "rice_shell_pest",
        "rice_caseworm": "rice_shell_pest",
        "nymphula_depunctalis": "rice_shell_pest",
    }
    DISPLAY_NAMES = {
        "rice_leaf_roller": "Sâu cuốn lá nhỏ",
        "brown_planthopper": "Rầy nâu",
        "yellow_rice_borer": "Sâu đục thân bướm 2 chấm",
        "asiatic_rice_borer": "Sâu đục thân 5 vạch",
        "rice_leaf_caterpillar": "Sâu cuốn lá lớn",
        "rice_shell_pest": "Sâu phao",
        "rice_gall_midge": "Muỗi hành (Sâu năng)",
        "grain_spreader_thrips": "Bọ trĩ (Bù lạch)",
        "rice_stem_maggot": "Nhện gié hại lúa",
    }

    @classmethod
    def normalize_yolo_label(cls, raw_label: str) -> str:
        """Quy đổi tên/mã lớp model về MaLopYOLO chuẩn của database."""
        normalized = str(raw_label).strip().casefold().replace(" ", "_")
        return cls.LABEL_ALIASES.get(normalized, normalized)

    def __init__(
        self,
        model_path: str | Path | None = None,
        results_dir: str | Path | None = None,
        confidence: float = 0.25,
    ) -> None:
        if not 0.0 <= confidence <= 1.0:
            raise ValueError("confidence phải nằm trong khoảng từ 0 đến 1.")

        self.project_root = Path(__file__).resolve().parents[2]
        self.results_dir = Path(results_dir or self.project_root / "Code" / "static" / "results")
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.model_path = self._resolve_model_path(model_path)
        self.confidence = confidence

        # Đã thêm: Kiểm tra và thiết lập thiết bị chạy AI (GPU RTX 3050 nếu có)
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"🚀 [YOLO] Khởi động AI... Đang chạy trên thiết bị: {self.device.upper()}")

        try:
            from ultralytics import YOLO
        except ImportError as exc:
            raise RuntimeError(
                "Chưa cài thư viện ultralytics. Hãy chạy: pip install ultralytics"
            ) from exc

        # Đã thêm: Nạp model thẳng vào GPU để tiết kiệm thời gian truyền dữ liệu
        self.model = YOLO(str(self.model_path)).to(self.device)

    def predict(self, image_bytes: bytes) -> dict[str, Any]:
        """Nhận diện ảnh bytes và trả về payload có thể lưu vào KetQuaAI_JSON."""
        if not isinstance(image_bytes, bytes) or not image_bytes:
            raise ValueError("image_bytes phải là bytes của một ảnh không rỗng.")

        if len(image_bytes) > self.MAX_IMAGE_BYTES:
            raise ValueError("Ảnh tải lên không được vượt quá 5 MB.")

        try:
            image_file = Image.open(BytesIO(image_bytes))
            image_file.verify()
            image_format = image_file.format
            if image_format not in self.ALLOWED_FORMATS:
                raise ValueError("Chỉ hỗ trợ ảnh JPEG, PNG hoặc WebP.")
            image = Image.open(BytesIO(image_bytes)).convert("RGB")
        except Exception as exc:
            if isinstance(exc, ValueError):
                raise
            raise ValueError(
                "Dữ liệu tải lên không phải ảnh JPEG, PNG hoặc WebP hợp lệ."
            ) from exc

        image_array = np.asarray(image)
        try:
            predictions = self.model.predict(
                source=image_array,
                conf=self.confidence,
                imgsz=self.INFERENCE_IMAGE_SIZE,
                device=self.device,  # Đã thêm: Ép luồng xử lý ảnh chạy qua GPU
                verbose=False,
            )
        except Exception as exc:
            raise RuntimeError("Không thể thực hiện suy luận YOLO.") from exc

        if not predictions:
            raise RuntimeError("Mô hình YOLO không trả về kết quả suy luận.")

        prediction = predictions[0]
        objects = self._extract_objects(prediction)
        output_path = self._save_annotated_image(prediction)
        class_counts = dict(Counter(item["ma_lop_yolo"] for item in objects))

        return {
            "đường_dẫn_ảnh_kết_quả": self._relative_result_path(output_path),
            "danh_sách_đối_tượng": objects,
            "tổng_số_lượng_phát_hiện": len(objects),
            "số_lượng_theo_lớp": class_counts,
        }

    def _extract_objects(self, prediction: Any) -> list[dict[str, Any]]:
        boxes = prediction.boxes
        if boxes is None:
            return []

        names = prediction.names
        xyxy = boxes.xyxy.cpu().tolist()
        class_ids = boxes.cls.cpu().tolist()
        confidences = boxes.conf.cpu().tolist()

        objects: list[dict[str, Any]] = []
        for coordinates, class_id, score in zip(
            xyxy, class_ids, confidences, strict=True
        ):
            class_id_int = int(class_id)
            raw_label = str(names[class_id_int])
            normalized_label = self.normalize_yolo_label(raw_label)
            objects.append(
                {
                    "ma_lop_yolo": normalized_label,
                    "tên": self.DISPLAY_NAMES.get(normalized_label, raw_label),
                    "độ_tin_cậy": round(float(score), 6),
                    "tọa_độ": {
                        "x1": round(float(coordinates[0]), 2),
                        "y1": round(float(coordinates[1]), 2),
                        "x2": round(float(coordinates[2]), 2),
                        "y2": round(float(coordinates[3]), 2),
                    },
                }
            )
        return objects

    def _save_annotated_image(self, prediction: Any) -> Path:
        filename = f"{uuid.uuid4().hex}.jpg"
        output_path = self.results_dir / filename
        prediction.names = {
            class_id: self.DISPLAY_NAMES.get(
                self.normalize_yolo_label(str(class_name)), str(class_name)
            )
            for class_id, class_name in prediction.names.items()
        }
        annotated_image = prediction.plot()
        Image.fromarray(annotated_image[:, :, ::-1]).save(output_path, format="JPEG")
        return output_path

    def _relative_result_path(self, output_path: Path) -> str:
        return output_path.relative_to(self.project_root).as_posix()

    def _resolve_model_path(self, model_path: str | Path | None) -> Path:
        configured_path = model_path or os.getenv("YOLO_MODEL_PATH")
        candidates = (
            [Path(configured_path)]
            if configured_path
            else [
                self.project_root / "Code" / "runs" / "detect" / "train-3" / "weights" / "best.pt",
                self.project_root / "Code" / "models" / "best.pt",
            ]
        )

        for candidate in candidates:
            resolved = candidate.expanduser().resolve()
            if resolved.is_file():
                return resolved

        searched = ", ".join(str(path.expanduser().resolve()) for path in candidates)
        raise FileNotFoundError(
            f"Không tìm thấy file trọng số YOLO best.pt. Đã kiểm tra: {searched}"
        ) 