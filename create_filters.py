#!/usr/bin/env python3
"""Create permanent Gmail filters for the organizer rules."""

import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.settings.basic",
]
RULES = {
    "from:scholaralerts-noreply@google.com": "INBOX/NewsLetters/Scholar Google",
    "from:info-diplo@monde-diplomatique.fr": "INBOX/NewsLetters/NewsPapers/Le Monde Diplomatique",
    "from:optica.org": "INBOX/NewsLetters/Optica.org",
    "from:jobalerts-noreply@linkedin.com": "INBOX/NewsLetters/Jobs/LinkedIn",
    "from:nexera-app.com": "INBOX/NewsLetters/AI",
    "from:contact@perspectives.ac": "INBOX/NewsLetters/AI",
    "from:monthlyreview.org": "INBOX/NewsLetters/NewsPapers/Monthly Reviews",
    "from:news@crosshilltraining.com": "INBOX/NewsLetters/Finance/Tom Crosshill",
    "from:alexis@aiweekly.co": "INBOX/NewsLetters/AI/AI Weekly",
    "from:mcafee@email.mcafee.com": "INBOX/NewsLetters/Security/McAfee",
    "from:hello@duolingo.com": "INBOX/NewsLetters/Languages/Duolingo",
}


def service():
    creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds.valid and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    if os.environ.get("GMAIL_REAUTH") == "1" or not creds.valid or not creds.scopes or "https://www.googleapis.com/auth/gmail.settings.basic" not in creds.scopes:
        flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
        creds = flow.run_local_server(port=0)
        with open("token.json", "w", encoding="utf-8") as token:
            token.write(creds.to_json())
    return build("gmail", "v1", credentials=creds)


gmail = service()
labels = gmail.users().labels().list(userId="me").execute().get("labels", [])
label_ids = {item["name"].lower(): item["id"] for item in labels}
filters = gmail.users().settings().filters().list(userId="me").execute().get("filter", [])
existing = {
    (item.get("criteria", {}).get("query"), tuple(sorted(item.get("action", {}).get("addLabelIds", []))))
    for item in filters
}

for query, label_name in RULES.items():
    label_id = label_ids.get(label_name.lower())
    if not label_id:
        raise SystemExit(f"Missing label: {label_name}")
    key = (query, (label_id,))
    if key in existing:
        print(f"Already exists: {query} -> {label_name}")
        continue
    gmail.users().settings().filters().create(
        userId="me",
        body={
            "criteria": {"query": query},
            "action": {"addLabelIds": [label_id], "removeLabelIds": ["INBOX"]},
        },
    ).execute()
    print(f"Created: {query} -> {label_name}, archived")
