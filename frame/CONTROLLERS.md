# CONTROLLERS - Quy định chi tiết theo từng chức năng

## 1. Cách hiểu

CONTROLLERS là bảng đặc tả chi tiết cho từng chức năng, không phải nơi chứa code thực thi chung và không đồng nghĩa với thư mục FastAPI `routers/`.

Mỗi controller chức năng phải mô tả:

- mục tiêu;
- actor/quyền;
- input;
- validation;
- workflow gọi lớp;
- database;
- output;
- lỗi;
- UX;
- tiêu chí nghiệm thu.

## 2. Controller chức năng: phân tích ảnh và DSS

### Mục tiêu

Nhận một ảnh lúa, nhận diện sâu bằng YOLO11n, lưu kết quả và chạy AHP/KNN để trả hỗ trợ quyết định.

### Endpoint contract

Endpoint chuẩn đề xuất:

```text
POST /api/analysis/analyze
Content-Type: multipart/form-data
```

Fields:

- `image`: bắt buộc, file ảnh.
- `giai_doan_lua`: `ma|de_nhanh|lam_dong|tro_bong|chin`.
- `mua_vu`: `dong_xuan|he_thu|thu_dong`.
- `vung_mien`: giá trị ENUM V6.
- `nhiet_do`: số thực, phù hợp `DECIMAL(4,1)`.
- `do_am`: số thực trong 0..100.
- `quy_mo_dien_tich`: chuỗi theo V6, ví dụ `1 m2`, `1 khóm`.

### Luồng bắt buộc

```text
Router
 -> Schema
 -> temporary storage
 -> yolo_service (load best.pt, inference, draw BBox)
 -> CRUD PhienPhanTich (KetQuaAI_JSON)
 -> dss_service
 -> CRUD PhienPhanTich (KetQuaDSS_JSON)
 -> response agent (URL ảnh kết quả)
 -> cleanup temporary storage
```

Router chỉ điều phối. Không đặt công thức mật độ, AHP, KNN hoặc SQL trong router.

### Quy định model và file

- `yolo_service` chỉ load `best.pt` đã huấn luyện sẵn, mặc định tại `Code/models/best.pt` hoặc đường dẫn cấu hình.
- Không được train, fine-tune, download hoặc tạo model thay thế trong controller này.
- Upload phải được lưu tạm trước inference.
- `yolo_service` phải tạo ảnh BBox mới sau khi inference xong.
- Response phải trả URL public/internal đã được backend expose an toàn cho ảnh BBox.
- Cleanup file gốc tạm phải chạy sau khi đã ghi nhận đường dẫn cần thiết; nếu policy yêu cầu lưu ảnh gốc thì chuyển sang storage lâu dài trước khi xóa file tạm.
- Tên file phải được sinh từ UUID hoặc storage key an toàn; không tin cậy tên file client.

### Output

```json
{
  "status": "ok",
  "message": "Phân tích ảnh thành công",
  "data": {
    "ma_phien": 1,
    "anh_goc": "string",
    "anh_ket_qua": "string|null",
    "detections": [
      {
        "ma_sau_hai": 1,
        "ten": "Rầy nâu",
        "class_id": 0,
        "confidence": 0.91,
        "bbox": [10, 20, 100, 160]
      }
    ],
    "counts": {"Rầy nâu": 1},
    "dss": {
      "mat_do": 1,
      "xep_hang_ahp": [],
      "ca_tuong_dong_knn": []
    }
  }
}
```

### Lỗi

- 400: file rỗng, loại file không hỗ trợ, diện tích không hợp lệ.
- 401: endpoint yêu cầu JWT nhưng thiếu/sai token.
- 422: context sai enum hoặc sai range.
- 404: class YOLO không có mapping trong `SauHai`.
- 503: model YOLO hoặc dependency chưa sẵn sàng.
- 500: lỗi nội bộ; log server, không lộ stack trace.

### Nghiệm thu

