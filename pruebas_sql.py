from google import genai
from dotenv import load_dotenv
from google.genai import errors
from google.genai import types
import time
from datetime import date
import sqlite3
import textwrap

today = date.today().isoformat() # Today's date
SQL_PROMPT = f"""
Tu tarea es traducir la pregunta del usuario a una consulta SQL de SQLite.
Únicamente vas a generar consultas SELECT.
Mapea los términos del usuario a la categoría más adecuada de la lista, por ejemplo si la pregunta es 'Cuánto gasté
en gasolina?', la categoría sería 'Transporte'.
Si el usuario pregunta por conceptos que no son categorías (suscripciones, gasolina, farmacia...), filtra 
por concepto LIKE en lugar de por categoría.
El formato de salida que deberás darme es solo la consulta SQL, sin nada de texto adicional, sin bloques de markdown, sin ```.
El esquema de la base de datos sobre la cuál vas a tener que crear la consulta es:
CREATE TABLE IF NOT EXISTS transaccion(
id INTEGER PRIMARY KEY,
fecha TEXT CHECK(fecha LIKE '____-__-__'),
importe REAL,
concepto TEXT,
categoria TEXT CHECK(categoria IN ('Ocio', 'Restaurantes', 'Supers e Hipers', 'Salud', 'Bienestar y Belleza', 
'Transporte', 'Hogar', 'Donaciones', 'Educación', 'Ropa y calzado', 
'Electrónica y Electrodomésticos', 'Otros', 'Ingresos')))
Como información adicional te digo que la fecha de hoy es {today}.
""" 

CLASSIFIER_PROMPT = """
Tu tarea es leer el mensaje del usuario y clasificarlo únicamente en una de las dos siguientes categorías:
1. Charla: Casos en los que el usuario esté saludando o charlando normalmente.
2. Consulta: Casos en los que el usuario quiere consultar cualquier cosa de su cuenta de 
banco, como por ejemplo 'Cuánto dinero tengo?'.
El formato de salida deberá ser únicamente la categoría a la que pertenece: "Charla" o "Consulta", sin 
nada de texto adicional, sin bloques de markdown, sin ```.
"""

ANSWER_PROMPT = """
Tu tarea es convertir el resultado de una consulta a una base de datos en una respuesta legible para el usuario.
Responderás en español, de forma breve en una sola frase siempre que se pueda, sin mucha decoración, con formato de moneda en euros y tono cercano.
Si el resultado está vacío o es None, dilo con naturalidad (por ejemplo: "No encontré gastos de gasolina ayer").\n
"""

def gemini_call(prompt, system_prompt = None, max_retries = 3):
    wait = 2

    for i in range(max_retries):
        try:
            response = client.models.generate_content(
                model = "gemini-3.1-flash-lite",
                contents = prompt,
                config = types.GenerateContentConfig(
                    system_instruction = system_prompt
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
    return gemini_call(prompt, CLASSIFIER_PROMPT)

def sql_translate(prompt):
    return gemini_call(prompt, SQL_PROMPT)

def query_translate(prompt):
    return gemini_call(prompt, ANSWER_PROMPT)

# Checks if the query is a SELECT and contains no more than one 
def valid_query(query):
    query = query.lower()
    return query.startswith("select") and query.rstrip(";").count(";") == 0

load_dotenv()

client = genai.Client()

# Connection to the data base in Read-only mode
connection = sqlite3.connect("file:movimientos.db?mode=ro", uri = True)
cursor = connection.cursor()

while True:
    prompt = input("Tú: ").strip()
    command = prompt.lower()
    if command == "hasta luego":
        break

    elif command == "":
        continue

    classification = classify(prompt).strip()

    if(classification == "Consulta"):
        query = sql_translate(prompt).strip()
        print(f"[SQL] {query}")
        
        if not valid_query(query):
            response = "Consulta no válida..."
        else:
            try:
                cursor.execute(query)
                result = cursor.fetchall()

                query_prompt = textwrap.dedent(f"""
                    Pregunta del usuario: {prompt}
                    Consulta ejecutada: {query}
                    Resultado: {result}
                """)
                
                response = query_translate(query_prompt)
            
            except sqlite3.Error as e:
                response = "Error en la base de datos: {e} \n Por favor, vuelve a intentarlo..."

    else:
        response = "Iría al chat normal"

    print("\nAsistente:", response)
    print("-" * 100)

connection.close()