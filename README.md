# Local Gmail Organizer

This tool reads Gmail metadata locally, sends classification prompts only to a
local Ollama server, and directly adds the existing `INBOX/NewsLetters` label to
matching messages. It does not use OpenAI or any cloud AI service.

## Setup

1. Create or select a Google Cloud project and enable the Gmail API.
2. Create an OAuth client of type **Desktop app** and download its JSON as
   `credentials.json` into this directory.
3. Install dependencies:

   ```bash
   python3 -m venv .venv
   . .venv/bin/activate
   pip install -r requirements.txt
   ```

4. Ensure Ollama is running and the model is available:

   ```bash
   ollama serve
   ollama list
   ```

## Run

The first run opens Google OAuth in a browser and creates local `token.json`.
The default mode makes direct label edits:

```bash
./.venv/bin/python organize.py
```

Use a dry run first if desired:

```bash
./.venv/bin/python organize.py --dry-run
```

Only messages matching `--query` are considered. Change the label or query as
needed, for example `--label 'INBOX/NewsLetters' --query 'in:inbox newer_than:1y'`.

The tool only adds a label; it does not delete, archive, send, or alter message
content. Keep `credentials.json` and `token.json` private.

To move already labeled messages out of the Inbox while keeping their labels,
run:

```bash
./.venv/bin/python move_labeled.py
```

To make the sender rules permanent in Gmail, create native Gmail filters:

```bash
./.venv/bin/python create_filters.py
```

## Browser control panel

Run the local browser app:

```bash
./.venv/bin/python webapp.py
```

It binds only to `127.0.0.1:8765` and opens the control panel in the browser.
The available actions are allowlisted; the panel does not accept shell commands.
