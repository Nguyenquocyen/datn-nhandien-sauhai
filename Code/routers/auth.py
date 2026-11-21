"""API đăng nhập Google và phát JWT nội bộ."""

from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException, status
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import NguoiDung, VaiTroNguoiDung
from ..security import create_access_token, hash_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


class GoogleLoginRequest(BaseModel):
    credential: str = Field(min_length=1, max_length=8192)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ma_nguoi_dung: int
    ten_dang_nhap: str
    email: str
    vai_tro: VaiTroNguoiDung
    is_verified: bool


@router.post("/google")
def google_login(
    payload: GoogleLoginRequest,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    """Xác thực Google ID token rồi phát JWT nội bộ của ứng dụng."""
    client_id = os.getenv(
        "GOOGLE_CLIENT_ID",
        "208794080286-qiiivi2nv892q9sj9pr5d64oj5ipdphc.apps.googleusercontent.com",
    )
    try:
        claims = id_token.verify_oauth2_token(
            payload.credential,
            google_requests.Request(),
            client_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google ID token không hợp lệ hoặc đã hết hạn.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    google_id = str(claims.get("sub", "")).strip()
    email = str(claims.get("email", "")).strip().lower()
    if not google_id or not email or claims.get("email_verified") is not True:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tài khoản Google chưa cung cấp email đã xác minh.",
        )

    user = db.scalar(select(NguoiDung).where(NguoiDung.GoogleId == google_id))
    if user is None:
        user = db.scalar(select(NguoiDung).where(NguoiDung.Email == email))
        if user is not None and user.GoogleId not in (None, google_id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email này đã được liên kết với một tài khoản Google khác.",
            )

    full_name = str(claims.get("name") or email.split("@", 1)[0]).strip()
    picture = str(claims.get("picture") or "").strip() or None
    if user is None:
        username_base = "".join(
            character if character.isalnum() else "_"
            for character in email.split("@", 1)[0]
        ).strip("_")[:90] or "google_user"
        username = username_base
        suffix = 1
        while db.scalar(select(NguoiDung).where(NguoiDung.TenDangNhap == username)):
            username = f"{username_base[:(99 - len(str(suffix)))]}_{suffix}"
            suffix += 1
        user = NguoiDung(
            TenDangNhap=username,
            Email=email,
            HoTen=full_name,
            GoogleId=google_id,
            AnhDaiDien=picture,
            MatKhauHash=hash_password(secrets.token_urlsafe(32)),
            VaiTro=VaiTroNguoiDung.FARMER,
            IsVerified=True,
        )
        db.add(user)
    else:
        user.GoogleId = google_id
        user.HoTen = full_name
        user.AnhDaiDien = picture or user.AnhDaiDien
        user.IsVerified = True
        if not user.TenDangNhap:
            user.TenDangNhap = full_name

    try:
        db.commit()
        db.refresh(user)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Không thể liên kết tài khoản Google với dữ liệu hiện tại.",
        ) from exc

    return {
        "status": "ok",
        "message": "Đăng nhập Google thành công.",
        "data": {
            "access_token": create_access_token(user, expires_minutes=7 * 24 * 60),
            "token_type": "bearer",
            "user": _serialize_user(user),
        },
    }


def _serialize_user(user: NguoiDung) -> dict[str, object]:
    return {
        "ma_nguoi_dung": user.MaNguoiDung,
        "ten_dang_nhap": user.TenDangNhap,
        "email": user.Email,
        "ho_ten": user.HoTen or user.TenDangNhap,
        "anh_dai_dien": user.AnhDaiDien,
        "google_id": user.GoogleId,
        "vai_tro": user.VaiTro.value,
        "is_verified": user.IsVerified,
    }
