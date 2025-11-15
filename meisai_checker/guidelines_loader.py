from __future__ import annotations

from pathlib import Path
from typing import Iterable


def _read_text_file(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def _read_md_file(path: Path) -> str:
    return _read_text_file(path)


def _read_docx_file(path: Path) -> str:
    try:
        from docx import Document  # type: ignore
    except Exception:
        return f"[WARN] python-docx 未導入のため {path.name} を読み飛ばしました。\n"
    doc = Document(str(path))
    return "\n".join(p.text for p in doc.paragraphs)


def _read_pdf_file(path: Path) -> str:
    try:
        import fitz  # PyMuPDF type: ignore
    except Exception:
        return f"[WARN] PyMuPDF 未導入のため {path.name} を読み飛ばしました。\n"
    with fitz.open(str(path)) as doc:
        pages = [page.get_text("text") for page in doc]
    return "\n".join(pages)


def read_guidelines_text(dir_path: Path) -> str:
    dir_path.mkdir(parents=True, exist_ok=True)
    texts: list[str] = []
    for p in sorted(_iter_files(dir_path)):
        header = f"\n\n===== SOURCE: {p.name} =====\n"
        if p.suffix.lower() in {".txt"}:
            body = _read_text_file(p)
        elif p.suffix.lower() in {".md"}:
            body = _read_md_file(p)
        elif p.suffix.lower() in {".docx"}:
            body = _read_docx_file(p)
        elif p.suffix.lower() in {".pdf"}:
            body = _read_pdf_file(p)
        else:
            body = f"[INFO] 未対応形式のため読み飛ばし: {p.name}\n"
        texts.append(header + body)
    if not texts:
        texts.append("[INFO] guidelines フォルダに参照ファイルがありません。README.md を参照してください。")
    return "\n".join(texts)


def _iter_files(base: Path) -> Iterable[Path]:
    for p in base.rglob("*"):
        if p.is_file():
            yield p

