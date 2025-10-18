# google/sa_utils.py
import os

def build_service_account_json():
    key_lines = []
    for i in range(1, 100):
        env_name = f"SERVICE_KEY_LINE_{i:02}"
        val = os.getenv(env_name)
        if not val:
            break
        key_lines.append(val)

    if not key_lines:
        raise ValueError("SERVICE_KEY_LINE_01 以降の環境変数が設定されていません。")

    private_key = "\n".join(key_lines)

    return {
        "type": "service_account",
        "project_id": "discord-bot-project-474420",
        "private_key_id": "a087f21ff4c7c86974680eb6605168d176d51e23",
        "private_key": private_key,
        "client_email": "observer-discord-bot-02@discord-bot-project-474420.iam.gserviceaccount.com",
        "client_id": "105596180367786843413",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/observer-discord-bot-02@discord-bot-project-474420.iam.gserviceaccount.com",
        "universe_domain": "googleapis.com"
    }
