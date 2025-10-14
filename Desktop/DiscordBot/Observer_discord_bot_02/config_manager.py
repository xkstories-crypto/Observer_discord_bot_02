import os
import json
import io
import discord
from discord.ext import commands
from discord.utils import get
from googleapiclient.discovery import build
from google.oauth2 import service_account
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload

CONFIG_LOCAL_PATH = os.path.join("data", "config_store.json")
GDRIVE_SERVICE_ACCOUNT_JSON = os.getenv("GDRIVE_SERVICE_ACCOUNT_JSON")
GDRIVE_CONFIG_FILE_ID = os.getenv("GDRIVE_CONFIG_FILE_ID")

SCOPES = ['https://www.googleapis.com/auth/drive.file']

class ConfigManager:
    def __init__(self, bot: commands.Bot):
        self.bot = bot

        # Google Drive API 初期化
        credentials = service_account.Credentials.from_service_account_info(
            json.loads(GDRIVE_SERVICE_ACCOUNT_JSON), scopes=SCOPES
        )
        self.service = build('drive', 'v3', credentials=credentials)

        os.makedirs("data", exist_ok=True)
        self.config = self.load_config()

        self.register_commands()
        self.register_drive_show_command()

    # ------------------------
    # Google Drive 上の JSON ロード/保存
    # ------------------------
    def load_config(self):
        try:
            request = self.service.files().get_media(fileId=GDRIVE_CONFIG_FILE_ID)
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()
            fh.seek(0)
            config = json.load(fh)
            if "server_pairs" not in config:
                config["server_pairs"] = []
            return config
        except Exception as e:
            # fallback: ローカルに保存されたファイルがあれば読み込む
            if os.path.exists(CONFIG_LOCAL_PATH):
                with open(CONFIG_LOCAL_PATH, "r", encoding="utf-8") as f:
                    return json.load(f)
            # 無ければデフォルト
            default = {"server_pairs": []}
            self.save_config(default)
            return default

    def save_config(self, data=None):
        if data:
            self.config = data

        # ローカル保存
        with open(CONFIG_LOCAL_PATH, "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)

        # Google Drive にアップロード
        try:
            fh = io.BytesIO()
            fh.write(json.dumps(self.config, indent=2, ensure_ascii=False).encode())
            fh.seek(0)
            media = MediaIoBaseUpload(fh, mimetype='application/json', resumable=True)
            self.service.files().update(fileId=GDRIVE_CONFIG_FILE_ID, media_body=media).execute()
        except Exception as e:
            print(f"[WARN] Google Drive へのアップロード失敗: {e}")

    # ------------------------
    # 管理者チェック・ペア取得
    # ------------------------
    def is_admin(self, guild_id, user_id):
        pair = self.get_pair_by_guild(guild_id)
        return pair and user_id in pair.get("ADMIN_IDS", [])

    def get_pair_by_guild(self, guild_id):
        for pair in self.config.get("server_pairs", []):
            if pair.get("A_ID") == guild_id or pair.get("B_ID") == guild_id:
                return pair
        return None

    # ------------------------
    # コマンド登録（Dropbox 版のロジックそのまま）
    # ------------------------
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
                    "CHANNEL_MAPPING": {"A_TO_B": {}, "B_TO_A": {}},
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

        # ここに set_server / set_channel / show_config のコマンドも同じロジックで登録

    def register_drive_show_command(self):
        bot = self.bot

        @bot.command(name="show")
        async def show_config(ctx: commands.Context):
            if not self.is_admin(ctx.guild.id, ctx.author.id):
                await ctx.send("❌ 管理者ではありません。")
                return

            try:
                config = self.load_config()
                json_text = json.dumps(config, indent=2, ensure_ascii=False)
                if len(json_text) < 1900:
                    await ctx.send(f"✅ Google Drive 上の設定 JSON\n```json\n{json_text}\n```")
                else:
                    with open(CONFIG_LOCAL_PATH, "w", encoding="utf-8") as f:
                        json.dump(config, f, indent=2, ensure_ascii=False)
                    await ctx.send("✅ Google Drive 上の設定 JSON（ファイル添付）", file=discord.File(CONFIG_LOCAL_PATH))
            except Exception as e:
                await ctx.send(f"⚠️ JSON 読み込みに失敗しました: {e}")
