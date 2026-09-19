# Báo Cáo Nhóm — Lab 7: Embedding & Vector Store

**Nhóm:** TDTU Library
**Thành viên:** Nguyễn Bá Chinh (2A202602654) — R1; Trần Anh Vũ (2A202602570) — R2; Dương Thị Hồng Viên (2A202602385) — R3
**Ngày:** 19/09/2026

> **Nộp 1 bản / nhóm.** Phần cá nhân (hướng tiếp cận, kết quả riêng, dự đoán…) mỗi thành viên nộp riêng trong `REPORT_CANHAN.md`. Chi tiết thang điểm: `docs/SCORING.md`.

**Tổng điểm phần nhóm: 40** = Lựa chọn tài liệu (10) + Thiết kế chiến lược (15) + Chất lượng truy xuất (10) + Thuyết trình (5).

---

## 1. Lựa chọn tài liệu (Document Set Quality) — Nhóm (10 điểm)

### Chủ đề (Domain) & Lý Do Chọn

**Chủ đề:** Tra cứu dịch vụ và quy định sử dụng Thư viện TDTU.

**Tại sao nhóm chọn chủ đề này?**
> Đây là nguồn công khai, có cấu trúc rõ ràng và có nhiều tình huống truy vấn thực tế (mượn, gia hạn, đặt phòng, tài khoản). Tài liệu chia theo nhiều nhóm đối tượng (`student`, `staff`, `all`) nên có việc thật cho metadata filter, và vì các mục đã chia sẵn theo heading nên phù hợp để so sánh các chiến lược chunking.

### Danh sách tài liệu (Data Inventory)

Số ký tự tính trên phần nội dung Markdown sau khi bỏ YAML frontmatter. Cả 6 tài liệu đều có `department=library`, `language=en`, `retrieved_at=2026-09-19`, `document_version=not-stated` (trang nguồn không nêu số hiệu).

| # | Tên tài liệu | Nguồn (Source URL) | Số ký tự | Metadata chính |
|---|--------------|--------------------|---------:|----------------|
| 1 | Undergraduate Student - Circulation Service | https://lib.tdtu.edu.vn/services/circulation/undergraduate-student | 1240 | audience=student, category=circulation |
| 2 | Library Card & Account | https://lib.tdtu.edu.vn/guides/essential/library-card-account | 1150 | audience=all, category=account |
| 3 | Renew Library Materials | https://lib.tdtu.edu.vn/guides/essential/renewal | 663 | audience=all, category=renewal |
| 4 | Reserve a Room | https://lib.tdtu.edu.vn/guides/essential/reserve-a-room | 1028 | audience=all, category=room_booking |
| 5 | Services for TDTU Undergraduate Students | https://lib.tdtu.edu.vn/user-group-services/undergraduate-student | 906 | audience=student, category=user_group_services |
| 6 | Services for TDTU Academic and Professional Staff | https://lib.tdtu.edu.vn/user-group-services/professional-staff | 1007 | audience=staff, category=user_group_services |

**Danh sách kiểm tra quản trị dữ liệu (Data governance checklist):**
- [x] Corpus chỉ dùng các trang công khai chính thức của TDTU Library, không chứa dữ liệu đăng nhập hay tài liệu nội bộ.
- [x] Mỗi tài liệu có `source_url`, `retrieved_at`, `document_version` cùng các metadata phục vụ truy xuất.

### Cấu trúc Metadata (Metadata Schema)

| Trường metadata | Kiểu | Ví dụ giá trị | Tại sao hữu ích cho truy xuất? |
|-----------------|------|---------------|-------------------------------|
| `doc_id` | string | `student-borrowing-policy` | Nhận diện tài liệu gốc của mỗi chunk, cần cho `delete_document` |
| `audience` | string | `student` | Lọc theo đúng nhóm người dùng (chứng minh được bằng A/B ở mục 3) |
| `category` | string | `circulation` | Phân biệt loại dịch vụ/quy định |
| `department`, `language` | string | `library`, `en` | Giới hạn theo đơn vị / ngôn ngữ khi corpus mở rộng |
| `source_url`, `retrieved_at`, `document_version` | string | URL, `2026-09-19`, `not-stated` | Truy vết nguồn và phiên bản |

---

## 2. Thiết kế chiến lược (Strategy Design) — Nhóm (15 điểm)

Mỗi thành viên dùng một chiến lược chunking khác nhau trên cùng 6 tài liệu và cùng 5 benchmark query.

### Phân tích đường cơ sở (Baseline Analysis)

`ChunkingStrategyComparator().compare()` trên 3 tài liệu, đã bỏ frontmatter:

