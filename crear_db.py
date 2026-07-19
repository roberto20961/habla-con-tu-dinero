import sqlite3
import json
from dotenv import load_dotenv
from google import genai
from google.genai import errors
from google.genai import types
import time

GENERATION_PROMPT = """
Genera 200 transacciones bancarias realistas de un cliente español normal.

Devuelve EXCLUSIVAMENTE un array JSON, sin texto antes ni después, sin markdown.
El formato es una lista de objetos, cada uno con exactamente estos campos:

[
  {"fecha": "2025-03-14", "importe": -48.75, "concepto": "REPSOL E.S. GRANADA", "categoria": "Transporte"},
  {"fecha": "2025-03-25", "importe": 1850.00, "concepto": "NÓMINA EMPRESA S.L.", "categoria": "Ingresos"}
]

Reglas:
- No incluyas el campo id (se autogenera en la base de datos).
- Las fechas van entre 2025-01-01 y 2026-07-19, en formato AAAA-MM-DD.
- Los gastos son importes NEGATIVOS; los ingresos, POSITIVOS.
- Solo un ingreso (nómina) por mes; el resto son gastos.
- El concepto debe ser el nombre real de un comercio o entidad (ej. "MERCADONA", "NETFLIX", "ENDESA ENERGIA"), en mayúsculas.
- La categoría debe ser coherente con el concepto y el importe.
- Usa SOLO estas categorías: Ocio, Restaurantes, Supers e Hipers, Salud, Bienestar y Belleza, Transporte, Hogar,
Donaciones, Educación, Ropa y calzado, Electrónica y Electrodomésticos, Otros, Ingresos.
"""

def gemini_call(prompt, max_retries = 3):
    wait = 2

    for i in range(max_retries):
        try:
            response = client.models.generate_content(
                model = "gemini-3.1-flash-lite",
                contents = prompt,
                config = types.GenerateContentConfig(
                    response_mime_type = "application/json"
                )
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

connection = sqlite3.connect("movimientos.db")
cursor = connection.cursor()

cursor.execute("""

    CREATE TABLE IF NOT EXISTS transaccion(
        id INTEGER PRIMARY KEY,
        fecha TEXT CHECK(fecha LIKE '____-__-__'),
        importe REAL,
        concepto TEXT,
        categoria TEXT CHECK(categoria IN ('Ocio', 'Restaurantes', 'Supers e Hipers', 'Salud', 'Bienestar y Belleza', 
                                           'Transporte', 'Hogar', 'Donaciones', 'Educación', 'Ropa y calzado', 
                                           'Electrónica y Electrodomésticos', 'Otros', 'Ingresos'))
    )

""")

load_dotenv()

client = genai.Client()

db_response = gemini_call(GENERATION_PROMPT)

if db_response is None:
    print("Servidor saturado... Intente nuevamente en unos instantes.")

else:
    cursor.execute("DELETE FROM transaccion")
    data = json.loads(db_response)
    
    for t in data:
        cursor.execute("INSERT INTO transaccion (fecha, importe, concepto, categoria) VALUES (?, ?, ?, ?)",
                       (t["fecha"], t["importe"], t["concepto"], t["categoria"]))
    
    connection.commit()

connection.close()