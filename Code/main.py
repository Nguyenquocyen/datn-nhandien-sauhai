"""Điểm khởi chạy FastAPI của RICE PEST AI."""

import sys
from pathlib import Path
from typing import Any

# Cho phép chạy trực tiếp từ thư mục Code bằng:
# python -m uvicorn main:app --reload
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    __package__ = "Code"

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import inspect, text

from .routers.analyze import router as analyze_router
from .routers.auth import router as auth_router
from .routers.chat import router as chat_router
from .routers.history import router as history_router
from . import models
from .database import engine
from .database import SessionLocal
from .seed_data import seed_ahp_scores

app = FastAPI(title="RICE PEST AI", version="1.0.0")

PROJECT_ROOT = Path(__file__).resolve().parent
STATIC_DIR = PROJECT_ROOT / "static"
TEMPLATES_DIR = PROJECT_ROOT / "templates"

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analyze_router)
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(history_router)


@app.on_event("startup")
def initialize_database() -> None:
    """Tạo bảng và bổ sung cột AHP/metadata cho database đã tồn tại."""
    models.Base.metadata.create_all(bind=engine)
    existing_columns = {
        column["name"] for column in inspect(engine).get_columns("GiaiPhapSinhHoc")
    }
    score_columns = {
        "score_mat_do": "FLOAT",
        "score_chi_phi": "FLOAT",
        "score_thoi_gian": "FLOAT",
        "score_an_toan": "FLOAT",
        "mo_ta": "TEXT",
        "cach_su_dung": "TEXT",
        "luu_y_khi_dung": "TEXT",
        "co_so_khoa_hoc": "TEXT",
    }
    pest_columns = {
        "DacDiemHinhThai": "TEXT",
        "CachThucGayHai": "TEXT",
        "MucDoGayHai": "TEXT",
    }
    history_columns = {
        "MatDo": "FLOAT NOT NULL DEFAULT 1.0",
        "DiemHieuQua": "FLOAT NOT NULL DEFAULT 0.0",
        "NguonTrichDan": "VARCHAR(1000) NULL",
        "GhiChuTrichDan": "TEXT NULL",
    }
    existing_pest_columns = {
        column["name"] for column in inspect(engine).get_columns("SauHai")
    }
    existing_history_columns = {
        column["name"] for column in inspect(engine).get_columns("LichSuCanhTac")
    }
    with engine.begin() as connection:
        for column_name, column_type in score_columns.items():
            if column_name not in existing_columns:
                connection.execute(
                    text(
                        f"ALTER TABLE `GiaiPhapSinhHoc` "
                        f"ADD COLUMN `{column_name}` {column_type} NULL"
                    )
                )
        for column_name, column_type in pest_columns.items():
            if column_name not in existing_pest_columns:
                connection.execute(
                    text(
                        f"ALTER TABLE `SauHai` "
                        f"ADD COLUMN `{column_name}` {column_type} NULL"
                    )
                )
        for column_name, column_type in history_columns.items():
            if column_name not in existing_history_columns:
                connection.execute(
                    text(
                        f"ALTER TABLE `LichSuCanhTac` "
                        f"ADD COLUMN `{column_name}` {column_type}"
                    )
                )
    with SessionLocal() as session:
        seed_ahp_scores(session)


@app.get("/", tags=["frontend"])
def dashboard(request: Request):
    """Render giao diện dashboard tích hợp trong FastAPI."""
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={"request": request},
    )


@app.get("/history", name="history_page", tags=["frontend"])
def history(request: Request):
    """Render nhật ký quét AI."""
    return templates.TemplateResponse(
        request=request,
        name="history.html",
        context={"request": request},
    )


@app.get("/dictionary", tags=["frontend"])
def dictionary(request: Request):
    """Render từ điển sâu hại."""
    return templates.TemplateResponse(
        request=request,
        name="dictionary.html",
        context={"request": request},
    )


@app.get("/login", tags=["frontend"])
def login_page(request: Request):
    """Render trang đăng nhập độc lập."""
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"request": request},
    )


@app.get("/health", tags=["system"])
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "message": "Backend đang hoạt động",
        "data": {"service": "rice-pest-ai"},
    }
