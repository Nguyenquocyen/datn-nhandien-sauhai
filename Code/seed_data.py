"""Idempotent seed for the user-provided rice-pest reference data.

Run from the project root with: ``python -m Code.seed_data``
Run from this directory with: ``python -m seed_data``
Set ``SEED_DEMO_PASSWORD`` in ``Code/.env`` to override the demo password.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import bcrypt
from dotenv import load_dotenv
from sqlalchemy import select
from sqlalchemy.orm import Session

# Support both ``python -m Code.seed_data`` from the project root and
# ``python -m seed_data`` (or ``python seed_data.py``) from Code.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from Code.database import SessionLocal
    from Code.models import (
        CauHinhDSS,
        GiaiDoanLua,
        GiaiPhapSinhHoc,
        KetQuaCanhTac,
        LichSuCanhTac,
        MuaVu,
        NguoiDung,
        SauHai,
        SauHaiGiaiPhap,
        VaiTroNguoiDung,
        VungMien,
    )
else:
    from .database import SessionLocal
    from .models import (
        CauHinhDSS,
        GiaiDoanLua,
        GiaiPhapSinhHoc,
        KetQuaCanhTac,
        LichSuCanhTac,
        MuaVu,
        NguoiDung,
        SauHai,
        SauHaiGiaiPhap,
        VaiTroNguoiDung,
        VungMien,
    )

load_dotenv(Path(__file__).resolve().parent / ".env", override=False)

PESTS = [
    ("rice_leaf_roller", "Sâu cuốn lá nhỏ", "Cnaphalocrocis medinalis", "18-25 ngày (Trứng: 3-5 ngày; Sâu non 5 tuổi: 10-14 ngày; Nhộng: 5-7 ngày)", "Sâu non nhả tơ cuốn dọc lá lúa thành ống, ăn phần nhu mô xanh chỉ chừa lại lớp biểu bì trắng bạc làm giảm diện tích quang hợp, lúa lép hạt. Gây hại mạnh giai đoạn đẻ nhánh đến đón đòng. [Nguồn: Nông Nghiệp SOFa (2025); Nông Nghiệp AVN (2023)]", ["ĐBSCL", "Đồng bằng sông Hồng", "Duyên hải miền Trung"], ["Lúa", "Ngô", "Cỏ hòa bản"]),
    ("brown_planthopper", "Rầy nâu", "Nilaparvata lugens", "25-30 ngày (Trứng đẻ thành ổ trong bẹ lá nở sau 7-10 ngày; Rầy non 5 tuổi: 12-15 ngày)", "Tập trung ở gốc lúa chích hút nhựa làm cây lúa khô héo màu nâu (cháy rầy từng chòm hoặc cả ruộng), đồng thời truyền virus bệnh lùn sọc đen và vàng lùn - lùn xoắn lá. Ngưỡng nguy hại cao khi mật số > 20 con/tép. [Nguồn: TT Khuyến nông Bắc Giang & Viện Lúa ĐBSCL (2022); SOFa (2025)]", ["ĐBSCL", "Đông Nam Bộ", "Đồng bằng sông Hồng"], ["Lúa"]),
    ("yellow_rice_borer", "Sâu đục thân bướm 2 chấm", "Scirpophaga incertulas", "35-40 ngày (Trứng đẻ thành ổ có phủ lông vàng nhạt nở sau 5-7 ngày; Sâu non 5 tuổi: 25-30 ngày)", "Sâu non đục vào trong thân lúa cắn đứt mạch dẫn chất dinh dưỡng. Giai đoạn lúa đẻ nhánh gây dảnh héo; giai đoạn làm đòng - trổ gây bông bạc trắng. [Nguồn: Nông Nghiệp SOFa (2025)]", ["ĐBSCL", "Đồng bằng sông Hồng", "Bắc Trung Bộ"], ["Lúa"]),
    ("asiatic_rice_borer", "Sâu đục thân 5 vạch", "Chilo suppressalis", "35-40 ngày (Trứng: 5-7 ngày; Sâu non đục thân: 25-30 ngày; Nhộng hóa trong gốc thân lúa)", "Sâu non đục rỗng thân lúa, làm khô héo lá non trung tâm và tạo bông bạc khi lúa trổ. [Nguồn: Nông Nghiệp SOFa (2025)]", ["Đồng bằng sông Hồng", "Trung du miền núi phía Bắc", "ĐBSCL"], ["Lúa", "Ngô", "Mía"]),
    ("rice_leaf_caterpillar", "Sâu cuốn lá lớn", "Marasmia patnalis / Parnara guttata", "Khoảng 20 ngày (Trứng đẻ mặt dưới lá; Sâu non 12-15 ngày, hóa nhộng trong bao lá cuốn)", "Sâu non cuốn gập nhiều lá lúa thành bao lớn và cắn khuyết phiến lá, gây hại mạnh ở giai đoạn đẻ nhánh. [Nguồn: Nông Nghiệp SOFa (2025)]", ["ĐBSCL", "Đồng bằng sông Hồng"], ["Lúa"]),
    ("rice_shell_pest", "Sâu phao", "Nymphula depunctalis", "25-30 ngày (Trứng trên lá gần mặt nước; Sâu non sống dưới nước 15-20 ngày)", "Xuất hiện ở ruộng ngập nước sâu, trũng. Sâu non cắt lá cuộn thành ống phao nổi và cắn khuyết lá lúa. [Nguồn: Nông Nghiệp SOFa (2025)]", ["ĐBSCL", "Đồng bằng sông Hồng"], ["Lúa"]),
    ("rice_gall_midge", "Muỗi hành (Sâu năng)", "Orseolia oryzae", "17-25 ngày, phát sinh 6-8 lứa/năm", "Dòi làm bẹ lá phình to giống cọng hành, cây lúa lùn, nhiều chồi vô hiệu và không trổ bông. [Nguồn: Nông Nghiệp SOFa (2025)]", ["ĐBSCL", "Đông Nam Bộ", "Duyên hải miền Trung"], ["Lúa", "Lúa hoang"]),
    ("grain_spreader_thrips", "Bọ trĩ (Bù lạch)", "Stenchaetothrips biformis", "10-16 ngày qua 5 giai đoạn", "Chích hút lá non giai đoạn mạ đến đẻ nhánh làm lá có chấm trắng, cuộn mép và khô vàng. [Nguồn: Nông Nghiệp AVN (2023)]", ["ĐBSCL", "Đồng bằng sông Hồng", "Miền Trung"], ["Lúa"]),
    ("rice_stem_maggot", "Nhện gié hại lúa", "Steneotarsonemus spinki", "7-14 ngày, bộc phát trong thời tiết khô nóng, ruộng sạ dày, thừa đạm", "Sống trong bẹ lá tạo vệt thâm nâu đen; hút nhựa đòng làm bông cong vẹo, hạt lép lửng thâm đen. [Nguồn: Nông Nghiệp AVN (2023)]", ["ĐBSCL", "Đông Nam Bộ"], ["Lúa"]),
]

PEST_DETAILS = {
    "rice_leaf_roller": ("Bướm nhỏ màu vàng nâu; sâu non màu xanh đến xanh vàng, đầu nâu, nhả tơ cuốn lá.", "Sâu non cuốn lá rồi cạo nhu mô xanh; lá bạc trắng, giảm quang hợp.", "Trung bình đến nặng khi mật độ cao, nhất là giai đoạn đẻ nhánh - làm đòng."),
    "brown_planthopper": ("Rầy trưởng thành màu nâu vàng, dạng cánh dài hoặc cánh ngắn; rầy non trắng kem đến nâu.", "Chích hút ở gốc và bẹ lá, gây cháy rầy và có thể truyền bệnh virus.", "Có thể rất nghiêm trọng ở ruộng sạ dày, thừa đạm hoặc mất thiên địch."),
    "yellow_rice_borer": ("Bướm màu vàng rơm; sâu non trắng ngà, đầu nâu, sống trong thân.", "Đục thân làm dảnh héo và gây bông bạc ở giai đoạn làm đòng - trổ.", "Nặng khi tỷ lệ dảnh héo hoặc bông bạc tăng; cần theo dõi ổ trứng."),
    "asiatic_rice_borer": ("Bướm vàng nâu có vạch sẫm; sâu non trắng ngà, đầu nâu.", "Đục mô thân, làm đứt mạch dẫn, héo dảnh hoặc bông bạc.", "Có thể gây thiệt hại đáng kể ở ruộng nhiều cỏ ký chủ và gốc rạ."),
    "rice_leaf_caterpillar": ("Sâu non màu xanh, đầu nâu; cuốn hoặc gập lá bằng tơ để trú ẩn.", "Cắn khuyết phiến lá, làm giảm diện tích lá xanh ở giai đoạn đẻ nhánh.", "Thường tăng cục bộ; cần đánh giá mật độ và tỷ lệ lá bị hại."),
    "rice_shell_pest": ("Sâu non xanh nhạt sống gần mặt nước, cắt lá làm ống phao.", "Cắt và ăn lá non dưới hoặc sát mặt nước, làm cây mạ sinh trưởng kém.", "Nặng hơn ở ruộng trũng, ngập sâu hoặc nhiều cỏ dại thủy sinh."),
    "rice_gall_midge": ("Con trưởng thành giống muỗi nhỏ; ấu trùng trắng sống trong bẹ làm bẹ phình dạng ống.", "Phá đỉnh sinh trưởng, tạo dảnh vô hiệu dạng cọng hành và làm cây không trổ.", "Có thể làm mất chồi và giảm năng suất khi phát sinh nhiều lứa."),
    "grain_spreader_thrips": ("Bọ trĩ rất nhỏ, thân vàng nâu đến nâu đen; con non nhạt màu, ẩn trong lá cuộn.", "Chích hút lá non, làm lá bạc, cuộn mép và khô vàng.", "Thường gây hại cục bộ giai đoạn mạ - đẻ nhánh, tăng khi nóng và khô."),
    "rice_stem_maggot": ("Nhện gié cực nhỏ, khó thấy bằng mắt thường; sống trong bẹ lá và vùng đòng.", "Chích hút mô bẹ và đòng, làm bông cong vẹo, hạt lép hoặc lửng.", "Tăng ở ruộng sạ dày, thừa đạm và thời tiết nóng khô."),
}

SOLUTIONS = [
    ("Chế phẩm nấm xanh Metarhizium anisopliae", "Pha 100g chế phẩm với 50 lít nước, phun chiều mát khi rầy/sâu tuổi 1-2. Hiệu lực diệt rầy 73.5%-91.5% sau 7 ngày theo Viện Lúa ĐBSCL.", 420000, 7, 9.5),
    ("Chế phẩm nấm trắng Beauveria bassiana", "Phun bào tử nấm trắng chiều mát khi sâu non tuổi 1-2; sâu ngừng ăn sau 2 ngày và chết phủ tơ trắng sau 5-7 ngày.", 400000, 6, 9.5),
    ("Chế phẩm vi khuẩn sinh học Bacillus thuringiensis (Bt)", "Phun Bt khi sâu non bộ Cánh vảy tuổi 1-2; tinh thể độc tố phá hủy hệ tiêu hóa và sâu chết sau 3-5 ngày.", 350000, 4, 9.5),
    ("Nhân nuôi và thả Ong ký sinh trứng (Trichogramma, Telenomus, Platygaster)", "Đặt thẻ trứng ong ký sinh trên ruộng khi bướm/muỗi trưởng thành ra rộ để làm ung ổ trứng sâu hại.", 300000, 8, 10.0),
    ("Bảo tồn thiên địch bắt mồi tự nhiên (Nhện sói Lycosa, Bọ xít mù xanh Cyrtorhinus, Kiến ba khoang)", "Không phun hóa học 40 ngày đầu sau sạ, kết hợp cây có hoa trên bờ ruộng để duy trì thiên địch.", 180000, 12, 10.0),
    ("Biện pháp Kỹ thuật Canh tác tổng hợp (IPM: Điều tiết nước, giảm giống, cân đối đạm, luân canh)", "Sạ thưa, bón N-P-K cân đối, điều tiết nước ngập-khô xen kẽ và luân canh cây họ đậu.", 150000, 14, 10.0),
    ("Bẫy đèn theo dõi và bắt bướm trưởng thành", "Dùng nguồn sáng thu hút một phần bướm trưởng thành của nhóm sâu đục thân và sâu cuốn lá để theo dõi cao điểm phát sinh.", 250000, 5, 9.0),
    ("Bẫy bả chua ngọt giám sát côn trùng trưởng thành", "Đặt bả trong chai hoặc khay có che mưa tại bờ ruộng để thu hút, theo dõi và giảm một phần côn trùng trưởng thành.", 120000, 5, 9.0),
    ("Chế phẩm thảo mộc tỏi - ớt", "Sử dụng chế phẩm đã đăng ký hoặc dịch chiết được khuyến cáo, phun thử trên diện tích nhỏ trước khi mở rộng.", 180000, 3, 8.0),
    ("Thả vịt trong ruộng theo giai đoạn phù hợp", "Thả vịt sau khi cây lúa đủ cứng và theo hướng dẫn địa phương để vịt ăn côn trùng, ốc và cỏ dại trên ruộng.", 280000, 6, 8.0),
    ("Chế phẩm Trichoderma cải thiện đất và vùng rễ", "Bón hoặc xử lý đất theo nhãn sản phẩm nhằm tăng hoạt tính vi sinh vật có ích và hỗ trợ sức khỏe bộ rễ.", 220000, 21, 9.0),
    ("Rút nước ruộng và vệ sinh ruộng đối với sâu phao", "Tháo nước tạm thời, vệ sinh cỏ dại và điều chỉnh mực nước theo giai đoạn lúa, tránh gây hạn hoặc ảnh hưởng cây.", 80000, 3, 9.0),
]

LINKS = [
    ("rice_leaf_roller", 3, 9.2), ("rice_leaf_roller", 2, 8.8), ("rice_leaf_roller", 4, 8.6), ("rice_leaf_roller", 6, 8.0),
    ("brown_planthopper", 1, 9.3), ("brown_planthopper", 5, 8.9), ("brown_planthopper", 6, 8.5),
    ("yellow_rice_borer", 4, 9.0), ("yellow_rice_borer", 3, 8.5), ("yellow_rice_borer", 2, 8.3),
    ("asiatic_rice_borer", 4, 8.9), ("asiatic_rice_borer", 3, 8.5), ("asiatic_rice_borer", 6, 8.2),
    ("rice_leaf_caterpillar", 3, 9.1), ("rice_leaf_caterpillar", 2, 8.7), ("rice_leaf_caterpillar", 5, 8.2),
    ("rice_shell_pest", 6, 9.1), ("rice_shell_pest", 3, 8.6),
    ("rice_gall_midge", 4, 8.9), ("rice_gall_midge", 5, 8.5), ("rice_gall_midge", 6, 8.4),
    ("grain_spreader_thrips", 6, 8.9), ("grain_spreader_thrips", 1, 8.6), ("grain_spreader_thrips", 5, 8.3),
    ("rice_stem_maggot", 6, 8.8), ("rice_stem_maggot", 1, 8.5), ("rice_stem_maggot", 5, 8.4),
    ("rice_leaf_roller", 7, 7.8), ("yellow_rice_borer", 7, 8.2), ("asiatic_rice_borer", 7, 8.2),
    ("rice_leaf_caterpillar", 7, 7.5), ("rice_gall_midge", 7, 7.0),
    ("rice_leaf_roller", 8, 7.0), ("brown_planthopper", 8, 6.8), ("grain_spreader_thrips", 8, 7.2),
    ("brown_planthopper", 9, 7.0), ("grain_spreader_thrips", 9, 7.5), ("rice_stem_maggot", 9, 6.5),
    ("brown_planthopper", 10, 7.2), ("rice_shell_pest", 10, 7.0), ("rice_gall_midge", 10, 6.8),
    ("rice_leaf_roller", 11, 6.5), ("rice_shell_pest", 11, 6.0), ("rice_stem_maggot", 11, 6.5),
    ("rice_shell_pest", 12, 8.8), ("brown_planthopper", 12, 7.0), ("rice_gall_midge", 12, 6.5),
]

SOURCE_URLS = {
    1: "http://www.khuyennongbacgiang.vn/ves-portal/210/Su-dung-nam-xanh-Metarhizium-anisopliae-tru-ray-nau.html",
    2: "https://nongnghiepsofa.com/cac-loai-sau-hai-tren-lua/",
    3: "https://khuyennongvn.gov.vn/portals/0/tailieu/2014/11/host/ttr22_dtuong_2012.pdf",
    4: "https://nongnghiepavn.com/bien-phap-phong-tru-sau-cuon-la-nho-hai-lua-trong-canh-tac-huu-co/",
    5: "https://sansangxuatkhau.ppd.gov.vn/FileUpload/Documents/181129_book_1_sach_hd2911_con_trungpdf.pdf",
}

# Locators are intentionally explicit about the heading/page and the scope of
# each supplied source; no unsupported page number is inferred for HTML pages.
CITATION_NOTES = {
    ("brown_planthopper", 1): 'Trích từ bài "Sử dụng nấm xanh Metarhizium anisopliae trừ rầy nâu" - Chi cục Bảo vệ thực vật Bắc Giang, đăng trên Cổng TTĐT Khuyến nông Bắc Giang; xem mục "Hướng dẫn nông dân kỹ thuật làm môi trường" và "Làm điểm tại huyện Yên Dũng".',
    ("rice_leaf_roller", 4): 'Trích từ bài "Biện pháp phòng trừ sâu cuốn lá nhỏ hại lúa trong canh tác hữu cơ" - Nông nghiệp Việt Nam; xem Mục 2, tiểu mục "b. Sử dụng phương pháp sinh học" và mục "Sử dụng ong mắt đỏ".',
    ("yellow_rice_borer", 2): 'Trích từ bài "Các loại sâu hại trên lúa" - Nông Nghiệp SOFa; xem Mục lục, mục "3. Sâu đục thân lúa (Scirpophaga incertulas & Chilo suppressalis)" trong phần "Danh sách chi tiết các loại sâu bệnh hại trên lúa thường gặp nhất".',
    ("asiatic_rice_borer", 2): 'Trích từ bài "Các loại sâu hại trên lúa" - Nông Nghiệp SOFa; xem Mục lục, mục "3. Sâu đục thân lúa (Scirpophaga incertulas & Chilo suppressalis)" trong phần "Danh sách chi tiết các loại sâu bệnh hại trên lúa thường gặp nhất".',
    ("rice_leaf_caterpillar", 4): 'Trích từ bài "Biện pháp phòng trừ sâu cuốn lá nhỏ hại lúa trong canh tác hữu cơ" - Nông nghiệp Việt Nam; xem Mục 2, tiểu mục "b. Sử dụng phương pháp sinh học" và Mục 3, "Biện pháp phòng trừ sâu cuốn lá nhỏ trong quản lý cây lúa".',
    ("rice_shell_pest", 2): 'Trích từ bài "Các loại sâu hại trên lúa" - Nông Nghiệp SOFa; xem phần "Giải pháp tổng hợp giúp quản lý sâu bệnh hại trên lúa" và đối chiếu mục "5. Sâu phao (Nymphula depunctalis)" trong Mục lục.',
    ("rice_gall_midge", 2): 'Trích từ bài "Các loại sâu hại trên lúa" - Nông Nghiệp SOFa; xem mục "6. Muỗi hành (Orseolia oryzae) – Gây hiện tượng bông hành bạc trắng" trong phần "Danh sách chi tiết các loại sâu bệnh hại trên lúa thường gặp nhất".',
    ("grain_spreader_thrips", 3): 'Trích từ tài liệu "Kỹ thuật gieo trồng các giống đậu tương mới" - Trung tâm Khuyến nông Quốc gia, chủ biên PGS.TS. Mai Quang Vinh; xem Trang 1 (trang bìa và thông tin ban hành). Lưu ý: tài liệu này không phải chuyên khảo về bọ trĩ hại lúa, nên chỉ dùng làm nguồn tham khảo bối cảnh canh tác, không dùng để khẳng định hiệu lực trừ bọ trĩ.',
    ("rice_stem_maggot", 5): 'Trích từ "Sổ tay về đặc điểm hình thái của một số loài đối tượng kiểm dịch thực vật nhóm I của Việt Nam" - Cục Bảo vệ thực vật, với sự tài trợ của GIZ; xem Trang 1 (tựa đề) và Trang 2 (ban biên tập/cơ quan ban hành). Tài liệu không được dùng để suy diễn hiệu lực trừ sâu hại lúa nếu không có mục loài tương ứng.',
}
HISTORY = [
    # (sâu, giai đoạn, vụ, vùng, nhiệt độ, độ ẩm, giải pháp ID, mật độ, hiệu quả %, nguồn ID)
    ("brown_planthopper", "de_nhanh", "dong_xuan", "dbscl", 28.0, 86.0, 1, 1.0, 92.0, 1),
    ("brown_planthopper", "lam_dong", "dong_xuan", "dbscl", 29.0, 88.0, 1, 1.0, 90.0, 1),
    ("brown_planthopper", "de_nhanh", "he_thu", "dbscl", 30.0, 84.0, 5, 2.0, 84.0, 1),
    ("brown_planthopper", "tro_bong", "thu_dong", "dbscl", 27.5, 90.0, 1, 2.0, 91.0, 1),
    ("brown_planthopper", "lam_dong", "he_thu", "dong_nam_bo", 28.5, 85.0, 6, 1.0, 86.0, 1),
    ("rice_leaf_roller", "de_nhanh", "dong_xuan", "dbscl", 27.0, 85.0, 3, 2.0, 94.0, 4),
    ("rice_leaf_roller", "lam_dong", "dong_xuan", "dbsh", 26.0, 88.0, 3, 2.0, 92.0, 4),
    ("rice_leaf_roller", "de_nhanh", "he_thu", "dbscl", 29.5, 82.0, 2, 2.0, 88.0, 4),
    ("rice_leaf_roller", "de_nhanh", "thu_dong", "dbscl", 28.0, 87.0, 4, 1.0, 82.0, 4),
    ("yellow_rice_borer", "de_nhanh", "dong_xuan", "dbscl", 27.5, 84.0, 4, 1.0, 85.0, 2),
    ("yellow_rice_borer", "lam_dong", "dong_xuan", "dbscl", 28.5, 86.0, 3, 3.0, 90.0, 2),
    ("yellow_rice_borer", "lam_dong", "he_thu", "dbsh", 29.0, 83.0, 4, 2.0, 84.0, 2),
    ("asiatic_rice_borer", "de_nhanh", "dong_xuan", "dbsh", 25.5, 85.0, 4, 1.0, 83.0, 2),
    ("asiatic_rice_borer", "lam_dong", "he_thu", "dbscl", 28.0, 84.0, 3, 3.0, 91.0, 2),
    ("asiatic_rice_borer", "ma", "dong_xuan", "dbsh", 24.5, 82.0, 6, 1.0, 87.0, 2),
    ("rice_leaf_caterpillar", "de_nhanh", "dong_xuan", "dbscl", 27.5, 83.0, 3, 2.0, 94.0, 4),
    ("rice_leaf_caterpillar", "de_nhanh", "he_thu", "dbsh", 29.0, 81.0, 2, 2.0, 89.0, 4),
    ("rice_shell_pest", "ma", "he_thu", "dbscl", 28.0, 89.0, 6, 2.0, 86.0, 2),
    ("rice_shell_pest", "de_nhanh", "thu_dong", "dbscl", 27.0, 91.0, 12, 3.0, 90.0, 2),
    ("rice_gall_midge", "de_nhanh", "dong_xuan", "dbscl", 26.5, 89.0, 4, 1.0, 82.0, 2),
    ("rice_gall_midge", "ma", "thu_dong", "dong_nam_bo", 27.0, 90.0, 5, 1.0, 80.0, 2),
    ("grain_spreader_thrips", "ma", "he_thu", "dbscl", 33.0, 65.0, 6, 2.0, 84.0, 3),
    ("grain_spreader_thrips", "de_nhanh", "dong_xuan", "dbscl", 32.0, 68.0, 1, 2.0, 78.0, 3),
    ("rice_stem_maggot", "lam_dong", "he_thu", "dbscl", 33.5, 64.0, 6, 1.0, 86.0, 5),
    ("rice_stem_maggot", "tro_bong", "he_thu", "dong_nam_bo", 32.5, 67.0, 1, 2.0, 80.0, 5),
]

HISTORY = [
    (*row, CITATION_NOTES[(row[0], row[9])])
    for row in HISTORY
]

AHP_SCORES = {
    # (mật độ, chi phí, thời gian tác dụng, an toàn sinh thái)
    # Cả bốn tiêu chí đều là điểm lợi ích: điểm cao hơn luôn tốt hơn.
    1: (8.0, 5.0, 4.0, 9.5),  # Nấm xanh Metarhizium
    2: (7.0, 6.0, 5.0, 9.5),  # Nấm trắng Beauveria
    3: (8.5, 7.0, 8.0, 8.5),  # Vi khuẩn Bt
    4: (7.0, 8.0, 4.0, 10.0),  # Ong ký sinh
    5: (6.0, 9.0, 3.0, 10.0),  # Bảo tồn thiên địch
    6: (7.0, 10.0, 2.0, 10.0),  # Canh tác IPM
    7: (7.0, 7.0, 7.0, 9.0),  # Bẫy đèn
    8: (6.0, 9.0, 6.0, 9.0),  # Bẫy bả chua ngọt
    9: (5.0, 8.0, 6.0, 8.0),  # Tỏi - ớt
    10: (7.0, 6.0, 7.0, 8.0),  # Thả vịt
    11: (5.0, 7.0, 3.0, 9.0),  # Trichoderma
    12: (8.0, 10.0, 8.0, 9.0),  # Rút nước
}

SOLUTION_METADATA = {
    1: ("Nấm ký sinh làm côn trùng ngừng ăn và chết dần.", "Phun chiều mát, ưu tiên sâu non tuổi nhỏ; tuân thủ nhãn sản phẩm.", "Tránh nắng gắt và thuốc nấm phổ rộng; thử trên diện tích nhỏ.", "Bào tử Metarhizium có thể gây bệnh cho côn trùng; IPM của IRRI/FAO khuyến khích bảo vệ thiên địch."),
    2: ("Nấm Beauveria ký sinh qua lớp biểu bì côn trùng.", "Phun khi ẩm độ phù hợp và sâu còn non; dùng đúng liều trên nhãn.", "Không phối hợp tùy tiện với thuốc diệt nấm; bảo quản chế phẩm khô mát.", "Beauveria bassiana là tác nhân kiểm soát sinh học phổ biến trong quản lý sâu hại."),
    3: ("Độc tố Bt phá hủy biểu mô ruột của sâu non mẫn cảm.", "Phun đúng thời điểm sâu non tuổi nhỏ; cần phủ đều tán lá.", "Hiệu quả giảm khi sâu lớn; tránh dùng sai đối tượng và tuân thủ nhãn.", "Tinh thể độc tố của Bacillus thuringiensis tác động qua đường ăn ở sâu non Lepidoptera."),
    4: ("Ong ký sinh làm giảm tỷ lệ trứng sâu nở.", "Treo thẻ ong theo lịch phát sinh bướm và hướng dẫn cán bộ bảo vệ thực vật.", "Không phun thuốc phổ rộng trong thời gian ong hoạt động.", "Ký sinh trứng là biện pháp sinh học bảo tồn thiên địch trong IPM lúa."),
    5: ("Duy trì nhện, bọ xít và thiên địch bản địa để khống chế quần thể sâu.", "Giảm thuốc phổ rộng, giữ bờ cỏ có kiểm soát và cây có hoa.", "Không xem đây là biện pháp xử lý tức thời khi mật độ vượt ngưỡng.", "Bảo tồn thiên địch là nguyên tắc cốt lõi của IPM theo FAO/IRRI."),
    6: ("Kết hợp giống, mật độ gieo sạ, dinh dưỡng, nước và theo dõi đồng ruộng.", "Ra quyết định theo ngưỡng và giai đoạn lúa, không phun theo lịch cố định.", "Cần điều chỉnh theo vùng, giống và khuyến cáo địa phương.", "IPM là hệ thống phối hợp biện pháp sinh học, canh tác và vật lý để giảm phụ thuộc thuốc."),
    7: ("Ánh sáng thu hút một phần côn trùng trưởng thành hoạt động ban đêm.", "Đặt ngoài ruộng hoặc bờ ruộng, ghi số lượng bắt được để theo dõi cao điểm.", "Không đặt gần khu dân cư; bẫy không thay thế điều tra và xử lý ổ dịch.", "Bẫy đèn được dùng chủ yếu để giám sát và hỗ trợ giảm trưởng thành trong IPM."),
    8: ("Mùi và vị của bả có thể thu hút một số côn trùng trưởng thành.", "Đặt nhiều điểm, thay bả định kỳ và ghi nhận lượng bắt; tránh để bả phân hủy.", "Hiệu quả phụ thuộc loài và thời tiết; không coi là thuốc diệt sâu diện rộng.", "Bẫy bả là công cụ giám sát/quản lý trưởng thành, cần xác nhận đối tượng trước khi áp dụng."),
    9: ("Hợp chất thứ cấp trong tỏi, ớt có thể xua đuổi hoặc làm giảm sự ăn của một số côn trùng.", "Ưu tiên chế phẩm có nguồn gốc rõ ràng, phun thử và tránh phun lúc nắng gắt.", "Có thể gây cháy lá nếu nồng độ cao; không tự pha chế không kiểm soát.", "Hoạt chất thực vật được nghiên cứu như công cụ hỗ trợ IPM, hiệu lực thay đổi theo công thức."),
    10: ("Vịt có thể ăn côn trùng, ốc và cỏ dại, góp phần giảm nguồn thức ăn trên ruộng.", "Chỉ thả khi cây đủ cứng, kiểm soát mật độ và đưa vịt ra trước giai đoạn trổ.", "Có thể làm đổ lúa hoặc ảnh hưởng ruộng mới gieo; cần quản lý đàn.", "Mô hình lúa - vịt là biện pháp canh tác sinh thái, hiệu quả phụ thuộc giống lúa và quản lý ruộng."),
    11: ("Trichoderma cạnh tranh và đối kháng vi sinh vật gây bệnh vùng rễ, hỗ trợ sức khỏe cây.", "Bón/xử lý đất theo nhãn, kết hợp hữu cơ và quản lý nước phù hợp.", "Không mô tả là thuốc diệt trực tiếp sâu hại; hiệu quả cần thời gian.", "Trichoderma chủ yếu phục vụ quản lý đất và bệnh vùng rễ, không thay thế biện pháp trừ côn trùng."),
    12: ("Tháo nước làm mất môi trường sống ngập của sâu phao và hỗ trợ vệ sinh ruộng.", "Điều chỉnh mực nước theo giai đoạn lúa, tháo tạm thời rồi cấp nước lại hợp lý.", "Không để cây thiếu nước; cần xét đất, thời tiết và khuyến cáo thủy lợi.", "Sâu phao phụ thuộc môi trường nước; quản lý nước và vệ sinh ruộng là biện pháp canh tác phù hợp."),
}


def seed_ahp_scores(session: Session) -> int:
    """Đồng bộ điểm AHP chuẩn hóa cho các giải pháp chính."""
    updated = 0
    for solution_id, scores in AHP_SCORES.items():
        solution = session.get(GiaiPhapSinhHoc, solution_id)
        if solution is None:
            continue
        current_scores = (
            solution.score_mat_do,
            solution.score_chi_phi,
            solution.score_thoi_gian,
            solution.score_an_toan,
        )
        if current_scores != scores:
            (
                solution.score_mat_do,
                solution.score_chi_phi,
                solution.score_thoi_gian,
                solution.score_an_toan,
            ) = scores
            updated += 1
    if updated:
        session.commit()
    return updated


def seed(session: Session) -> dict[str, int]:
    pests: dict[str, SauHai] = {}
    for row in PESTS:
        label, vietnamese, scientific, lifecycle, symptoms, regions, hosts = row
        pest = session.scalar(select(SauHai).where(SauHai.MaLopYOLO == label))
        if pest is None:
            pest = SauHai(MaLopYOLO=label)
            session.add(pest)
        pest.TenTiengViet = vietnamese
        pest.TenKhoaHoc = scientific
        pest.VongDoi = lifecycle
        pest.TrieuChungGayHai = symptoms
        (
            pest.DacDiemHinhThai,
            pest.CachThucGayHai,
            pest.MucDoGayHai,
        ) = PEST_DETAILS[label]
        pest.VungPhanBo_JSON = regions
        pest.CayTrongBiHai_JSON = hosts
        pests[label] = pest
    session.flush()

    solutions: dict[int, GiaiPhapSinhHoc] = {}
    for solution_id, (name, method, cost, days, safety) in enumerate(SOLUTIONS, 1):
        solution = session.get(GiaiPhapSinhHoc, solution_id)
        if solution is None:
            solution = GiaiPhapSinhHoc(MaGiaiPhap=solution_id)
            session.add(solution)
        solution.TenGiaiPhap = name
        solution.PhuongPhapApDung = method
        solution.ChiPhiMoiHecta = cost
        solution.SoNgayHieuQua = days
        solution.DiemAnToanMoiTruong = safety
        (
            solution.mo_ta,
            solution.cach_su_dung,
            solution.luu_y_khi_dung,
            solution.co_so_khoa_hoc,
        ) = SOLUTION_METADATA[solution_id]
        (
            solution.score_mat_do,
            solution.score_chi_phi,
            solution.score_thoi_gian,
            solution.score_an_toan,
        ) = AHP_SCORES[solution_id]
        solutions[solution_id] = solution
    session.flush()

    for label, solution_id, score in LINKS:
        link = session.scalar(select(SauHaiGiaiPhap).where(
            SauHaiGiaiPhap.MaSauHai == pests[label].MaSauHai,
            SauHaiGiaiPhap.MaGiaiPhap == solution_id,
        ))
        if link is None:
            link = SauHaiGiaiPhap(MaSauHai=pests[label].MaSauHai, MaGiaiPhap=solution_id)
            session.add(link)
        link.DiemHieuQua = score

    config = session.get(CauHinhDSS, 1)
    if config is None:
        config = CauHinhDSS(MaCauHinh=1, TenCauHinh="AHP 4 tiêu chí chuẩn")
        session.add(config)
    config.MaTranSoSanh_JSON = [[1.0, 3.0, 2.0, 1.0], [0.333333, 1.0, 0.5, 0.333333], [0.5, 2.0, 1.0, 0.5], [1.0, 3.0, 2.0, 1.0]]
    config.TrongSo_JSON = {"mat_do": 0.3512, "chi_phi": 0.1089, "thoi_gian_hieu_qua": 0.1887, "an_toan_moi_truong": 0.3512}

    for (
        label,
        stage,
        season,
        region,
        temperature,
        humidity,
        solution_id,
        density,
        effectiveness,
        source_id,
        citation_note,
    ) in HISTORY:
        pest_id = pests[label].MaSauHai
        values = dict(
            MaSauHai=pest_id,
            GiaiDoanLua=GiaiDoanLua(stage),
            MuaVu=MuaVu(season),
            VungMien=VungMien(region),
            NhietDo=temperature,
            DoAm=humidity,
        )
        existing = session.scalar(select(LichSuCanhTac).where(*[getattr(LichSuCanhTac, key) == value for key, value in values.items()]))
        if existing is None:
            session.add(
                LichSuCanhTac(
                    **values,
                    MatDo=density,
                    DiemHieuQua=effectiveness,
                    NguonTrichDan=SOURCE_URLS[source_id],
                    GhiChuTrichDan=citation_note,
                    MaGiaiPhapDaChon=solution_id,
                    KetQua=KetQuaCanhTac.TOT,
                )
            )
        else:
            existing.MatDo = density
            existing.DiemHieuQua = effectiveness
            existing.NguonTrichDan = SOURCE_URLS[source_id]
            existing.GhiChuTrichDan = citation_note
            existing.MaGiaiPhapDaChon = solution_id
            existing.KetQua = KetQuaCanhTac.TOT

    password = os.getenv("SEED_DEMO_PASSWORD", "admin").encode("utf-8")
    for username, email, role in (("admin", "admin@example.com", VaiTroNguoiDung.ADMIN), ("nongdan", "nongdan@example.com", VaiTroNguoiDung.FARMER)):
        user = session.scalar(select(NguoiDung).where(NguoiDung.TenDangNhap == username))
        if user is None:
            user = NguoiDung(
                TenDangNhap=username,
                MatKhauHash=bcrypt.hashpw(password, bcrypt.gensalt()).decode("utf-8"),
                IsVerified=True,
            )
            session.add(user)
        user.Email = email
        user.VaiTro = role
        user.IsVerified = True

    session.commit()
    return {"SauHai": len(PESTS), "GiaiPhapSinhHoc": len(SOLUTIONS), "SauHai_GiaiPhap": len(LINKS), "CauHinhDSS": 1, "LichSuCanhTac": len(HISTORY), "NguoiDung": 2}


def main() -> None:
    with SessionLocal() as session:
        print("Seed hoàn tất:", seed(session))


if __name__ == "__main__":
    main()
