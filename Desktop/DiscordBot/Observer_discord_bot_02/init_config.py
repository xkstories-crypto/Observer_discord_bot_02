# init_config.py
import os
import json

# 保存先（ConfigManager と同じ）
CONFIG_FILE = os.path.join("data", "config_store.json")

# data フォルダがなければ作成
os.makedirs("data", exist_ok=True)

# ------------------------
# 古いファイルをバックアップ（任意）
# ------------------------
if os.path.exists(CONFIG_FILE):
    backup_file = CONFIG_FILE + ".bak"
    os.rename(CONFIG_FILE, backup_file)
    print(f"[BACKUP] 既存ファイルをバックアップ: {backup_file}")

# ------------------------
# 空のデフォルト構造を作成
# ------------------------
default_config = {
    "server_pairs": [
        {
            "A_ID": None,
            "B_ID": None,
            "CHANNEL_MAPPING": {"A_TO_B": {}},
            "ADMIN_IDS": [],
            "DEBUG_CHANNEL": None,
            "VC_LOG_CHANNEL": None,
            "AUDIT_LOG_CHANNEL": None,
            "OTHER_CHANNEL": None,
            "READ_USERS": []
        }
    ]
}

# ------------------------
# 保存
# ------------------------
with open(CONFIG_FILE, "w", encoding="utf-8") as f:
    json.dump(default_config, f, indent=2, ensure_ascii=False)

print(f"[CREATE] 空のデフォルト構造を {CONFIG_FILE} に保存しました")
