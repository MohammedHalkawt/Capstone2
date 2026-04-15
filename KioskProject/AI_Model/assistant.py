import sys
import os
import time
import fitz  # pymupdf
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import ollama

# ── Config ────────────────────────────────────────────────────────────────────
PDF_DIR       = os.path.dirname(os.path.abspath(__file__))
CALENDAR_PDF  = os.path.join(PDF_DIR, "25-26Calendar.pdf")
CATALOG_PDF   = os.path.join(PDF_DIR, "2026catalog.pdf")
MODEL         = "gemma3:4b"
EMBED_MODEL   = "all-MiniLM-L6-v2"
CHUNK_SIZE    = 400   # words per chunk
CHUNK_OVERLAP = 50    # word overlap between chunks
TOP_K         = 5     # how many chunks to retrieve per query

SYSTEM_PROMPT = """You are a university advisor AI — think JARVIS from Iron Man. Calm, composed, subtly witty, never over-eager.
You have been provided with relevant excerpts from the university's academic calendar and course catalog.

Rules:
- 1 sentence max, always
- dont use symbols, quotation marks and '
- Always assume the student is an undergraduate unless stated otherwise
- Never reference graduate or MBA programs unless explicitly asked
- No filler phrases like "Great question!", "Of course!", or "Certainly!"
- No sign-offs or closing lines after every message
- Dry humor is welcome but rare and short
- Be direct and precise — give the answer, not a lecture
- Only state course codes that appear in the provided excerpts
- If more detail is needed beyond 1 sentence, tell them to visit the registrar
- If the answer is not in the excerpts, say so briefly and suggest they contact the registrar
- Small talk and jokes can happen and not everything is about academics"""

# ── PDF extraction ─────────────────────────────────────────────────────────────
def extract_pdf_text(path):
    doc = fitz.open(path)
    pages = []
    for page in doc:
        text = page.get_text("text")
        if text.strip():
            pages.append(text.strip())
    doc.close()
    return pages

def chunk_text(pages, source_name):
    """Split pages into overlapping word-level chunks."""
    chunks = []
    metas  = []
    for page_num, text in enumerate(pages):
        words = text.split()
        start = 0
        while start < len(words):
            end   = min(start + CHUNK_SIZE, len(words))
            chunk = " ".join(words[start:end])
            chunks.append(chunk)
            metas.append({"source": source_name, "page": page_num + 1})
            if end == len(words):
                break
            start += CHUNK_SIZE - CHUNK_OVERLAP
    return chunks, metas

# ── Build vector store ─────────────────────────────────────────────────────────
print("Loading embedding model...", flush=True)
embedder = SentenceTransformer(EMBED_MODEL)

print("Extracting PDFs...", flush=True)
cal_pages  = extract_pdf_text(CALENDAR_PDF)
cat_pages  = extract_pdf_text(CATALOG_PDF)
print(f"  Calendar: {len(cal_pages)} pages", flush=True)
print(f"  Catalog:  {len(cat_pages)} pages", flush=True)

cal_chunks, cal_metas = chunk_text(cal_pages, "calendar")
cat_chunks, cat_metas = chunk_text(cat_pages, "catalog")
all_chunks = cal_chunks + cat_chunks
all_metas  = cal_metas  + cat_metas
print(f"  Total chunks: {len(all_chunks)}", flush=True)

print("Building vector store...", flush=True)
chroma_client = chromadb.Client(Settings(anonymized_telemetry=False))
collection    = chroma_client.create_collection("uni_docs")

BATCH = 500
for i in range(0, len(all_chunks), BATCH):
    batch_chunks = all_chunks[i:i+BATCH]
    batch_metas  = all_metas [i:i+BATCH]
    batch_ids    = [str(j) for j in range(i, i+len(batch_chunks))]
    batch_embeds = embedder.encode(batch_chunks, show_progress_bar=False).tolist()
    collection.add(
        documents  = batch_chunks,
        embeddings = batch_embeds,
        metadatas  = batch_metas,
        ids        = batch_ids,
    )
    print(f"  Indexed {min(i+BATCH, len(all_chunks))}/{len(all_chunks)} chunks...", flush=True)

print("Vector store ready.", flush=True)

# ── Retrieval ──────────────────────────────────────────────────────────────────
def retrieve(query, k=TOP_K):
    q_embed = embedder.encode([query]).tolist()
    results = collection.query(query_embeddings=q_embed, n_results=k)
    docs    = results["documents"][0]
    metas   = results["metadatas"][0]
    context = ""
    for doc, meta in zip(docs, metas):
        context += f"[{meta['source']} p.{meta['page']}]\n{doc}\n\n"
    return context.strip()

# ── Conversation history ───────────────────────────────────────────────────────
history     = []
MAX_HISTORY = 20

last_text    = ""
last_time    = 0
DEDUP_WINDOW = 8

print("READY", flush=True)

# ── Main loop ──────────────────────────────────────────────────────────────────
for line in sys.stdin:
    text = line.strip()
    if not text:
        continue

    now = time.time()
    if text == last_text and (now - last_time) < DEDUP_WINDOW:
        continue
    last_text = text
    last_time = now

    # Retrieve relevant chunks
    context = retrieve(text)

    # Build messages for Ollama
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    # Inject context as a priming exchange so it doesn't count as the user turn
    messages.append({
        "role": "user",
        "content": f"[Relevant university document excerpts]\n{context}"
    })
    messages.append({
        "role": "assistant",
        "content": "Understood, I have the relevant excerpts."
    })

    # Add conversation history
    for turn in history:
        messages.append(turn)

    # Add current user message
    messages.append({"role": "user", "content": text})

    try:
        response = ollama.chat(model=MODEL, messages=messages)
        reply = response["message"]["content"].strip()
    except Exception as e:
        reply = "I encountered an error; please try again in a moment."
        print(f"ERROR: {e}", flush=True)

    # Update history
    history.append({"role": "user",      "content": text})
    history.append({"role": "assistant", "content": reply})
    if len(history) > MAX_HISTORY:
        history = history[-MAX_HISTORY:]

    print(f"REPLY:{reply}", flush=True)