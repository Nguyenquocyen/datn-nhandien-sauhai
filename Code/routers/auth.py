"""API đăng ký, xác thực OTP và đăng nhập bằng JWT."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..database import get_db
from ..mail_config import send_otp_email
from ..models import NguoiDung, OTPVerification, VaiTroNguoiDung
from ..security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    """Email/mật khẩu là bắt buộc; username cũ vẫn được hỗ trợ tùy chọn."""

    email: EmailStr
    mat_khau: str = Field(min_length=8, max_length=128)
    ten_dang_nhap: str | None = Field(default=None, min_length=3, max_length=100)


class VerifyOTPRequest(BaseModel):
    email: EmailStr
    otp: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")


class LoginRequest(BaseModel):
    """Đăng nhập bằng email hoặc tên đăng nhập."""

    email: EmailStr | None = None
    ten_dang_nhap: str | None = Field(default=None, min_length=1, max_length=100)
    mat_khau: str = Field(min_length=1, max_length=128)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ma_nguoi_dung: int
    ten_dang_nhap: str
    email: EmailStr
    vai_tro: VaiTroNguoiDung
    is_verified: bool


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    email = str(payload.email).strip().lower()
    username = (payload.ten_dang_nhap or email.split("@", 1)[0]).strip()
    if not username:
        raise HTTPException(status_code=422, detail="Tên đăng nhập không được để trống.")

    existing = db.scalar(
        select(NguoiDung).where(
            or_(NguoiDung.TenDangNhap == username, NguoiDung.Email == email)
        )
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="Tên đăng nhập hoặc email đã được sử dụng.")

    user = NguoiDung(
        TenDangNhap=username,
        Email=email,
        MatKhauHash=hash_password(payload.mat_khau),
        VaiTro=VaiTroNguoiDung.FARMER,
        IsVerified=False,
    )
    otp = f"{secrets.randbelow(1_000_000):06d}"
    otp_record = OTPVerification(
        nguoi_dung=user,
        MaOTP=hash_password(otp),
        HetHanLuc=datetime.utcnow() + timedelta(minutes=5),
        DaSuDung=False,
    )
    db.add_all([user, otp_record])
    try:
        db.flush()
        await send_otp_email(email, otp)
        db.commit()
        db.refresh(user)
    except RuntimeError as exc:
        db.rollback()
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=503,
            detail="Không thể gửi email OTP. Vui lòng kiểm tra cấu hình SMTP.",
        ) from exc

    return {
        "status": "ok",
        "message": "Đăng ký thành công. Mã OTP đã được gửi qua email.",
        "data": {"user": _serialize_user(user)},
    }


@router.post("/verify-otp")
def verify_otp(
    payload: VerifyOTPRequest,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    email = str(payload.email).strip().lower()
    user = db.scalar(select(NguoiDung).where(NguoiDung.Email == email))
    if user is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài khoản.")

    otp_record = db.scalar(
        select(OTPVerification)
        .where(
            OTPVerification.MaNguoiDung == user.MaNguoiDung,
            OTPVerification.DaSuDung.is_(False),
        )
        .order_by(OTPVerification.NgayTao.desc())
    )
    if (
        otp_record is None
        or otp_record.HetHanLuc < datetime.utcnow()
        or not verify_password(payload.otp, otp_record.MaOTP)
    ):
        raise HTTPException(status_code=400, detail="OTP không đúng hoặc đã hết hạn.")

    user.IsVerified = True
    otp_record.DaSuDung = True
    db.commit()
    return {"status": "ok", "message": "Xác thực email thành công."}


@router.post("/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> dict[str, object]:
    identifier = (str(payload.email).strip().lower() if payload.email else "").strip()
    identifier = identifier or (payload.ten_dang_nhap or "").strip()
    user = db.scalar(
        select(NguoiDung).where(
            or_(NguoiDung.Email == identifier, NguoiDung.TenDangNhap == identifier)
        )
    )
    if user is None or not verify_password(payload.mat_khau, user.MatKhauHash):
        raise HTTPException(
            status_code=401,
            detail="Email/tên đăng nhập hoặc mật khẩu không đúng.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.IsVerified:
        raise HTTPException(status_code=403, detail="Tài khoản chưa xác thực OTP.")

    return {
        "status": "ok",
        "message": "Đăng nhập thành công",
        "data": {
            "access_token": create_access_token(user),
            "token_type": "bearer",
            "user": _serialize_user(user),
        },
    }


def _serialize_user(user: NguoiDung) -> dict[str, object]:
    return {
        "ma_nguoi_dung": user.MaNguoiDung,
        "ten_dang_nhap": user.TenDangNhap,
        "email": user.Email,
        "vai_tro": user.VaiTro.value,
        "is_verified": user.IsVerified,
    }
