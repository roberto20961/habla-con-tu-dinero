import textwrap
import llm
import database
import prompts
import charts
import json
import gradio as gr
import time

state = {
    "history_sql": [],
    "history_operation": [],
    "mid_operation": False,
    "pending_bizum": None
}

# Formats an amount output to Euro format
def format_euros(amount):
    return f"{amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# Converts Gradio's chat history format to Gemini's expected format
def to_gemini_history(history):
    result = []
    for msg in history:
        content = msg["content"]
        if isinstance(content, str):
            text = content
        elif isinstance(content, list):
            text = "".join(p.get("text", "") for p in content if isinstance(p, dict))
        else:
            continue
        result.append({
            "role": "model" if msg["role"] == "assistant" else "user",
            "parts": [{"text": text}],
        })
    return result

def chat_logic(message, history):
    user_msg = message.strip()

    command = user_msg.lower()

    if command == "":
        yield "Ningún mensaje recibido."
        return

    if not state["mid_operation"] and state["pending_bizum"] is None:
        classification = llm.classify(user_msg)

        # If the server is overloaded and has not responded, the user should try again
        if classification is None:
            yield "Servidor saturado... Intente nuevamente en unos instantes."
            return

        classification = classification.strip()

    else:
        classification = "Operation"

    prompt = {
        "role": "user", 
        "parts": [{"text": user_msg}]
    }

    if classification == "Operation":
        yield "Preparando la operación..."

        if state["pending_bizum"] is not None:
            bizum_response = llm.bizum_approval(user_msg)

            # If the server is overloaded and has not responded, the user should try again
            if bizum_response is None:
                yield "Servidor saturado... Intente nuevamente en unos instantes."
                return
    
            bizum_response = bizum_response.strip()

            if bizum_response == "Positivo":
                # '**pending_bizum' autocompletes the function arguments with the user values
                response = database.send_bizum(**state["pending_bizum"])

            elif bizum_response == "Negativo":
                response = "Entendido, operación cancelada."

            else:
                response = f"He cancelado el Bizum a {state['pending_bizum']['receiver']} porque no entendí tu respuesta. Si quieres, vuelve a pedírmelo."

            state["mid_operation"] = False
            state["pending_bizum"] = None

        else:
            # Only the last six operations are used as the operations history in order to reduce the LLM usage
            operation = llm.operation_call(state["history_operation"][-6:] + [prompt])

            # If the server is overloaded and has not responded, the user should try again
            if operation is None:
                yield "Servidor saturado... Intente nuevamente en unos instantes."
                return

            # Name of the function that Gemini decided that should be called
            fc = operation.candidates[0].content.parts[0].function_call

            state["mid_operation"] = fc is None

            # If the model did not choose a function (most of the times because of lack of information)
            if fc is None:
                response = operation.text

                state["history_operation"].append(prompt)
                state["history_operation"].append({
                    "role": "model",
                    "parts": [{"text": response}]
                })

            else:
                if fc.name == "saldo":
                    balance = database.check_balance()
                    if balance is None:
                        yield "Error al acceder al saldo de la cuenta. Porfavor, vuelva a intentarlo."
                        return
                    
                    response = f"El saldo de su cuenta es de {format_euros(balance)}€"

                elif fc.name == "bizum":
                    args = fc.args
                    amount = args.get("amount")
                    receiver = args.get("receiver")

                    if not isinstance(amount, (int, float)) or not receiver:
                        yield "No he podido procesar el Bizum. Por favor, vuelve a intentarlo."
                        return

                    state["pending_bizum"] = args
                    response = f"Vas a enviar {format_euros(amount)}€ a {receiver}. ¿Confirmas?"

                    state["history_operation"].append(prompt)
                    state["history_operation"].append({
                        "role": "model",
                        "parts": [{"text": response}]
                    })

                else:
                    response = "Error en la operación. Por favor, inténtelo nuevamente..."

    elif classification == "Consulta":
        yield "Consultando la base de datos..."

        query = llm.sql_translate(state["history_sql"] + [prompt])

        # If the server is overloaded and has not responded, the user should try again
        if query is None:
           yield "Servidor saturado... Intente nuevamente en unos instantes."
           return

        query = query.strip()
        
        if not database.valid_query(query):
            response = "Consulta no válida, inténtelo de nuevo."

        # If the query does not access the transaction table, we redirect the conversation
        elif not database.table_query(query):
            classification = "Charla"

        else:
            result, columns = database.run_query(query)

            if result is None:
                response = "Error en la base de datos. Por favor, vuelve a intentarlo..."

            else:
                query_prompt = textwrap.dedent(f"""
                    Pregunta del usuario: {user_msg}
                    Consulta ejecutada: {query}
                    Resultado: {result}
                """)
                
                response = llm.query_translate(state["history_sql"] + [query_prompt])

                # If the server is overloaded and has not responded, the user should try again
                if response is None:
                    yield "Servidor saturado... Intente nuevamente en unos instantes."
                    return

                figure = None
                # If the query returns only one row, we don't even ask whether a chart is needed
                if len(result) > 1:
                    yield "Analizando los datos..."

                    graph_prompt = query_prompt + f"\n Nombres de las columnas: {columns}"
                    graph_response = llm.graphic_call(graph_prompt)

                    if graph_response is not None:
                        try:
                            graph_info = json.loads(graph_response)
                            print(graph_info)
                            figure = charts.build_plot(graph_info, result, columns)

                        except (json.JSONDecodeError, TypeError):
                            figure = None

                state["history_sql"].append(prompt)

                state["history_sql"].append({
                    "role": "model",
                    "parts": [{"text": query}]
                })

                if figure is not None:
                    yield [
                        {"role": "assistant", "content": response},
                        {"role": "assistant", "content": gr.Plot(figure)},
                    ]
                    return
                else:
                    yield response
                    return


    if classification != "Consulta" and classification != "Operation":
        response = llm.gemini_call(to_gemini_history(history) + [prompt], prompts.SYSTEM_PROMPT)

        # If the server is overloaded and has not responded, the user should try again
        if response is None:
            yield "Servidor saturado... Intente nuevamente en unos instantes."
            return

    yield response

def chat(message, history):
    start = time.time()
    for chunk in chat_logic(message, history):
        yield chunk
    print(f"[TIEMPO] {time.time() - start:.2f}s")