| Tài liệu | Chiến lược | Số chunk | Độ dài TB | Giữ được ngữ cảnh không? |
|----------|-----------|---------:|----------:|--------------------------|
| student-borrowing-policy | FixedSizeChunker | 3 | 447.00 | Khá, có thể cắt giữa section |
| | SentenceChunker | 5 | 246.20 | Tốt ở mức câu, chunk nhỏ |
| | RecursiveChunker | 3 | 413.67 | Tốt, ưu tiên ranh giới tự nhiên |
| reserve-a-room | FixedSizeChunker | 3 | 376.33 | Khá |
| | SentenceChunker | 3 | 340.33 | Tốt |
| | RecursiveChunker | 3 | 343.00 | Tốt |
| undergraduate-student-services | FixedSizeChunker | 2 | 478.50 | Khá |
| | SentenceChunker | 3 | 299.67 | Tốt ở mức câu |
| | RecursiveChunker | 2 | 453.50 | Tốt |

### Chiến lược của từng thành viên

**Thành viên 1 — Nguyễn Bá Chinh (R1): `FixedSizeChunker(chunk_size=500, overlap=50)`**
- **Mô tả & lý do:** Đơn giản, kích thước chunk ổn định, làm baseline rõ ràng. Overlap 50 ký tự giảm khả năng mất thông tin tại ranh giới hai chunk.
- **Code:** dùng `FixedSizeChunker` trong `src/chunking.py`.

**Thành viên 2 — Trần Anh Vũ (R2): `RecursiveChunker(chunk_size=500)`**
- **Mô tả & lý do:** Tách theo đoạn, dòng, câu trước khi phải cắt theo ký tự, nên chunk giữ được cấu trúc ngữ nghĩa hơn cắt cứng.
- **Code:** dùng `RecursiveChunker` trong `src/chunking.py` (có bước gom các mảnh nhỏ liền kề tới sát `chunk_size`).

**Thành viên 3 — Dương Thị Hồng Viên (R3): Heading/Section Chunking (`chunk_size=500`)**
- **Mô tả & lý do:** Tài liệu tổ chức theo heading (`Loan Periods`, `Renewal`, `Learning Support`, `Booking and Cancellation`) nên mỗi section là một đơn vị ngữ nghĩa. Section quá dài thì chia tiếp bằng `RecursiveChunker` nhưng vẫn gắn lại heading vào từng chunk con.
```python
sections = re.split(r"(?=^#{1,6}\s+)", text.strip(), flags=re.MULTILINE)

if len(section) > self.chunk_size:
    fallback = RecursiveChunker(chunk_size=available_size)
    for subchunk in fallback.chunk(body):
        chunks.append(f"{heading}\n{subchunk}".strip())
```

### So Sánh Giữa Các Thành Viên

Cùng embedder local `paraphrase-multilingual-MiniLM-L12-v2`, cùng corpus, cùng 5 query, top-k = 3. Điểm truy xuất chấm chặt theo `docs/SCORING.md`: 2 điểm nếu gold ở top-1 và chunk chứa đáp án, 1 điểm nếu chunk chứa đáp án chỉ ở top-2/3, 0 nếu không có.

| Thành viên | Chiến lược | Điểm truy xuất (/10) | Chunk trong store | Điểm mạnh | Điểm yếu |
|-----------|-----------|---------------------:|------------------:|-----------|----------|
| Nguyễn Bá Chinh | FixedSize (500, overlap 50) | 8 | 16 | Đơn giản, dễ kiểm soát, overlap giảm mất ngữ cảnh ở biên | Cắt qua section; Q4 không có chunk chứa đáp án trong top-3 |
| Trần Anh Vũ | Recursive (500) | 9 | 16 | Giữ ranh giới tự nhiên, cả 5 query có chunk liên quan trong top-3 | Q4 đáp án chỉ đứng hạng 2 |
| Dương Thị Hồng Viên | Heading/Section (500) | 10 | 35 | Mỗi chunk là một section có tiêu đề nên rất tập trung; Q4 đứng top-1 | Phụ thuộc tài liệu có heading rõ; nhiều chunk hơn |

**Chiến lược nào tốt nhất cho chủ đề này? Tại sao?**
> Heading/Section tốt nhất (10/10) vì tài liệu thư viện vốn chia theo section có ý nghĩa riêng, và việc gắn heading vào chunk giúp embedding của chunk tập trung đúng vào chủ đề của section. Recursive đứng thứ hai (9/10) nhờ tôn trọng ranh giới đoạn/dòng, còn Fixed-size (8/10) là baseline hợp lý nhưng cắt ngang section. Kết quả này chỉ phản ánh corpus 6 tài liệu nhỏ và benchmark hiện tại, không có nghĩa một chiến lược luôn thắng trên mọi loại tài liệu.

