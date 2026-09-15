#!/usr/bin/env python3
"""Local browser control panel for the Gmail organizer."""

import html
import os
import subprocess
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs


ROOT = os.path.dirname(os.path.abspath(__file__))
PYTHON = os.path.join(ROOT, ".venv", "bin", "python")
PORT = int(os.environ.get("GMAIL_ORGANIZER_PORT", "8765"))
RUN_LOCK = threading.Lock()

ACTIONS = {
    "rules": ("Apply sender rules", ["apply_rules.py"], 600),
    "archive": ("Archive labeled mail", ["move_labeled.py"], 600),
    "filters": ("Create or update Gmail filters", ["create_filters.py"], 600),
    "ai-preview": ("Preview local AI classification", ["organize.py", "--dry-run", "--limit", "20"], 900),
}


def page(message=""):
    safe_message = html.escape(message)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Local Gmail Organizer</title>
<style>
  :root {{ color-scheme: dark; font-family: system-ui, sans-serif; }}
  body {{ background: #111827; color: #e5e7eb; margin: 0; }}
  main {{ max-width: 760px; margin: 8vh auto; padding: 0 24px; }}
  h1 {{ font-size: 2rem; letter-spacing: -.03em; }}
  p {{ color: #9ca3af; line-height: 1.5; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px; margin: 28px 0; }}
  form {{ background: #1f2937; border: 1px solid #374151; border-radius: 12px; padding: 16px; }}
  button {{ width: 100%; background: #60a5fa; border: 0; border-radius: 8px; color: #0f172a; cursor: pointer; font: inherit; font-weight: 700; padding: 11px; }}
  button:hover {{ background: #93c5fd; }}
  pre {{ background: #030712; border: 1px solid #374151; border-radius: 12px; overflow: auto; padding: 16px; white-space: pre-wrap; }}
  .notice {{ color: #bfdbfe; }}
</style>
</head>
<body><main>
<h1>Local Gmail Organizer</h1>
<p class="notice">Local control panel: Gmail data is handled by the existing scripts and Ollama stays on this machine.</p>
<div class="grid">
  <form method="post" action="/run"><input type="hidden" name="action" value="rules"><button>Apply sender rules</button></form>
  <form method="post" action="/run"><input type="hidden" name="action" value="archive"><button>Archive labeled mail</button></form>
  <form method="post" action="/run"><input type="hidden" name="action" value="filters"><button>Create/update Gmail filters</button></form>
  <form method="post" action="/run" onsubmit="return confirm('Run a local AI preview on 20 messages?')"><input type="hidden" name="action" value="ai-preview"><button>Preview AI classification</button></form>
</div>
{('<h2>Last result</h2><pre>' + safe_message + '</pre>') if message else ''}
</main></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def send_page(self, body, status=200):
        encoded = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(encoded)

    def do_GET(self):
        if self.path != "/":
            self.send_page("Not found", 404)
            return
        self.send_page(page())

    def do_POST(self):
        if self.path != "/run":
            self.send_page("Not found", 404)
            return
        length = int(self.headers.get("Content-Length", "0"))
        values = parse_qs(self.rfile.read(length).decode("utf-8"))
        action = values.get("action", [""])[0]
        if action not in ACTIONS:
            self.send_page(page("Unknown action"), 400)
            return
        if not RUN_LOCK.acquire(blocking=False):
            self.send_page(page("Another action is already running."), 409)
            return
        title, command, timeout = ACTIONS[action]
        try:
            result = subprocess.run(
                [PYTHON, *command], cwd=ROOT, capture_output=True, text=True, timeout=timeout, check=False
            )
            output = f"{title}\n\n$ {' '.join(command)}\n\n{result.stdout}{result.stderr}"
            if result.returncode:
                output += f"\nExit code: {result.returncode}"
            self.send_page(page(output), 200 if result.returncode == 0 else 500)
        except Exception as error:
            self.send_page(page(f"{title}\n\n{error}"), 500)
        finally:
            RUN_LOCK.release()

    def log_message(self, format, *args):
        return


def main():
    if not os.path.exists(PYTHON):
        raise SystemExit(f"Missing virtual environment interpreter: {PYTHON}")
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    url = f"http://127.0.0.1:{PORT}/"
    print(f"Gmail Organizer: {url}", flush=True)
    webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
