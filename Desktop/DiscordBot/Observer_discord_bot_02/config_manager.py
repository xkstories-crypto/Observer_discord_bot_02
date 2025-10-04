import json
import os

CONFIG_FILE = "config_data.json"

class ConfigManager:
    def __init__(self):
        self.load_config()

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                self.config = json.load(f)
        else:
            self.config = {"servers": {}}

    def save_config(self):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)

    def get_server_config(self, guild_id: int):
        """サーバーIDで設定を取得（Aサーバーのみ登録される想定）"""
        return self.config["servers"].get(str(guild_id))

    def set_server_pair(self, a_id: int, b_id: int):
        """AサーバーにBを紐付け"""
        sid = str(a_id)
        if sid not in self.config["servers"]:
            self.config["servers"][sid] = {"CHANNEL_MAPPING": {}, "ADMIN_IDS": []}
        self.config["servers"][sid]["DEST_SERVER_ID"] = b_id
        self.save_config()

    def set_channel_mapping(self, a_id: int, mapping: dict):
        sid = str(a_id)
        if sid not in self.config["servers"]:
            self.config["servers"][sid] = {"CHANNEL_MAPPING": {}, "ADMIN_IDS": []}
        self.config["servers"][sid]["CHANNEL_MAPPING"] = mapping
        self.save_config()

    def is_admin(self, guild_id: int, user_id: int):
        server = self.get_server_config(guild_id)
        if not server:
            return False
        return user_id in server.get("ADMIN_IDS", [])
