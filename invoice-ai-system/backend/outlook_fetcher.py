import os
from imap_tools import MailBox, AND
from dotenv import load_dotenv

load_dotenv()

class OutlookFetcher:
    def __init__(self):
        self.server = os.getenv("OUTLOOK_SERVER", "outlook.office365.com")
        self.email = os.getenv("OUTLOOK_EMAIL")
        self.password = os.getenv("OUTLOOK_PASSWORD")
        self.folder = os.getenv("OUTLOOK_FOLDER", "INBOX")
        self.download_path = "data/uploads"
        
        os.makedirs(self.download_path, exist_ok=True)

    def fetch_attachments(self):
        if not all([self.email, self.password]):
            print("Outlook credentials missing in .env")
            return []

        saved_files = []
        try:
            with MailBox(self.server).login(self.email, self.password, self.folder) as mailbox:
                # Search for unread emails with attachments (basic filter)
                for msg in mailbox.fetch(AND(seen=False)):
                    for att in msg.attachments:
                        # Only download PDF/Images
                        if att.filename.lower().endswith(('.pdf', '.jpg', '.jpeg', '.png')):
                            file_path = os.path.join(self.download_path, att.filename)
                            with open(file_path, 'wb') as f:
                                f.write(att.payload)
                            saved_files.append({
                                "filename": att.filename,
                                "path": file_path,
                                "sender": msg.from_,
                                "subject": msg.subject
                            })
                    # Mark as seen post-download
                    # mailbox.flag(msg.uid, [imap_tools.MailMessageFlags.SEEN], True)
            return saved_files
        except Exception as e:
            print(f"Error fetching email: {e}")
            return []

if __name__ == "__main__":
    # Test block
    fetcher = OutlookFetcher()
    # files = fetcher.fetch_attachments()
    # print(f"Downloaded {len(files)} files.")
