"""
Text extractors for PDF, DOCX, and TXT files.

WHY SEPARATE EXTRACTOR FUNCTIONS:
  Each file type has a different library. Keeping them isolated means
  adding a new format (e.g., PPTX, HTML) doesn't touch existing logic.

WHY RETURN PLAIN TEXT:
  The chunker and embedder work on plain strings. Extractors do one job:
  turn bytes → string. Structuring is the chunker's responsibility.
"""
import io
from pathlib import Path
from pdfminer.high_level import extract_text as pdf_extract_text
from docx import Document as DocxDocument


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract text from a PDF file given its raw bytes."""
    return pdf_extract_text(io.BytesIO(file_bytes)) or ""


def extract_text_from_docx(file_bytes: bytes) -> str:
    """Extract text from a DOCX file given its raw bytes."""
    doc = DocxDocument(io.BytesIO(file_bytes))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n".join(paragraphs)


def extract_text_from_txt(file_bytes: bytes) -> str:
    """Decode a plain text file; try UTF-8 then fall back to latin-1."""
    try:
        return file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return file_bytes.decode("latin-1")


# Registry: map file extension → extractor function
EXTRACTOR_MAP: dict[str, callable] = {
    "pdf": extract_text_from_pdf,
    "docx": extract_text_from_docx,
    "txt": extract_text_from_txt,
}

SUPPORTED_EXTENSIONS = set(EXTRACTOR_MAP.keys())


def extract_text(file_bytes: bytes, extension: str) -> str:
    """
    Dispatch to the correct extractor based on file extension.
    Raises ValueError for unsupported types.
    """
    ext = extension.lower().lstrip(".")
    extractor = EXTRACTOR_MAP.get(ext)
    if extractor is None:
        raise ValueError(f"Unsupported file type: '.{ext}'. Supported: {SUPPORTED_EXTENSIONS}")
    return extractor(file_bytes)
