# AURA

AURA is a cross-platform personal AI assistant for macOS and Windows.

This first build is a local desktop-style web app with a Python backend, SQLite memory, system status, basic safe tools, and a futuristic command interface.

## Run

```bash
python3 backend/app.py
```

Then open:

```text
http://127.0.0.1:8765
```

On Windows, use:

```powershell
py backend/app.py
```

## Current Capabilities

- Futuristic AURA command interface
- Local chat endpoint with assistant responses
- Persistent memory using SQLite
- Basic system status
- Open websites and selected local apps
- Cross-platform backend structure

## Planned Capabilities

- Voice input and speech output
- OpenAI model integration
- Screen understanding
- File search and summarization
- Reminders and daily briefings
- Windows-specific PC control tools
- Packaged desktop app
