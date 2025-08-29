//  ADRES BACKENDU
//  ustawiamy adres swojego API 
const API_BASE = "http://127.0.0.1:8000";

function addLine(html) {

  const chatBox = document.getElementById("chatBox");

  // tworzymy nowy div z treścią html
  chatBox.insertAdjacentHTML("beforeend", `<div>${html}</div>`);

  chatBox.scrollTop = chatBox.scrollHeight;
}

async function uploadFiles() {
  const filesEl = document.getElementById("fileInput");

  const files = filesEl?.files || [];

  if (!files.length) {
    alert("Nie wybrałaś żadnego pliku!");
    return;
  }

  try {
    const form = new FormData();
       for (const f of files) form.append("files", f);
    const res = await fetch(`${API_BASE}/upload`, { 
      method: "POST", 
      body: form 
    });

    // Jeśli błąd to rzucamy wyjątek
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);

    // Odczytujemy odpowiedź serwera jako JSON
    const data = await res.json();

    // info ile fragmentów tekstu zostało zapisanych
    alert("Zaindeksowano: " + (data.indexed ?? 0) + " kawałków tekstu");
  } catch (e) {
    
    alert("Błąd uploadu: " + e.message);
  }
}

async function askQuestion() {
  // Pobieramy pole input z pytaniem
  const input = document.getElementById("questionInput");

  // Usuwamy zbędne spacje
  const q = (input?.value || "").trim();

  if (!q) return;

  // Opcjonalny filtr (plik, CMS)
  const sourceSel = document.getElementById("sourceFilter");
  const source = sourceSel && sourceSel.value ? sourceSel.value : null;

  // pytanie użytkownika 
  addLine(`<b>Ty:</b> ${q}`);

  input.value = "";

  try {
    // obiekt body - treść zapytania do backendu
    const body = { query: q, top_k: 5 }; // top_k = ile najlepszych fragmentów pobrać
    if (source) body.source = source;    // jeśli podano źródło, dodajemy je do zapytania

    // zapytanie POST do chat
    const res = await fetch(`${API_BASE}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    // Jeśli błąd np. 400 albo 500)
    if (!res.ok) {
      const text = await res.text(); 
      console.error("Chat error", res.status, text);
      addLine(`<span style="color:red">Błąd: ${res.status}</span>`);
      return;
    }

    const data = await res.json();

    // odpowiedź bota
    const answer = data.answer || "Nie mam na to odpowiedzi w dokumentach";
    addLine(`<b>Bot:</b> ${answer}`);

    // pokaż źródła
    const matches = data.matches || [];
    \if (matches.length) {
    const srcSet = new Set(
    matches.map(m => (m.payload && m.payload.source) || m.source).filter(Boolean)
  );
  const src = [...srcSet].join(", ");
  if (src) addLine(`<i>Źródła:</i> ${src}`);
}

  } catch (e) {
    
    console.error(e);
    addLine(`<span style="color:red">Błąd sieci: ${e.message}</span>`);
  }
}


//  PODPINANIE EVENTÓW (kliknięcia, enter)

document.addEventListener("DOMContentLoaded", () => {
  const sendBtn = document.getElementById("sendBtn");

  const sendFilesBtn = document.getElementById("sendFilesBtn");

  const input = document.getElementById("questionInput");
  
  if (sendBtn) {
    sendBtn.addEventListener("click", (e) => {
      e.preventDefault(); 
      askQuestion();      
    });
  }
 
  if (sendFilesBtn) {
    sendFilesBtn.addEventListener("click", (e) => {
      e.preventDefault();
      uploadFiles(); 
    });
  }

  if (input) {
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault(); 
        askQuestion();      
      
    });
  }
});

