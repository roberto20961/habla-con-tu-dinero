from google import genai
from dotenv import load_dotenv
from google.genai import errors
import time

def gemini_call(history, max_retries = 3):
    wait = 2

    for i in range(max_retries):
        try:
            response = client.models.generate_content(
                model = "gemini-3.1-flash-lite",
                contents = history
            )

            return response.text

        except errors.APIError as e:
            if e.code not in {503, 429}:
                raise

            if i < max_retries - 1:
                print(f"Reintento {i + 1}, esperando {wait} segundos...")
                time.sleep(wait)
                wait = wait * 2

    return None

load_dotenv()

client = genai.Client()

print("Bienvenido al asistente bancario de Unicaja, ¿qué desea hoy?\n")

history = []

while True:
    user_message = input("Tú: ")
    if user_message == "Hasta luego":
        break
    
    prompt = {
        "role": "user", 
        "parts": [{"text": user_message}]
    }

    response = gemini_call(history + [prompt])

    if response is None:
        print("Servidor saturado... Intente nuevamente en unos instantes.")
        print("-" * 100)
        continue

    history.append(prompt)

    history.append({
        "role": "model",
        "parts": [{"text": response}]
    })

    print("\nAsistente:", response)
    print("-" * 100)