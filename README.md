# AURA

AURA is a cross-platform personal AI assistant for macOS and Windows.

This first build is a local desktop-style web app with a Python backend, SQLite memory, system status, basic safe tools, and a futuristic command interface.

## Run

Install dependencies:

```bash
python3 -m pip install -r requirements.txt
```

Create a local environment file:

```bash
cp .env.example .env
```

Then edit `.env` for the AI brain you want. Never commit `.env` to GitHub.

For free local AI on a Windows PC, install Ollama, then run:

```powershell
ollama pull llama3.1:8b
```

Use this local-only `.env` setup:

```text
AURA_PROVIDER=ollama
OLLAMA_URL=http://127.0.0.1:11434
OLLAMA_MODEL=llama3.1:8b
OPENAI_API_KEY=
OPENAI_MODEL=gpt-5.5
```

For OpenAI API mode, set `AURA_PROVIDER=openai` and add your `OPENAI_API_KEY`.
For automatic mode, set `AURA_PROVIDER=auto`; AURA will try Ollama first, then OpenAI.

Start AURA:

```bash
python3 backend/app.py
```

Then open:

```text
http://127.0.0.1:8765
```

On Windows, use:

```powershell
py -m pip install -r requirements.txt
copy .env.example .env
py backend/app.py
```

## Current Capabilities

- Futuristic AURA command interface
- Local chat endpoint with assistant responses
- Persistent memory using SQLite
- Basic system status
- Open websites and selected local apps
- Local AI through Ollama when configured
- OpenAI-powered responses when `OPENAI_API_KEY` is configured
- Cross-platform backend structure

## Planned Capabilities

- Voice input and speech output
- Screen understanding
- File search and summarization
- Reminders and daily briefings
- Windows-specific PC control tools
- Packaged desktop app
