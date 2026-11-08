"""Strict RAG chatbot service backed by the MySQL knowledge base."""

from __future__ import annotations

import json
from collections.abc import Callable, Iterable, Mapping
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..models import (
    GiaiPhapSinhHoc,
    PhienPhanTich,
    SauHai,
    SauHaiGiaiPhap,
)
from .llm_service import GeminiLLMAdapter


class ChatbotRAGService:
    """Builds database-grounded context and streams a Hybrid RAG response."""

    FALLBACK_MESSAGE = "Tôi không có thông tin này trong cơ sở dữ liệu"
    OUT_OF_SCOPE_CONTEXT = "__OUT_OF_SCOPE__"
    ALLOWED_KEYWORDS = (
        "lúa",
        "lua",
        "ruộng",
        "ruong",
        "nông nghiệp",
        "nong nghiep",
        "sâu",
        "sau",
        "bệnh",
        "benh",
        "rầy",
        "ray",
        "bọ",
        "bo",
        "đạo ôn",
        "dao on",
        "cây trồng",
        "cay trong",
        # Cho phép hỏi trực tiếp bằng nhãn lớp YOLO mà frontend đã nhận diện.
        "rice_leaf_roller",
        "brown_planthopper",
        "yellow_rice_borer",
        "asiatic_rice_borer",
        "rice_leaf_caterpillar",
        "rice_shell_pest",
        "rice_gall_midge",
        "grain_spreader_thrips",
        "rice_stem_maggot",
    )
    SYSTEM_PROMPT_TEMPLATE = (
        "Bạn là một Trợ lý Nông nghiệp AI chuyên gia về cây lúa.\n"
        "Nhiệm vụ chính: Trả lời các câu hỏi về sâu hại lúa, phương pháp "
        "canh tác và giải pháp phòng trừ.\n"
        "Quy tắc trả lời:\n"
        "- Luôn ƯU TIÊN sử dụng thông tin từ Context (Dữ liệu truy xuất "
        "từ Database) nếu có.\n"
        "- Nếu Context không chứa thông tin trực tiếp, BẠN ĐƯỢC PHÉP sử "
        "dụng kiến thức chuyên môn nông nghiệp sẵn có của mình để tư vấn, "
        "giải thích và mở rộng câu trả lời.\n"
        "- Tuyệt đối không được trả lời 'Tôi không có thông tin' nếu câu "
        "hỏi liên quan đến lúa và sâu hại lúa.\n"
        "- Khi tư vấn thuốc bảo vệ thực vật, luôn nhắc người dùng tuân thủ "
        "nhãn thuốc, liều lượng được phép, thời gian cách ly và quy định "
        "an toàn địa phương.\n\n"
        "Context từ cơ sở dữ liệu:\n{context}"
    )

    def __init__(
        self,
        llm_client: Callable[..., str | Iterable[str]] | None = None,
    ) -> None:
        self.llm_client = llm_client
        self._gemini_adapter: GeminiLLMAdapter | None = None
        self.last_system_prompt: str | None = None

    def build_context(
        self,
        ma_phien: int | None,
        db_session: Session,
        user_message: str | None = None,
    ) -> str:
        """JOIN phiên, sâu hại và giải pháp để tạo Context JSON."""
        if user_message is not None and not self.is_in_scope(user_message):
            return self.OUT_OF_SCOPE_CONTEXT

        if ma_phien is None:
            if not user_message or not user_message.strip():
                return self.FALLBACK_MESSAGE
            rows = self._search_knowledge_base(db_session, user_message)
            if not rows:
                return self.FALLBACK_MESSAGE
            return self._serialize_rows(
                {"che_do": "chat_doc_lap", "du_lieu_kien_thuc": rows}
            )

        if not isinstance(ma_phien, int) or ma_phien <= 0:
            raise ValueError("ma_phien phải là số nguyên dương hoặc None.")
        phien = db_session.get(PhienPhanTich, ma_phien)
        if phien is None:
            return self.FALLBACK_MESSAGE

        ai_result = phien.KetQuaAI_JSON or {}
        detected_objects = ai_result.get("danh_sách_đối_tượng") or []
        detected_names = {
            name
            for item in detected_objects
            if isinstance(item, Mapping)
            for name in (
                item.get("ma_lop_yolo"),
                item.get("tên"),
            )
            if isinstance(name, str) and name.strip()
        }
        detected_names.discard(None)
        rows = self._knowledge_rows(db_session, detected_names)
        context = {
            "ma_phien": phien.MaPhien,
            "ket_qua_yolo": ai_result,
            "ket_qua_dss": phien.KetQuaDSS_JSON,
            "du_lieu_sau_hai_va_giai_phap": rows,
        }
        if not phien.KetQuaAI_JSON and not phien.KetQuaDSS_JSON and not rows:
            return self.FALLBACK_MESSAGE
        return self._serialize_rows(context)

    def generate_streaming_response(
        self,
        user_message: str,
        context: str,
        chat_history: Iterable[Mapping[str, Any]] | None = None,
    ) -> Iterable[str]:
        """Chặn ngoài phạm vi trước, sau đó mới gọi Gemini."""
        if not isinstance(user_message, str) or not user_message.strip():
            raise ValueError("user_message không được để trống.")
        if not self.is_in_scope(user_message):
            yield self.FALLBACK_MESSAGE
            return
        if context == self.OUT_OF_SCOPE_CONTEXT:
            yield self.FALLBACK_MESSAGE
            return
        if not isinstance(context, str) or not context.strip():
            raise ValueError("context không được để trống.")

        history = self._normalize_history(chat_history)
        system_prompt = self.SYSTEM_PROMPT_TEMPLATE.format(context=context)
        self.last_system_prompt = system_prompt
        try:
            response = self._call_llm(system_prompt, user_message.strip(), history)
            if isinstance(response, str):
                if not response.strip():
                    raise RuntimeError("LLM trả về câu trả lời rỗng.")
                yield response
                return
            yielded = False
            for chunk in response:
                if not isinstance(chunk, str):
                    raise RuntimeError("LLM trả về chunk không phải chuỗi.")
                if chunk:
                    yielded = True
                    yield chunk
            if not yielded:
                raise RuntimeError("LLM không trả về dữ liệu streaming.")
        except RuntimeError:
            raise
        except Exception as exc:
            raise RuntimeError("LLM không thể tạo câu trả lời streaming.") from exc

    def generate_response(self, user_message: str, context: str) -> str:
        return "".join(self.generate_streaming_response(user_message, context, []))

    @classmethod
    def is_in_scope(cls, user_message: str) -> bool:
        normalized = user_message.casefold()
        return any(keyword in normalized for keyword in cls.ALLOWED_KEYWORDS)

    def _knowledge_rows(
        self, db_session: Session, class_names: set[Any]
    ) -> list[dict[str, Any]]:
        if not class_names:
            return []
        statement = (
            select(SauHai, SauHaiGiaiPhap, GiaiPhapSinhHoc)
            .outerjoin(
                SauHaiGiaiPhap,
                SauHaiGiaiPhap.MaSauHai == SauHai.MaSauHai,
            )
            .outerjoin(
                GiaiPhapSinhHoc,
                GiaiPhapSinhHoc.MaGiaiPhap == SauHaiGiaiPhap.MaGiaiPhap,
            )
            .where(SauHai.MaLopYOLO.in_(class_names))
        )
        return [self._row_to_dict(sau_hai, link, solution) for sau_hai, link, solution in db_session.execute(statement)]

    def _search_knowledge_base(
        self, db_session: Session, user_message: str
    ) -> list[dict[str, Any]]:
        terms = [term for term in user_message.split() if len(term) >= 3]
        if not terms:
            return []
        conditions = []
        for term in terms:
            pattern = f"%{term}%"
            conditions.extend(
                (
                    SauHai.MaLopYOLO.ilike(pattern),
                    SauHai.TenTiengViet.ilike(pattern),
                    SauHai.TenKhoaHoc.ilike(pattern),
                    SauHai.VongDoi.ilike(pattern),
                    SauHai.TrieuChungGayHai.ilike(pattern),
                )
            )
        statement = (
            select(SauHai, SauHaiGiaiPhap, GiaiPhapSinhHoc)
            .outerjoin(SauHaiGiaiPhap, SauHaiGiaiPhap.MaSauHai == SauHai.MaSauHai)
            .outerjoin(
                GiaiPhapSinhHoc,
                GiaiPhapSinhHoc.MaGiaiPhap == SauHaiGiaiPhap.MaGiaiPhap,
            )
            .where(or_(*conditions))
            .limit(20)
        )
        return [self._row_to_dict(sau_hai, link, solution) for sau_hai, link, solution in db_session.execute(statement)]

    @staticmethod
    def _row_to_dict(
        sau_hai: SauHai,
        link: SauHaiGiaiPhap | None,
        solution: GiaiPhapSinhHoc | None,
    ) -> dict[str, Any]:
        return {
            "ma_lop_yolo": sau_hai.MaLopYOLO,
            "ten_tieng_viet": sau_hai.TenTiengViet,
            "ten_khoa_hoc": sau_hai.TenKhoaHoc,
            "vong_doi": sau_hai.VongDoi,
            "trieu_chung_gay_hai": sau_hai.TrieuChungGayHai,
            "vung_phan_bo": sau_hai.VungPhanBo_JSON,
            "cay_trong_bi_hai": sau_hai.CayTrongBiHai_JSON,
            "giai_phap": (
                {
                    "ten": solution.TenGiaiPhap,
                    "phuong_phap": solution.PhuongPhapApDung,
                    "chi_phi_moi_hecta": solution.ChiPhiMoiHecta,
                    "so_ngay_hieu_qua": solution.SoNgayHieuQua,
                    "diem_an_toan_moi_truong": solution.DiemAnToanMoiTruong,
                    "diem_hieu_qua": link.DiemHieuQua if link else None,
                }
                if solution
                else None
            ),
        }

    @staticmethod
    def _serialize_rows(value: Mapping[str, Any]) -> str:
        return json.dumps(value, ensure_ascii=False, default=str, indent=2)

    def _call_llm(
        self, system_prompt: str, user_message: str, chat_history: list[dict[str, str]]
    ) -> str | Iterable[str]:
        if self.llm_client is None:
            if self._gemini_adapter is None:
                self._gemini_adapter = GeminiLLMAdapter()
            return self._gemini_adapter.stream_response(
                system_prompt, user_message, chat_history
            )
        try:
            return self.llm_client(system_prompt, user_message, chat_history)
        except TypeError:
            return self.llm_client(system_prompt, user_message)

    @staticmethod
    def _normalize_history(
        chat_history: Iterable[Mapping[str, Any]] | None,
    ) -> list[dict[str, str]]:
        if chat_history is None:
            return []
        history = []
        for item in chat_history:
            role = item.get("role")
            content = item.get("content", item.get("text"))
            if role in {"user", "assistant"} and isinstance(content, str):
                history.append({"role": role, "content": content})
        return history[-10:]
