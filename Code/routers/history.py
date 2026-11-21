"""API truy vấn lịch sử phân tích."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import NguoiDung, PhienPhanTich
from ..security import get_current_user

router = APIRouter(tags=["history"])


@router.get("/api/history")
def history(
    db: Session = Depends(get_db),
    current_user: NguoiDung | None = Depends(get_current_user),
) -> dict[str, Any]:
    """Lấy các phiên phân tích của một người dùng."""
    if current_user is None:
        raise HTTPException(
            status_code=401,
            detail="Vui lòng đăng nhập để xem nhật ký quét.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        sessions = db.scalars(
            select(PhienPhanTich)
            .where(PhienPhanTich.MaNguoiDung == current_user.MaNguoiDung)
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
                    "confidence": _extract_confidence(item.KetQuaAI_JSON),
                    "ngay_tao": item.NgayTao,
                }
                for item in sessions
            ],
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Không thể lấy lịch sử phân tích.") from exc


def _extract_confidence(result: Any) -> float | None:
    if not isinstance(result, dict):
        return None
    objects = result.get("danh_sách_đối_tượng") or []
    if not objects or not isinstance(objects[0], dict):
        return None
    value = objects[0].get("độ_tin_cậy", objects[0].get("confidence"))
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


@router.delete("/api/history/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_history(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: NguoiDung | None = Depends(get_current_user),
) -> None:
    """Xóa một phiên quét thuộc tài khoản hiện tại."""
    if current_user is None:
        raise HTTPException(
            status_code=401,
            detail="Vui lòng đăng nhập để xóa nhật ký quét.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    session = db.scalar(
        select(PhienPhanTich).where(
            PhienPhanTich.MaPhien == session_id,
            PhienPhanTich.MaNguoiDung == current_user.MaNguoiDung,
        )
    )
    if session is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiên quét của tài khoản.")
    db.delete(session)
    db.commit()
