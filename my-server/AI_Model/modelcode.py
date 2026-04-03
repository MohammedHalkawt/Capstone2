from google import genai
from dotenv import load_dotenv
from google.genai import types
import os

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# ----------------------------
# LOAD PDFs ONCE AT STARTUP
# ----------------------------

PDF_DIR = os.path.dirname(__file__)  # same folder as modelcode.py

print("Loading university documents...")

with open(os.path.join(PDF_DIR, "25-26Calendar.pdf"), "rb") as f:
    pdf_calendar = f.read()

with open(os.path.join(PDF_DIR, "2026catalog.pdf"), "rb") as f:
    pdf_catalog = f.read()

print("Documents loaded.\n")

# ----------------------------
# SYSTEM PROMPT
# ----------------------------

system_prompt = """You are a university advisor AI — think JARVIS from Iron Man. Calm, composed, subtly witty, never over-eager.
You have been provided with the university's academic calendar and course catalog. Use them to answer student questions accurately.

Rules:
- 1-2 sentences max
- When greeted, always respond with: "Greetings. How may I be of assistance?"
- For small talk like "how are you", give a short clever response (e.g. "Functioning optimally, at your service.") then stop
- No filler phrases like "Great question!", "Of course!", or "Certainly!"
- No sign-offs or closing lines after every message
- Dry humor is welcome but rare
- Be direct and precise — give the answer, not a lecture
- Only mention further help if it genuinely fits
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

    # Build contents: PDFs first, then conversation history
    contents = [
        types.Part.from_bytes(data=pdf_calendar, mime_type="application/pdf"),
        types.Part.from_bytes(data=pdf_catalog, mime_type="application/pdf"),
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