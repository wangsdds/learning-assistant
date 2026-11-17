"""Split learning material into overlapping chunks for retrieval."""
import re


_BOUNDARIES = ("\n\n", "\n", "。", "！", "？", "；", ".", "!", "?", ";")


def chunk_text(text: str, max_chars: int = 700, overlap: int = 100) -> list[str]:
    """Return deterministic, sentence-aware chunks no longer than max_chars."""
    if max_chars <= 0:
        raise ValueError("max_chars must be positive")
    if overlap < 0 or overlap >= max_chars:
        raise ValueError("overlap must be between 0 and max_chars - 1")

    normalized = re.sub(r"\r\n?", "\n", text or "").strip()
    if not normalized:
        return []
    if len(normalized) <= max_chars:
        return [normalized]

    chunks: list[str] = []
    start = 0
    text_length = len(normalized)

    while start < text_length:
        end = min(start + max_chars, text_length)
        if end < text_length:
            search_start = start + max_chars // 2
            candidates = [normalized.rfind(boundary, search_start, end) for boundary in _BOUNDARIES]
            boundary = max(candidates)
            if boundary >= search_start:
                end = boundary + 1

        chunk = normalized[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= text_length:
            break
        start = max(end - overlap, start + 1)

    return chunks
