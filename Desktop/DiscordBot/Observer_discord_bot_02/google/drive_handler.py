# google/drive_handler.py
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
from oauth2client.service_account import ServiceAccountCredentials

class DriveHandler:
    def __init__(self, service_json: dict, file_id: str):
        self.file_id = file_id
        self.gauth = GoogleAuth()
        scope = ["https://www.googleapis.com/auth/drive"]
        self.gauth.credentials = ServiceAccountCredentials.from_json_keyfile_dict(service_json, scopes=scope)
        self.drive = GoogleDrive(self.gauth)

    def download_config(self, local_path: str):
        file = self.drive.CreateFile({"id": self.file_id})
        file.GetContentFile(local_path)

    def upload_config(self, local_path: str):
        file = self.drive.CreateFile({"id": self.file_id})
        file.SetContentFile(local_path)
        file.Upload()
