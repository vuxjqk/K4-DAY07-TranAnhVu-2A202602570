"""Benchmark 3 chiến lược chunking trên data/Library.

Chạy:  python bench.py [fixed|recursive|heading|all]   (mặc định: all)
Đổi chiến lược của riêng bạn bằng CHUNKER bên dưới (hoặc truyền đối số).
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv

from src.chunking import FixedSizeChunker, RecursiveChunker
from src.embeddings import (
    GEMINI_EMBEDDING_MODEL,
    LOCAL_EMBEDDING_MODEL,
    OPENAI_EMBEDDING_MODEL,
    GeminiEmbedder,
    LocalEmbedder,
    OpenAIEmbedder,
    _mock_embed,
)
from src.models import Document
from src.store import EmbeddingStore

DATA_DIR = Path("data/Library")
CHUNK_SIZE = 300
CHUNKER = "all"  # <- dòng duy nhất mỗi thành viên đổi: fixed | recursive | heading


class HeadingChunker:
    """Mỗi mục `##`/`###` là một chunk; mục quá dài hạ xuống Recursive.

    Mỗi chunk được gắn lại đường dẫn tiêu đề (breadcrumb) để không mất ngữ cảnh.
    """

    def __init__(self, max_size: int = CHUNK_SIZE * 2) -> None:
        self.max_size = max_size
        self._fallback = RecursiveChunker(chunk_size=max_size)

    def chunk(self, text: str) -> list[str]:
        title, sections, path, body = "", [], [], []

        def flush() -> None:
            content = "\n".join(body).strip()
            if content:
                sections.append(("\n".join(path), content))
            body.clear()

        for line in text.splitlines():
            m = re.match(r"^(#{1,3})\s+(.*)", line)
            if not m:
                body.append(line)
                continue
            flush()
            level = len(m.group(1))
            if level == 1:
                title, path[:] = m.group(2), []
            else:
                del path[level - 2 :]
                path.append(line)
        flush()

        chunks = []
        for header, content in sections:
            prefix = f"# {title}\n{header}\n" if header else f"# {title}\n"
            if len(prefix) + len(content) <= self.max_size:
                chunks.append(prefix + content)
            else:
                chunks.extend(prefix + part for part in self._fallback.chunk(content))
        return chunks


CHUNKERS = {
    "fixed": FixedSizeChunker(chunk_size=CHUNK_SIZE, overlap=50),
    "recursive": RecursiveChunker(chunk_size=CHUNK_SIZE),
    "heading": HeadingChunker(),
}

# gold_docs: doc_id đúng · must_contain: chuỗi đặc trưng phải có trong ngữ cảnh top-k (any-of)
QUERIES = [
    {
        "q": "What is the overdue fine for a late book?",
        "gold_docs": {"student-borrowing-policy"},
        "must_contain": ["20,000 VND per day"],
        "filter": None,
    },
    {
        "q": "In which situations can I not renew my borrowed materials?",
        "gold_docs": {"renewal-guide", "student-borrowing-policy"},
        "must_contain": ["already overdue", "not overdue"],
        "filter": None,
    },
    {
        "q": "How do I cancel a room reservation?",
        "gold_docs": {"reserve-a-room"},
        "must_contain": ["phone, email, Facebook"],
        "filter": None,
    },
    {
        "q": "How many people must be in my group to book a study room?",
        "gold_docs": {"reserve-a-room"},
        "must_contain": ["at least 50%"],
        "filter": None,
    },
    {  # Không nêu người hỏi là ai; staff cũng có "Teaching Support/course reserves" -> cần filter
        "q": "What support does the library provide for my courses and required readings?",
        "gold_docs": {"undergraduate-student-services"},
        "must_contain": ["required reading lists"],
        "filter": {"audience": "student"},
    },
]


def parse_frontmatter(raw: str) -> tuple[dict, str]:
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", raw.lstrip("﻿"), re.S)
    if not m:
        return {}, raw
    meta = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip().strip('"')
    return meta, m.group(2)


def make_embedder():
    load_dotenv(override=False)
    provider = os.getenv("EMBEDDING_PROVIDER", "mock").strip().lower()
    try:
        if provider == "local":
            return LocalEmbedder(os.getenv("LOCAL_EMBEDDING_MODEL", LOCAL_EMBEDDING_MODEL))
        if provider == "openai":
            return OpenAIEmbedder(os.getenv("OPENAI_EMBEDDING_MODEL", OPENAI_EMBEDDING_MODEL))
        if provider == "gemini":
            return GeminiEmbedder(os.getenv("GEMINI_EMBEDDING_MODEL", GEMINI_EMBEDDING_MODEL))
    except Exception as exc:  # thiếu thư viện/key -> mock
        print(f"[!] Không bật được embedder '{provider}': {exc}")
    return _mock_embed


class CachedEmbedder:
    """Cache theo nội dung để chạy lại/chạy 3 chiến lược không embed trùng."""

    def __init__(self, inner) -> None:
        self.inner, self.cache = inner, {}
        self._backend_name = getattr(inner, "_backend_name", inner.__class__.__name__)

    def __call__(self, text: str) -> list[float]:
        if text not in self.cache:
            self.cache[text] = self.inner(text)
        return self.cache[text]


def build_store(chunker, embedder) -> EmbeddingStore:
    docs = []
    for path in sorted(DATA_DIR.glob("*.md")):
        meta, body = parse_frontmatter(path.read_text(encoding="utf-8"))
        for i, chunk in enumerate(chunker.chunk(body)):
            docs.append(Document(f"{path.stem}#{i}", chunk, {**meta, "doc_id": path.stem, "chunk_index": i}))
    store = EmbeddingStore(collection_name="bench", embedding_fn=embedder)
    store.add_documents(docs)
    return store


def score(results: list[dict], q: dict) -> tuple[int, bool, bool]:
    """(điểm 0-2, gold_doc có trong top-3, ngữ cảnh chứa đáp án)."""
    doc_hit = [r["metadata"]["doc_id"] in q["gold_docs"] for r in results]
    context = " ".join(r["content"] for r in results)
    has_answer = any(s in context for s in q["must_contain"])
    top1_answer = bool(results) and any(s in results[0]["content"] for s in q["must_contain"])
    if not has_answer or not any(doc_hit):
        return 0, any(doc_hit), has_answer
    return (2 if doc_hit[0] and top1_answer else 1), True, has_answer


def show(results: list[dict], q: dict) -> None:
    for rank, r in enumerate(results, 1):
        ok = "v" if any(s in r["content"] for s in q["must_contain"]) else " "
        print(f"    {rank}. {r['score']:+.3f} [{ok}] {r['id']:<36} {r['content'][:60]!r}")


def run(name: str, embedder) -> int:
    store = build_store(CHUNKERS[name], embedder)
    print(f"\n{'=' * 78}\nChien luoc: {name} | {store.get_collection_size()} chunk da nap\n{'=' * 78}")
    total = naive = 0
    for n, q in enumerate(QUERIES, 1):
        results = store.search_with_filter(q["q"], top_k=3, metadata_filter=q["filter"])
        pts, doc_hit, has_answer = score(results, q)
        total, naive = total + pts, naive + doc_hit
        print(f"\n  Q{n}: {q['q']}  (filter={q['filter']})")
        show(results, q)
        print(f"    -> diem={pts}/2 | gold doc trong top-3={doc_hit} | ngu canh chua dap an={has_answer}")

    q = next(q for q in QUERIES if q["filter"])
    print(f"\n  A/B filter cho: {q['q']}")
    for label, flt in (("CO filter", q["filter"]), ("KHONG filter", None)):
        res = store.search_with_filter(q["q"], top_k=3, metadata_filter=flt)
        print(f"   {label}:")
        show(res, q)
    print(f"\n  TONG {name}: {total}/10 diem (cham chat) | {naive}/5 (chi kiem doc_id)")
    return total


def main() -> None:
    choice = sys.argv[1] if len(sys.argv) > 1 else CHUNKER
    embedder = CachedEmbedder(make_embedder())
    print(f"Embedding backend: {embedder._backend_name}")
    if embedder.inner is _mock_embed:
        print("[!] MockEmbedder khong co ngu nghia -> diem so chi la nhieu, khong dung de ket luan.")
    names = list(CHUNKERS) if choice == "all" else [choice]
    totals = {n: run(n, embedder) for n in names}
    print("\nTONG KET:", ", ".join(f"{n}={t}/10" for n, t in totals.items()))


if __name__ == "__main__":
    main()
