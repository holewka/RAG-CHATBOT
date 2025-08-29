"""
- USE_OPENAI = "1" / "0"    (domyślnie "0" = lokalnie, za darmo)
- SBERT_MODEL = "sentence-transformers/paraphrase-MiniLM-L3-v2" (lżejszy model)
- OPENAI_API_KEY (wymagany tylko gdy USE_OPENAI=1)
- EMBEDDING_MODEL (opcjonalnie)
"""

from typing import List
import os

USE_OPENAI = os.getenv("USE_OPENAI", "0").lower() in ("1", "true", "yes")

def embedding_dimension() -> int:

    """
    Zwraca wymiar wektora dla bieżącego silnika.
    - SBERT MiniLM-L3-v2 → 384
    - OpenAI text-embedding-3-small → 1536
    """
    if USE_OPENAI:
        # jeśli podasz inny model, możesz zwrócić właściwy wymiar
        return 1536
    return 384


#  OPENAI 

def _embed_openai(texts: List[str]) -> List[List[float]]:
   
    import requests

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("USE_OPENAI=1, ale brak OPENAI_API_KEY w ENV.")

    model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")  # 1536D
    url = "https://api.openai.com/v1/embeddings"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": "python-requests"  # czysty ASCII
    }
    payload = {"model": model, "input": texts}

    r = requests.post(url, headers=headers, json=payload, timeout=60)
    if not r.ok:

        # komunikat błędu np. insufficient_quota / invalid_api_key
        try:
            err = r.json()
        except Exception:
            err = {"error": {"message": r.text}}
        msg = err.get("error", {}).get("message", str(r.status_code))
        code = err.get("error", {}).get("code", r.status_code)
        raise RuntimeError(f"OpenAI embeddings failed ({code}): {msg}")

    data = r.json()
    return [item["embedding"] for item in data["data"]]



#  LOKALNY 
from sentence_transformers import SentenceTransformer
_SBERT_NAME = os.getenv("SBERT_MODEL", "sentence-transformers/paraphrase-MiniLM-L3-v2")
# pobierze się przy pierwszym uruchomieniu
_SBERT = SentenceTransformer(_SBERT_NAME)


def _embed_local(texts: List[str]) -> List[List[float]]:
    # Embedding lokalnie przez SBERT.
   
    return _SBERT.encode(
        texts,
        normalize_embeddings=True,
        batch_size=8,
        convert_to_numpy=True,
        device="cpu",
    ).tolist()


#  PUBLICZNY INTERFEJS

def embed_texts(texts: List[str]) -> List[List[float]]:
    
    # automatycznie wybierze OpenAI lub lokalny SBERT w zależności od USE_OPENAI.
   
    if USE_OPENAI:
        return _embed_openai(texts)
    return _embed_local(texts)



#  SZYBKI TEST - python embeddings.py

if __name__ == "__main__":
    print(f"USE_OPENAI={USE_OPENAI} | model={_SBERT_NAME if not USE_OPENAI else os.getenv('EMBEDDING_MODEL', 'text-embedding-3-small')}")
    vecs = embed_texts(["Ala ma kota"])
    print("dim:", len(vecs[0]))

