import sys

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


creds = Credentials.from_authorized_user_file(
    "token.json", ["https://www.googleapis.com/auth/gmail.modify"]
)
gmail = build("gmail", "v1", credentials=creds)
result = gmail.users().messages().list(userId="me", q=sys.argv[1], maxResults=50).execute()
print(f"count shown: {len(result.get('messages', []))}")
for item in result.get("messages", []):
    message = gmail.users().messages().get(
        userId="me", id=item["id"], format="metadata",
        metadataHeaders=["From", "To", "Subject", "Date"],
    ).execute()
    headers = {h["name"]: h["value"] for h in message.get("payload", {}).get("headers", [])}
    print("---")
    print(" | ".join(headers.get(name, "") for name in ("Date", "From", "To", "Subject")))
    print(message.get("snippet", ""))
