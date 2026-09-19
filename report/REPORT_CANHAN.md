# Báo Cáo Cá Nhân — Lab 7: Embedding & Vector Store

**Họ tên:** Trần Anh Vũ (MSSV 2A202602570)
**Nhóm:** [Điền tên nhóm]
**Ngày:** 2026-09-19

> **Nộp 1 bản / sinh viên.** Phần nhóm (lựa chọn tài liệu, thiết kế chiến lược, bộ câu hỏi đánh giá, demo) nộp chung 1 bản trong `REPORT_NHOM.md`. Chi tiết thang điểm: `docs/SCORING.md`.

**Tổng điểm phần cá nhân: 60** = Khởi động (5) + Hướng tiếp cận (10) + Hoàn thiện code (30) + Dự đoán độ tương tự (5) + Kết quả truy xuất của tôi (10).

---

## 1. Khởi động (Warm-up) — Cá nhân (5 điểm)

### Độ tương tự Cosine (Cosine Similarity) (Bài tập 1.1)

**Độ tương tự cosine cao (High cosine similarity) nghĩa là gì?**
> Hai vector embedding có hướng gần nhau, tức hai đoạn text có nghĩa gần nhau (không nhất thiết trùng từ). Giá trị tiến về 1 là cùng nghĩa, về 0 là không liên quan.

**Ví dụ có độ tương tự CAO:**
- Câu A: Reserve a study room for my group.
- Câu B: Booking a room for group study.
- Tại sao tương đồng: cùng ý định đặt phòng học nhóm, chỉ đổi cách diễn đạt. Điểm thực tế 0.848 (embedder `paraphrase-multilingual-MiniLM-L12-v2`).

**Ví dụ có độ tương tự THẤP:**
- Câu A: The library closes at night.
- Câu B: Neural networks learn from data.
- Tại sao khác: hai câu thuộc hai chủ đề hoàn toàn khác nhau. Điểm thực tế -0.076.

**Tại sao độ tương tự cosine (cosine similarity) được ưu tiên hơn khoảng cách Euclid (Euclidean distance) cho text embeddings?**
> Cosine chỉ đo góc giữa hai vector nên không bị ảnh hưởng bởi độ dài vector (ví dụ đoạn dài hay ngắn), còn khoảng cách Euclid bị lệch theo độ lớn. Với embedding đã chuẩn hoá thì cosine bằng dot product nên tính rất gọn.

### Bài toán tính toán Chunking (Bài tập 1.2)

**Tài liệu 10,000 ký tự, chunk_size=500, overlap=50. Bao nhiêu chunks?**
> Phép tính: ceil((10000 − 50) / (500 − 50)) = ceil(9950 / 450) = ceil(22.11)
> Đáp án: **23 chunk** (đã kiểm lại bằng `FixedSizeChunker(500, 50).chunk("a"*10000)`, cho kết quả 23).

**Nếu độ chồng chéo (overlap) tăng lên 100, số lượng chunk thay đổi thế nào? Tại sao muốn độ chồng chéo nhiều hơn?**
> Số chunk tăng lên 25 (ceil(9900/400)), vì mỗi bước tiến chỉ còn 400 ký tự. Overlap lớn giúp thông tin nằm ở ranh giới hai chunk không bị cắt đứt và có thêm cơ hội lọt vào top-k, đổi lại tốn thêm chunk và chi phí embedding.

---

## 2. Hướng tiếp cận của tôi (My Approach) — Cá nhân (10 điểm)

### Các hàm chia nhỏ (Chunking Functions)

**`SentenceChunker.chunk`** — hướng tiếp cận:
> Tách câu bằng `re.split(r"(?<=[.!?])\s+", text)`. Lookbehind giữ nguyên dấu câu trong câu, không bị nuốt. Sau đó gom mỗi `max_sentences_per_chunk` câu thành một chunk. Text rỗng hoặc toàn khoảng trắng trả `[]`. Edge case chưa xử lý: chữ viết tắt (`TS.`, `v.v.`, `e.g.`) và số thập phân sẽ bị cắt sai câu.

