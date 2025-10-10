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
        service_json_env = os.getenv("SERVICE_ACCOUNT_JSON")
        if not service_json_env:
            raise ValueError("SERVICE_ACCOUNT_JSON が環境変数に設定されていません。")
        
        # Render 用: 改行文字を復元
        service_json_env = os.getenv("SERVICE_ACCOUNT_JSON")
        print(repr(service_json_env)[:200])

        # JSON を dict に変換
        sa_info = json.loads(service_json_env)

        # ----------- Google Drive 認証処理 -------------
        self.gauth = GoogleAuth()
        scope = ["https://www.googleapis.com/auth/drive"]
        self.gauth.credentials = ServiceAccountCredentials.from_json_keyfile_dict(sa_info, scopes=scope)
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
