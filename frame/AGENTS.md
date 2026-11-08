# AGENTS - Hiến pháp toàn cục của dự án

## 1. Mục đích và phạm vi

Tài liệu này là bộ luật áp dụng cho mọi thay đổi trong đồ án:

> **WEB APP PHÂN TÍCH HÌNH ẢNH BẰNG AI ĐỂ NHẬN DIỆN SÂU HẠI TRÊN CÂY LÚA VÀ HỖ TRỢ RA QUYẾT ĐỊNH**

AGENTS là bước nhận thức quy định chung trước khi lập Workflow hoặc viết code. Mọi tác vụ phải trả lời được:

1. Dự án đang dùng quy ước nào?
2. Dữ liệu và giao diện hiện có yêu cầu gì?
3. Thay đổi này có làm sai kiến trúc, database, Strict RAG hoặc UX không?

## 2. Quy tắc thư mục bắt buộc

- Mọi mã nguồn hoàn thiện web app, database, backend, frontend, API, model và logic nghiệp vụ phải nằm trong `Code/`.
- `frame/` chỉ chứa tài liệu kiến trúc và quy ước `AGENTS -> WORKFLOW -> CONTROLLERS`; không đặt mã nguồn ứng dụng thực thi vào đây.
- Trước mỗi lần sửa code trong `Code/`, phải đọc các tài liệu liên quan trong `frame/`.
- Không ghi đè thay đổi không thuộc tác vụ hiện tại.
- Không tạo file kế hoạch tạm trong repository nếu người dùng không yêu cầu.

## 3. Luật kiến trúc tư duy

Ba khái niệm được hiểu như sau:

### 3.1. AGENTS - nhận thức quy định chung

AGENTS không phải một controller xử lý HTTP. Đây là bộ luật toàn cục: công nghệ, giao diện, quy tắc dữ liệu, chuẩn lỗi, cách kiểm tra, bảo mật, chất lượng và vị trí file.

### 3.2. WORKFLOW - lộ trình thực hiện

WORKFLOW là kế hoạch đi từ yêu cầu đến kết quả: đọc nguồn nào, xác định phụ thuộc nào, sửa hoặc tạo file nào, kết nối dữ liệu ra sao, kiểm tra gì và điều kiện hoàn tất là gì.

### 3.3. CONTROLLERS - quy định chi tiết theo từng chức năng

CONTROLLERS không được hiểu là bước thực thi code chung. Đây là các quy định chi tiết của từng chức năng: input, output, luồng gọi, quyền hạn, lỗi, database cần dùng, UX và tiêu chí nghiệm thu.

## 4. Bối cảnh nghiệp vụ cốt lõi

Hệ thống có ba module:

1. **AI nhận diện:** dùng YOLO11n để nhận ảnh, phát hiện sâu hại, trả bounding box, tên sâu, độ tin cậy và số lượng.
2. **DSS:** dùng AHP để xếp hạng giải pháp sinh học và KNN để tìm ca canh tác tương đồng.
3. **Chatbot AI:** tư vấn nông nghiệp theo Strict RAG; câu trả lời phải dựa trên Knowledge Base/CSDL, không tự bịa thông tin khi không có nguồn.

### Quy tắc mô hình AI đã huấn luyện

- Mô hình `best.pt` đã được huấn luyện xong và là artifact inference chính của dự án.
- AI chỉ được load và sử dụng `best.pt` để suy luận; không được tạo code, notebook, script hoặc pipeline để train lại model.
- Đường dẫn model phải được cấu hình bằng biến môi trường hoặc cấu hình ứng dụng, mặc định tham chiếu artifact trong `Code/models/best.pt`.
- Nếu không tìm thấy, không đọc được hoặc sai phiên bản model, phải báo lỗi rõ ràng; không tự tải model khác, không tạo model giả và không fallback sang huấn luyện.
- Mọi thay đổi class mapping phải đối chiếu `MaLopYOLO` trong bảng `SauHai` và được ghi nhận trước khi triển khai.

### AHP

- Mật độ là biến đầu vào quan trọng.
- Mật độ được tính từ số lượng bounding box chia cho quy mô diện tích.
- Kết quả phải giải thích được tiêu chí, trọng số và thứ hạng.
- Giải pháp sinh học lấy từ Knowledge Base, không tạo tên giải pháp giả.

### KNN

Vector đặc trưng gồm:

- Giai đoạn lúa
- Mùa vụ
- Vùng miền
- Nhiệt độ
- Độ ẩm

Không tự thay thế giá trị thiếu bằng dữ liệu nghiệp vụ bịa đặt. Phải báo thiếu context hoặc dùng quy tắc mặc định đã được phê duyệt.

## 5. Chuẩn dữ liệu và CSDL

Nguồn chuẩn hiện tại là yêu cầu schema 9 bảng mới và script đã triển khai `init_db.sql`. Tài liệu V6 14 bảng cũ chỉ là lịch sử, không còn là chuẩn để tạo model, CRUD, API hoặc mock data mới.

Database:

- Tên: `nhandien_sauhai_db`
- Host mặc định: `127.0.0.1`
- Port mặc định: `3306`
- User mặc định: `root`
- Password mặc định: rỗng trong môi trường XAMPP cục bộ

9 bảng:

1. `NguoiDung`
2. `SauHai`
3. `GiaiPhapSinhHoc`
4. `CauHinhDSS`
5. `SauHai_GiaiPhap`
6. `LichSuCanhTac`
7. `PhienPhanTich`
8. `LuongChat`
9. `TinNhanChat`

Quy tắc CSDL:

