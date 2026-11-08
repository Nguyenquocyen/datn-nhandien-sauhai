"""API nhận diện ảnh và tính DSS."""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import (
    AHPHistory,
    CauHinhDSS,
    GiaiPhapSinhHoc,
    LichSuCanhTac,
    NguoiDung,
    PhienPhanTich,
    SauHai,
    SauHaiGiaiPhap,
)
from ..services.dss_service import DSSService
from ..services.yolo_service import YoloService
from ..security import get_current_user

router = APIRouter(tags=["analysis"])
_dss_service = DSSService()
_yolo_service: YoloService | None = None
logger = logging.getLogger(__name__)


class DSSRequest(BaseModel):
    ma_phien: int | None = None
    ma_lop_yolo: str = Field(min_length=1, max_length=80)
    mat_do: int = Field(ge=1, le=3)
    nhiet_do: Decimal
    do_am: Decimal = Field(ge=0, le=100)
    giai_doan_lua: str = "de_nhanh"
    mua_vu: str = "dong_xuan"
    vung_mien: str = "dbscl"


class AHPRequest(BaseModel):
    comparisons: list[float] = Field(min_length=6, max_length=6)
    ma_lop_yolo: str = Field(min_length=1, max_length=80)


class KNNRequest(BaseModel):
    ma_lop_yolo: str = Field(min_length=1, max_length=80)
    nhiet_do: Decimal
    do_am: Decimal = Field(ge=0, le=100)
    mat_do: float = Field(ge=1, le=3)
    giai_doan_lua: str
    mua_vu: str


