"""
prosty backend do RAG - FastAPI + Qdrant + lokalne embeddingi

Endpointy:
- GET  /health
- GET  /test-embed
- POST /upload       
- POST /ingest_cms   
- POST /chat         
"""

from __future__ import annotations
from typing import List, Optional, Dict, Any
import os, re, random, shutil, tempfile

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from embeddings import embed_texts, embedding_dimension
from qdrant_utils import get_client, ensure_collection, upsert_chunks, search
from document_parser import parse_file

# ustawienia
MIN_SCORE = float(os.getenv("MIN_SCORE", "0.22"))        # próg podobieństwa
STRICT_WORDS = os.getenv("STRICT_WORDS", "1").lower() not in ("0", "false")
SMALLTALK = os.getenv("SMALLTALK", "1").lower() not in ("0", "false")

# FastAPI + CORS
app = FastAPI(title="Prosty RAG Chatbot")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

# Qdrant 
QDR = get_client()
ensure_collection(QDR, force_recreate=False)

# modele wejścia 
class ChatReq(BaseModel):
    query: str
    top_k: int = 5
    source: Optional[str] = None

class CMSItem(BaseModel):
    id: str
    title: Optional[str] = None
    body: str

class CMSIngest(BaseModel):
    items: List[CMSItem]

# utilsy 
def _tokens(s: str) -> list[str]:
    return [t for t in re.findall(r"[a-zA-Z0-9ąćęłńóśźżĄĆĘŁŃÓŚŹŻ]+", (s or "").lower()) if len(t) >= 3]

def _contains_any(query: str, txt: str) -> bool:
    if not STRICT_WORDS:
        return True
    keys = _tokens(query)
    if not keys:
        return True
    low = (txt or "").lower()
    return any(k in low for k in keys)

def _pick_relevant_sentences(query: str, text: str, max_sents: int = 2) -> str:

    """Zwróć 1–2 zdania z fragmentu, które zawierają słowa z pytania.
       Jeśli nic nie pasuje, oddaj pierwsze zdanie."""
    keys = _tokens(query)
    sents = re.split(r'(?<=[\.\!\?])\s+', (text or "").strip())
    hits = []
    for s in sents:
        low = s.lower()
        if not keys or any(k in low for k in keys):
            hits.append(s.strip())
        if len(hits) >= max_sents:
            break
    return " ".join(hits) if hits else (sents[0].strip() if sents else (text or "").strip())

# small-talk
TRIGGERS = {
    "hej","hej!","heja","hejka","elo","siema","siemka","cześć","czesc","witam","halo","yo","yo!",
    "co tam","jak leci","jak tam","jak sie masz","jak się masz",
    "dzień dobry","dzien dobry","dobry wieczór","dobry wieczor","ok","okej","okey","thanks","dzięki","dzieki","thx"
}
ANSWERS = [
    "Hej! Jak mogę pomóc? 😊",
    "Cześć! Wgraj plik i zapytaj o jego treść.",
    "Siema, spróbuję znaleźć odpowiedź w Twoich dokumentach.",
    "Yo! Jakie masz pytanie?",
    "Dzień dobry! O co chcesz zapytać?"
]
def _looks_like_smalltalk(q: str) -> bool:
    t = q.lower().strip()
    return len(t) <= 20 and any(x in t for x in TRIGGERS)

# endpointy 
@app.get("/health")
def health():
    return {"ok": True, "dim": embedding_dimension()}

@app.get("/test-embed")
def test_embed(text: str):
    v = embed_texts([text])[0]
    return {"length": len(v), "preview": v[:8]}

@app.post("/upload")
async def upload(files: List[UploadFile] = File(...)):
    if not files:
        raise HTTPException(400, "Nie przesłano plików.")
    tmpdir = tempfile.mkdtemp(prefix="ingest_")
    indexed = 0
    try:
        for f in files:
            path = os.path.join(tmpdir, f.filename)
            with open(path, "wb") as w:
                w.write(await f.read())

            items = parse_file(path)  # [{"text":..., "meta":...}]
            if not items:
                continue

            vectors = embed_texts([it["text"] for it in items])
            payloads = []
            for it in items:
                m = dict(it["meta"])
                m["text"] = it["text"]  # zapisz pełny tekst chunka
                payloads.append(m)

            upsert_chunks(QDR, vectors, payloads)
            indexed += len(items)
        return {"indexed": indexed}
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

@app.post("/ingest_cms")
def ingest_cms(payload: CMSIngest):
    if not payload.items:
        raise HTTPException(400, "Brak 'items'.")
    texts, metas = [], []
    for it in payload.items:
        txt = f"{it.title or ''}\n{it.body}".strip()
        if not txt:
            continue
        texts.append(txt)
        metas.append({"source": f"cms:{it.id}", "type": "cms", "title": it.title or "", "text": txt})
    if not texts:
        return {"indexed": 0}
    vecs = embed_texts(texts)
    upsert_chunks(QDR, vecs, metas)
    return {"indexed": len(texts)}

@app.post("/chat")
def chat(req: ChatReq):
    q = (req.query or "").strip()
    if not q:
        raise HTTPException(400, "Puste zapytanie.")

    # small-talk wcześniej niż wyszukiwanie
    if SMALLTALK and _looks_like_smalltalk(q):
        return {"answer": random.choice(ANSWERS), "sources": [], "matches": []}

    # krótkie hasła, luźny próg, zwiększ top_k
    is_one_word = len(q.split()) == 1
    top_k = max(5, int(req.top_k or 5))
    min_score = 0.0 if is_one_word else MIN_SCORE
    if is_one_word:
        top_k = max(top_k, 10)

    # wyszukiwanie
    q_vec = embed_texts([q])[0]
    results = search(QDR, q_vec, top_k=top_k, source=req.source)

    # lekki „bonus” za obecność słów z pytania
    scored = []
    for r in results:
        base = float(r.score)
        txt = (r.payload or {}).get("text") or ""
        bonus = 0.05 if _contains_any(q, txt) else 0.0
        scored.append((base + bonus, r))
    scored.sort(key=lambda x: x[0], reverse=True)

    # filtr po progu
    filtered = []
    for s, r in scored:
        txt = (r.payload or {}).get("text") or ""
        if s >= min_score and _contains_any(q, txt):
            filtered.append((s, r))

    # brak dopasowań 
    if not filtered:
        return {"answer": "Nie mam na to odpowiedzi w dokumentach.", "sources": [], "matches": []}

    # odpowiedź: tylko pasujące
    best_payload = (filtered[0][1].payload or {})
    best_text = (best_payload.get("text") or "")
    answer = _pick_relevant_sentences(q, best_text, max_sents=2)

    # źródła i matches 
    seen = set()
    sources = []
    matches = []
    for s, r in filtered:
        p = r.payload or {}
        src = p.get("source")
        matches.append({"payload": p, "score": round(float(s), 4)})
        if src and src not in seen:
            seen.add(src)
            sources.append({"source": src, "type": p.get("type"), "score": round(float(s), 4)})

    return {"answer": answer, "sources": sources, "matches": matches}

