#!/usr/bin/env python3
"""Archive messages carrying the organizer's destination labels."""

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]
LABELS = [
    "INBOX/NewsLetters/Scholar Google",
    "INBOX/NewsLetters/NewsPapers/Le Monde Diplomatique",
    "INBOX/NewsLetters/Optica.org",
    "INBOX/NewsLetters/Jobs/LinkedIn",
    "INBOX/NewsLetters/AI",
]


def get_service():
    creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return build("gmail", "v1", credentials=creds)


def message_ids(gmail, query):
    found = []
    page = None
    while True:
        result = gmail.users().messages().list(
            userId="me", q=query, pageToken=page, maxResults=100
        ).execute()
        found.extend(item["id"] for item in result.get("messages", []))
        page = result.get("nextPageToken")
        if not page:
            return found


def main():
    gmail = get_service()
    labels = gmail.users().labels().list(userId="me").execute().get("labels", [])
    names = {item["name"].lower(): item["name"] for item in labels}
    total = 0
    for label in LABELS:
        actual = names.get(label.lower())
        if not actual:
            print(f"Missing label: {label}")
            continue
        ids = message_ids(gmail, f'label:"{actual}" in:inbox')
        for start in range(0, len(ids), 1000):
            gmail.users().messages().batchModify(
                userId="me",
                body={"ids": ids[start : start + 1000], "removeLabelIds": ["INBOX"]},
            ).execute()
        total += len(ids)
        print(f"Archived from Inbox: {len(ids)} | {actual}")
    print(f"Archived total: {total}")


if __name__ == "__main__":
    main()