---

## 3. Câu hỏi đánh giá & Chất lượng truy xuất (Retrieval Quality) — Nhóm (10 điểm)

### Câu hỏi đánh giá & Câu trả lời chuẩn (nhóm thống nhất)

| # | Câu hỏi (Query) | Câu trả lời chuẩn (Gold Answer) | Chunk nào chứa thông tin? |
|---|-----------------|--------------------------------|--------------------------|
| 1 | For undergraduate students, how long is the loan period for circulating materials, and how many renewals are allowed? | 5 days; one renewal for an additional 5 days. | `student-borrowing-policy` → Loan Periods → Circulating Materials |
| 2 | Under what conditions is renewal not allowed? | When the material is overdue or another user has placed a hold request. | `renewal-guide` → When Renewal Is Not Allowed |
| 3 | How can a user cancel a library room booking? | By phone, email, Facebook, or by contacting staff at a Service Desk or Information Desk. | `reserve-a-room` → Booking and Cancellation |
| 4 | Which credentials are used to sign in to the Library Portal? | The same credentials as the Student Information Portal or Lecturer/Staff Information Portal. | `library-card-account` → Library Portal Account |
| 5 | What course-related support resources are available? *(filter `audience=student`)* | Course readings, subject guides, and required reading lists by course. | `undergraduate-student-services` → Learning Support |

### Tổng hợp chất lượng truy xuất của nhóm

Điểm từng câu theo thang 2 / 1 / 0:

| Query | FixedSize | Recursive | Heading | Ghi chú |
|-------|:---------:|:---------:|:-------:|---------|
| Q1 — Loan period & renewal | 2 | 2 | 2 | Câu tra số liệu, cả ba đều dễ |
| Q2 — Renewal conditions | 2 | 2 | 2 | Hai tài liệu cùng nói về gia hạn nhưng đều chứa đáp án |
| Q3 — Cancel room booking | 2 | 2 | 2 | Tiêu đề mục chứa đúng từ "Cancellation" |
| Q4 — Library Portal credentials | **0** | **1** | **2** | Phân hoá rõ nhất giữa ba chiến lược |
| Q5 — Course support (có filter) | 2 | 2 | 2 | Xem A/B bên dưới |
| **Tổng** | **8** | **9** | **10** | |

**Chấm theo `doc_id` sẽ thổi phồng kết quả.** Ở Q4, FixedSize vẫn lấy được chunk của đúng tài liệu `library-card-account` trong top-3 nên nếu chỉ kiểm document thì được điểm, nhưng không chunk nào chứa câu trả lời. Vì vậy nhóm chấm ở mức chunk (ngữ cảnh có chứa chuỗi đáp án hay không).

### Failure case: Q4 với FixedSizeChunker

- **Câu hỏi hỏng:** "Which credentials are used to sign in to the Library Portal?"
- **Điều gì xảy ra:** Top-3 gồm `library-card-account#2` (0.58) và hai chunk của `professional-staff-services` (0.53); không chunk nào chứa "same credentials as the Student Information Portal…". Recursive đưa chunk đúng lên hạng 2 (0.559 so với top-1 sai 0.567), Heading đưa section `Library Portal Account` lên top-1 (0.772).
- **Vì sao:** Không phải do corpus thiếu thông tin hay metadata sai. Nguyên nhân là ranh giới chunk: cắt theo số ký tự cắt ngang section, hoặc gộp nhiều chủ đề (thẻ thư viện, hỗ trợ theo nhóm đối tượng, tài khoản portal) vào cùng chunk, nên embedding không tập trung vào "Library Portal credentials". Cosine đo độ giống chủ đề chứ không đo chunk có chứa đáp án hay không.
- **Đề xuất sửa:** giảm `chunk_size`; dùng Recursive hoặc Heading cho tài liệu Markdown có cấu trúc; gắn heading vào nội dung chunk; thêm bước rerank sau vector search nếu cần độ chính xác cao hơn.

### Metadata filtering (A/B bắt buộc trên Q5)

| | Top-1 | Score | Kết quả |
|--|-------|------:|---------|
| Có `audience=student` (FixedSize) | `undergraduate-student-services` | 0.668 | Đúng, chứa course readings, subject guides, required reading lists |
| Không filter (FixedSize) | `professional-staff-services` | 0.688 | Sai đối tượng; tài liệu sinh viên tụt xuống hạng 2 |

