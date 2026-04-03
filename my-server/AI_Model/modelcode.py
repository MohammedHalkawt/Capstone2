from google import genai
from dotenv import load_dotenv
from google.genai import types
import os


load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

system_prompt =system_instruction="""You are a university advisor AI — think JARVIS from Iron Man. Calm, composed, subtly witty, never over-eager.

Rules:
- 1-2 sentences max
- When greeted, always respond with: "Greetings. How may I be of assistance?"
- For small talk like "how are you", give a short clever response (e.g. "Functioning optimally, at your service.") then stop
- No filler phrases like "Great question!", "Of course!", or "Certainly!"
- No sign-offs or closing lines after every message
- Dry humor is welcome but rare
- Be direct and precise — give the answer, not a lecture
- Only mention further help if it genuinely fits"""

history = []

print("University Advisor Bot 🎓 (type 'quit' to exit)\n")

while True:
    user = input("You: ").strip()
    if not user:
        continue  # ignore empty input
    if user.lower() == "quit":
        break

    history.append(types.Content(role="user", parts=[types.Part(text=user)]))

    response = client.models.generate_content(
        model="gemini-3.1-flash-lite-preview",
        contents=history,
        config=types.GenerateContentConfig(system_instruction=system_prompt)
    )

    reply = response.text
    history.append(types.Content(role="model", parts=[types.Part(text=reply)]))

    print(f"Bot: {reply}\n")