# PROJEKT: RAG Chatbot (FastAPI + Qdrant)

## Cel
Chatbot, który:
- działa na stronie (HTML + JS + CSS),
- backend w Pythonie (FastAPI),
- obsługa plików: TXT, PDF, DOCX, CSV + dane z CMS (JSON),
- zapisuje embeddingi w Qdrant i zwraca najbliższe fragmenty,
- ma prosty small-talk („hej”, „co tam?”).

## Technologie
- **Frontend:** HTML, CSS, JavaScript  
- **Backend:** Python + FastAPI  
- **Baza wektorowa:** Qdrant (Docker / Cloud free)  
- **Embeddingi:** SentenceTransformers (MiniLM offline)  
- **Parsery:** pypdf, python-docx, pandas  


## STRUKTURA
.
├─ backend/
│  ├─ __pycache__/                # cache Pythona (ignorowane w git)
│  ├─ test_data/                  # próbki danych / pliki demonstracyjne
│  ├─ __init__.py
│  ├─ app.py                      # główny serwer FastAPI (endpoints)
│  ├─ document_parser.py          # parser TXT/PDF/DOCX/CSV + JSON z CMS
│  ├─ embeddings.py               # generowanie embeddingów
│  └─ qdrant_utils.py             # inicjalizacja i operacje na Qdrant
│
├─ frontend/
│  ├─ index.html                  # UI czatu (bubble chat)
│  ├─ styles.css                  # stylowanie
│  ├─ chatbot.js                  # logika frontu (upload, chat, źródła)
│  └─ retro.newspaper.jpg         # tło/grafika
│
├─ test_data/
│  └─ cms_demo.json               # przykładowy „CMS” (dane w JSON)
│
├─ venv/                          # (opcjonalny) wirtualne środowisko Pythona
├─ .gitignore
├─ requirements.txt
├─ test_api.py                    # proste testy/zapytania do API
├─ __init__.py
├─ zespoly_test.txt               # prosty plik TXT do testów
└─ README.md





## Uruchomienie (Windows)

### 1) Instalacja
```powershell / cmd
git clone <ADRES_REPO>
cd project/backend
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt

2) Qdrant
powershell
docker run --name qdrant -p 6333:6333 qdrant/qdrant
Panel: http://127.0.0.1:6333/dashboard

(Cloud: ustaw QDRANT_URL, QDRANT_API_KEY)

3) Backend
powershell
uvicorn app:app --reload
Swagger: http://127.0.0.1:8000/docs

Health: http://127.0.0.1:8000/health


4) Frontend
Otwórz frontend/index.html w przeglądarce.

Pierwszy test
Swagger → POST /upload → wybierz plik (data/zespoly_test.txt)
→ dostaniesz {"indexed": X}

W czacie wpisz np. metallica → bot zwróci fragment + źródło

CMS demo: POST /ingest_cms z JSON, potem zapytaj w czacie sport / fortnite.

Reset (dev)
Jeśli zmienisz parser/chunkowanie, wyczyść kolekcję i wgraj pliki ponownie:

powershell
python qdrant_utils.py


## Najczęstsze błędy

- **WinError 10061 / brak połączenia z Qdrant**  
  Kontener Dockera nie działa → uruchom `docker start qdrant` i sprawdź    <http://127.0.0.1:6333/dashboard>.

- **ModuleNotFoundError (pypdf / python-docx / pandas)**  
  Brak bibliotek → zainstaluj zależności:  
  ```bash
  pip install -r backend/requirements.txt

- **Brak odpowiedzi w dokumentach**
  Upewnij się, że najpierw wgrałaś pliki (/upload) lub dane CMS (/ingest_cms).
Krótkie hasła (np. „metallica”) mogą nie wystarczyć – lepiej pytać pełnym zdaniem.

- **Swagger działa, ale frontend nie widzi odpowiedzi**
  Sprawdź, czy backend chodzi na http://127.0.0.1:8000 i czy w chatbot.js masz taki adres    w API_BASE.
