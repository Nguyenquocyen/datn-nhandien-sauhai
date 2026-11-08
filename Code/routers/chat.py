"""API chatbot RAG."""

from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import LuongChat, NguoiDung, TinNhanChat, VaiTroTinNhan
from ..services.chat_service import ChatbotRAGService

router = APIRouter(tags=["chat"])
_chat_service = ChatbotRAGService()
logger = logging.getLogger(__name__)


class CreateChatRequest(BaseModel):
    """Thông tin tối thiểu để tạo một luồng chat mới."""

    ma_nguoi_dung: int = Field(default=1, gt=0)
    ten_luong: str = Field(default="Luồng chat mới", min_length=1, max_length=255)


class ChatRequest(BaseModel):
    ma_luong: int = Field(gt=0)
    ma_phien_context: int | None = Field(default=None, gt=0)
    noi_dung: str = Field(min_length=1)


@router.post("/api/chat/threads", status_code=201)
def create_chat_thread(
    payload: CreateChatRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Tạo luồng chat để giao diện có mã hợp lệ trước khi gửi tin nhắn."""
    user = db.get(NguoiDung, payload.ma_nguoi_dung)
    if user is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy người dùng.")

    thread = LuongChat(
        MaNguoiDung=user.MaNguoiDung,
        TenLuong=payload.ten_luong.strip(),
    )
    db.add(thread)
    try:
        db.commit()
        db.refresh(thread)
    except Exception as exc:
        db.rollback()
        logger.exception("Không thể tạo luồng chat.")
        raise HTTPException(status_code=500, detail="Không thể tạo luồng chat.") from exc

    return {
        "status": "ok",
        "message": "Tạo luồng chat thành công",
        "data": {"ma_luong": thread.MaLuong, "ten_luong": thread.TenLuong},
    }


@router.post("/api/chat")
def chat(
    payload: ChatRequest, db: Session = Depends(get_db)
) -> StreamingResponse:
    """Lưu tin nhắn và trả phản hồi chatbot theo Server-Sent Events."""
    luong = db.get(LuongChat, payload.ma_luong)
    if luong is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy luồng chat.")

    try:
        user_message = TinNhanChat(
            MaLuong=payload.ma_luong,
            MaPhien_Context=payload.ma_phien_context,
            VaiTro=VaiTroTinNhan.USER,
            NoiDung=payload.noi_dung,
        )
        db.add(user_message)
        db.commit()
        db.refresh(user_message)
        context = _chat_service.build_context(
            payload.ma_phien_context,
            db,
            payload.noi_dung,
        )
        history = [
            {"role": "user", "content": item.NoiDung}
            for item in luong.tin_nhan[-10:]
            if item.MaTinNhan != user_message.MaTinNhan
        ]
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        db.rollback()
        logger.exception("Không thể chuẩn bị tin nhắn chat.")
        raise HTTPException(status_code=500, detail="Không thể xử lý tin nhắn.") from exc

    def event_stream():
        chunks: list[str] = []
        try:
            yield _sse("thought", "Đang truy vấn dữ liệu và tạo câu trả lời...")
            for chunk in _chat_service.generate_streaming_response(
                payload.noi_dung, context, history
            ):
                chunks.append(chunk)
                yield _sse("delta", chunk)

            bot_message = TinNhanChat(
                MaLuong=payload.ma_luong,
                MaPhien_Context=payload.ma_phien_context,
                VaiTro=VaiTroTinNhan.AI,
                NoiDung="".join(chunks),
            )
            db.add(bot_message)
            db.commit()
            yield _sse("thought", "Hoàn tất")
            yield "data: [DONE]\n\n"
        except Exception as exc:
            db.rollback()
            logger.exception("Lỗi trong luồng streaming chat.")
            yield _sse("error", str(exc))
            yield "data: [DONE]\n\n"
        finally:
            db.close()

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


def _sse(event_type: str, content: str) -> str:
    if event_type == "delta":
        payload = {"type": event_type, "text": content}
    else:
        payload = {"type": event_type, "content": content}
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
