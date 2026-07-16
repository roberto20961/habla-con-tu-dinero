# habla-con-tu-dinero

**habla-con-tu-dinero** es un agente conversacional capaz de permitir una interacción natural con el usuario y actuar como un asistente financiero capaz de realizar **operaciones financieras** y **consultas de movimientos**.

**El agente se encuentra en ESTADO DE DESARROLLO**

El stack utilizado en su desarrollo es la combinación de **Python**, **Gemini**, **SQLite**, **Plotly** y **Gradio**.

## Cómo ejecutarlo

Necesitas Python 3.9 o superior.

**1. Clona el repositorio**

```bash
git clone git@github.com:roberto20961/habla-con-tu-dinero.git
cd habla-con-tu-dinero
```

**2. Crea y activa un entorno virtual**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

**3. Instala las dependencias**

```bash
pip install -r requirements.txt
```

**4. Configura tu API key**

Consigue una clave gratuita en [Google AI Studio](https://aistudio.google.com/app/apikey) y crea un archivo `.env` en la raíz del proyecto con el siguiente contenido:

```
GEMINI_API_KEY=tu_clave_aqui
```

**5. Ejecuta el asistente**

```bash
python asistente.py
```
