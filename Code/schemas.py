"""Pydantic schemas cho các API chính của RICE PEST AI."""

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .models import VaiTroTinNhan


class PhienPhanTichBase(BaseModel):
    """Các trường dùng chung khi tạo và trả về một phiên phân tích."""

    model_config = ConfigDict(from_attributes=True)

    MaNguoiDung: int | None = None
    DuongDanAnhGoc: str = Field(..., max_length=500)
    DuongDanAnhKetQua: str | None = Field(default=None, max_length=500)
    QuyMoDienTich: str | None = Field(default=None, max_length=100)
    NhietDo: Decimal | None = None
    DoAm: Decimal | None = None
    KetQuaAI_JSON: dict[str, Any] | list[Any] | None = None
    KetQuaDSS_JSON: dict[str, Any] | list[Any] | None = None


class PhienPhanTichCreate(PhienPhanTichBase):
    """Dữ liệu tạo phiên phân tích mới."""


class PhienPhanTichResponse(PhienPhanTichBase):
    """Dữ liệu phiên phân tích trả về cho client."""

    MaPhien: int
    NgayTao: datetime


class TinNhanChatBase(BaseModel):
    """Các trường dùng chung của một tin nhắn trong luồng chat."""

    model_config = ConfigDict(from_attributes=True)

    MaLuong: int
    MaPhien_Context: int | None = None
    VaiTro: VaiTroTinNhan
    NoiDung: str


class TinNhanChatCreate(TinNhanChatBase):
    """Dữ liệu tạo tin nhắn chat mới."""


class TinNhanChatResponse(TinNhanChatBase):
    """Dữ liệu tin nhắn trả về cho client."""

    MaTinNhan: int
    NgayTao: datetime


class SauHaiBase(BaseModel):
    """Các trường dùng chung để khai báo thông tin sâu hại."""

    model_config = ConfigDict(from_attributes=True)

    MaLopYOLO: str = Field(..., max_length=50)
    VongDoi: str | None = None
    TrieuChungGayHai: str | None = None
    ThuVienAnh_JSON: dict[str, Any] | list[Any] | None = None
    VungPhanBo_JSON: dict[str, Any] | list[Any] | None = None
    CayTrongBiHai_JSON: dict[str, Any] | list[Any] | None = None


class SauHaiCreate(SauHaiBase):
    """Dữ liệu tạo loài sâu hại mới."""


class SauHaiResponse(SauHaiBase):
    """Dữ liệu loài sâu hại trả về cho client."""

    MaSauHai: int


class AnalyzeEnvironmentSchema(BaseModel):
    """Context môi trường gửi kèm multipart request phân tích ảnh."""

    model_config = ConfigDict(from_attributes=True)

    nhiet_do: Decimal
    do_am: Decimal = Field(..., ge=0, le=100)
    giai_doan_lua: str | None = None
    mua_vu: str | None = None
    # Vùng miền là đặc trưng thứ năm của vector KNN.
    vung_mien: str | None = Field(default=None, max_length=80)
    quy_mo_dien_tich: str | None = Field(default=None, max_length=100)
