# WORKFLOW - Lộ trình triển khai chức năng

## 1. Mục đích

WORKFLOW là đường đi bắt buộc sau khi đã đọc AGENTS và trước khi thực thi. Nó trả lời:

- Cần đọc những nguồn nào?
- Chức năng chạm tới module nào?
- Dữ liệu đi qua các lớp theo thứ tự nào?
- File nào được tạo/sửa?
- Kiểm tra nào chứng minh chức năng hoàn tất?

Workflow không thay thế quy định chi tiết của CONTROLLERS và không cho phép bỏ qua AGENTS.

## 2. Quy trình chung

### Bước 1 - Tiếp nhận yêu cầu

Ghi rõ:

- mục tiêu đo được;
- người dùng/actor;
- input và output;
- phạm vi làm và không làm;
- có thay đổi hành vi hiện hữu hay không.

Nếu có nhiều cách hợp lý làm thay đổi thiết kế, phải hỏi người dùng trước.

### Bước 2 - Nạp AGENTS

Đọc:

- `frame/AGENTS.md`;
- các CONTROLLERS liên quan;
- cấu trúc `frame/` để hiểu quy ước;
- file code hiện tại trong `Code/`.

Không viết code nếu chưa xác định vị trí đúng trong `Code/`.

### Bước 3 - Khảo sát nguồn hiện hữu

Với database/backend:

- đọc schema 9 bảng mới đã được phê duyệt;
- đọc `init_db.sql`;
- kiểm tra models, CRUD, connection và migration hiện có;
- đối chiếu 9 bảng, FK, ENUM và JSON.

Với chatbot/frontend:

- đọc `test/testchatAI/chatbot.html`;
- đọc `test/testchatAI/dashboard.html`;
- đọc `test/testchatAI/chatbot_test.html`;
- ghi nhận ID DOM, field upload, endpoint, response field, session key, streaming và error state.

Với AI/DSS:

- xác định model YOLO11n và format output;
- xác định mapping `MaLopYOLO` với `SauHai`;
- xác định nguồn trọng số AHP;
- xác định dataset/vector KNN và quy tắc thiếu dữ liệu.

### Bước 4 - Lập Workflow cụ thể

Tạo lộ trình dạng:

1. schema/Pydantic nhận input;
2. router tiếp nhận và kiểm tra quyền;
3. service xử lý nghiệp vụ;
4. CRUD đọc/ghi CSDL;
5. model ánh xạ bảng;
6. response agent đóng gói;
7. frontend gọi API và cập nhật UI;
8. test và kiểm tra hồi quy.

Mỗi bước phải ghi file đích, phụ thuộc và output trung gian.

### Bước 5 - Kiểm tra dependency graph

Đối với database:

`NguoiDung`, `SauHai`, `GiaiPhapSinhHoc`, `CauHinhDSS`
→ `SauHai_GiaiPhap`, `LichSuCanhTac`, `PhienPhanTich`, `LuongChat`
→ `TinNhanChat`.

Đối với backend:

`Models -> CRUD -> Services -> Schemas -> Routers -> app`.

Router không được gọi ngược model để thực hiện SQL.

### Bước 6 - Thực thi

- Chỉ sửa/tạo file trong `Code/`.
- Tuân thủ CONTROLLER của chức năng.
- Tái sử dụng helper/agent hiện có.
- Giữ response `{status, message, data}`.
- Giữ backward compatibility hoặc ghi rõ migration.

### Bước 7 - Kiểm tra

Kiểm tra tối thiểu:

- syntax/type/lint;
- schema validation;
- response thành công và lỗi;
- upload file rỗng/sai loại/quá lớn;
- JWT thiếu/sai/hết hạn;
- DB FK và cascade;
- Strict RAG khi không tìm thấy Knowledge Base;
- streaming bị ngắt;
- session history và UI responsive.

### Bước 8 - Bàn giao

Báo rõ:

- file đã sửa/tạo;
- luồng dữ liệu;
- lệnh kiểm tra đã chạy;
- kết quả;
- giới hạn còn lại;
- thao tác cài dependency hoặc migration cần chạy.

## 3. Workflow cho AI nhận diện

