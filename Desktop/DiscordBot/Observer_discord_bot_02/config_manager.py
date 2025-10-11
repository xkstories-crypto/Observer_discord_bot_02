import os
import json
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
from oauth2client.service_account import ServiceAccountCredentials
from discord.ext import commands

CONFIG_LOCAL_PATH = os.path.join("data", "config_store.json")

class ConfigManager:
    def __init__(self, bot: commands.Bot, drive_file_id: str):
        self.bot = bot
        self.drive_file_id = drive_file_id

        # ----------- サービスアカウント認証情報 -------------
        # 改行ごとに分割された環境変数から鍵を復元
        key_lines = []
        i = 1
        while True:
            env_name = f"SERVICE_ACCOUNT_KEY_{i}"
            line = os.getenv(env_name)
            if line is None:
                break
            key_lines.append(line)
            i += 1

        if not key_lines:
            raise ValueError("SERVICE_ACCOUNT_KEY_1 以降の環境変数が設定されていません。")

        private_key = "\n".join(key_lines)

        # ここで他の情報と結合
        service_json = {
            "type": "service_account",
            "project_id": "discord-bot-project-474420",
            "private_key_id": "e719591d1b99197d5eb0cede954efcb1caf67e7a",
            "private_key": private_key,
            "client_email": "discord-bot-drive@discord-bot-project-474420.iam.gserviceaccount.com",
            "client_id": "106826889279899095896",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/discord-bot-drive@discord-bot-project-474420.iam.gserviceaccount.com",
            "universe_domain": "googleapis.com"
        }

        # ----------- Google Drive 認証処理 -------------
        self.gauth = GoogleAuth()
        scope = ["https://www.googleapis.com/auth/drive"]
        self.gauth.credentials = ServiceAccountCredentials.from_json_keyfile_dict(service_json, scopes=scope)
        self.drive = GoogleDrive(self.gauth)

        # ----------- 設定ロード -------------
        os.makedirs("data", exist_ok=True)
        self.config = self.load_config()
        self.register_commands()

    # ---------------------------- 設定ロード ----------------------------
    def load_config(self):
        """Google Driveから設定を読み込む"""
        try:
            file = self.drive.CreateFile({"id": self.drive_file_id})
            file.GetContentFile(CONFIG_LOCAL_PATH)
            with open(CONFIG_LOCAL_PATH, "r", encoding="utf-8") as f:
                config = json.load(f)
            print("[LOAD] Google Drive から設定を読み込みました")
            return config
        except Exception as e:
            print(f"[WARN] Google Drive 読み込み失敗: {e}")
            default = {"server_pairs": []}
            self.save_config(default)
            return default

    # ---------------------------- 設定保存 ----------------------------
    def save_config(self, data=None):
        """Google Driveに設定を保存"""
        if data:
            self.config = data
        with open(CONFIG_LOCAL_PATH, "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)
        try:
            file = self.drive.CreateFile({"id": self.drive_file_id})
            file.SetContentFile(CONFIG_LOCAL_PATH)
            file.Upload()
            print("[SAVE] Google Drive に設定をアップロードしました")
        except Exception as e:
            print(f"[ERROR] Google Drive へのアップロード失敗: {e}")

    # ---------------------------- 管理者チェック ----------------------------
    def is_admin(self, guild_id, user_id):
        pair = self.get_pair_by_guild(guild_id)
        return pair and user_id in pair.get("ADMIN_IDS", [])

    def get_pair_by_guild(self, guild_id):
        for pair in self.config["server_pairs"]:
            if pair.get("A_ID") == guild_id or pair.get("B_ID") == guild_id:
                return pair
        return None

    # ---------------------------- コマンド登録 ----------------------------
    def register_commands(self):
        bot = self.bot

        @bot.command(name="adomin")
        async def adomin(ctx: commands.Context):
            guild_id = ctx.guild.id
            author_id = ctx.author.id

            pair = self.get_pair_by_guild(guild_id)
            if not pair:
                pair = {
                    "A_ID": None,
                    "B_ID": guild_id,
                    "CHANNEL_MAPPING": {"A_TO_B": {}},
                    "ADMIN_IDS": [author_id],
                    "DEBUG_CHANNEL": ctx.channel.id,
                    "VC_LOG_CHANNEL": None,
                    "AUDIT_LOG_CHANNEL": None,
                    "OTHER_CHANNEL": None,
                    "READ_USERS": []
                }
                self.config["server_pairs"].append(pair)
                self.save_config()
                await ctx.send(f"✅ {ctx.author.name} を管理者登録しました。")
                return

            if author_id in pair.get("ADMIN_IDS", []):
                await ctx.send("⚠️ すでに管理者として登録されています。")
                return

            pair["ADMIN_IDS"].append(author_id)
            self.save_config()
            await ctx.send(f"✅ {ctx.author.name} を管理者登録しました。")

        @bot.command(name="set_server")
        async def set_server(ctx: commands.Context, target_guild_id: int):
            guild_id = ctx.guild.id
            pair = self.get_pair_by_guild(guild_id)

            if not pair:
                await ctx.send("⚠️ このサーバーはまだ登録されていません。まず `!adomin` を実行してください。")
                return

            if not self.is_admin(guild_id, ctx.author.id):
                await ctx.send("❌ 管理者権限がありません。")
                return

            if guild_id == pair.get("B_ID"):
                pair["A_ID"] = target_guild_id
                self.save_config()
                await ctx.send(f"✅ 対応サーバーを `{target_guild_id}` に設定しました。")
            else:
                await ctx.send("⚠️ このサーバーからは対応サーバーの設定を行えません。")