- Mỗi bounding box có tên, confidence và tọa độ.
- `total` bằng số detection.
- Dữ liệu ghi đúng `PhienPhanTich.KetQuaAI_JSON` và `PhienPhanTich.KetQuaDSS_JSON`.
- Mật độ dùng đúng số lượng BBox/quy mô.
- AHP không xếp hạng giải pháp ngoài Knowledge Base.
- KNN dùng đủ 5 đặc trưng hoặc báo thiếu dữ liệu.
- Ảnh BBox mở được bằng URL trả về.
- File tạm được dọn trong cả nhánh thành công và lỗi theo storage policy.

### Quy định thư viện DSS

- **AHP:** dùng `numpy` cho vector, ma trận, chuẩn hóa trọng số và các phép tính nhất quán; kết quả phải lưu/ trả tiêu chí, trọng số và tỷ số nhất quán.
- **KNN:** dùng `scikit-learn`, ưu tiên `NearestNeighbors` khi cần tìm ca tương đồng; chỉ dùng `KNeighborsClassifier` nếu có nhãn dự đoán rõ ràng.
- Không đưa phép tính AHP/KNN vào router hoặc CRUD.
- Không import TensorFlow/PyTorch cho DSS nếu không có yêu cầu riêng; YOLO inference là trách nhiệm riêng của `yolo_service`.
- Dependency phải được ghi vào manifest backend và có kiểm tra import/version trong môi trường triển khai.
- Khi thiếu một trong 5 đặc trưng, không tự bịa giá trị; trả trạng thái thiếu dữ liệu hoặc áp dụng default đã được phê duyệt.

## 3. Controller chức năng: chatbot text Strict RAG

### Endpoint tương thích

Phải hỗ trợ adapter cho:

- `POST /chatbot/api/`
- `POST /insects/chatbot/api/`

Request legacy:

```json
{"message": "rầy nâu gây hại thế nào?"}
```

Response chuẩn mới:

```json
{
  "status": "ok",
  "message": "Đã truy xuất Knowledge Base",
  "data": {
    "reply": "Nội dung dựa trên dữ liệu đã truy xuất.",
    "sources": [],
    "grounded": true
  }
}
```

Nếu cần giữ frontend cũ, adapter có thể expose `reply` ở lớp tương thích nhưng response nội bộ vẫn giữ chuẩn AGENTS.

### Luồng bắt buộc

```text
Router
 -> Schema message/chat_history
 -> chat service
 -> CRUD Knowledge Base
 -> grounded response/stream
 -> response agent
```

### Strict RAG policy

- Truy vấn `SauHai` bằng tên Việt, tên Anh, tên khoa học, triệu chứng hoặc từ khóa.
- Có thể đọc JSON `ThuVienAnh`, `VungPhanBo`, `CayTrongBiHai`.
- Không trả thông tin không có trong context.
- Nếu không có kết quả, trả `grounded: false`, nêu rõ chưa tìm thấy dữ liệu.
- Không tự suy ra thuốc, liều lượng, thời gian cách ly hoặc chẩn đoán chắc chắn.
- Câu trả lời phải có nguồn bản ghi hoặc mã loài khi có thể.

### History

- Request có thể chứa `chat_history`.
- Frontend lưu `{role, text}` trong `sessionStorage` với key `sessionChatHistory`.
- Giới hạn gửi/lưu 10 message gần nhất.
- Không lưu token vào history.

## 4. Controller chức năng: chatbot upload ảnh

### Endpoint tương thích

- `POST /chatbot/api/image/`
- `POST /insects/chatbot/upload/`

Field bắt buộc:

```text
image
```

### Luồng

```text
UploadFile
 -> validate image
 -> YOLO service
 -> map Knowledge Base
 -> optional chat context
 -> response/stream
```

### Output tối thiểu

```json
{
  "status": "ok",
  "message": "Đã xử lý ảnh",
  "data": {
    "reply": "Kết quả dựa trên dữ liệu nhận diện.",
    "bbox_image_url": "string|null",
    "detections": [],
    "grounded": true
  }
}
```

