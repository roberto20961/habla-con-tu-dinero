from google import genai
from dotenv import load_dotenv

load_dotenv()

client = genai.Client()

print("Bienvenido al asistente bancario de Unicaja, ¿qué desea hoy?\n")

history = []

while True:
    prompt = input("Tú: ")
    if prompt == "Hasta luego":
        break

    history.append({
        "role": "user",
        "parts": [{"text": prompt}]
    })

    response = client.models.generate_content(
        model="gemini-3.1-flash-lite",
        contents=history
    )

    history.append({
        "role": "model",
        "parts": [{"text": response.text}]
    })

    print("\nAsistente:", response.text)
    print("-" * 100)