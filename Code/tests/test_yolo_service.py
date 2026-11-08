"""Kiểm thử tích hợp YoloService với mô hình YOLO và CUDA."""

from __future__ import annotations

import io
import shutil
import sys
from pathlib import Path
from collections.abc import Iterator

import pytest
from PIL import Image

# Cho phép giữ đúng import ``services.yolo_service`` khi chạy pytest từ
# thư mục gốc Code1 hoặc trực tiếp từ thư mục Code.
CODE_DIR = Path(__file__).resolve().parents[1]
if str(CODE_DIR) not in sys.path:
    sys.path.insert(0, str(CODE_DIR))

from services.yolo_service import YoloService


@pytest.fixture(scope="module")
def yolo_service() -> Iterator[YoloService]:
    """Khởi tạo YoloService một lần cho toàn bộ test module."""
    # Service trả đường dẫn tương đối theo project_root, vì vậy thư mục test
    # phải nằm cùng project root thay vì nằm trong thư mục Temp của Windows.
    results_dir = CODE_DIR / "tests" / ".tmp_yolo_results"
    results_dir.mkdir(parents=True, exist_ok=True)
    try:
        yield YoloService(results_dir=results_dir)
    finally:
        shutil.rmtree(results_dir, ignore_errors=True)


def test_yolo_service_loads_model_on_cuda(yolo_service: YoloService) -> None:
    """Đảm bảo service chọn CUDA và model thực sự có tham số trên GPU."""
    assert yolo_service.device == "cuda", (
        "YoloService không chạy trên CUDA. Hãy kiểm tra driver NVIDIA "
        "và bản PyTorch CUDA."
    )

    # Ultralytics lưu mạng PyTorch trong thuộc tính model.model. Kiểm tra
    # tham số đầu tiên để xác nhận model đã được chuyển vào thiết bị CUDA.
    model_parameters = list(yolo_service.model.model.parameters())
    assert model_parameters, "Mô hình YOLO không có tham số để kiểm tra thiết bị."
    assert model_parameters[0].device.type == "cuda"


def test_predict_accepts_in_memory_jpeg(
    yolo_service: YoloService,
) -> None:
    """Kiểm tra predict với ảnh JPEG tạo trực tiếp trong bộ nhớ."""
    image = Image.new("RGB", (128, 128), color=(80, 160, 80))
    image_buffer = io.BytesIO()
    image.save(image_buffer, format="JPEG")

    result = yolo_service.predict(image_buffer.getvalue())

    assert isinstance(result, dict)
    assert {
        "đường_dẫn_ảnh_kết_quả",
        "danh_sách_đối_tượng",
        "tổng_số_lượng_phát_hiện",
        "số_lượng_theo_lớp",
    }.issubset(result)
