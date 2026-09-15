import sys

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


gmail = build(
    "gmail", "v1",
    credentials=Credentials.from_authorized_user_file(
        "token.json", ["https://www.googleapis.com/auth/gmail.modify"]
    ),
)
for term in sys.argv[1:]:
    query = f'label:"INBOX/NewsLetters/Scholar Google" "{term}"'
    count = 0
    page = None
    while True:
        result = gmail.users().messages().list(userId="me", q=query, pageToken=page, maxResults=500).execute()
        count += len(result.get("messages", []))
        page = result.get("nextPageToken")
        if not page:
            break
    print(f"{term}: {count}")
