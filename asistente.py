from google import genai
from dotenv import load_dotenv
from google.genai import errors
from google.genai import types
import time
from datetime import date
import sqlite3
import textwrap

SYSTEM_PROMPT = """
Eres un asistente virtual de finanzas que trabaja para el banco Unicaja. 
Tu deber es realizar operaciones claves y sencillas como 'Consulta de saldo' o
'Transferencias via Bizum'. Tambien deberás saber responder a preguntas como
'¿Cuánto llevo gastado en gasolina este mes?' o '¿Cuándo pagué el seguro del coche?,
Evita responder cualquier pregunta que este fuera de este contexto, si te preguntan algo ajeno al banco, 
di que no es tu función, sin dar más motivos.
Hablarás en español, con un tono cercano y amigable, con respuestas cortas y en máximo de dos frases.
Además, no termines cada respuesta ofreciendo más ayuda.
Cuando no seas capaz de generar una respuesta o no tengas el dato, no te inventarás nada
y responderás con sinceridad.
"""

today = date.today().isoformat() # Today's date
SQL_PROMPT = f"""
Tu tarea es traducir la pregunta del usuario a una consulta SQL de SQLite.
Únicamente vas a generar consultas SELECT.
Mapea los términos del usuario a la categoría más adecuada de la lista, por ejemplo si la pregunta es 'Cuánto gasté
en gasolina?', la categoría sería 'Transporte'.
Si el usuario pregunta por conceptos que no son categorías (suscripciones, gasolina, farmacia...), filtra 
por concepto LIKE en lugar de por categoría, y además, deberás buscar en el concepto por ejemplo para gasolina busca REPSOL, CEPSA, BP...
O para suscripciones busca NETFLIX, SPOTIFY, HBO... Prueba con empresas famosas.
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
Tu tarea es leer el mensaje del usuario y clasificarlo únicamente en una de las tres siguientes categorías:
1. Charla: Casos en los que el usuario esté saludando o charlando normalmente.
2. Operation: Casos en los que el usuario quiera saber el saldo de su cuenta o quiera enviar un Bizum a alguien.
3. Consulta: Casos en los que el usuario quiere consultar cualquier cosa de su cuenta de 
banco excepto el saldo (que sería "Operation"), como por ejemplo 'Cuánto dinero gasté el mes pasado en gasolina?'.
El formato de salida deberá ser únicamente la categoría a la que pertenece: "Charla", "Operation" o "Consulta", sin 
nada de texto adicional, sin bloques de markdown, sin ```.
"""

ANSWER_PROMPT = """
Tu tarea es convertir el resultado de una consulta a una base de datos en una respuesta legible para el usuario.
Responderás en español, de forma breve en una sola frase siempre que se pueda, sin mucha decoración, 
con formato de moneda en euros y tono cercano.
Si el resultado está vacío o es None, dilo con naturalidad (por ejemplo: "No encontré gastos de gasolina ayer").\n
"""

OPERATION_PROMPT = """
Tu tarea es elegir y preparar una entre dos operaciones disponibles:
1. saldo: Permite al usuario saber el saldo actual de su cuenta de banco. No tiene ningun requisito.
2. bizum: Permite al usuario enviar una cantidad de dinero mediante Bizum a un contacto o número de teléfono.
Debes responder siempre siempre de forma breve en una frase sin juzgar si la cantidad es válida o si hay saldo,
solo debes llamar a la función con lo que el usuario pidió.
En este caso sí que existen requisitos, y es que el usuario debe especificar el Destinatario y la Cantidad.
Si no tienes uno de estos datos, deberás pedírselos al usuario de forma breve en una frase corta: NUNCA invertarte ninguno si no
lo tienes, SIEMPRE pedirlos la usuario.
"""

BIZUM_PROMPT = """
Tu tarea es leer el mensaje del usuario a una pregunta de si autoriza un determinado Bizum y decidir si está autorizando realizar la 
operación, está negando la operación o si ha cambiado de tema.
La información del Bizum es un destinatario y una cantidad, así que solo podría cambiar una de estas cosas.
Deberás clasificar el mensaje en una de estas categorías:
1. Positivo: Casos en los que el usuario autorice la operación.
2. Negativo: Casos en los que el usuario rechace la operación.
3. Otro: Casos en los que el usuario responda algo que no tenga nada que ver.
El formato de salida deberá ser únicamente la categoría a la que pertenece: "Positivo", "Negativo" o "Otro", sin 
nada de texto adicional, sin bloques de markdown, sin ```.
"""

#************************************************************************************************************************

# Allows making Gemini calls with history or simple prompt, system instructions and exponential backoff
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

def bizum_approval(prompt):
    return gemini_call(prompt, BIZUM_PROMPT)

# Checks if the query is a SELECT and contains no more than one 
def valid_query(query):
    query = query.lower()
    return query.startswith("select") and query.rstrip(";").count(";") == 0

# Checks whether the query accesses the transaction table
def table_query(query):
    query = query.lower()
    return "from transaccion" in query

# Formats an amount output to Euro format
def format_euros(amount):
    return f"{amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
#************************************************************************************************************************

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

# Returns the total balance of the user bank account
def check_balance():
    try:
        cursor.execute("SELECT SUM(importe) FROM transaccion")
        balance = cursor.fetchone()
        if balance[0] is None:
            return None
        
        return float(balance[0])
    
    except sqlite3.Error:
        return None

