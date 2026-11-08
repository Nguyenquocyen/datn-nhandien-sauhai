"""Adapter kết nối Google Gemini cho chatbot Strict RAG."""

from __future__ import annotations

import os
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - dependency is optional at import time
    load_dotenv = None

if load_dotenv is not None:
    load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=True)


class GeminiLLMAdapter:
    """Gọi Gemini với system instruction và trả về các text chunk."""

    def __init__(
        self,
        model_name: str | None = None,
        api_key: str | None = None,
    ) -> None:
        self.model_name = model_name or os.getenv(
            "GEMINI_MODEL", "gemini-1.5-flash"
        )
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self._model: Any | None = None

    def stream_response(
        self,
        system_prompt: str,
        user_message: str,
        chat_history: Iterable[Mapping[str, str]] | None = None,
    ) -> Iterable[str]:
        """Stream từng đoạn text từ Gemini.

        SSE được đóng gói ở router để giữ một đầu mối giao thức HTTP:
        ``data: {"type":"delta","text":"..."}``.
        """
        model = self._get_model(system_prompt)
        history = self._build_history(chat_history)
        chat = model.start_chat(history=history)
        try:
            response_stream = chat.send_message(user_message, stream=True)
            for response in response_stream:
                text = getattr(response, "text", "")
                if text:
                    yield text
        except Exception as exc:
            raise RuntimeError("Gemini không thể tạo phản hồi streaming.") from exc

    def _get_model(self, system_prompt: str) -> Any:
        if not self.api_key:
            raise RuntimeError(
                "Thiếu GEMINI_API_KEY. Hãy cấu hình API key trong file .env."
            )
        try:
            import google.generativeai as genai
        except ImportError as exc:
            raise RuntimeError(
                "Chưa cài google-generativeai. Hãy chạy: "
                "pip install google-generativeai"
            ) from exc

        genai.configure(api_key=self.api_key)
        self._model = genai.GenerativeModel(
            model_name=self.model_name,
            system_instruction=system_prompt,
        )
        return self._model

    @staticmethod
    def _build_history(
        chat_history: Iterable[Mapping[str, str]] | None,
    ) -> list[dict[str, str]]:
        history: list[dict[str, str]] = []
        if chat_history is None:
            return history
        for item in chat_history:
            role = item.get("role")
            content = item.get("content", "")
            if role not in {"user", "assistant"} or not content:
                continue
            history.append(
                {
                    "role": "model" if role == "assistant" else "user",
                    "parts": content,
                }
            )
        return history[-10:]
