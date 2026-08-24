from google import genai
from dotenv import load_dotenv
from google.genai import errors
from google.genai import types
import time
import prompts

load_dotenv()
client = genai.Client()

# These are not the real functions, only describe what Gemini can call with their parameters 
saldo_function = {
    "name" : "saldo",
    "description" : "Devuelve el saldo actual de la cuenta del usuario.",
    "parameters": {"type": "object", "properties": {}},
}

bizum_function = {
    "name" : "bizum",
    "description" : "Envía dinero a un contacto o número de teléfono mediante Bizum",
    "parameters": {
        "type": "object",
        "properties": {
            "receiver": {"type": "string", "description": "Nombre o número de teléfono del contacto que recibe el dinero"},
            "amount": {"type": "number", "description": "Cantidad en euros a enviar"},
        },
        "required": ["receiver", "amount"],
    },
}

tools = types.Tool(function_declarations=[saldo_function, bizum_function])

# Allows making Gemini calls with history or simple prompt, system instructions and exponential backoff
def gemini_call(prompt, system_prompt = None, max_retries = 3, mime_type = None):
    wait = 2

    for i in range(max_retries):
        try:
            response = client.models.generate_content(
                model = "gemini-3.1-flash-lite",
                contents = prompt,
                config = types.GenerateContentConfig(
                    system_instruction = system_prompt,
                    response_mime_type = mime_type
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

def classify(prompt):
    return gemini_call(prompt, prompts.CLASSIFIER_PROMPT)

def sql_translate(prompt):
    return gemini_call(prompt, prompts.SQL_PROMPT)

def query_translate(prompt):
    return gemini_call(prompt, prompts.ANSWER_PROMPT)

def bizum_approval(prompt):
    return gemini_call(prompt, prompts.BIZUM_PROMPT)

def graphic_call(prompt):
    return gemini_call(prompt, prompts.GRAPHIC_PROMPT, mime_type = "application/json")

# Same logic as 'gemini_call' but oriented to Bizum operations
def operation_call(prompt, max_retries = 3):
    wait = 2

    for i in range(max_retries):
        try:
            response = client.models.generate_content(
                model = "gemini-3.1-flash-lite",
                contents = prompt,
                config = types.GenerateContentConfig(
                    tools = [tools],
                    system_instruction = prompts.OPERATION_PROMPT
                )
            )

            return response

        except errors.APIError as e:
            if e.code not in {503, 429}:
                raise
            
            # Exponential backoff if the error is due to server overload
            if i < max_retries - 1:
                print(f"Reintento {i + 1}, esperando {wait} segundos...")
                time.sleep(wait)
                wait = wait * 2
    
    return None