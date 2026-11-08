"""SQLAlchemy models khớp với schema 9 bảng trong ``init_db.sql``."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum as PyEnum
from typing import Any

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, Numeric, String, Text, text
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class VaiTroNguoiDung(str, PyEnum):
    ADMIN = "Admin"
    FARMER = "Farmer"
    # Giữ giá trị cũ để các tài khoản đã seed vẫn đọc được sau migration.
    USER = "User"


class VaiTroTinNhan(str, PyEnum):
    USER = "User"
    AI = "AI"


class GiaiDoanLua(str, PyEnum):
    MA = "ma"
    DE_NHANH = "de_nhanh"
    LAM_DONG = "lam_dong"
    TRO_BONG = "tro_bong"
    CHIN = "chin"


class MuaVu(str, PyEnum):
    DONG_XUAN = "dong_xuan"
    HE_THU = "he_thu"
    THU_DONG = "thu_dong"


class VungMien(str, PyEnum):
    DBSCL = "dbscl"
    DONG_NAM_BO = "dong_nam_bo"
    TAY_NGUYEN = "tay_nguyen"
    DBSH = "dbsh"
    BAC_TRUNG_BO = "bac_trung_bo"
    DUYEN_HAI_MIEN_TRUNG = "duyen_hai_mien_trung"


class KetQuaCanhTac(str, PyEnum):
    TOT = "tot"
    TRUNG_BINH = "trung_binh"
    KEM = "kem"
    CHUA_DANH_GIA = "chua_danh_gia"


class NguoiDung(Base):
    __tablename__ = "NguoiDung"

    MaNguoiDung: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    TenDangNhap: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    Email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    MatKhauHash: Mapped[str] = mapped_column(String(255), nullable=False)
    VaiTro: Mapped[VaiTroNguoiDung] = mapped_column(
        Enum(VaiTroNguoiDung, values_callable=lambda cls: [item.value for item in cls]),
        nullable=False,
        default=VaiTroNguoiDung.FARMER,
    )
    IsVerified: Mapped[bool] = mapped_column(
        "IsVerified", Boolean, nullable=False, default=False, server_default=text("0")
    )
    NgayTao: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )

    phien_phan_tich: Mapped[list[PhienPhanTich]] = relationship(
        back_populates="nguoi_dung"
    )
    luong_chat: Mapped[list[LuongChat]] = relationship(back_populates="nguoi_dung")
    ahp_history: Mapped[list[AHPHistory]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class OTPVerification(Base):
    """Mã OTP xác thực email, có hiệu lực trong thời gian giới hạn."""

    __tablename__ = "OTP_Verification"

    Id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    MaNguoiDung: Mapped[int] = mapped_column(
        ForeignKey("NguoiDung.MaNguoiDung", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    MaOTP: Mapped[str] = mapped_column(String(255), nullable=False)
    HetHanLuc: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    DaSuDung: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("0")
    )
    NgayTao: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )

    nguoi_dung: Mapped[NguoiDung] = relationship()


class SauHai(Base):
    __tablename__ = "SauHai"

    MaSauHai: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    TenTiengViet: Mapped[str] = mapped_column(String(100), nullable=False)
    TenKhoaHoc: Mapped[str | None] = mapped_column(String(150))
    MaLopYOLO: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    VongDoi: Mapped[str | None] = mapped_column(Text)
    DacDiemHinhThai: Mapped[str | None] = mapped_column(Text)
    CachThucGayHai: Mapped[str | None] = mapped_column(Text)
    MucDoGayHai: Mapped[str | None] = mapped_column(Text)
    TrieuChungGayHai: Mapped[str | None] = mapped_column(Text)
    ThuVienAnh_JSON: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(JSON)
    VungPhanBo_JSON: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(JSON)
    CayTrongBiHai_JSON: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(JSON)

    giai_phap_lien_ket: Mapped[list[SauHaiGiaiPhap]] = relationship(
        back_populates="sau_hai", cascade="all, delete-orphan"
    )
    lich_su_canh_tac: Mapped[list[LichSuCanhTac]] = relationship(
        back_populates="sau_hai", cascade="all, delete-orphan"
    )


class GiaiPhapSinhHoc(Base):
    __tablename__ = "GiaiPhapSinhHoc"

    MaGiaiPhap: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    TenGiaiPhap: Mapped[str] = mapped_column(String(255), nullable=False)
    ChiPhiMoiHecta: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    SoNgayHieuQua: Mapped[int | None] = mapped_column(Integer)
    DiemAnToanMoiTruong: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    PhuongPhapApDung: Mapped[str | None] = mapped_column(Text)
    score_mat_do: Mapped[float | None] = mapped_column(Float)
    score_chi_phi: Mapped[float | None] = mapped_column(Float)
    score_thoi_gian: Mapped[float | None] = mapped_column(Float)
    score_an_toan: Mapped[float | None] = mapped_column(Float)
    mo_ta: Mapped[str | None] = mapped_column(Text)
    cach_su_dung: Mapped[str | None] = mapped_column(Text)
    luu_y_khi_dung: Mapped[str | None] = mapped_column(Text)
    co_so_khoa_hoc: Mapped[str | None] = mapped_column(Text)

    sau_hai_lien_ket: Mapped[list[SauHaiGiaiPhap]] = relationship(
        back_populates="giai_phap", cascade="all, delete-orphan"
    )
    lich_su_canh_tac: Mapped[list[LichSuCanhTac]] = relationship(
        back_populates="giai_phap_da_chon"
    )


class AHPHistory(Base):
    """Lưu ma trận so sánh và kết quả kiểm tra nhất quán của AHP."""

    __tablename__ = "ahp_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("NguoiDung.MaNguoiDung", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    result_matrix: Mapped[list[list[float]]] = mapped_column(JSON, nullable=False)
    cr_value: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )

    user: Mapped[NguoiDung] = relationship(back_populates="ahp_history")


class SauHaiGiaiPhap(Base):
    __tablename__ = "SauHai_GiaiPhap"

    MaLienKet: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    MaSauHai: Mapped[int] = mapped_column(
        ForeignKey("SauHai.MaSauHai", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    MaGiaiPhap: Mapped[int] = mapped_column(
        ForeignKey("GiaiPhapSinhHoc.MaGiaiPhap", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    DiemHieuQua: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))

    sau_hai: Mapped[SauHai] = relationship(back_populates="giai_phap_lien_ket")
    giai_phap: Mapped[GiaiPhapSinhHoc] = relationship(back_populates="sau_hai_lien_ket")


class LichSuCanhTac(Base):
    __tablename__ = "LichSuCanhTac"

    MaLichSu: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    MaSauHai: Mapped[int] = mapped_column(
        ForeignKey("SauHai.MaSauHai", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    GiaiDoanLua: Mapped[GiaiDoanLua] = mapped_column(
        Enum(GiaiDoanLua, values_callable=lambda cls: [item.value for item in cls]),
        nullable=False,
    )
    MuaVu: Mapped[MuaVu] = mapped_column(
        Enum(MuaVu, values_callable=lambda cls: [item.value for item in cls]),
        nullable=False,
    )
    VungMien: Mapped[VungMien] = mapped_column(
        Enum(VungMien, values_callable=lambda cls: [item.value for item in cls]),
        nullable=False,
    )
    NhietDo: Mapped[Decimal] = mapped_column(Numeric(4, 1), nullable=False)
    DoAm: Mapped[Decimal] = mapped_column(Numeric(4, 1), nullable=False)
    MatDo: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    DiemHieuQua: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    NguonTrichDan: Mapped[str | None] = mapped_column(String(1000))
    GhiChuTrichDan: Mapped[str | None] = mapped_column(Text)
    MaGiaiPhapDaChon: Mapped[int | None] = mapped_column(
        ForeignKey("GiaiPhapSinhHoc.MaGiaiPhap", ondelete="SET NULL", onupdate="CASCADE")
    )
    KetQua: Mapped[KetQuaCanhTac] = mapped_column(
        Enum(KetQuaCanhTac, values_callable=lambda cls: [item.value for item in cls]),
        nullable=False,
        default=KetQuaCanhTac.CHUA_DANH_GIA,
    )

    sau_hai: Mapped[SauHai] = relationship(back_populates="lich_su_canh_tac")
    giai_phap_da_chon: Mapped[GiaiPhapSinhHoc | None] = relationship(
        back_populates="lich_su_canh_tac"
    )


class CauHinhDSS(Base):
    __tablename__ = "CauHinhDSS"

    MaCauHinh: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    TenCauHinh: Mapped[str] = mapped_column(String(150), nullable=False)
    MaTranSoSanh_JSON: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(JSON)
    TrongSo_JSON: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(JSON)
    NgayTao: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )


class PhienPhanTich(Base):
    __tablename__ = "PhienPhanTich"

    MaPhien: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    MaNguoiDung: Mapped[int | None] = mapped_column(
        ForeignKey("NguoiDung.MaNguoiDung", ondelete="SET NULL", onupdate="CASCADE")
    )
    DuongDanAnhGoc: Mapped[str] = mapped_column(String(500), nullable=False)
    DuongDanAnhKetQua: Mapped[str | None] = mapped_column(String(500))
    QuyMoDienTich: Mapped[str | None] = mapped_column(String(100))
    NhietDo: Mapped[Decimal | None] = mapped_column(Numeric(4, 1))
    DoAm: Mapped[Decimal | None] = mapped_column(Numeric(4, 1))
    KetQuaAI_JSON: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(JSON)
    KetQuaDSS_JSON: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(JSON)
    NgayTao: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )

    nguoi_dung: Mapped[NguoiDung | None] = relationship(back_populates="phien_phan_tich")
    tin_nhan_context: Mapped[list[TinNhanChat]] = relationship(
        back_populates="phien_context"
    )


class LuongChat(Base):
    __tablename__ = "LuongChat"

    MaLuong: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    MaNguoiDung: Mapped[int] = mapped_column(
        ForeignKey("NguoiDung.MaNguoiDung", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    TenLuong: Mapped[str] = mapped_column(String(255), nullable=False)
    NgayTao: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )

    nguoi_dung: Mapped[NguoiDung] = relationship(back_populates="luong_chat")
    tin_nhan: Mapped[list[TinNhanChat]] = relationship(
        back_populates="luong_chat", cascade="all, delete-orphan"
    )


class TinNhanChat(Base):
    __tablename__ = "TinNhanChat"

    MaTinNhan: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    MaLuong: Mapped[int] = mapped_column(
        ForeignKey("LuongChat.MaLuong", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    MaPhien_Context: Mapped[int | None] = mapped_column(
        ForeignKey("PhienPhanTich.MaPhien", ondelete="SET NULL", onupdate="CASCADE")
    )
    VaiTro: Mapped[VaiTroTinNhan] = mapped_column(
        Enum(VaiTroTinNhan, values_callable=lambda cls: [item.value for item in cls]),
        nullable=False,
    )
    NoiDung: Mapped[str] = mapped_column(Text, nullable=False)
    NgayTao: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )

    luong_chat: Mapped[LuongChat] = relationship(back_populates="tin_nhan")
    phien_context: Mapped[PhienPhanTich | None] = relationship(
        back_populates="tin_nhan_context"
    )
