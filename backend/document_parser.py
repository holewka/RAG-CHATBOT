from __future__ import annotations
from typing import List, Dict, Any
from pathlib import Path
import re
import pandas as pd

# Preferuj pypdf; jeśli brak, użyj PyPDF2
try:
    from pypdf import PdfReader
except Exception:  # pragma: no cover
    from PyPDF2 import PdfReader  # type: ignore

from docx import Document as DocxDocument


# pomocnicze

def _normalize_ws(text: str) -> str:

    # oczyszczenie nadmiaru spacji w liniach, zachowuje podziały tekstu
    lines = [re.sub(r"\s+", " ", ln).strip() for ln in text.splitlines()]
    return "\n".join([ln for ln in lines if ln])


def chunk_text_paragraphs(text: str, target_size: int, overlap: int) -> List[str]:
   
    # overlap 
    text = _normalize_ws(text)
    lines = [ln for ln in text.split("\n") if ln.strip()]

    out: List[str] = []
    buf = ""

    def push(x: str):
        x = x.strip()
        if x:
            out.append(x)

    for ln in lines:
        new_len = len(buf) + (1 if buf else 0) + len(ln)
        if new_len <= target_size:
            buf = (buf + " " + ln).strip()
        else:
            if buf:
                push(buf)
                # overlap = końcówka poprzedniego bufora jako punkt startowy nowego
                buf = (buf[-overlap:].lstrip() if overlap > 0 and len(buf) > overlap else "")
            buf = (buf + " " + ln).strip()

    if buf:
        push(buf)

    return out


# parsowanie plików 

def parse_file(path: str) -> List[Dict[str, Any]]:
    
    p = Path(path)
    items: List[Dict[str, Any]] = []
    suffix = p.suffix.lower()

    # Ustawienia chunków 
    T_TXT = 250   # target_size dla tekstów (pdf/docx/txt)
    O_TXT = 30    # overlap
    T_CSV = 220   # dla wierszy CSV
    O_CSV = 25


    # PDF 
    if suffix == ".pdf":
        reader = PdfReader(str(p))
        for i, page in enumerate(reader.pages, start=1):
            # Uwaga: skany bez OCR zwrócą pusty tekst.
            txt = page.extract_text() or ""
            for ch in chunk_text_paragraphs(txt, target_size=T_TXT, overlap=O_TXT):
                items.append({
                    "text": ch,
                    "meta": {"source": p.name, "type": "pdf", "page": i},
                })
        return items


    # DOCX 
    if suffix == ".docx":
        doc = DocxDocument(str(p))
        txt = "\n".join([para.text for para in doc.paragraphs])
        for ch in chunk_text_paragraphs(txt, target_size=T_TXT, overlap=O_TXT):
            items.append({
                "text": ch,
                "meta": {"source": p.name, "type": "docx"},
            })
        return items


    # CSV 
    if suffix == ".csv":
        # Każdy wiersz → tekst z połączonych kolumn
        df = pd.read_csv(p, dtype=str).fillna("")
        for idx, row in df.iterrows():
            row_text = " | ".join(map(str, row.values))
            for ch in chunk_text_paragraphs(row_text, target_size=T_CSV, overlap=O_CSV):
                items.append({
                    "text": ch,
                    "meta": {"source": p.name, "type": "csv", "row": int(idx)},
                })
        return items


    # TXT itp.
    txt = p.read_text(encoding="utf-8", errors="ignore")
    for ch in chunk_text_paragraphs(txt, target_size=T_TXT, overlap=O_TXT):
        items.append({
            "text": ch,
            "meta": {"source": p.name, "type": "txt"},
        })
    return items
