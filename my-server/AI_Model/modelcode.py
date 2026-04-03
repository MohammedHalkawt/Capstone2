from google import genai
from dotenv import load_dotenv
from google.genai import types
from inputimeout import inputimeout, TimeoutOccurred
import os

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY not found in .env file")

client = genai.Client(api_key=api_key)

# ----------------------------
# UPLOAD PDFs ONCE AT STARTUP
# ----------------------------

PDF_DIR = os.path.dirname(__file__)

print("Uploading university documents... (only happens once)")

file_calendar = client.files.upload(
    file=os.path.join(PDF_DIR, "25-26Calendar.pdf"),
    config={"mime_type": "application/pdf"}
)

file_catalog = client.files.upload(
    file=os.path.join(PDF_DIR, "2026catalog.pdf"),
    config={"mime_type": "application/pdf"}
)

print("Documents ready.\n")

# ----------------------------
# SYSTEM PROMPT
# ----------------------------

system_prompt = """You are a university advisor AI — think JARVIS from Iron Man. Calm, composed, subtly witty, never over-eager.
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
- If more detail is needed beyond 1 sentence, ask them a follow up question or tell them to visit the registrar
- If the answer is not in the documents, say so briefly and suggest they contact the registrar"""

# ----------------------------
# SMART PDF ROUTING
# ----------------------------

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

def needs_pdf(text):
    text_lower = text.lower()

    # fast check — obvious small talk
    if any(kw in text_lower for kw in SMALL_TALK):
        return False

    # fast check — obvious uni question
    if any(kw in text_lower for kw in UNI_KEYWORDS):
        return True

    # ambiguous — ask Gemini to decide (no PDFs needed for this)
    check = client.models.generate_content(
        model="models/gemini-2.0-flash-lite",
        contents=[{
            "role": "user",
            "parts": [{"text": f"Is this question about university, academics, courses, or student life? Answer only yes or no:\n{text}"}]
        }]
    )
    return check.text.strip().lower().startswith("yes")

# ----------------------------
# MAIN LOOP
# ----------------------------

history = []
INACTIVITY_TIMEOUT = 60  # seconds before session resets

print("University Advisor Bot 🎓 (type 'quit' to exit)\n")

while True:
    try:
        user = inputimeout("You: ", timeout=INACTIVITY_TIMEOUT).strip()
    except TimeoutOccurred:
        if history:
            history = []
            print("\n🔄 Session reset — next student welcome.\n")
        continue

    if not user:
        continue
    if user.lower() == "quit":
        break

    history.append(types.Content(role="user", parts=[types.Part(text=user)]))

    # smart routing — only attach PDFs when needed
    if needs_pdf(user):
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
        config=types.GenerateContentConfig(system_instruction=system_prompt)
    )

    reply = response.text
    history.append(types.Content(role="model", parts=[types.Part(text=reply)]))

    print(f"Bot: {reply}\n")