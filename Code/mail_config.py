"""Cấu hình Gmail SMTP và gửi OTP xác thực tài khoản."""

from __future__ import annotations

import os

from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType


def _required_setting(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Thiếu cấu hình SMTP bắt buộc: {name}.")
    return value


def build_mail_config() -> ConnectionConfig:
    return ConnectionConfig(
        MAIL_USERNAME=_required_setting("MAIL_USERNAME"),
        MAIL_PASSWORD=_required_setting("MAIL_PASSWORD"),
        MAIL_FROM=os.getenv("MAIL_FROM", os.getenv("MAIL_USERNAME", "")),
        MAIL_PORT=int(os.getenv("MAIL_PORT", "587")),
        MAIL_SERVER=os.getenv("MAIL_SERVER", "smtp.gmail.com"),
        MAIL_STARTTLS=os.getenv("MAIL_STARTTLS", "true").lower() == "true",
        MAIL_SSL_TLS=os.getenv("MAIL_SSL_TLS", "false").lower() == "true",
        USE_CREDENTIALS=True,
        VALIDATE_CERTS=True,
    )


async def send_otp_email(recipient: str, otp: str) -> None:
    message = MessageSchema(
        subject="Mã OTP xác thực tài khoản RICE PEST AI",
        recipients=[recipient],
        body=(
            "Mã OTP xác thực tài khoản của bạn là: "
            f"{otp}\nMã có hiệu lực trong 5 phút."
        ),
        subtype=MessageType.plain,
    )
    await FastMail(build_mail_config()).send_message(message)
