import json
import re
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
CARDS_JSON = BASE_DIR / "cards" / "knowledge_cards.json"
CHUNKS_DIR = BASE_DIR / "chunks"
CHUNKS_JSON = CHUNKS_DIR / "knowledge_chunks.json"
CHUNKS_JSONL = CHUNKS_DIR / "knowledge_chunks.jsonl"

MAX_CHUNK_CHARS = 900
SENTENCE_END_RE = re.compile(r"(?<=[.!?])\s+")


def load_cards() -> list[dict]:
    return json.loads(CARDS_JSON.read_text(encoding="utf-8"))


def split_sentences(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    sentences = [part.strip() for part in SENTENCE_END_RE.split(text) if part.strip()]
    if not sentences:
        return [text]
    return sentences


def split_long_unit(text: str, max_chars: int = MAX_CHUNK_CHARS) -> list[str]:
    if len(text) <= max_chars:
        return [text]

    words = text.split()
    parts: list[str] = []
    current: list[str] = []

    for word in words:
        candidate = " ".join(current + [word]).strip()
        if current and len(candidate) > max_chars:
            parts.append(" ".join(current).strip())
            current = [word]
        else:
            current.append(word)

    if current:
        parts.append(" ".join(current).strip())

    return parts


def chunk_sentences(sentences: list[str], max_chars: int = MAX_CHUNK_CHARS) -> list[str]:
    if not sentences:
        return []

    units: list[str] = []
    for sentence in sentences:
        units.extend(split_long_unit(sentence, max_chars=max_chars))

    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for sentence in units:
        sentence_len = len(sentence) + (1 if current else 0)
        if current and current_len + sentence_len > max_chars:
            chunks.append(" ".join(current).strip())
            overlap = current[-1:] if len(current) > 1 else []
            current = overlap + [sentence]
            current_len = len(" ".join(current))
            continue

        current.append(sentence)
        current_len = len(" ".join(current))

    if current:
        chunks.append(" ".join(current).strip())

    return chunks


def build_chunk_record(card: dict, chunk_text: str, index: int, total: int) -> dict:
    chunk_id = f"{card['id']}-chunk-{index}"
    title = card["title"]
    if total > 1:
        title = f"{title} [chunk {index}/{total}]"

    return {
        "id": chunk_id,
        "card_id": card["id"],
        "doc_id": card["doc_id"],
        "doc_title": card["doc_title"],
        "title": title,
        "topic": card["topic"],
        "section": card["section"],
        "source": card["source"],
        "usage": card["usage"],
        "chunk_index": index,
        "chunk_total": total,
        "content": chunk_text,
    }


def build_chunks(cards: list[dict]) -> list[dict]:
    records: list[dict] = []
    for card in cards:
        sentences = split_sentences(card["content"])
        chunks = chunk_sentences(sentences)
        if not chunks:
            continue
        total = len(chunks)
        for index, chunk_text in enumerate(chunks, 1):
            records.append(build_chunk_record(card, chunk_text, index, total))
    return records


def main() -> None:
    CHUNKS_DIR.mkdir(parents=True, exist_ok=True)
    cards = load_cards()
    chunks = build_chunks(cards)

    CHUNKS_JSON.write_text(json.dumps(chunks, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    with CHUNKS_JSONL.open("w", encoding="utf-8") as handle:
        for chunk in chunks:
            handle.write(json.dumps(chunk, ensure_ascii=False) + "\n")

    print(f"loaded {len(cards)} cards")
    print(f"wrote {len(chunks)} chunks")
    print(CHUNKS_JSON)
    print(CHUNKS_JSONL)


if __name__ == "__main__":
    main()
