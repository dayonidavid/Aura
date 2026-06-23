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

Then edit `.env` and replace `your_api_key_here` with your OpenAI API key.
Never commit `.env` to GitHub.

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
- OpenAI-powered responses when `OPENAI_API_KEY` is configured
- Cross-platform backend structure

## Planned Capabilities

- Voice input and speech output
- Screen understanding
- File search and summarization
- Reminders and daily briefings
- Windows-specific PC control tools
- Packaged desktop app
