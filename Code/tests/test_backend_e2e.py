"""E2E tests for the real MySQL knowledge base.

These tests intentionally use ``SessionLocal`` and do not mock the database.
Run them from the project root after MySQL and the seed data are available.
"""

from __future__ import annotations

import pytest
from sqlalchemy import select

from Code.database import SessionLocal
from Code.models import (
    CauHinhDSS,
    GiaiPhapSinhHoc,
    LichSuCanhTac,
    SauHai,
    SauHaiGiaiPhap,
)
from Code.services.chat_service import ChatbotRAGService
from Code.services.dss_service import DSSService
from Code.services.yolo_service import YoloService


@pytest.fixture()
def db_session():
    with SessionLocal() as session:
        yield session


def test_yolo_labels_map_to_seeded_database_labels(db_session):
    expected = {
        "0": "rice_leaf_roller",
        "8": "brown_planthopper",
        "4": "yellow_rice_borer",
        "brown_plant_hopper": "brown_planthopper",
        "Cnaphalocrocis medinalis": "rice_leaf_roller",
    }

    for raw_label, database_label in expected.items():
        normalized = YoloService.normalize_yolo_label(raw_label)
        assert normalized == database_label
        assert db_session.scalar(
            select(SauHai).where(SauHai.MaLopYOLO == normalized)
        ) is not None


def test_ahp_calculates_density_and_ranks_brown_planthopper_solutions(db_session):
    config = db_session.get(CauHinhDSS, 1)
    assert config is not None, "Thiếu cấu hình AHP trong bảng CauHinhDSS."

    pest = db_session.scalar(
        select(SauHai).where(SauHai.MaLopYOLO == "brown_planthopper")
    )
    assert pest is not None, "Thiếu dữ liệu rầy nâu trong bảng SauHai."

    solutions = db_session.scalars(
        select(GiaiPhapSinhHoc)
        .join(SauHaiGiaiPhap)
        .where(SauHaiGiaiPhap.MaSauHai == pest.MaSauHai)
    ).all()
    result = DSSService().calculate_ahp_ranking(
        config.MaTranSoSanh_JSON,
        solutions,
        total_bounding_boxes=5,
        quy_mo_dien_tich=0.5,
    )

    assert result["mat_do"] == pytest.approx(10.0)
    assert result["severity"] == "Nặng"
    assert result["consistency_ratio"] <= 0.1

    metarhizium = next(
        item
        for item in result["xep_hang"]
        if "Metarhizium" in item["ten_giai_phap"]
    )
    assert metarhizium["xep_hang"] <= 2, (
        "Dữ liệu/cấu hình AHP hiện tại xếp Nấm xanh ngoài Top 2; "
        f"hạng thực tế: {metarhizium['xep_hang']}."
    )


def test_knn_retrieves_similar_real_cultivation_cases(db_session):
    historical_data = db_session.scalars(select(LichSuCanhTac)).all()
    assert historical_data, "Bảng LichSuCanhTac chưa có dữ liệu seed."

    results = DSSService().find_similar_cases(
        {
            "GiaiDoanLua": "de_nhanh",
            "MuaVu": "dong_xuan",
            "VungMien": "dbscl",
            "NhietDo": 28,
            "DoAm": 85,
        },
        historical_data,
        top_k=5,
    )

    assert len(results) == 5
    assert all("ma_lich_su" in result for result in results)
    assert all("khoang_cach" in result for result in results)


def test_strict_rag_reads_database_and_blocks_out_of_scope_questions(db_session):
    service = ChatbotRAGService()

    context = service.build_context(
        None,
        db_session,
        "Rầy nâu nên dùng Nấm xanh Metarhizium như thế nào?",
    )
    assert context != service.FALLBACK_MESSAGE
    assert "Rầy nâu" in context
    assert "Metarhizium" in context

    out_of_scope_context = service.build_context(
        None,
        db_session,
        "cách nấu phở bò",
    )
    assert out_of_scope_context == service.OUT_OF_SCOPE_CONTEXT
    assert list(
        service.generate_streaming_response(
            "cách nấu phở bò",
            out_of_scope_context,
        )
    ) == [service.FALLBACK_MESSAGE]
