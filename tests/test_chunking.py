from app.chunking import chunk_text


def test_chunk_text_handles_empty_and_short_content():
    assert chunk_text("") == []
    assert chunk_text("  \n\n ") == []
    assert chunk_text("一段短资料。") == ["一段短资料。"]


def test_chunk_text_respects_limit_and_overlap():
    text = "第一部分。" + ("甲" * 260) + "第二部分。" + ("乙" * 260) + "结尾。"
    chunks = chunk_text(text, max_chars=220, overlap=30)

    assert len(chunks) >= 3
    assert all(chunk for chunk in chunks)
    assert all(len(chunk) <= 220 for chunk in chunks)
    assert "第一部分" in chunks[0]
    assert "结尾" in chunks[-1]


def test_chunk_text_prefers_sentence_boundary():
    text = "甲" * 150 + "。这里应该成为分界。" + "乙" * 150
    chunks = chunk_text(text, max_chars=180, overlap=20)

    assert chunks[0].endswith("。")
    assert len(chunks) == 2