# Allow the user to send a Bizum and adds the movement to the bank account
def send_bizum(receiver, amount):
    balance = check_balance()
    if balance is None:
        return "Error en la base de datos..."

    elif amount <= 0:
        return "La cantidad del Bizum no puede ser de nula o negativa."

    elif amount > balance:
        return "La cantidad del Bizum supera al saldo de su cuenta."
    
    try:
        w_connection = sqlite3.connect("movimientos.db")
        w_cursor = w_connection.cursor()

        w_cursor.execute("INSERT INTO transaccion (fecha, importe, concepto, categoria) VALUES (?, ?, ?, ?)",
                          (today, -amount, f"Bizum a {receiver}", "Otros"))
        
        w_connection.commit()
        w_connection.close()
        
        return f"Bizum de {amount}€ enviado a {receiver} correctamente."
    
    except sqlite3.Error:
        w_connection.close()
        return "Error en la base de datos..."

def operation_call(prompt, max_retries = 3):
    wait = 2

    for i in range(max_retries):
        try:
            response = client.models.generate_content(
                model = "gemini-3.1-flash-lite",
                contents = prompt,
                config = types.GenerateContentConfig(
                    tools = [tools],
                    system_instruction = OPERATION_PROMPT
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

#************************************************************************************************************************

load_dotenv()

client = genai.Client()

print("Bienvenido al asistente bancario de Unicaja, ¿qué desea hoy?\n")

# Connection to the data base in Read-only mode
connection = sqlite3.connect("file:movimientos.db?mode=ro", uri = True)
cursor = connection.cursor()

history = []
history_sql = []
history_operation = []

mid_operation = False
pending_bizum = None

while True:
    user_msg = input("Tú: ").strip()
    command = user_msg.lower()
    if command == "hasta luego":
        break

    # To delete the memory of the chatbot, introduce 'clear' in the chat
    elif command == "clear":
        history.clear()
        history_sql.clear()
        history_operation.clear()
        mid_operation = False
        pending_bizum = None
        print("\nLimpiando historial...")
        print("-" * 100)
        continue

    elif command == "":
        continue

    if not mid_operation and pending_bizum is None:
        classification = classify(user_msg)

        # If the server is overloaded and has not responded, the user should try again
        if classification is None:
            print("Servidor saturado... Intente nuevamente en unos instantes.")
            print("-" * 100)
            continue

        classification = classification.strip()

    else:
        classification = "Operation"

    prompt = {
        "role": "user", 
        "parts": [{"text": user_msg}]
    }

    if classification == "Operation":
        if pending_bizum is not None:
            bizum_response = bizum_approval(user_msg)

            # If the server is overloaded and has not responded, the user should try again
            if bizum_response is None:
                print("Servidor saturado... Intente nuevamente en unos instantes.")
                print("-" * 100)
                continue
    
            bizum_response = bizum_response.strip()

            if bizum_response == "Positivo":
                # '**pending_bizum' autocompletes the function arguments with the user values
                response = send_bizum(**pending_bizum)

            elif bizum_response == "Negativo":
                response = "Entendido, operación cancelada."

            else:
                response = f"He cancelado el Bizum a {pending_bizum['receiver']} porque no entendí tu respuesta. Si quieres, vuelve a pedírmelo."

            mid_operation = False
            pending_bizum = None
            
        else:
            # Only the last six operations are used as the operations history in order to reduce the LLM usage
            operation = operation_call(history_operation[-6:] + [prompt])

            # If the server is overloaded and has not responded, the user should try again
            if operation is None:
                print("Servidor saturado... Intente nuevamente en unos instantes.")
                print("-" * 100)
                continue

            # Name of the function that Gemini decided that should be called
            fc = operation.candidates[0].content.parts[0].function_call

            mid_operation = fc is None

            # If the model did not choose a function (most of the times because of lack of information)
            if fc is None:
                response = operation.text

                history_operation.append(prompt)
                history_operation.append({
                    "role": "model",
                    "parts": [{"text": response}]
                })

            else:
                if fc.name == "saldo":
                    response = f"El saldo de su cuenta es de {format_euros(check_balance())}€"

                elif fc.name == "bizum":
                    pending_bizum = fc.args
                    response = f"Vas a enviar {format_euros(pending_bizum['amount'])}€ a {pending_bizum['receiver']}. ¿Confirmas?"

                    history_operation.append(prompt)
                    history_operation.append({
                        "role": "model",
                        "parts": [{"text": response}]
                    })

                else:
                    response = "Error en la operación. Por favor, inténtelo nuevamente..."

    elif classification == "Consulta":
        query = sql_translate(history_sql + [prompt])

        # If the server is overloaded and has not responded, the user should try again
        if query is None:
            print("Servidor saturado... Intente nuevamente en unos instantes.")
            print("-" * 100)
            continue
        
        print(f"[SQL] {query}")

        query = query.strip()
        
        if not valid_query(query):
            response = "Consulta no válida, inténtelo de nuevo."

        # If the query does not access the transaction table, we redirect the conversation
        elif not table_query(query):
            classification = "Charla"

        else:
            try:
                cursor.execute(query)
                result = cursor.fetchall()

                query_prompt = textwrap.dedent(f"""
                    Pregunta del usuario: {user_msg}
                    Consulta ejecutada: {query}
                    Resultado: {result}
                """)
                
                response = query_translate(history_sql + [query_prompt])

                # If the server is overloaded and has not responded, the user should try again
                if response is None:
                    print("Servidor saturado... Intente nuevamente en unos instantes.")
                    print("-" * 100)
                    continue

                history_sql.append(prompt)

                history_sql.append({
                    "role": "model",
                    "parts": [{"text": query}]
                })
            
            except sqlite3.Error as e:
                response = f"Error en la base de datos: {e} \n Por favor, vuelve a intentarlo..."

    if classification != "Consulta" and classification != "Operation":
        response = gemini_call(history + [prompt], SYSTEM_PROMPT)

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

connection.close()