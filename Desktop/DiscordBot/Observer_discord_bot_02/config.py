# config.py
import os

# Render の環境変数から直接取得

TOKEN = os.getenv("DISCORD_TOKEN")
if TOKEN is None:
    raise ValueError("DISCORD_TOKEN が取得できません。Render の環境変数を確認してください。")
print("TOKEN length:", len(TOKEN))


SERVER_A_ID = 123456789012345678  # AサーバーID
SERVER_B_ID = 987654321098765432  # BサーバーID

CHANNEL_MAPPING = {
    "a1": "b1",
    "a2": "b2",
    "a3": "b3",
    "a4": "b4",
    "a_other": "b_other"
}

VC_LOG_CHANNEL = "vc-log"
AUDIT_LOG_CHANNEL = "audit-log"
