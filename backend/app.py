from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import json
import os
import platform
import sqlite3
import subprocess
import sys
import time
import urllib.parse
import webbrowser


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "aura.db"
HOST = "127.0.0.1"
PORT = int(os.environ.get("AURA_PORT", "8765"))


class AuraCore:
    def __init__(self) -> None:
        DATA_DIR.mkdir(exist_ok=True)
        self._init_db()

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
        return {
            "platform": platform.system(),
            "platform_release": platform.release(),
            "machine": platform.machine(),
            "python": platform.python_version(),
            "cwd": str(ROOT),
        }

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
                    "and keep an activity log. Next upgrades: voice, model intelligence, "
                    "file search, reminders, and deeper Windows controls."
                )
            }

        recent = self.memories(3)
        memory_hint = ""
        if recent:
            memory_hint = " I am also keeping local memory for this project."
        return {
            "reply": (
                "AURA is online. I can take simple commands now: try 'status', "
                "'remember my favorite color is blue', or 'open https://github.com'."
                + memory_hint
            )
        }


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