**`RecursiveChunker.chunk` / `_split`** — hướng tiếp cận:
> Thử lần lượt các separator `["\n\n", "\n", ". ", " ", ""]`. Mảnh nào vẫn dài hơn `chunk_size` thì đệ quy xuống separator nhỏ hơn (chiều xuống), sau đó các mảnh nhỏ liền kề được gộp lại tới sát `chunk_size` (chiều lên) để không sinh chunk vụn. Base case gồm ba trường hợp: text đã ngắn hơn `chunk_size`, hết separator hoặc separator là chuỗi rỗng (cắt cứng theo `chunk_size`), và separator không xuất hiện trong text (chuyển sang separator kế tiếp).

### Lớp EmbeddingStore

**`add_documents` + `search`** — hướng tiếp cận:
> Lưu in-memory dưới dạng list các record `{id, content, metadata, embedding}` (bỏ hẳn nhánh ChromaDB vì test không cần). `_make_record` copy metadata và luôn đảm bảo có `doc_id`. `search` và `search_with_filter` cùng gọi `_search_records`, tính cosine giữa embedding của query và từng record, sắp giảm dần, lấy top_k và bỏ vector embedding khỏi kết quả.

**`search_with_filter` + `delete_document`** — hướng tiếp cận:
> Lọc **trước** rồi mới search trên tập ứng viên đã lọc. Nếu lấy top-k trước rồi lọc sau, k slot có thể bị tài liệu sai chiếm hết và kết quả trả về rỗng dù store vẫn còn tài liệu hợp lệ. `delete_document` xây lại list, loại các record có `metadata['doc_id']` khớp, trả `True` nếu số record giảm.

### Tác tử KnowledgeBaseAgent

**`answer`** — hướng tiếp cận:
> Lấy top-k chunk, đánh số `[1] [2] [3]` kèm `doc_id` nguồn rồi đưa vào prompt. Prompt yêu cầu chỉ trả lời dựa trên ngữ cảnh, trích dẫn số đoạn, và nói rõ nếu không tìm thấy. Nếu store rỗng thì trả thông báo mà không gọi `llm_fn`.

---

## 3. Hoàn thiện code (Core Implementation) — Cá nhân (30 điểm)

Vượt qua bộ kiểm thử là điều kiện tính điểm phần này.

### Kết Quả Kiểm Thử (Test Results)

```
$ pytest tests/ -v
...
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_returns_true_for_existing_doc PASSED [100%]

============================= 42 passed in 0.08s ==============================
```

**Số lượng bài test vượt qua (pass):** 42 / 42

---

## 4. Dự đoán độ tương tự (Similarity Predictions) — Cá nhân (5 điểm)

Embedder: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (local).

| Cặp | Câu A | Câu B | Dự đoán | Điểm thực tế | Đúng? |
|------|-----------|-----------|---------|--------------|-------|
| 1 | The library fines late returns. | Overdue books are charged a penalty per day. | cao | 0.468 | Đúng (mức trung bình khá) |
| 2 | How do I renew a book? | Extend the loan period of borrowed materials online. | cao | 0.212 | Sai |
| 3 | Reserve a study room for my group. | Booking a room for group study. | cao | 0.848 | Đúng |
| 4 | The library closes at night. | Neural networks learn from data. | thấp | -0.076 | Đúng |
| 5 | Undergraduate students can borrow 2 items. | I love eating pho for breakfast. | thấp | 0.033 | Đúng |

