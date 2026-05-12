"""
core/resume_parser.py
Extracts and structures resume text for Ollama analysis.
"""

import os
import json
import re
from pathlib import Path


def extract_text_from_pdf(file_path: str) -> str:
    try:
        from pdfminer.high_level import extract_text
        return extract_text(file_path)
    except Exception as e:
        return f"PDF extraction error: {e}"


def extract_text_from_docx(file_path: str) -> str:
    try:
        from docx import Document
        doc = Document(file_path)
        return "\n".join([p.text for p in doc.paragraphs])
    except Exception as e:
        return f"DOCX extraction error: {e}"


def extract_text_from_txt(file_path: str) -> str:
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def parse_resume(file_path: str) -> dict:
    """Parse resume file and return raw text."""
    ext = Path(file_path).suffix.lower()
    if ext == ".pdf":
        raw_text = extract_text_from_pdf(file_path)
    elif ext in (".docx", ".doc"):
        raw_text = extract_text_from_docx(file_path)
    else:
        raw_text = extract_text_from_txt(file_path)

    # Clean up whitespace
    raw_text = re.sub(r"\n{3,}", "\n\n", raw_text).strip()
    return {"raw_text": raw_text, "file": file_path}
