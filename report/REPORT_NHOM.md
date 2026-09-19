# Báo Cáo Nhóm — Lab 7: Embedding & Vector Store

**Nhóm:** [Điền tên nhóm]
**Thành viên:** Trần Anh Vũ (2A202602570), [Thành viên 2], [Thành viên 3]
**Ngày:** 2026-09-19

> **Nộp 1 bản / nhóm.** Phần cá nhân (hướng tiếp cận, kết quả riêng, dự đoán…) mỗi thành viên nộp riêng trong `REPORT_CANHAN.md`. Chi tiết thang điểm: `docs/SCORING.md`.

**Tổng điểm phần nhóm: 40** = Lựa chọn tài liệu (10) + Thiết kế chiến lược (15) + Chất lượng truy xuất (10) + Thuyết trình (5).

---

## 1. Lựa chọn tài liệu (Document Set Quality) — Nhóm (10 điểm)

### Chủ đề (Domain) & Lý Do Chọn

**Chủ đề:** Dịch vụ thư viện đại học (thư viện TDTU: mượn trả, gia hạn, đặt phòng, thẻ và tài khoản, dịch vụ theo nhóm đối tượng).

**Tại sao nhóm chọn chủ đề này?**
> Đây là chủ đề thuộc phạm vi bắt buộc của lớp L3A (dịch vụ/quy định đại học). Nội dung công khai, có con số và điều kiện cụ thể nên gold answer kiểm chứng được. Cùng một chủ đề lại có tài liệu riêng cho sinh viên và cho giảng viên/nhân viên, nên metadata filter `audience` có việc thật để làm.

### Danh sách tài liệu (Data Inventory)

| # | Tên tài liệu | Nguồn (Source URL) | Ngày lấy / Phiên bản | Số ký tự | Metadata đã gán |
|---|--------------|------------|--------------------|----------|-----------------|
| 1 | student-borrowing-policy | https://lib.tdtu.edu.vn/services/circulation/undergraduate-student | 2026-09-19 / not-stated | 1542 | audience=student, category=circulation |
| 2 | library-card-account | https://lib.tdtu.edu.vn/guides/essential/library-card-account | 2026-09-19 / not-stated | 1414 | audience=all, category=account |
| 3 | renewal-guide | https://lib.tdtu.edu.vn/guides/essential/renewal | 2026-09-19 / not-stated | 908 | audience=all, category=renewal |
| 4 | reserve-a-room | https://lib.tdtu.edu.vn/guides/essential/reserve-a-room | 2026-09-19 / not-stated | 1277 | audience=all, category=room_booking |
| 5 | undergraduate-student-services | https://lib.tdtu.edu.vn/user-group-services/undergraduate-student | 2026-09-19 / not-stated | 1218 | audience=student, category=user_group_services |
| 6 | professional-staff-services | https://lib.tdtu.edu.vn/user-group-services/professional-staff | 2026-09-19 / not-stated | 1369 | audience=staff, category=user_group_services |

**Danh sách kiểm tra quản trị dữ liệu (Data governance checklist):**
- [x] Tập tài liệu (Corpus) chỉ chứa nguồn công khai/được phép dùng và không chứa dữ liệu cá nhân, thông tin đăng nhập hoặc tài liệu nội bộ.
- [x] Mỗi tài liệu có `source_url`, `retrieved_at`, `document_version` (hoặc ngày hiệu lực) trong metadata.

### Cấu trúc Metadata (Metadata Schema)

| Trường metadata | Kiểu | Ví dụ giá trị | Tại sao hữu ích cho truy xuất (retrieval)? |
|----------------|------|---------------|-------------------------------|
| `audience` | string (student / faculty / staff / all) | `student` | Lọc theo đối tượng hỏi, tránh lẫn quy định của sinh viên với của nhân viên |
| `category` | string | `circulation`, `room_booking` | Thu hẹp theo loại dịch vụ |
| `department` | string | `library` | Lọc theo đơn vị phụ trách |
| `language` | string | `en` | Lọc theo ngôn ngữ nếu corpus đa ngữ |
| `source_url`, `retrieved_at`, `document_version` | string | `2026-09-19`, `not-stated` | Truy vết nguồn và phiên bản |

---

## 2. Thiết kế chiến lược (Strategy Design) — Nhóm (15 điểm)

> Mỗi thành viên thử **một chiến lược khác nhau** trên cùng bộ tài liệu; nhóm tổng hợp và so sánh ở đây.

### Phân tích đường cơ sở (Baseline Analysis)

`ChunkingStrategyComparator().compare(text, chunk_size=300)` trên phần thân (đã bỏ frontmatter):