**Lọc bằng metadata có giúp ích không? Ở câu hỏi nào?**
> Có, ở Q5. Tài liệu staff cũng có mục hỗ trợ giảng dạy và học liệu nên cosine cao hơn (0.688 so với 0.668) dù người dùng trong benchmark là sinh viên. Filter loại candidate sai **trước** khi xếp hạng nên ổn định hơn. Một điểm cần nói rõ: Heading/Section cho kết quả đúng ở top-1 ngay cả khi không filter (0.671 so với 0.666 của tài liệu staff), nhưng khoảng cách rất mỏng, nên filter vẫn là lớp bảo vệ cần thiết chứ không chỉ là tối ưu. Đánh đổi: filter cứng theo `student` sẽ loại các tài liệu `audience=all` cũng chứa thông tin cần thiết (giảm recall).

### Kiểm tra câu trả lời của Agent (FixedSize, R1)

`KnowledgeBaseAgent` đánh số các chunk `[1] [2] [3]` kèm nguồn, yêu cầu chỉ dùng ngữ cảnh, trích dẫn số đoạn, không suy đoán khi thiếu, và không làm theo chỉ dẫn nằm trong tài liệu được truy xuất.

| Query | Kết quả |
|-------|---------|
| Q1 | Đúng: 5 ngày, gia hạn một lần thêm 5 ngày |
| Q2 | Đúng: overdue và hold request; bổ sung thêm thông tin có căn cứ trong corpus về non-circulating material |
| Q3 | Đúng: phone, email, Facebook hoặc Service/Information Desk |
| Q4 | Retrieved context không có đáp án, Agent thông báo context chưa đủ thay vì bịa credentials |
| Q5 | Đúng: course readings, subject guides, required reading lists |

Hành vi ở Q4 là điểm đáng giá: khi evidence chưa đủ, hệ thống nói rõ là chưa đủ thay vì tạo câu trả lời không có căn cứ.

---

## 4. Thuyết trình (Demo) & Bài học nhóm — Nhóm (5 điểm)

**Những phân tích hay nhất nhóm sẽ trình bày:**
> 1. Cùng corpus và embedder, chỉ đổi cách chia chunk mà Q4 đi từ 0 điểm (Fixed) lên 1 (Recursive) rồi 2 (Heading).
> 2. Chấm theo `doc_id` cho kết quả đẹp hơn thực tế; phải chấm ở mức chunk và nội dung.
> 3. Metadata filter thay đổi hẳn Top-1 của Q5 (A/B có và không filter).

**Bài học rút ra khi so sánh trong nhóm:**
> - *Chunking ảnh hưởng trực tiếp đến embedding:* chunk gom nhiều chủ đề sẽ có vector "pha loãng" nên similarity với query cụ thể thấp hơn, còn chunk tập trung một section thì khớp hơn.
> - *Embedding và metadata giải quyết hai việc khác nhau:* embedding trả lời "nội dung nào gần nghĩa với query", metadata trả lời "được phép hoặc nên tìm trong tài liệu nào". Kết hợp hai lớp cho kết quả chính xác hơn.
> - *Chiến lược phải hợp với cấu trúc dữ liệu:* Fixed-size hợp khi cần đơn giản và kích thước ổn định, Recursive hợp với văn bản tự nhiên, Heading/Section hợp với Markdown, policy, FAQ có cấu trúc rõ. Không có chiến lược tốt nhất cho mọi corpus.
> - *Grounding quan trọng hơn việc luôn trả lời:* ở Q4 Agent chọn nói "chưa đủ ngữ cảnh", là hành vi an toàn hơn trong hệ thống RAG thực tế.

**Nếu làm lại, nhóm sẽ thay đổi gì trong chiến lược dữ liệu (data strategy)?**
> Bổ sung thêm tài liệu dành cho giảng viên/nhân viên về cùng chủ đề (ví dụ hạn mức mượn của nhân viên) để A/B filter rõ hơn ở nhiều câu hơn; thêm overlap hoặc rerank để giảm lỗi kiểu Q4; và chạy nhiều giá trị `chunk_size` thay vì cố định 500.

**Kịch bản demo (6–8 phút):** (1) giới thiệu 6 tài liệu và metadata (1'); (2) mỗi thành viên nói chiến lược của mình (2'); (3) chạy `bench.py` cho 3 chiến lược, tập trung Q4 và Q5 (3'); (4) demo Q5 có và không có `metadata_filter={"audience": "student"}`, rồi Agent trả lời Q4 với Fixed-size để thấy hành vi từ chối suy đoán (2').

---

## Tự Đánh Giá (Phần Nhóm)

| Tiêu chí | Điểm tự đánh giá |
|----------|------------------|
| Lựa chọn tài liệu (Document Set Quality) | / 10 |
| Thiết kế chiến lược (Strategy Design) | / 15 |
| Chất lượng truy xuất (Retrieval Quality) | / 10 |
| Thuyết trình (Demo) | / 5 |
| **Tổng phần nhóm** | **/ 40** |
