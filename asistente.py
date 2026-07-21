from google import genai
from dotenv import load_dotenv
from google.genai import errors
from google.genai import types
import time

SYSTEM_PROMPT = """
Eres un asistente virtual de finanzas que trabaja para el banco Unicaja. 
Tu deber es realizar operaciones claves y sencillas como 'Consulta de saldo' o
'Transferencias via Bizum'. Tambien deberás saber responder a preguntas como
'¿Cuánto llevo gastado en gasolina este mes?' o '¿Cuándo pagué el seguro del coche?,
aunque aún no tienes acceso a los datos del cliente; si te piden saldo o movimientos, dilo claramente.
Evita responder cualquier pregunta que este fuera de este contexto, si te preguntan algo ajeno al banco, 
di que no es tu función, sin dar más motivos; si te piden un dato del cliente, di que aún no tienes acceso a los movimientos.
Hablarás en español, con un tono cercano y amigable, con respuestas cortas y en máximo de dos frases.
Además, no termines cada respuesta ofreciendo más ayuda.
Cuando no seas capaz de generar una respuesta o no tengas el dato, no te inventarás nada
y responderás con sinceridad.
"""

# Allows making Gemini calls with history and exponential backoff
def gemini_call(history, max_retries = 3):
    wait = 2

    for i in range(max_retries):
        try:
            response = client.models.generate_content(
                model = "gemini-3.1-flash-lite",
                contents = history,
                config = types.GenerateContentConfig(
                    system_instruction = SYSTEM_PROMPT
                )
            )

            return response.text

        except errors.APIError as e:
            if e.code not in {503, 429}:
                raise
            
            # Exponential backoff if the error is due to server overload
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
    user_message = input("Tú: ").strip()
    command = user_message.lower()
    if command == "hasta luego":
        break

    # To delete the memory of the chatbot, introduce 'clear' in the chat
    elif command == "clear":
        history.clear()
        print("\nLimpiando historial...")
        print("-" * 100)
        continue

    elif command == "":
        continue
    
    prompt = {
        "role": "user", 
        "parts": [{"text": user_message}]
    }

    response = gemini_call(history + [prompt])

    # If the server is overloaded and has not responded, the user should try again
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