| Tài liệu | Chiến lược (Strategy) | Số lượng Chunk | Độ dài trung bình | Giữ được ngữ cảnh không? |
|-----------|----------|-------------|------------|-------------------|
| student-borrowing-policy (1241 ký tự) | FixedSizeChunker (`fixed_size`) | 5 | 248 | Không, cắt giữa câu |
| | SentenceChunker (`by_sentences`) | 5 | 246 | Tạm, nhưng dòng gạch đầu dòng bị dính nhau |
| | RecursiveChunker (`recursive`) | 6 | 205 | Tốt, cắt theo đoạn/dòng |
| reserve-a-room (1029 ký tự) | FixedSizeChunker (`fixed_size`) | 4 | 257 | Không, cắt giữa câu |
| | SentenceChunker (`by_sentences`) | 3 | 340 | Tạm |
| | RecursiveChunker (`recursive`) | 5 | 204 | Tốt |
| library-card-account (1151 ký tự) | FixedSizeChunker (`fixed_size`) | 4 | 288 | Không |
| | SentenceChunker (`by_sentences`) | 4 | 285 | Tạm |
| | RecursiveChunker (`recursive`) | 6 | 190 | Tốt |

### Chiến lược của từng thành viên

**Thành viên 1 — Trần Anh Vũ**
- **Loại chiến lược:** custom, chunk theo heading (`HeadingChunker`).
- **Mô tả & lý do chọn cho chủ đề này:** Tài liệu quy định của thư viện đã được chia sẵn thành mục `##`/`###`, mỗi mục là một đơn vị ngữ nghĩa trọn vẹn (ví dụ "Fines and Lost Items", "Capacity Rule"). Mỗi mục thành một chunk, có gắn lại tiêu đề `# Title` và tiêu đề mục để chunk không mất ngữ cảnh; mục dài hơn 600 ký tự hạ xuống `RecursiveChunker`.
- **Code snippet (nếu custom):** xem `HeadingChunker` trong `bench.py`.
```python
for header, content in sections:
    prefix = f"# {title}\n{header}\n" if header else f"# {title}\n"
    if len(prefix) + len(content) <= self.max_size:
        chunks.append(prefix + content)
    else:
        chunks.extend(prefix + part for part in self._fallback.chunk(content))
```

**Thành viên 2 — [Tên]**
- **Loại chiến lược:** [FixedSize (chunk_size=300, overlap=50) — chạy `python bench.py fixed`]
- **Mô tả & lý do chọn:** [Điền]
- **Code snippet (nếu custom):** không

**Thành viên 3 — [Tên]**
- **Loại chiến lược:** [Recursive (chunk_size=300) — chạy `python bench.py recursive`]
- **Mô tả & lý do chọn:** [Điền]
- **Code snippet (nếu custom):** không

### So Sánh Giữa Các Thành Viên

Số liệu dưới đây do một máy chạy cả ba chiến lược trên cùng corpus và embedder (`paraphrase-multilingual-MiniLM-L12-v2`). Mỗi thành viên nên tự chạy lại để xác nhận.

| Thành viên | Chiến lược (Strategy) | Điểm truy xuất (/10) | Điểm mạnh | Điểm yếu |
|-----------|----------|----------------------|-----------|----------|
| Trần Anh Vũ | Heading | 9 | Mỗi chunk là một mục trọn vẹn, có tiêu đề nên ngữ cảnh rõ; giữ được đáp án trong top-3 khi có filter | Nhiều chunk hơn (35); các mục cùng tài liệu có điểm gần nhau nên câu 4 xếp sai mục lên top-1 |
| [Tên 2] | FixedSize (300, overlap 50) | 7 | Đơn giản, độ dài chunk đều | Cắt giữa câu; khi không có filter thì chunk chứa đáp án của câu 5 rơi khỏi top-3 |
| [Tên 3] | Recursive (300) | 8 | Cắt theo đoạn/dòng nên chunk mạch lạc hơn Fixed | Không có tiêu đề trong chunk nên mất ngữ cảnh mục |

**Chiến lược nào tốt nhất cho chủ đề này? Tại sao?**
> Chunk theo heading cho điểm cao nhất (9/10) vì tài liệu quy định vốn đã chia theo mục có ý nghĩa, và việc gắn lại tiêu đề vào chunk giúp embedding "biết" chunk nói về gì. Tuy nhiên với corpus chỉ 6 tài liệu nhỏ, chênh lệch 7, 8 và 9 chưa đủ để kết luận chắc chắn, và cả ba đều gặp cùng một lỗi ở câu 4 (xem mục 3).

---

## 3. Câu hỏi đánh giá & Chất lượng truy xuất (Retrieval Quality) — Nhóm (10 điểm)

### Câu hỏi đánh giá & Câu trả lời chuẩn (nhóm thống nhất)

