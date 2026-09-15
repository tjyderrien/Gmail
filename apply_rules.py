#!/usr/bin/env python3
"""Apply deterministic Gmail labels for known senders."""

import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]
RULES = {
    "scholaralerts-noreply@google.com": "INBOX/NewsLetters/Scholar Google",
    "info-diplo@monde-diplomatique.fr": "INBOX/NewsLetters/NewsPapers/Le Monde Diplomatique",
    "@optica.org": "INBOX/NewsLetters/Optica.org",
    "jobalerts-noreply@linkedin.com": "INBOX/NewsLetters/Jobs/LinkedIn",
    "nexera-app.com": "INBOX/NewsLetters/AI",
    "contact@perspectives.ac": "INBOX/NewsLetters/AI",
}


def service():
    token_path = "token.json"
    creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(token_path, "w", encoding="utf-8") as token:
            token.write(creds.to_json())
    return build("gmail", "v1", credentials=creds)


def all_ids(gmail, query):
    ids = []
    page = None
    while True:
        result = gmail.users().messages().list(
            userId="me", q=query, pageToken=page, maxResults=100
        ).execute()
        ids.extend(item["id"] for item in result.get("messages", []))
        page = result.get("nextPageToken")
        if not page:
            return ids


def main():
    gmail = service()
    labels = gmail.users().labels().list(userId="me").execute().get("labels", [])
    by_name = {item["name"].lower(): item for item in labels}

    label_ids = {}
    for label_name in set(RULES.values()):
        label = by_name.get(label_name.lower())
        if not label:
            label = gmail.users().labels().create(
                userId="me", body={"name": label_name, "labelListVisibility": "labelShow", "messageListVisibility": "show"}
            ).execute()
            print(f"Created label: {label_name}")
        label_ids[label_name] = label["id"]

    for sender, label_name in RULES.items():
        query = f"from:{sender}" if not sender.startswith("@") else f"from:{sender[1:]}"
        ids = all_ids(gmail, query)
        for start in range(0, len(ids), 1000):
            gmail.users().messages().batchModify(
                userId="me",
                body={"ids": ids[start : start + 1000], "addLabelIds": [label_ids[label_name]]},
            ).execute()
        print(f"{sender} -> {label_name}: {len(ids)} message(s)")


if __name__ == "__main__":
    if not os.path.exists("token.json"):
        raise SystemExit("token.json not found; authorize Gmail first")
    main()