**Kết quả nào bất ngờ nhất? Điều này nói gì về cách embeddings biểu diễn ý nghĩa?**
> Cặp 2 bất ngờ nhất: một câu hỏi và một câu trả lời cùng nói về gia hạn sách nhưng chỉ đạt 0.212, vì mô hình paraphrase đo độ giống nhau về cách diễn đạt và dạng câu (hỏi so với khẳng định) nhiều hơn quan hệ hỏi–đáp. Cặp 1 cũng chỉ ở mức 0.468 dù cùng ý. Điều này cho thấy embedding bắt được nghĩa nhưng điểm số không tuyệt đối, và là lý do retrieval có thể xếp chunk "cùng chủ đề" cao hơn chunk thật sự chứa đáp án.

---

## 5. Kết quả truy xuất của tôi (Competition Results) — Cá nhân (10 điểm)

Chiến lược của tôi: **chunk theo heading** (`HeadingChunker` trong `bench.py`, mỗi mục `##`/`###` một chunk, gắn lại breadcrumb tiêu đề, mục dài hơn 600 ký tự hạ xuống Recursive). Corpus: `data/Library/` (6 tài liệu, 35 chunk). Embedder local ở trên, top-k = 3. Chi tiết trong `ket_qua_benchmark.txt`.

Lưu ý: chưa dùng LLM thật, nên cột "Câu trả lời của Agent" là đánh giá xem ngữ cảnh top-3 đưa cho agent có chứa đáp án hay không.

| # | Câu hỏi (Query) | Top-1 Chunk truy xuất được (tóm tắt) | Điểm Score | Có liên quan không? (Relevant) | Câu trả lời của Agent (tóm tắt) |
|---|-------|--------------------------------|-------|-----------|------------------------|
| 1 | What is the overdue fine for a late book? | `student-borrowing-policy#3` mục Fines and Lost Items | 0.511 | Có | Ngữ cảnh chứa "20,000 VND per day per item" → trả lời đúng |
| 2 | In which situations can I not renew my borrowed materials? | `renewal-guide#3` mục When Renewal Is Not Allowed | 0.614 | Có | Quá hạn hoặc có người khác đặt giữ → đúng |
| 3 | How do I cancel a room reservation? | `reserve-a-room#0` mục Booking and Cancellation | 0.592 | Có | Liên hệ qua phone, email, Facebook hoặc quầy dịch vụ → đúng |
| 4 | How many people must be in my group to book a study room? | `reserve-a-room#1` mục Usage Time | 0.563 | Không (đáp án ở top-2, `#5` Capacity Rule, score 0.433) | Ngữ cảnh top-3 có "at least 50% of the room's capacity" nhưng agent dễ bị nhiễu bởi top-1 |
| 5 | What support does the library provide for my courses and required readings? (filter `audience=student`) | `undergraduate-student-services#3` mục Learning Support | 0.607 | Có | course readings, subject guides, required reading lists → đúng |

**Bao nhiêu câu hỏi trả về chunk có liên quan trong top-3?** 5 / 5 (chấm chặt theo chuỗi đáp án: 9 / 10 điểm, câu 4 chỉ được 1 điểm vì đáp án không ở top-1)

**Điều hay nhất tôi học được từ thành viên khác / nhóm khác (qua demo):**
> Chấm benchmark chỉ theo `doc_id` thổi phồng kết quả: cả ba chiến lược đều được 5/5, nhưng khi kiểm chuỗi đáp án trong ngữ cảnh thì chỉ còn 7 (fixed), 8 (recursive) và 9 (heading) trên 10. [Bổ sung điều học được từ nhóm khác sau buổi demo.]

---

## Tự Đánh Giá (Phần Cá Nhân)

| Tiêu chí | Điểm tự đánh giá |
|----------|-------------------|
| Khởi động (Warm-up) | 5 / 5 |
| Hướng tiếp cận của tôi (My Approach) | 9 / 10 |
| Hoàn thiện code (Core Implementation — tests) | 30 / 30 |
| Dự đoán độ tương tự (Similarity Predictions) | 4 / 5 |
| Kết quả truy xuất của tôi (Competition Results) | 8 / 10 |
| **Tổng phần cá nhân** | **56 / 60** |
