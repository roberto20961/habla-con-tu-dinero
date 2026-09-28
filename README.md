# Habla con tu dinero

Asistente conversacional que permite consultar y gestionar movimientos bancarios hablando con naturalidad. Traduce preguntas en lenguaje natural a consultas SQL, ejecuta operaciones financieras y decide por sí mismo cuándo una respuesta se entiende mejor con un gráfico.

Proyecto desarrollado para el reto de la **Cátedra UGR-Unicaja de IA Responsable en Finanzas**.

## Qué hace

- **Conversación natural** con memoria de contexto, capaz de resolver referencias entre turnos (*"¿y el mes anterior?"*).
- **Consultas sobre movimientos** en lenguaje natural, traducidas a SQL y ejecutadas contra la base de datos del cliente.
- **Operaciones financieras** simuladas mediante invocación de funciones: consulta de saldo y envío de Bizum con confirmación previa.
- **Respuestas visuales**: el sistema decide si la respuesta necesita un gráfico, de qué tipo, y lo genera dentro de la conversación.

## Stack

Python · Gemini API · SQLite · Plotly · Gradio

## Cómo ejecutarlo

Probado con Python 3.12.

**1. Clona el repositorio**

```bash
git clone https://github.com/roberto20961/habla-con-tu-dinero.git
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

Consigue una clave gratuita en [Google AI Studio](https://aistudio.google.com/app/apikey) y crea un archivo `.env` en la raíz del proyecto:

```
GEMINI_API_KEY=tu_clave_aqui
```

**5. Genera la base de datos**

Los movimientos son ficticios y se generan con el propio modelo. Este paso solo se ejecuta una vez:

```bash
python crear_db.py
```

**6. Lanza el asistente**

```bash
cd src
python app.py
```

La interfaz se abre en `http://127.0.0.1:7860`.

## Estructura del proyecto

```
habla-con-tu-dinero/
├── crear_db.py         # Generación de la base de datos (ejecución única)
├── movimientos.db      # Base de datos SQLite (generada, no versionada)
├── requirements.txt
└── src/
    ├── app.py          # Punto de entrada: interfaz Gradio
    ├── agent.py        # Orquestación: clasificación, enrutado y estado
    ├── llm.py          # Llamadas a Gemini y declaración de herramientas
    ├── database.py     # Acceso a SQLite y validación de consultas
    ├── charts.py       # Construcción de gráficos con Plotly
    └── prompts.py      # Instrucciones de cada llamada al modelo
```

## Notas

- Los movimientos son **ficticios**, generados con un LLM. No hay datos reales de ninguna persona.
- Las operaciones de Bizum son una **simulación**: escriben en la base de datos local, no realizan ninguna transferencia real.
- La aplicación debe lanzarse desde `src/`, ya que las rutas a la base de datos son relativas.