### UX bắt buộc

- Hiển thị preview ảnh người dùng.
- Hiển thị trạng thái `Đang xử lý...`.
- Hiển thị ảnh BBox nếu server trả về.
- Xóa input file sau khi hoàn tất.
- Không cho upload file trên 5 MB theo hành vi hiện hữu nếu chưa có policy mới.
- Không để lỗi upload làm mất lịch sử chat.

## 5. Controller chức năng: streaming

Streaming được dùng cho chatbot/dashboard khi endpoint hỗ trợ:

- Server gửi chunk theo giao thức được công bố.
- Client đọc `ReadableStream`, nối chunk theo thứ tự.
- Client tạo message assistant rỗng trước chunk đầu.
- Nếu stream lỗi, giữ phần đã nhận và hiển thị lỗi có thể thử lại.
- Khi kết thúc, lưu câu trả lời hoàn chỉnh vào history.
- Không render raw HTML từ chunk chưa sanitize.

## 6. Controller chức năng: quản lý context ảnh

Dashboard có pinned context:

- hiển thị thumbnail;
- hiển thị tên sâu/loài nhận diện;
- cho phép xóa context;
- sau khi xóa, chatbot phải nhận biết ảnh cũ không còn hiệu lực;
- câu xác nhận xóa context phải là message mới và được lưu history.

Không được gửi context ảnh cũ sau khi người dùng đã xóa.

## 7. Controller chức năng: trang test chatbot

Trang test phải hỗ trợ:

- nút test nhanh theo loài;
- câu hỏi đặc điểm, gây hại, phòng trừ, phân bố;
- thống kê tổng loài, loài có ảnh, loài gây hại, tổng ảnh;
- hiển thị mẫu dữ liệu Knowledge Base;
- health check;
- stats;
- suggestions;
- kết quả và lỗi trong vùng `result-box`.

Mọi endpoint test phải dùng cùng response contract hoặc adapter ghi rõ khác biệt.

## 8. Controller chức năng: bảo mật

- Endpoint private dùng Bearer JWT.
- Token sai/hết hạn trả 401 chuẩn.
- Không ghi token vào log hoặc database chat.
- Upload path phải được server tạo an toàn, không dùng trực tiếp filename làm đường dẫn.
- Sanitize Markdown/HTML và đặt link ngoài với `noopener noreferrer`.
- CORS chỉ cho phép origin đã cấu hình.

## 9. Controller chức năng: CRUD và model

CRUD phải mô tả riêng từng thao tác:

- tạo phiên phân tích;
- lưu kết quả nhận diện;
- đọc tri thức sâu hại;
- đọc giải pháp sinh học;
- đọc ma trận so sánh/trọng số AHP từ `CauHinhDSS.MaTranSoSanh_JSON` và `CauHinhDSS.TrongSo_JSON`;
- đọc ca canh tác KNN;
- tạo luồng chat;
- lưu tin nhắn chat;
- đọc kết quả DSS.

Model phải bám 9 bảng mới. Kết quả AI/DSS lưu trong JSON của `PhienPhanTich`; không tạo lại các bảng kết quả đã loại bỏ. Không thêm cột tùy tiện trong endpoint. Mọi migration phải được phê duyệt và cập nhật schema tài liệu.

## 10. Tiêu chí hoàn tất chức năng

Một chức năng chỉ được coi là hoàn tất khi:

1. Có controller đặc tả phù hợp trong tài liệu này.
2. Có schema validation.
3. Có service đúng nghiệp vụ.
4. Router chỉ điều phối.
5. CRUD/model đúng database 9 bảng mới.
6. Response đúng `{status, message, data}`.
7. Có xử lý lỗi và quyền.
8. Frontend tương thích với DOM/API hiện hữu.
9. Có test thành công và test lỗi.
10. Không vi phạm Strict RAG hoặc quy tắc thư mục.