1. Frontend chọn ảnh và context KNN/AHP.
2. Schema kiểm tra MIME, size, context enum/range.
3. Router nhận `UploadFile`, không chạy YOLO trực tiếp.
4. Lưu file upload tạm vào thư mục storage đã cấu hình, dùng tên file an toàn và ghi nhận đường dẫn nội bộ.
5. `yolo_service` load `Code/models/best.pt` đã huấn luyện sẵn và chạy inference YOLO11n; tuyệt đối không train lại.
6. Service vẽ bounding box lên ảnh kết quả và lưu ảnh mới vào thư mục output đã cấu hình.
7. Service map class YOLO sang `SauHai`.
8. CRUD tạo `PhienPhanTich` và lưu kết quả nhận diện vào `KetQuaAI_JSON` theo schema 9 bảng.
9. `dss_service` tính mật độ, AHP và KNN.
10. CRUD ghi kết quả DSS vào `KetQuaDSS_JSON`.
11. Response agent trả detection, counts, DSS và URL ảnh kết quả cho Frontend.
12. Frontend hiển thị ảnh gốc, ảnh BBox, số lượng và giải pháp.
13. Sau khi request hoàn tất, job cleanup xóa file tạm theo policy; ảnh kết quả chỉ xóa khi hết thời gian lưu trữ hoặc người dùng yêu cầu.

### Policy file tạm

- Dùng thư mục tạm riêng, không dùng thư mục source code hoặc đường dẫn người dùng gửi lên.
- Giới hạn dung lượng, loại file và thời gian tồn tại trước khi inference.
- Dọn file trong cả nhánh thành công và lỗi, nhưng không xóa ảnh kết quả trước khi Frontend có URL hợp lệ.
- Cleanup phải an toàn, giới hạn trong root storage đã cấu hình, không xóa đệ quy ngoài phạm vi.
- Nếu cleanup thất bại, phải log cảnh báo có mã file nội bộ để job dọn rác định kỳ xử lý; không biến response thành thành công giả.

## 4. Workflow cho chatbot Strict RAG

1. Frontend phục hồi `sessionChatHistory`.
2. Người dùng gửi text hoặc ảnh `image`.
3. Interceptor gắn Bearer Token và xử lý 401/500.
4. Router validate request.
5. Chat service tìm Knowledge Base theo từ khóa/ngữ nghĩa.
6. CRUD đọc `SauHai` và quan hệ cần thiết.
7. Nếu có context: sinh trả lời chỉ từ context.
8. Nếu không có context: trả thông báo thiếu dữ liệu, không hallucinate.
9. Streaming trả từng chunk theo giao thức đã thống nhất.
10. Frontend sanitize, render Markdown/gallery và lưu 10 message gần nhất.

## 5. Workflow cho DSS

1. Nhận kết quả YOLO và context.
2. Chuẩn hóa số lượng và quy mô diện tích.
3. Tính mật độ, báo lỗi nếu diện tích không hợp lệ theo policy.
4. Nạp tiêu chí/trọng số AHP qua CRUD.
5. Nạp giải pháp sinh học phù hợp loài sâu.
6. Dùng `numpy` cho các phép toán ma trận/vector AHP; không tự cài lại phép toán nếu thư viện đã có sẵn.
7. Kiểm tra tổng trọng số và tỷ số nhất quán trước khi xếp hạng.
8. Xếp hạng AHP và giữ giải thích điểm.
9. Mã hóa 5 đặc trưng KNN theo một mapping cố định, lưu version mapping.
10. Dùng `scikit-learn` (`NearestNeighbors` hoặc `KNeighborsClassifier` tùy bài toán) cho KNN; không import framework ML nặng hơn nếu không có yêu cầu.
11. Truy vấn ca canh tác tương đồng qua CRUD.
12. Trả kết quả có version/config, khoảng cách và số láng giềng để tái lập.

## 6. Quy tắc khi thiếu hoặc mâu thuẫn nguồn

- Schema 9 bảng mới là nguồn chuẩn database.
- `database_schema_v6_final.md` là tài liệu lịch sử 14 bảng, không được dùng làm chuẩn mới.
- Code đang chạy là nguồn chuẩn hành vi cần bảo toàn cho tới khi có yêu cầu đổi.
- Giao diện test là nguồn chuẩn về field/endpoint legacy cần tương thích.
- Không suy đoán nội dung nguồn không đọc được.
- Nếu hai nguồn mâu thuẫn về hành vi hoặc enum, dừng và hỏi người dùng.
