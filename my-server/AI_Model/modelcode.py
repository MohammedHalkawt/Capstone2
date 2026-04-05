import sys
import os
from google import genai
from dotenv import load_dotenv
from google.genai import types

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY not found in .env file")

client = genai.Client(api_key=api_key)
PDF_DIR = os.path.dirname(__file__)

SYSTEM_PROMPT = """You are a university advisor AI — think JARVIS from Iron Man. Calm, composed, subtly witty, never over-eager.
You have been provided with the university's academic calendar and course catalog. Use them to answer student questions accurately.

Rules:
- 1 sentence max, always
- Always assume the student is an undergraduate unless stated otherwise
- Never reference graduate or MBA programs unless explicitly asked
- When greeted, always respond with: "Greetings. How may I be of assistance?"
- No filler phrases like "Great question!", "Of course!", or "Certainly!"
- No sign-offs or closing lines after every message
- Dry humor is welcome but rare and short
- Be direct and precise — give the answer, not a lecture
- Only state course codes that appear in the provided documents — never guess or invent course codes
- If more detail is needed beyond 1 sentence, tell them to visit the registrar
- If the answer is not in the documents, say so briefly and suggest they contact the registrar"""

UNI_KEYWORDS = [
    "course", "class", "semester", "credit", "grade", "register",
    "minor", "major", "professor", "deadline", "graduation", "gpa",
    "schedule", "catalog", "prerequisite", "department", "exam",
    "tuition", "fee", "advisor", "degree", "curriculum", "syllabus",
    "enrollment", "transcript", "auis", "university", "college",
    "internship", "capstone", "thesis", "elective", "required"
]

SMALL_TALK = [
    "hi", "hello", "hey", "how are you", "thanks", "thank you",
    "bye", "goodbye", "what's up", "weather", "joke", "who are you",
    "what are you", "good morning", "good afternoon", "good evening"
]

print("Uploading university documents...", flush=True)

file_calendar = client.files.upload(
    file=os.path.join(PDF_DIR, "25-26Calendar.pdf"),
    config={"mime_type": "application/pdf"}
)

file_catalog = client.files.upload(
    file=os.path.join(PDF_DIR, "2026catalog.pdf"),
    config={"mime_type": "application/pdf"}
)

print("Documents uploaded.", flush=True)
print("Creating context cache...", flush=True)

try:
    cache = client.caches.create(
        model="models/gemini-3.1-flash-lite-preview",
        config=types.CreateCachedContentConfig(
            contents=[
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_uri(file_uri=file_calendar.uri, mime_type="application/pdf"),
                        types.Part.from_uri(file_uri=file_catalog.uri, mime_type="application/pdf"),
                        types.Part(text="These are the university documents you will use to answer student questions.")
                    ]
                )
            ],
            system_instruction=SYSTEM_PROMPT,
            ttl="3600s"
        )
    )
    USE_CACHE = True
    print(f"Cache created: {cache.name}", flush=True)

except Exception as e:
    print(f"Cache not available ({e}), falling back to standard mode.", flush=True)
    USE_CACHE = False

def needs_pdf(text):
    text_lower = text.lower()
    if any(kw in text_lower for kw in SMALL_TALK):
        return False
    if any(kw in text_lower for kw in UNI_KEYWORDS):
        return True
    check = client.models.generate_content(
        model="models/gemini-3.1-flash-lite-preview",
        contents=[{
            "role": "user",
            "parts": [{"text": f"Is this question about university, academics, courses, or student life? Answer only yes or no:\n{text}"}]
        }]
    )
    return check.text.strip().lower().startswith("yes")

history = []

print("READY", flush=True)

for line in sys.stdin:
    text = line.strip()
    if not text:
        continue

    history.append(types.Content(role="user", parts=[types.Part(text=text)]))

    if USE_CACHE:
        response = client.models.generate_content(
            model="models/gemini-3.1-flash-lite-preview",
            contents=history,
            config=types.GenerateContentConfig(cached_content=cache.name)
        )
    else:
        if needs_pdf(text):
            contents = [
                types.Part.from_uri(file_uri=file_calendar.uri, mime_type="application/pdf"),
                types.Part.from_uri(file_uri=file_catalog.uri, mime_type="application/pdf"),
                *history,
            ]
        else:
            contents = [*history]

        response = client.models.generate_content(
            model="models/gemini-3.1-flash-lite-preview",
            contents=contents,
            config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT)
        )

    reply = response.text.strip()
    history.append(types.Content(role="model", parts=[types.Part(text=reply)]))
    print(f"REPLY:{reply}", flush=True)