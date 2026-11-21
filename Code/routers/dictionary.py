"""API dữ liệu thật cho từ điển sâu hại."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import GiaiPhapSinhHoc, SauHai, SauHaiGiaiPhap

router = APIRouter(tags=["dictionary"])

_LOCAL_DICTIONARY_IMAGES = {
    "rice_leaf_roller": "/static/images/dictionary/rice_leaf_roller.jpg",
    "brown_planthopper": "/static/images/dictionary/brown_planthopper.jpg",
    "yellow_rice_borer": "/static/images/dictionary/yellow_rice_borer.jpg",
    "asiatic_rice_borer": "/static/images/dictionary/asiatic_rice_borer.jpg",
    "rice_leaf_caterpillar": "/static/images/dictionary/rice_leaf_caterpillar.jpg",
    "rice_shell_pest": "/static/images/dictionary/rice_shell_pest.jpg",
    "rice_gall_midge": "/static/images/dictionary/rice_gall_midge.jpg",
    "grain_spreader_thrips": "/static/images/dictionary/grain_spreader_thrips.jpg",
    "rice_stem_maggot": "/static/images/dictionary/rice_stem_maggot.jpg",
}


def _image_url(value: Any) -> str | None:
    """Lấy URL ảnh trong JSON thư viện ảnh, không tự bịa URL."""
    if isinstance(value, str) and value.startswith(("http://", "https://", "/")):
        return value
    if isinstance(value, list):
        for item in value:
            result = _image_url(item)
            if result:
                return result
    if isinstance(value, dict):
        for key in ("url", "URL", "image_url", "anh", "hinh_anh"):
            result = _image_url(value.get(key))
            if result:
                return result
    return None


@router.get("/api/dictionary")
def get_dictionary(db: Session = Depends(get_db)) -> dict[str, Any]:
    """Trả danh mục sâu hại và giải pháp liên kết từ database."""
    try:
        rows = db.execute(
            select(SauHai, SauHaiGiaiPhap, GiaiPhapSinhHoc)
            .outerjoin(SauHaiGiaiPhap, SauHaiGiaiPhap.MaSauHai == SauHai.MaSauHai)
            .outerjoin(
                GiaiPhapSinhHoc,
                GiaiPhapSinhHoc.MaGiaiPhap == SauHaiGiaiPhap.MaGiaiPhap,
            )
            .order_by(SauHai.TenTiengViet, GiaiPhapSinhHoc.TenGiaiPhap)
        ).all()
        items: dict[int, dict[str, Any]] = {}
        for pest, _link, solution in rows:
            local_image = _LOCAL_DICTIONARY_IMAGES.get(pest.MaLopYOLO)
            item = items.setdefault(
                pest.MaSauHai,
                {
                    "ma_sau_hai": pest.MaSauHai,
                    "ten_tieng_viet": pest.TenTiengViet,
                    "ten_khoa_hoc": pest.TenKhoaHoc,
                    "ma_lop_yolo": pest.MaLopYOLO,
                    "dac_diem_hinh_thai": pest.DacDiemHinhThai,
                    "cach_thuc_gay_hai": pest.CachThucGayHai,
                    "image_url": local_image or _image_url(pest.ThuVienAnh_JSON),
                    "image_urls": [local_image] if local_image else [],
                    "giai_phap_ipm": [],
                },
            )
            if solution is not None:
                item["giai_phap_ipm"].append(
                    {
                        "ma_giai_phap": solution.MaGiaiPhap,
                        "ten_giai_phap": solution.TenGiaiPhap,
                        "mo_ta": solution.mo_ta,
                    }
                )
        return {"status": "ok", "data": list(items.values())}
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Không thể tải dữ liệu từ điển từ cơ sở dữ liệu.",
        ) from exc
