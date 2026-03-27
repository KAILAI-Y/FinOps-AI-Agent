import json
import os
from pathlib import Path

import faiss
import numpy as np
import torch
from transformers import AutoModel, AutoTokenizer


BASE_DIR = Path(__file__).resolve().parent
CHUNKS_JSON = BASE_DIR / "chunks" / "knowledge_chunks.json"
INDEX_DIR = BASE_DIR / "index"
SEMANTIC_FAISS_INDEX = INDEX_DIR / "knowledge_semantic.faiss"
SEMANTIC_METADATA_JSON = INDEX_DIR / "semantic_metadata.json"
SEMANTIC_CONFIG_JSON = INDEX_DIR / "semantic_index_config.json"
DEFAULT_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
torch.set_num_threads(1)


def load_chunks() -> list[dict]:
    return json.loads(CHUNKS_JSON.read_text(encoding="utf-8"))


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


def mean_pool(last_hidden_state: torch.Tensor, attention_mask: torch.Tensor) -> torch.Tensor:
    mask = attention_mask.unsqueeze(-1).expand(last_hidden_state.size()).float()
    masked = last_hidden_state * mask
    summed = masked.sum(dim=1)
    counts = mask.sum(dim=1).clamp(min=1e-9)
    return summed / counts


def encode_texts(tokenizer: AutoTokenizer, model: AutoModel, texts: list[str], batch_size: int = 8) -> np.ndarray:
    rows: list[np.ndarray] = []
    model.eval()
    with torch.inference_mode():
        for start in range(0, len(texts), batch_size):
            batch = texts[start : start + batch_size]
            encoded = tokenizer(batch, padding=True, truncation=True, return_tensors="pt")
            outputs = model(**encoded)
            pooled = mean_pool(outputs.last_hidden_state, encoded["attention_mask"])
            normalized = torch.nn.functional.normalize(pooled, p=2, dim=1)
            rows.append(normalized.cpu().numpy().astype(np.float32))
            print(f"encoded {min(start + batch_size, len(texts))}/{len(texts)}")
    return np.vstack(rows)


def main() -> None:
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    chunks = load_chunks()
    tokenizer = AutoTokenizer.from_pretrained(DEFAULT_MODEL_NAME)
    model = AutoModel.from_pretrained(DEFAULT_MODEL_NAME)
    matrix = encode_texts(tokenizer, model, [chunk["content"] for chunk in chunks])

    index = faiss.IndexFlatIP(matrix.shape[1])
    index.add(matrix)
    faiss.write_index(index, str(SEMANTIC_FAISS_INDEX))

    SEMANTIC_METADATA_JSON.write_text(
        json.dumps(build_metadata(chunks), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    SEMANTIC_CONFIG_JSON.write_text(
        json.dumps(
            {
                "model_name": DEFAULT_MODEL_NAME,
                "dimension": int(matrix.shape[1]),
                "normalize_embeddings": True,
                "pooling": "mean",
                "similarity": "inner_product",
                "implementation": "transformers",
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    print(f"loaded {len(chunks)} chunks")
    print(f"model {DEFAULT_MODEL_NAME}")
    print(f"embedding dim {matrix.shape[1]}")
    print(f"wrote {SEMANTIC_FAISS_INDEX}")
    print(f"wrote {SEMANTIC_METADATA_JSON}")
    print(f"wrote {SEMANTIC_CONFIG_JSON}")


if __name__ == "__main__":
    main()
