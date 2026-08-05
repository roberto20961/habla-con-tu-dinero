import gradio as gr
import agent

gr.ChatInterface(agent.chat).launch()