- Luôn bám đúng tên cột, kiểu dữ liệu, `ENUM`, `JSON`, PK và FK của schema 9 bảng mới.
- Tạo bảng cha trước bảng con.
- Không dùng lại `TieuChiAHP`, `CauHinhAHP`, `SoSanhCapAHP`, `TrongSoAHP`, `KetQuaNhanDien` hoặc `KetQuaDSS` trong model mới.
- `ThuVienAnh_JSON`, `VungPhanBo_JSON`, `CayTrongBiHai_JSON`, `MaTranSoSanh_JSON`, `TrongSo_JSON`, `KetQuaAI_JSON`, `KetQuaDSS_JSON` là JSON; phải validate JSON trước khi ghi.
- Không đưa SQL trực tiếp vào router/controller.
- CRUD là nơi duy nhất thao tác truy vấn DB.
- Xóa phiên phân tích phải set null `TinNhanChat.MaPhien_Context`; xóa người dùng phải set null `PhienPhanTich.MaNguoiDung` nhưng cascade `LuongChat`; dữ liệu tri thức chỉ cascade qua `SauHai_GiaiPhap` và `LichSuCanhTac` theo FK mới.

## 6. Chuẩn API backend

Backend dùng FastAPI theo layered architecture:

`Routers -> Schemas -> Services -> CRUD -> Models`

Mọi response phải có đúng hình dạng:

```json
{
  "status": "ok|error",
  "message": "Mô tả rõ ràng",
  "data": {}
}
```

Quy tắc:

- Không trả response lỗi thô của framework cho client.
- Lỗi validation là lỗi input; không che giấu chi tiết cần thiết cho frontend.
- Lỗi 500 phải log ở server nhưng không làm lộ secret, SQL, stack trace hoặc đường dẫn nội bộ.
- Endpoint cần bảo vệ phải dùng JWT độc lập.
- Không log token, mật khẩu, file nhạy cảm hoặc dữ liệu cá nhân không cần thiết.
- Upload phải kiểm tra MIME type, phần mở rộng, dung lượng và dữ liệu rỗng.
- File upload và ảnh kết quả phải dùng tên sinh an toàn, không dùng nguyên filename của người dùng làm đường dẫn.
- File tạm phải có thư mục riêng, thời gian sống và cơ chế dọn dẹp; không commit file ảnh người dùng hoặc file inference sinh ra.

## 7. Chuẩn frontend và UI hiện hữu

Nguồn tham chiếu trong `test/testchatAI/`:

- `chatbot.html`: giao diện chatbot dạng chuyên gia, có gửi text, upload ảnh, CSRF, gợi ý và thông báo lỗi.
- `dashboard.html`: giao diện chat tập trung, pinned image context, session history, Markdown, gallery, stream và nút xóa context.
- `chatbot_test.html`: trang test nhanh, thống kê Knowledge Base và các endpoint chatbot.

Quy tắc tương thích:

- Không đổi tùy tiện các ID DOM/API mà giao diện hiện có đang dùng.
- Giữ khả năng gửi `FormData` với field ảnh tên `image`.
- Giữ lịch sử tương thích `{ role, text }` và key `sessionChatHistory` nếu chưa có migration frontend.
- Streaming phải xử lý chunk, kết thúc stream, lỗi mạng và trạng thái loading.
- Nội dung Markdown/HTML từ AI phải sanitize; không đưa raw HTML không tin cậy vào DOM.
- Ảnh người dùng và ảnh kết quả phải có alt text, giới hạn kích thước và trạng thái lỗi tải ảnh.
- Giao diện phải giữ responsive ở desktop, tablet và mobile.
- Lỗi 401/500 phải được interceptor hoặc lớp UI chung xử lý, không lặp logic ở từng component.

Endpoint legacy được ghi nhận từ test:

- `POST /chatbot/api/`: chat text
- `POST /chatbot/api/image/`: chat/image API test
- `POST /insects/chatbot/api/`: chat text trong `chatbot.html`
- `POST /insects/chatbot/upload/`: upload ảnh trong `chatbot.html`
- `GET /chatbot/api/stats/`: thống kê
- `GET /chatbot/api/health/`: health check
- `GET /chatbot/api/suggestions/?q=query`: gợi ý

Khi chuẩn hóa endpoint mới, phải có adapter hoặc cập nhật đồng bộ frontend; không âm thầm phá endpoint đang dùng.

## 8. Strict RAG

Chatbot phải:

1. Chuẩn hóa câu hỏi.
2. Truy xuất bản ghi liên quan từ Knowledge Base.
3. Trích dẫn hoặc liên kết context được dùng.
4. Chỉ trả lời trong phạm vi dữ liệu đã truy xuất.
5. Nói rõ “chưa có dữ liệu” khi truy xuất rỗng.
6. Không tự tạo liều lượng, thời gian cách ly, tên thuốc hoặc khuyến cáo chuyên môn không có nguồn.

Các trường tri thức chính của `SauHai` là `MoTa`, `VongDoi`, `TrieuChungGayHai`, `ThuVienAnh`, `VungPhanBo`, `CayTrongBiHai`.

## 9. Chất lượng và kiểm tra

Mỗi thay đổi phải:

- Đọc đủ ngữ cảnh trước khi sửa.
- Có type/schema rõ ràng.
- Không nuốt exception bằng `except` rộng.
- Chạy kiểm tra nhỏ nhất bao phủ thay đổi.
- Kiểm tra route, response shape, validation, quyền, DB relation và frontend loading/error nếu có liên quan.
- Không kết luận thành công chỉ vì code “trông đúng”.
