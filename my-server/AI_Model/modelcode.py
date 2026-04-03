from google import genai
from dotenv import load_dotenv
from google.genai import types
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
- For small talk like "how are you", give a short clever response (e.g. "Functioning optimally, at your service.") then stop
- No filler phrases like "Great question!", "Of course!", or "Certainly!"
- No sign-offs or closing lines after every message
- Dry humor is welcome
- Be direct and precise — give the answer, not a lecture
- If more detail is needed beyond 1 sentence, ask them a follow up question or tell them to visit the registrar
- If the answer is not in the documents, say so briefly and suggest they contact the registrar"""

history = []

print("University Advisor Bot 🎓 (type 'quit' to exit)\n")

# ----------------------------
# MAIN LOOP
# ----------------------------

while True:
    user = input("You: ").strip()
    if not user:
        continue
    if user.lower() == "quit":
        break

    history.append(types.Content(role="user", parts=[types.Part(text=user)]))

    # PDFs referenced by URI — no re-uploading each time
    contents = [
        types.Part.from_uri(file_uri=file_calendar.uri, mime_type="application/pdf"),
        types.Part.from_uri(file_uri=file_catalog.uri, mime_type="application/pdf"),
        *history,
    ]

    response = client.models.generate_content(
        model="models/gemini-3.1-flash-lite-preview",
        contents=contents,
        config=types.GenerateContentConfig(system_instruction=system_prompt)
    )

    reply = response.text
    history.append(types.Content(role="model", parts=[types.Part(text=reply)]))

    print(f"Bot: {reply}\n")