| # | Câu hỏi (Query) | Câu trả lời chuẩn (Gold Answer) | Chunk nào chứa thông tin? |
|---|-------|-------------------------------|--------------------------|
| 1 | What is the overdue fine for a late book? | 20,000 VND per day per item | `student-borrowing-policy`, mục Fines and Lost Items |
| 2 | In which situations can I not renew my borrowed materials? | Khi tài liệu đã quá hạn, hoặc có người khác đã đặt giữ | `renewal-guide`, mục When Renewal Is Not Allowed |
| 3 | How do I cancel a room reservation? | Liên hệ thư viện qua điện thoại, email, Facebook, hoặc nói với nhân viên ở Service/Information Desk | `reserve-a-room`, mục Booking and Cancellation |
| 4 | How many people must be in my group to book a study room? | Nhóm đăng ký phải đạt ít nhất 50% sức chứa phòng và không vượt sức chứa tối đa | `reserve-a-room`, mục Capacity Rule |
| 5 | What support does the library provide for my courses and required readings? (`metadata_filter={"audience": "student"}`) | Course readings, subject guides, required reading lists by course | `undergraduate-student-services`, mục Learning Support |

### Tổng hợp chất lượng truy xuất của nhóm

> Cách chấm (theo `docs/SCORING.md`): **2 điểm/câu**: top-3 chứa chunk liên quan và ngữ cảnh có đáp án (2 nếu gold ở top-1), có liên quan nhưng không ở top-1 (1), không có trong top-3 (0).

| # | Câu hỏi | Chiến lược tốt nhất cho câu này | Có chunk liên quan trong top-3? | Ghi chú |
|---|---------|-------------------------------|-------------------------------|---------|
| 1 | Phí quá hạn | Cả ba (2/2) | Có | Câu tra số liệu, dễ |
| 2 | Khi nào không gia hạn | Recursive, Heading (2/2); Fixed 1/2 | Có | Hai tài liệu cùng nói về gia hạn |
| 3 | Huỷ đặt phòng | Cả ba (2/2) | Có | Tiêu đề mục chứa đúng từ "Cancellation" |
| 4 | Số người tối thiểu | Không chiến lược nào (cả ba 1/2) | Có, nhưng không ở top-1 | Xem failure case bên dưới |
| 5 | Hỗ trợ học tập (cần filter) | Heading (2/2); Fixed và Recursive 1/2 | Có (khi có filter) | Không filter thì `fixed` mất hẳn chunk chứa đáp án |

**Failure case (câu 4):** top-1 là mục "Usage Time" (score 0.563) còn mục "Capacity Rule" chứa đáp án chỉ đứng hạng 2 (0.433). Nguyên nhân: mục Usage Time lặp các từ "Group Study … Room" giống câu hỏi, và cosine đo độ giống chủ đề chứ không đo việc chunk có chứa đáp án hay không. Đề xuất sửa: thêm bước rerank, hoặc viết lại truy vấn cho cụ thể ("capacity" / "minimum group size").

**Lọc bằng metadata có giúp ích không? Ở câu hỏi nào?**
> Có, ở câu 5. Không filter thì hai chunk của tài liệu dành cho nhân viên (`professional-staff-services`) chiếm slot top-1 và top-3 (chiến lược Heading), và với chiến lược Fixed thì cả top-3 không còn chunk chứa "required reading lists". Có `audience=student` thì chunk đúng quay lại top-3. Đánh đổi: filter cứng có thể loại nhầm tài liệu `audience=all` nếu ta chỉ lọc bằng `student`.

---

## 4. Thuyết trình (Demo) & Bài học nhóm — Nhóm (5 điểm)

**Những phân tích (insights) hay nhất nhóm sẽ trình bày:**
> 1. Chấm theo `doc_id` cho 5/5 ở cả ba chiến lược, nhưng chấm theo chuỗi đáp án chỉ còn 7, 8 và 9 trên 10.
> 2. Metadata filter `audience` có tác dụng thật ở câu 5 (A/B có và không filter).
> 3. Failure case câu 4: cosine ưu tiên chunk cùng chủ đề hơn chunk chứa đáp án.

**Bài học rút ra khi so sánh trong nhóm:**
> Cùng một corpus và embedder, cách chia chunk làm thay đổi việc chunk chứa đáp án có lọt top-3 hay không. Chunk có tiêu đề mục (Heading) giữ được ngữ cảnh tốt hơn chunk cắt cứng theo số ký tự.

**Nếu làm lại, nhóm sẽ thay đổi gì trong chiến lược dữ liệu (data strategy)?**
> Thu thập thêm tài liệu dành cho giảng viên/nhân viên cùng chủ đề (ví dụ hạn mức mượn sách của nhân viên) để A/B filter rõ hơn, và ghi `audience_detail` đầy đủ. Ngoài ra sẽ thêm overlap hoặc rerank để giảm lỗi kiểu câu 4.

---

## Tự Đánh Giá (Phần Nhóm)

| Tiêu chí | Điểm tự đánh giá |
|----------|-------------------|
| Lựa chọn tài liệu (Document Set Quality) | 8 / 10 |
| Thiết kế chiến lược (Strategy Design) | 12 / 15 |
| Chất lượng truy xuất (Retrieval Quality) | 8 / 10 |
| Thuyết trình (Demo) | [Điền sau demo] / 5 |
| **Tổng phần nhóm** | **[Điền] / 40** |
