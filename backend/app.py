from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import json
import os
import platform
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "aura.db"
HOST = "127.0.0.1"
PORT = int(os.environ.get("AURA_PORT", "8765"))


def load_env_file() -> None:
    env_path = ROOT / ".env"
    if not env_path.exists():
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        clean = line.strip()
        if not clean or clean.startswith("#") or "=" not in clean:
            continue
        key, value = clean.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


load_env_file()
AURA_PROVIDER = os.environ.get("AURA_PROVIDER", "auto").lower()
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", os.environ.get("AURA_MODEL", "gpt-5.5"))
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.1:8b")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")


class AuraCore:
    def __init__(self) -> None:
        DATA_DIR.mkdir(exist_ok=True)
        self.ai_error = ""
        self.ai_provider = "offline"
        self.openai_client = self._create_openai_client()
        self._init_db()

    def _create_openai_client(self):
        if not os.environ.get("OPENAI_API_KEY"):
            return None

        try:
            from openai import OpenAI
        except ImportError:
            self.ai_error = "The openai Python package is not installed."
            return None

        try:
            return OpenAI()
        except Exception as exc:
            self.ai_error = f"Could not initialize OpenAI client: {exc}"
            return None

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(DB_PATH)

    def _init_db(self) -> None:
        with self._connect() as db:
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    kind TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at REAL NOT NULL
                )
                """
            )
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action TEXT NOT NULL,
                    detail TEXT NOT NULL,
                    created_at REAL NOT NULL
                )
                """
            )

    def remember(self, kind: str, content: str) -> dict:
        content = content.strip()
        if not content:
            return {"ok": False, "message": "Nothing to remember."}
        with self._connect() as db:
            db.execute(
                "INSERT INTO memories (kind, content, created_at) VALUES (?, ?, ?)",
                (kind, content, time.time()),
            )
        self.log_event("memory", content)
        return {"ok": True, "message": "Memory saved."}

    def memories(self, limit: int = 8) -> list[dict]:
        with self._connect() as db:
            rows = db.execute(
                "SELECT kind, content, created_at FROM memories ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [
            {"kind": kind, "content": content, "created_at": created_at}
            for kind, content, created_at in rows
        ]

    def log_event(self, action: str, detail: str) -> None:
        with self._connect() as db:
            db.execute(
                "INSERT INTO events (action, detail, created_at) VALUES (?, ?, ?)",
                (action, detail, time.time()),
            )

    def events(self, limit: int = 8) -> list[dict]:
        with self._connect() as db:
            rows = db.execute(
                "SELECT action, detail, created_at FROM events ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [
            {"action": action, "detail": detail, "created_at": created_at}
            for action, detail, created_at in rows
        ]

    def system_status(self) -> dict:
        display_provider = self.ai_provider
        if display_provider == "offline" and AURA_PROVIDER in {"auto", "ollama", "openai"}:
            display_provider = AURA_PROVIDER
        return {
            "platform": platform.system(),
            "platform_release": platform.release(),
            "machine": platform.machine(),
            "python": platform.python_version(),
            "cwd": str(ROOT),
            "ai_enabled": display_provider != "offline" or self.openai_client is not None,
            "ai_provider": display_provider,
            "ai_model": self.ai_model_label(),
            "ai_error": self.ai_error,
        }

    def ai_model_label(self) -> str:
        if self.ai_provider == "ollama":
            return OLLAMA_MODEL
        if self.ai_provider == "openai":
            return OPENAI_MODEL
        if AURA_PROVIDER == "ollama":
            return OLLAMA_MODEL
        if AURA_PROVIDER == "openai":
            return OPENAI_MODEL
        return f"auto: {OLLAMA_MODEL} / {OPENAI_MODEL}"

    def open_target(self, target: str) -> dict:
        target = target.strip()
        if not target:
            return {"ok": False, "message": "No target provided."}

        if target.startswith(("http://", "https://")):
            webbrowser.open(target)
            self.log_event("open_url", target)
            return {"ok": True, "message": f"Opened {target}"}

        app_result = self._open_app(target)
        self.log_event("open_app", target)
        return app_result

    def _open_app(self, app_name: str) -> dict:
        system = platform.system()
        try:
            if system == "Darwin":
                subprocess.Popen(["open", "-a", app_name])
            elif system == "Windows":
                os.startfile(app_name)  # type: ignore[attr-defined]
            elif system == "Linux":
                subprocess.Popen([app_name])
            else:
                return {"ok": False, "message": f"Unsupported platform: {system}"}
        except Exception as exc:
            return {"ok": False, "message": f"Could not open {app_name}: {exc}"}
        return {"ok": True, "message": f"Opening {app_name}"}

    def reply(self, message: str) -> dict:
        clean = message.strip()
        lower = clean.lower()
        self.log_event("message", clean)

        if not clean:
            return {"reply": "I am here. Give me a command or a thought to work with."}

        if lower.startswith("remember "):
            memory = clean[len("remember ") :]
            result = self.remember("user", memory)
            return {"reply": result["message"]}

        if lower in {"status", "system status", "pc status"}:
            status = self.system_status()
            return {
                "reply": (
                    f"AURA core is online on {status['platform']} {status['platform_release']} "
                    f"using Python {status['python']}."
                )
            }

        if lower.startswith("open "):
            target = clean[len("open ") :]
            result = self.open_target(target)
            return {"reply": result["message"]}

        if "what can you do" in lower:
            return {
                "reply": (
                    "I can remember notes, report system status, open websites or apps, "
                    "keep an activity log, and use a local Ollama model or OpenAI for natural "
                    "conversation when configured. Next upgrades: voice, file search, reminders, "
                    "and deeper Windows controls."
                )
            }

        ai_reply = self.ask_ai(clean)
        if ai_reply:
            return {"reply": ai_reply}

        recent = self.memories(3)
        memory_hint = ""
        if recent:
            memory_hint = " I am also keeping local memory for this project."
        return {
            "reply": (
                "AURA is online, but no AI brain is available yet. For a free local brain, "
                "install Ollama, pull a model, and set AURA_PROVIDER=ollama in .env. "
                "For now, try 'status', 'remember my favorite color is blue', or "
                "'open https://github.com'."
                + memory_hint
            )
        }

    def ask_ai(self, message: str) -> str:
        instructions = self.ai_instructions()

        if AURA_PROVIDER in {"auto", "ollama"}:
            reply = self.ask_ollama(
                instructions,
                message,
                log_errors=AURA_PROVIDER == "ollama",
            )
            if reply:
                self.ai_provider = "ollama"
                self.ai_error = ""
                return reply
            if AURA_PROVIDER == "ollama":
                return ""

        if AURA_PROVIDER in {"auto", "openai"}:
            reply = self.ask_openai(instructions, message)
            if reply:
                self.ai_provider = "openai"
                self.ai_error = ""
                return reply

        self.ai_provider = "offline"
        return ""

    def ai_instructions(self) -> str:
        memory_lines = [f"- {item['content']}" for item in reversed(self.memories(5))]
        memory_context = "\n".join(memory_lines) or "- No saved memories yet."
        status = self.system_status()

        return f"""
You are AURA, a futuristic personal desktop AI assistant for David.
You are calm, concise, capable, and a little sleek. You help with daily tasks,
computer work, coding, planning, and learning.

Current local system:
- Platform: {status['platform']} {status['platform_release']}
- Machine: {status['machine']}

Current saved memories:
{memory_context}

Important behavior:
- If the user asks for a local action, explain what you can do now and what command
  they can type, such as "open Safari" or "remember ...".
- Do not pretend you have performed OS actions unless the local backend did it.
- Keep answers practical and direct.
""".strip()

    def ask_ollama(self, instructions: str, message: str, log_errors: bool = True) -> str:
        payload = {
            "model": OLLAMA_MODEL,
            "stream": False,
            "messages": [
                {"role": "system", "content": instructions},
                {"role": "user", "content": message},
            ],
        }
        request = urllib.request.Request(
            f"{OLLAMA_URL.rstrip('/')}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                data = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            self.ai_error = f"Ollama unavailable: {exc}"
            if log_errors:
                self.log_event("ai_error", self.ai_error)
            return ""

        content = data.get("message", {}).get("content", "").strip()
        if content:
            self.log_event("ai_reply", f"ollama:{OLLAMA_MODEL}")
        return content

    def ask_openai(self, instructions: str, message: str) -> str:
        if self.openai_client is None:
            if not self.ai_error:
                self.ai_error = "OPENAI_API_KEY is not set."
            return ""

        try:
            response = self.openai_client.responses.create(
                model=OPENAI_MODEL,
                instructions=instructions,
                input=message,
            )
        except Exception as exc:
            self.ai_error = str(exc)
            self.log_event("ai_error", str(exc))
            return (
                "I tried to use the OpenAI brain, but it failed. Check your API key, "
                "model access, and internet connection."
            )

        self.log_event("ai_reply", f"openai:{OPENAI_MODEL}")
        return response.output_text.strip()


core = AuraCore()


class AuraHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(FRONTEND), **kwargs)

    def do_GET(self) -> None:
        if self.path == "/api/status":
            self.send_json(
                {
                    "system": core.system_status(),
                    "memories": core.memories(),
                    "events": core.events(),
                }
            )
            return
        super().do_GET()

    def do_POST(self) -> None:
        body = self.read_json()
        if self.path == "/api/chat":
            self.send_json(core.reply(str(body.get("message", ""))))
            return
        if self.path == "/api/remember":
            self.send_json(core.remember(str(body.get("kind", "user")), str(body.get("content", ""))))
            return
        if self.path == "/api/open":
            self.send_json(core.open_target(str(body.get("target", ""))))
            return
        self.send_error(404, "Unknown endpoint")

    def read_json(self) -> dict:
        length = int(self.headers.get("content-length", "0"))
        if length == 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {}

    def send_json(self, payload: dict) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def main() -> None:
    if not FRONTEND.exists():
        print("Missing frontend directory.", file=sys.stderr)
        raise SystemExit(1)
    server = ThreadingHTTPServer((HOST, PORT), AuraHandler)
    print(f"AURA online: http://{HOST}:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nAURA shutting down.")


if __name__ == "__main__":
    main()
