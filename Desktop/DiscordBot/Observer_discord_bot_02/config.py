# config.py
import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TOKEN")

SERVER_A_ID = 123456789012345678  # AサーバーID
SERVER_B_ID = 987654321098765432  # BサーバーID

CHANNEL_MAPPING = {
    "a1": "b1",
    "a2": "b2",
    "a3": "b3",
    "a4": "b4",
    "a_other": "b_other"
}

VC_LOG_CHANNEL = "vc-log"       # VC入退出ログチャンネル名
AUDIT_LOG_CHANNEL = "audit-log" # 監査ログチャンネル名
