import base64
import html
import re
import sys

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


def decode(data):
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4)).decode("utf-8", "ignore")


def text_from_part(part):
    body = part.get("body", {})
    text = decode(body["data"]) if body.get("data") else ""
    if part.get("mimeType") == "text/html":
        text = re.sub(r"<[^>]+>", " ", text)
    for child in part.get("parts", []):
        text += " " + text_from_part(child)
    return html.unescape(re.sub(r"\s+", " ", text))


creds = Credentials.from_authorized_user_file("token.json", ["https://www.googleapis.com/auth/gmail.modify"])
gmail = build("gmail", "v1", credentials=creds)
result = gmail.users().messages().list(userId="me", q=sys.argv[1], maxResults=50).execute()
for item in result.get("messages", []):
    message = gmail.users().messages().get(userId="me", id=item["id"], format="full").execute()
    print("---")
    print(text_from_part(message.get("payload", {}))[:12000])
