import gradio as gr
import agent

gr.ChatInterface(
    agent.chat,
    title = "Habla con tu dinero",
    description = "Asistente virtual de Unicaja. Consulta tus movimientos, revisa tu saldo y envía Bizums hablando con naturalidad.",
    examples = [
        "Envía un Bizum.",
        "¿Cuál es el saldo actual de mi cuenta?",
        "¿Cuánto gasté en gasolina en abril?",
        "¿Cómo han evolucionado mis gastos el año pasado?",
    ],
    textbox=gr.Textbox(placeholder="Escribe tu mensaje..."),
    chatbot=gr.Chatbot(placeholder="<center><h2>¿En qué puedo ayudarte hoy?</h2></center>", height=450,),
).launch(theme=gr.themes.Default(primary_hue="green"), footer_links=[])