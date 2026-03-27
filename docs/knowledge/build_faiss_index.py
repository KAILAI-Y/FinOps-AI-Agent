import json
import math
import re
from collections import Counter
from pathlib import Path

import faiss
import numpy as np


BASE_DIR = Path(__file__).resolve().parent
CHUNKS_JSON = BASE_DIR / "chunks" / "knowledge_chunks.json"
INDEX_DIR = BASE_DIR / "index"
FAISS_INDEX = INDEX_DIR / "knowledge.faiss"
METADATA_JSON = INDEX_DIR / "metadata.json"
VECTORIZER_JSON = INDEX_DIR / "vectorizer.json"

TOKEN_RE = re.compile(r"[a-z0-9_./-]+")


def tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())


def load_chunks() -> list[dict]:
    return json.loads(CHUNKS_JSON.read_text(encoding="utf-8"))


def build_vocabulary(chunks: list[dict], min_doc_freq: int = 2) -> tuple[dict[str, int], list[float]]:
    doc_freq: Counter[str] = Counter()
    for chunk in chunks:
        tokens = set(tokenize(chunk["content"]))
        doc_freq.update(tokens)

    terms = sorted(token for token, freq in doc_freq.items() if freq >= min_doc_freq)
    vocab = {term: index for index, term in enumerate(terms)}
    total_docs = len(chunks)
    idf = [math.log((1 + total_docs) / (1 + doc_freq[term])) + 1.0 for term in terms]
    return vocab, idf


def vectorize(text: str, vocab: dict[str, int], idf: list[float]) -> np.ndarray:
    vec = np.zeros(len(vocab), dtype=np.float32)
    tokens = tokenize(text)
    if not tokens or not vocab:
        return vec

    counts = Counter(token for token in tokens if token in vocab)
    if not counts:
        return vec

    total_terms = sum(counts.values())
    for token, count in counts.items():
        index = vocab[token]
        tf = count / total_terms
        vec[index] = tf * idf[index]

    norm = np.linalg.norm(vec)
    if norm > 0:
        vec /= norm
    return vec


def build_matrix(chunks: list[dict], vocab: dict[str, int], idf: list[float]) -> np.ndarray:
    matrix = np.vstack([vectorize(chunk["content"], vocab, idf) for chunk in chunks]).astype(np.float32)
    return matrix


def build_metadata(chunks: list[dict]) -> list[dict]:
    keep_fields = [
        "id",
        "card_id",
        "doc_id",
        "doc_title",
        "title",
        "topic",
        "section",
        "source",
        "usage",
        "chunk_index",
        "chunk_total",
        "content",
    ]
    return [{field: chunk[field] for field in keep_fields} for chunk in chunks]


def main() -> None:
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    chunks = load_chunks()
    vocab, idf = build_vocabulary(chunks)
    matrix = build_matrix(chunks, vocab, idf)

    index = faiss.IndexFlatIP(matrix.shape[1])
    index.add(matrix)
    faiss.write_index(index, str(FAISS_INDEX))

    METADATA_JSON.write_text(json.dumps(build_metadata(chunks), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    VECTORIZER_JSON.write_text(
        json.dumps(
            {
                "token_pattern": TOKEN_RE.pattern,
                "dimension": len(vocab),
                "vocab": vocab,
                "idf": idf,
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    print(f"loaded {len(chunks)} chunks")
    print(f"vocab size {len(vocab)}")
    print(f"embedding dim {matrix.shape[1]}")
    print(f"wrote {FAISS_INDEX}")
    print(f"wrote {METADATA_JSON}")
    print(f"wrote {VECTORIZER_JSON}")


if __name__ == "__main__":
    main()