@router.post("/api/ahp")
def run_pairwise_ahp(
    payload: AHPRequest,
    db: Session = Depends(get_db),
    current_user: NguoiDung | None = Depends(get_current_user),
) -> dict[str, Any]:
    """Tính AHP theo sáu so sánh cặp và loài sâu AI đã nhận diện."""
    try:
        result = _dss_service.calculate_pairwise_ahp(
            payload.comparisons,
            payload.ma_lop_yolo,
            db,
        )
        if current_user is not None:
            db.add(
                AHPHistory(
                    user_id=current_user.MaNguoiDung,
                    result_matrix=result["matrix"],
                    cr_value=result["cr"],
                )
            )
            db.commit()
        return {"status": "ok", "data": result}
    except HTTPException:
        db.rollback()
        raise
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/api/dss")
def run_dss(
    payload: DSSRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Chạy DSS sau khi người dùng đánh giá mật độ ngoài ruộng."""
    ai_result = {
        "danh_sách_đối_tượng": [{"ma_lop_yolo": payload.ma_lop_yolo}],
    }
    pest_details = _find_pest_details(db, ai_result)
    solution_links = _find_solutions(db, ai_result)
    config = db.scalar(select(CauHinhDSS).order_by(CauHinhDSS.MaCauHinh.desc()))
    if config is None:
        raise HTTPException(status_code=503, detail="Chưa có cấu hình AHP trong cơ sở dữ liệu.")

    ahp_result = _dss_service.calculate_ahp_ranking(
        config.MaTranSoSanh_JSON,
        solution_links,
        total_bounding_boxes=payload.mat_do,
        quy_mo_dien_tich="1",
    )
    historical_data = _find_history_with_context(db)
    knn_result = _dss_service.find_similar_cases(
        {
            "GiaiDoanLua": payload.giai_doan_lua,
            "MuaVu": payload.mua_vu,
            "ma_lop_yolo": payload.ma_lop_yolo,
            "NhietDo": payload.nhiet_do,
            "DoAm": payload.do_am,
            "MatDo": payload.mat_do,
        },
        historical_data,
    )
    dss_result = {"ahp": ahp_result, "knn": knn_result}
    if payload.ma_phien:
        session = db.get(PhienPhanTich, payload.ma_phien)
        if session is not None:
            session.KetQuaDSS_JSON = dss_result
            db.commit()
    return {"status": "ok", "message": "Đã chạy Hệ Chuyên gia AHP & KNN.", "data": dss_result}


@router.post("/api/knn")
def run_knn(payload: KNNRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
    """Tìm ba ca lịch sử gần nhất theo bối cảnh ruộng hiện tại."""
    historical_data = _find_history_with_context(db)
    results = _dss_service.find_similar_cases(
        {
            "GiaiDoanLua": payload.giai_doan_lua,
            "MuaVu": payload.mua_vu,
            "ma_lop_yolo": payload.ma_lop_yolo,
            "NhietDo": payload.nhiet_do,
            "DoAm": payload.do_am,
            "MatDo": payload.mat_do,
        },
        historical_data,
        top_k=3,
    )
    return {"status": "ok", "data": {"knn_results": results}}


def _find_history_with_context(db: Session) -> list[dict[str, Any]]:
    rows = db.execute(
        select(LichSuCanhTac, SauHai, GiaiPhapSinhHoc)
        .join(SauHai, SauHai.MaSauHai == LichSuCanhTac.MaSauHai)
        .outerjoin(
            GiaiPhapSinhHoc,
            GiaiPhapSinhHoc.MaGiaiPhap == LichSuCanhTac.MaGiaiPhapDaChon,
        )
    ).all()
    return [
        {
            "MaLichSu": history.MaLichSu,
            "MaSauHai": history.MaSauHai,
            "GiaiDoanLua": history.GiaiDoanLua,
            "MuaVu": history.MuaVu,
            "NhietDo": history.NhietDo,
            "DoAm": history.DoAm,
            "MatDo": history.MatDo,
            "MaGiaiPhapDaChon": history.MaGiaiPhapDaChon,
            "DiemHieuQua": history.DiemHieuQua,
            "NguonTrichDan": history.NguonTrichDan,
            "GhiChuTrichDan": history.GhiChuTrichDan,
            "KetQua": history.KetQua,
            "ma_lop_yolo": pest.MaLopYOLO,
            "ten_giai_phap": solution.TenGiaiPhap if solution else "Chưa ghi nhận",
        }
        for history, pest, solution in rows
    ]


def _get_yolo_service() -> YoloService:
    global _yolo_service
    if _yolo_service is None:
        try:
            _yolo_service = YoloService()
        except (FileNotFoundError, RuntimeError, ValueError) as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
    return _yolo_service


@router.post("/api/analyze")
def analyze(
    image: UploadFile = File(...),
    nhiet_do: Decimal | None = Form(default=None),
    do_am: Decimal | None = Form(default=None),
    ma_nguoi_dung: int | None = Form(default=None),
    giai_doan_lua: str | None = Form(default=None),
    mua_vu: str | None = Form(default=None),
    vung_mien: str | None = Form(default=None),
    quy_mo_dien_tich: str | None = Form(default=None),
    db: Session = Depends(get_db),
    current_user: NguoiDung | None = Depends(get_current_user),
) -> dict[str, Any]:
    """Nhận diện ảnh; chỉ user có JWT mới tạo lịch sử trong database."""
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(status_code=415, detail="File tải lên phải là ảnh.")

    image_bytes = image.file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Ảnh tải lên không được rỗng.")

    try:
        ai_result = _get_yolo_service().predict(image_bytes)
        analysis_session: PhienPhanTich | None = None
        if current_user is not None:
            analysis_session = PhienPhanTich(
                MaNguoiDung=current_user.MaNguoiDung,
                DuongDanAnhGoc=image.filename or "uploaded_image",
                DuongDanAnhKetQua=ai_result["đường_dẫn_ảnh_kết_quả"],
                QuyMoDienTich=quy_mo_dien_tich,
                NhietDo=nhiet_do,
                DoAm=do_am,
                KetQuaAI_JSON=ai_result,
            )
            db.add(analysis_session)
            db.flush()

        pest_details = _find_pest_details(db, ai_result)
        solution_links = _find_solutions(db, ai_result)
        basic_solutions = list(
            {
                item["MaGiaiPhap"]: {
                    "ma_giai_phap": item["MaGiaiPhap"],
                    "ten_giai_phap": item["TenGiaiPhap"],
                }
                for item in solution_links
            }.values()
        )

        if nhiet_do is None or do_am is None:
            if analysis_session is not None:
                db.commit()
                db.refresh(analysis_session)
            return {
                "status": "ok",
                "message": "Nhận diện ảnh thành công",
                "data": {
                    "ma_phien": analysis_session.MaPhien if analysis_session else None,
                    "ket_qua_ai": ai_result,
                    "giai_phap_co_ban": basic_solutions,
                    "thong_tin_sau_hai": pest_details,
                    "ket_qua_dss": None,
                },
            }

        density = _dss_service.calculate_density(
            ai_result["tổng_số_lượng_phát_hiện"], quy_mo_dien_tich or "1"
        )
        ahp_result: dict[str, Any] = {
            **density,
            "xep_hang": [],
            "giai_thich_top_1": "Chưa chạy AHP.",
        }
        config = db.scalar(select(CauHinhDSS).order_by(CauHinhDSS.MaCauHinh.desc()))
        if config is not None and solution_links and density["severity"] != "Không phát hiện":
            ahp_result = _dss_service.calculate_ahp_ranking(
                config.MaTranSoSanh_JSON,
                solution_links,
                total_bounding_boxes=ai_result["tổng_số_lượng_phát_hiện"],
                quy_mo_dien_tich=quy_mo_dien_tich,
            )

        historical_data = db.scalars(select(LichSuCanhTac)).all()
        knn_result: list[dict[str, Any]] = []
        if giai_doan_lua and mua_vu and vung_mien and historical_data:
            knn_result = _dss_service.find_similar_cases(
                {
                    "GiaiDoanLua": giai_doan_lua,
                    "MuaVu": mua_vu,
                    "VungMien": vung_mien,
                    "NhietDo": nhiet_do,
                    "DoAm": do_am,
                },
                historical_data,
            )

        dss_result = {
            "ahp": ahp_result,
            "knn": knn_result,
        }
        if analysis_session is not None:
            analysis_session.KetQuaDSS_JSON = dss_result
            db.commit()
            db.refresh(analysis_session)
        return {
            "status": "ok",
            "message": "Phân tích ảnh thành công",
            "data": {
                "ma_phien": analysis_session.MaPhien if analysis_session else None,
                "ket_qua_ai": ai_result,
                "giai_phap_co_ban": basic_solutions,
                "thong_tin_sau_hai": pest_details,
                "ket_qua_dss": dss_result,
            },
        }
    except HTTPException:
        db.rollback()
        raise
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        db.rollback()
        logger.exception("Không thể hoàn tất phân tích ảnh.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Không thể hoàn tất phân tích ảnh.",
        ) from exc


def _find_solutions(db: Session, ai_result: dict[str, Any]) -> list[dict[str, Any]]:
    objects = ai_result.get("danh_sách_đối_tượng", [])
    class_names = {
        item.get("ma_lop_yolo")
        for item in objects
        if isinstance(item, dict) and item.get("ma_lop_yolo")
    }
    if not class_names:
        return []

    links = db.execute(
        select(SauHaiGiaiPhap, GiaiPhapSinhHoc)
        .join(SauHai, SauHai.MaSauHai == SauHaiGiaiPhap.MaSauHai)
        .join(
            GiaiPhapSinhHoc,
            GiaiPhapSinhHoc.MaGiaiPhap == SauHaiGiaiPhap.MaGiaiPhap,
        )
        .where(SauHai.MaLopYOLO.in_(class_names))
    ).all()
    return [
        {
            "MaGiaiPhap": solution.MaGiaiPhap,
            "TenGiaiPhap": solution.TenGiaiPhap,
            "DiemHieuQua": link.DiemHieuQua or 0,
            "ChiPhiMoiHecta": solution.ChiPhiMoiHecta or 0,
            "SoNgayHieuQua": solution.SoNgayHieuQua or 0,
            "DiemAnToanMoiTruong": solution.DiemAnToanMoiTruong or 0,
        }
        for link, solution in links
    ]


def _find_pest_details(db: Session, ai_result: dict[str, Any]) -> list[dict[str, Any]]:
    class_names = {
        item.get("ma_lop_yolo")
        for item in ai_result.get("danh_sách_đối_tượng", [])
        if isinstance(item, dict) and item.get("ma_lop_yolo")
    }
    if not class_names:
        return []
    pests = db.scalars(select(SauHai).where(SauHai.MaLopYOLO.in_(class_names))).all()
    return [
        {
            "ma_lop_yolo": pest.MaLopYOLO,
            "ten_tieng_viet": pest.TenTiengViet,
            "ten_khoa_hoc": pest.TenKhoaHoc,
            "vong_doi": pest.VongDoi,
            "dac_diem_hinh_thai": pest.DacDiemHinhThai,
            "cach_thuc_gay_hai": pest.CachThucGayHai,
            "muc_do_gay_hai": pest.MucDoGayHai,
            "trieu_chung_gay_hai": pest.TrieuChungGayHai,
        }
        for pest in pests
    ]
