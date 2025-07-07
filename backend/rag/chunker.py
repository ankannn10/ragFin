# File: clearfiling/backend/rag/chunker.py

"""
Section-aware chunker for SEC filings.

Key features
------------
1. split_into_sections(text)  -> {"ITEM 1.": "...", ...}
2. chunk_text(text)           -> ["chunk1", "chunk2", ...]
3. chunk_sections(text)       -> [{section, chunk_index, text}, ...]
4. chunk_pdf(pdf_bytes)       -> same as (3) but starts from raw PDF bytes
5. chunk_html(html_bytes)     -> same as (3) but starts from raw HTML bytes
"""

import re
from typing import List, Dict

# Re-use the existing parsers without modifying them
from ..parser import (
    extract_text_from_pdf,    # accepts raw PDF bytes
    extract_text_from_html,   # accepts raw HTML bytes
)

# --------------------------------------------------------------------------- #
# 1. Section splitting
# --------------------------------------------------------------------------- #
def split_into_sections(text: str) -> Dict[str, str]:
    """
    Split filing text by standard SEC headings (ITEM 1., ITEM 1A., etc.).

    Returns
    -------
    Dict[str, str]
        Keys are section titles (upper-cased exactly as found),
        values are the section body text.
    """
    pattern = re.compile(r"(ITEM\s+\d+[A-Za-z]?\.)", re.IGNORECASE)
    matches = list(pattern.finditer(text))
    if not matches:
        return {"FULL_TEXT": text}

    sections: Dict[str, str] = {}
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        title = m.group(1).strip().upper()
        sections[title] = text[start:end].strip()

    return sections


# --------------------------------------------------------------------------- #
# 2. Chunking helpers
# --------------------------------------------------------------------------- #
def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    """
    Break a long text into word-count windows with overlap.

    Parameters
    ----------
    text : str
    chunk_size : int
        Target words per chunk.
    overlap : int
        Words reused at the beginning of the next chunk.

    Returns
    -------
    List[str]
    """
    words = text.split()
    step = max(chunk_size - overlap, 1)
    chunks = [
        " ".join(words[i : i + chunk_size])
        for i in range(0, len(words), step)
    ]
    return chunks


def chunk_sections(
    text: str,
    chunk_size: int = 500,
    overlap: int = 50,
) -> List[Dict[str, object]]:
    """
    High-level convenience: split into SEC sections then chunk each section.

    Returns
    -------
    List[Dict] with keys:
        section      : str
        chunk_index  : int
        text         : str
    """
    sections = split_into_sections(text)
    out: List[Dict[str, object]] = []

    for title, body in sections.items():
        for idx, chunk in enumerate(chunk_text(body, chunk_size, overlap)):
            out.append({"section": title, "chunk_index": idx, "text": chunk})

    return out


# --------------------------------------------------------------------------- #
# 3. PDF / HTML wrappers (use existing parser utilities)
# --------------------------------------------------------------------------- #
def chunk_pdf(
    pdf_bytes: bytes,
    chunk_size: int = 500,
    overlap: int = 50,
) -> List[Dict[str, object]]:
    """
    Extracts text from raw PDF bytes, then returns section-aware chunks.
    """
    text = extract_text_from_pdf(pdf_bytes)
    return chunk_sections(text, chunk_size, overlap)


def chunk_html(
    html_bytes: bytes,
    chunk_size: int = 500,
    overlap: int = 50,
) -> List[Dict[str, object]]:
    """
    Extracts visible text from raw HTML bytes, then returns section-aware chunks.
    """
    text = extract_text_from_html(html_bytes)
    return chunk_sections(text, chunk_size, overlap)