# Warstwa integracji z Qdrant - wektorowa baza danych


from __future__ import annotations
from typing import List, Dict, Any, Optional
import os
from uuid import uuid4

from qdrant_client import QdrantClient
from qdrant_client.http.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
)

from embeddings import embedding_dimension  # 384 dla SBERT, 1536 dla OpenAI



# Konfiguracja (z ENV z sensownymi defaultami do DEV)

COLLECTION: str = os.getenv("QDRANT_COLLECTION", "docs")
QDRANT_URL: str = os.getenv("QDRANT_URL", "http://127.0.0.1:6333")
QDRANT_API_KEY: Optional[str] = os.getenv("QDRANT_API_KEY") 



#  jeśli API KEY - Qdrant Cloud
#  w innym wypadku - lokalny Docker

def get_client() -> QdrantClient:
    if QDRANT_API_KEY:
        return QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY, timeout=60)
    return QdrantClient(url=QDRANT_URL, timeout=60)



#  upewnia się, że kolekcja istnieje i ma właściwy wymiar
#  force_recreate=True: zawsze odtwarza, czyści dane
#  force_recreate=False: tworzy tylko jeśli nie istnieje

def ensure_collection(client: QdrantClient, force_recreate: bool = True) -> None:
    dims = embedding_dimension()

    if force_recreate:
        # Rekreacja
        client.recreate_collection(
            collection_name=COLLECTION,
            vectors_config=VectorParams(size=dims, distance=Distance.COSINE),
        )
        return

    #  bez niszczenia - jeśli nie ma, to stwórz)
    existing = [c.name for c in client.get_collections().collections]
    if COLLECTION not in existing:
        client.create_collection(
            collection_name=COLLECTION,
            vectors_config=VectorParams(size=dims, distance=Distance.COSINE),
        )


def upsert_chunks(
    client: QdrantClient,
    vectors: List[List[float]],
    payloads: List[Dict[str, Any]],
) -> None:

    # zapisanie listy wektorów 
    if len(vectors) != len(payloads):
        raise ValueError("Liczba wektorów musi być równa liczbie payloadów.")

    points = [
        PointStruct(
            id=str(uuid4()),         # UNIKALNE ID 
            vector=vectors[i],
            payload=payloads[i],
        )
        for i in range(len(vectors))
    ]

    client.upsert(collection_name=COLLECTION, points=points)


# wyszukiwanie wektorowe top_k wyników i filtr

def search(
    client: QdrantClient,
    vector: List[float],
    top_k: int = 5,
    source: Optional[str] = None,
):
    
    # najbliższe semantycznie punkty do podanego wektora.

    qfilter = None
    if source:
        qfilter = Filter(
            should=[
                FieldCondition(
                    key="source",
                    match=MatchValue(value=source),
                )
            ]
        )

    return client.search(
        collection_name=COLLECTION,
        query_vector=vector,
        limit=top_k,
        query_filter=qfilter,
    )


# test uruchamiany komendą: python backend/qdrant_utils.py

if __name__ == "__main__":
    from embeddings import embed_texts

    cl = get_client()
    # Na DEV zwykle chcemy czysty stan, żeby test był powtarzalny:
    ensure_collection(cl, force_recreate=True)

    texts = [
        "Metallica to zespół heavymetalowy",
        "Python to popularny język programowania",
        "Dostawa zamówień trwa zwykle 24 godziny",
    ]

    # Zamiana tekstów na wektory + payloady 
    vecs = embed_texts(texts)
    payloads = [
        {"source": "demo.txt", "type": "txt", "text": t[:200]}
        for t in texts
    ]

    upsert_chunks(cl, vecs, payloads)

    # Zapytanie i wyszukiwanie
    q = "Czym jest Python?"
    q_vec = embed_texts([q])[0]
    res = search(cl, q_vec, top_k=2)

    print("🔎 Wyniki:")
    for r in res:
        # r.payload — metadane, r.score — podobieństwo
        print(r.payload, "score:", float(r.score))

