from concurrent.futures import ThreadPoolExecutor
import threading
import time

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


LABELS = [
    "INBOX/NewsLetters/Scholar Google",
    "INBOX/NewsLetters/NewsPapers/Le Monde Diplomatique",
    "INBOX/NewsLetters/Optica.org",
    "INBOX/NewsLetters/Jobs/LinkedIn",
    "INBOX/NewsLetters/AI",
]
SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]


def make_service():
    creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return build("gmail", "v1", credentials=creds)


def ids_for_label(gmail, label_id):
    ids = []
    page = None
    while True:
        result = gmail.users().messages().list(
            userId="me", labelIds=[label_id], pageToken=page, maxResults=500
        ).execute()
        ids.extend(item["id"] for item in result.get("messages", []))
        page = result.get("nextPageToken")
        if not page:
            return ids


thread_state = threading.local()


def size_for_message(message_id):
    if not hasattr(thread_state, "gmail"):
        thread_state.gmail = make_service()
    while True:
        try:
            return thread_state.gmail.users().messages().get(
                userId="me", id=message_id, format="minimal"
            ).execute().get("sizeEstimate", 0)
        except HttpError as error:
            if error.resp.status != 403:
                raise
            time.sleep(10)


gmail = make_service()
available = {item["name"]: item["id"] for item in gmail.users().labels().list(userId="me").execute().get("labels", [])}
by_label = {name: ids_for_label(gmail, available[name]) for name in LABELS if name in available}
all_ids = set().union(*by_label.values())
with ThreadPoolExecutor(max_workers=2) as pool:
    total = sum(pool.map(size_for_message, all_ids))
print(f"Unique messages: {len(all_ids)}")
for name, ids in by_label.items():
    print(f"{name}: {len(ids)}")
print(f"Estimated total: {total} bytes ({total / 1024 / 1024:.1f} MiB, {total / 1000 / 1000:.1f} MB)")
