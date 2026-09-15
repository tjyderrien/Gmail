#!/usr/bin/env python3
"""Local browser control panel for the Gmail organizer."""

import html
import json
import os
import re
import subprocess
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs


ROOT = os.path.dirname(os.path.abspath(__file__))
PYTHON = os.path.join(ROOT, ".venv", "bin", "python")
PORT = int(os.environ.get("GMAIL_ORGANIZER_PORT", "8765"))
RUN_LOCK = threading.Lock()
JOB = {
    "running": False,
    "title": "",
    "processed": 0,
    "total": 0,
    "output": "",
    "returncode": None,
}
PROGRESS = re.compile(r"\[(\d+)/(\d+)\]")

ACTIONS = {
    "rules": ("Apply sender rules", ["apply_rules.py"], 600),
    "archive": ("Archive labeled mail", ["move_labeled.py"], 600),
    "filters": ("Create or update Gmail filters", ["create_filters.py"], 600),
        1800,
    ),
        1800,
    ),
        1800,
    ),
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
  progress {{ height: 18px; width: 100%; }}
  
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
<section>
  <h2 id="title">Ready</h2>
  <progress id="bar" value="0" max="1"></progress>
  <div id="progress-text">No action running.</div>
  <pre id="output">{safe_message}</pre>
</section>
<script>
async function refresh() {{
  const response = await fetch('/status', {{cache: 'no-store'}});
  const job = await response.json();
  document.getElementById('title').textContent = job.running ? job.title : (job.returncode === 0 ? 'Finished' : 'Ready');
  const bar = document.getElementById('bar');
  bar.max = job.total || 1;
  bar.value = job.processed || 0;
  document.getElementById('progress-text').textContent = job.running
    ? (job.total ? `${{job.processed}}/${{job.total}} processed` : 'Running...')
    : (job.returncode === null ? 'No action running.' : `Exit code: ${{job.returncode}}`);
  document.getElementById('output').textContent = job.output || '';
  if (job.running) setTimeout(refresh, 1000);
}}
refresh();
</script>
</main></body></html>"""


def run_action(action):
    title, command, timeout = ACTIONS[action]
    started = time.monotonic()
    process = subprocess.Popen(
        [PYTHON, *command], cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, bufsize=1,
    )
    lines = []
    for line in process.stdout:
        lines.append(line)
        match = PROGRESS.search(line)
        with RUN_LOCK:
            JOB["output"] = "".join(lines)[-20000:]
            if match:
                JOB["processed"] = int(match.group(1))
                JOB["total"] = int(match.group(2))
        if time.monotonic() - started > timeout:
            process.kill()
            lines.append(f"\nTimed out after {timeout}s\n")
            break
    returncode = process.wait()
    with RUN_LOCK:
        JOB["running"] = False
        JOB["output"] = "".join(lines)[-20000:]
        JOB["returncode"] = returncode


def start_action(action):
    with RUN_LOCK:
        if JOB["running"]:
            return False
        JOB.update({"running": True, "title": ACTIONS[action][0], "processed": 0,
                    "total": 0, "output": "", "returncode": None})
    threading.Thread(target=run_action, args=(action,), daemon=True).start()
    return True


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
        if self.path == "/download":
            path = next((os.path.join(ROOT, name) for name in GRAPH_FILES if os.path.exists(os.path.join(ROOT, name))), None)
            if not path:
                return
            with open(path, "rb") as graph_file:
                payload = graph_file.read()
            self.send_response(200)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        if self.path == "/status":
            with RUN_LOCK:
                payload = json.dumps(JOB).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(payload)
            return
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
        if not start_action(action):
            self.send_page(page("Another action is already running."), 409)
            return
        self.send_page(page(f"Started: {ACTIONS[action][0]}"))

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
