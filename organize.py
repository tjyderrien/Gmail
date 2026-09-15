#!/usr/bin/env python3
"""Use a local Ollama model to apply an existing Gmail label to similar mail."""

import argparse
import json
import os
import re
import sys
import urllib.request
from email.utils import parseaddr

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]


def gmail_service(credentials_path, token_path, open_browser=True):
    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(credentials_path):
                raise SystemExit(
                    f"Missing {credentials_path}. Download an OAuth desktop-app client "
                    "from Google Cloud and place it there."
                )
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
            creds = flow.run_local_server(port=0, open_browser=open_browser)
        with open(token_path, "w", encoding="utf-8") as token:
            token.write(creds.to_json())
    return build("gmail", "v1", credentials=creds)


def all_messages(service, query, limit):
    messages = []
    page = None
    while len(messages) < limit:
        result = service.users().messages().list(
            userId="me", q=query, pageToken=page, maxResults=min(100, limit - len(messages))
        ).execute()
        messages.extend(result.get("messages", []))
        page = result.get("nextPageToken")
        if not page:
            break
    return messages[:limit]


def message_text(service, message_id):
    message = service.users().messages().get(
        userId="me", id=message_id, format="metadata", metadataHeaders=["From", "Subject", "List-Id"]
    ).execute()
    headers = {h["name"].lower(): h["value"] for h in message.get("payload", {}).get("headers", [])}
    sender = parseaddr(headers.get("from", ""))[1] or headers.get("from", "")
    return {
        "id": message_id,
        "from": sender,
        "subject": headers.get("subject", ""),
        "list_id": headers.get("list-id", ""),
        "snippet": message.get("snippet", ""),
    }


def classify(model, examples, message):
    prompt = f"""You classify Gmail messages using examples from a label named NewsLetter.
Return only YES or NO. Return YES only when the message is clearly a newsletter,
mailing-list publication, digest, or recurring promotional publication like the examples.
Do not classify ordinary one-to-one mail, receipts, alerts, or personal conversations as YES.

Examples already in NewsLetter:
{json.dumps(examples, ensure_ascii=False)}

Message to classify:
{json.dumps(message, ensure_ascii=False)}
"""
    body = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0, "num_predict": 2},
    }).encode()
    request = urllib.request.Request(
        os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434") + "/api/generate",
        data=body,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        answer = json.load(response).get("response", "")
    return bool(re.match(r"^\s*YES\b", answer, re.IGNORECASE))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", default="INBOX/NewsLetters", help="Existing Gmail label to extend")
    parser.add_argument("--query", default="in:anywhere", help="Gmail search query for candidates")
    parser.add_argument("--model", default=os.environ.get("OLLAMA_MODEL", "gpt-oss:latest"))
    parser.add_argument("--examples", type=int, default=10)
    parser.add_argument("--limit", type=int, default=200)
    parser.add_argument("--dry-run", action="store_true", help="Classify but do not change Gmail")
    parser.add_argument("--credentials", default="credentials.json")
    parser.add_argument("--token", default="token.json")
    parser.add_argument("--no-browser", action="store_true", help="Print the OAuth URL instead of opening it")
    args = parser.parse_args()

    service = gmail_service(args.credentials, args.token, open_browser=not args.no_browser)
    labels = service.users().labels().list(userId="me").execute().get("labels", [])
    label = next((item for item in labels if item["name"].lower() == args.label.lower()), None)
    if not label:
        raise SystemExit(f"Gmail label not found: {args.label}")

    example_ids = all_messages(service, f'label:"{args.label}"', args.examples)
    if not example_ids:
        raise SystemExit(f'No messages found under label "{args.label}"')
    examples = [message_text(service, item["id"]) for item in example_ids]
    candidates = all_messages(service, f'{args.query} -label:"{args.label}"', args.limit)

    matches = []
    for index, item in enumerate(candidates, 1):
        message = message_text(service, item["id"])
        if classify(args.model, examples, message):
            matches.append(message)
        print(f"[{index}/{len(candidates)}] {message['from']} | {message['subject']}", file=sys.stderr)

    if matches and not args.dry_run:
        service.users().messages().batchModify(
            userId="me", body={"ids": [item["id"] for item in matches], "addLabelIds": [label["id"]]}
        ).execute()
    action = "would label" if args.dry_run else "labeled"
    print(f"{action} {len(matches)} message(s) as {label['name']}.")


if __name__ == "__main__":
    main()
