"""API truy vấn lịch sử phân tích."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import PhienPhanTich

router = APIRouter(tags=["history"])


@router.get("/api/history")
def history(
    ma_nguoi_dung: int = Query(..., gt=0),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Lấy các phiên phân tích của một người dùng."""
    try:
        sessions = db.scalars(
            select(PhienPhanTich)
            .where(PhienPhanTich.MaNguoiDung == ma_nguoi_dung)
            .order_by(PhienPhanTich.MaPhien.desc())
        ).all()
        return {
            "status": "ok",
            "message": "Lấy lịch sử phân tích thành công",
            "data": [
                {
                    "ma_phien": item.MaPhien,
                    "duong_dan_anh_goc": item.DuongDanAnhGoc,
                    "duong_dan_anh_ket_qua": item.DuongDanAnhKetQua,
                    "quy_mo_dien_tich": item.QuyMoDienTich,
                    "nhiet_do": item.NhietDo,
                    "do_am": item.DoAm,
                    "ket_qua_ai": item.KetQuaAI_JSON,
                    "ket_qua_dss": item.KetQuaDSS_JSON,
                }
                for item in sessions
            ],
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Không thể lấy lịch sử phân tích.") from exc
