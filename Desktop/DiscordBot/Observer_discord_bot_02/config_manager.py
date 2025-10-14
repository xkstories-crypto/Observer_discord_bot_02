import os
import json
import asyncio
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
from oauth2client.service_account import ServiceAccountCredentials
from discord.ext import commands

CONFIG_LOCAL_PATH = os.path.join("data", "config_store.json")
ADMIN_CHANNEL_ID = int(os.getenv("ADMIN_CHANNEL_ID", 0))  # デバッグ送信先

async def send_debug(bot, message: str):
    if ADMIN_CHANNEL_ID:
        channel = bot.get_channel(ADMIN_CHANNEL_ID)
        if channel:
            await channel.send(f"[DEBUG] {message}")
        else:
            print(f"[WARN] 管理者チャンネル取得失敗: {ADMIN_CHANNEL_ID}")
    else:
        print(f"[DEBUG] {message}")

class ConfigManager:
    def __init__(self, bot: commands.Bot, drive_file_id: str):
        self.bot = bot
        self.drive_file_id = drive_file_id

        asyncio.create_task(send_debug(self.bot, "ConfigManager 初期化開始"))

        # ----------- サービスアカウント認証情報 -------------
        service_json_env = os.getenv("SERVICE_JSON")
        if not service_json_env:
            raise ValueError("環境変数 SERVICE_JSON が設定されていません。")
        
        try:
            service_json = json.loads(service_json_env)
            asyncio.create_task(send_debug(self.bot, f"サービスアカウント JSON 読み込み成功"))
        except Exception as e:
            raise ValueError(f"SERVICE_JSON の読み込みに失敗: {e}")

        # ----------- Google Drive 認証処理 -------------
        try:
            self.gauth = GoogleAuth()
            scope = ["https://www.googleapis.com/auth/drive"]
            self.gauth.credentials = ServiceAccountCredentials.from_json_keyfile_dict(service_json, scopes=scope)
            self.drive = GoogleDrive(self.gauth)
            asyncio.create_task(send_debug(self.bot, "GoogleAuth 認証成功"))
        except Exception as e:
            asyncio.create_task(send_debug(self.bot, f"GoogleAuth 認証失敗: {e}"))
            raise

        # ----------- 設定ロード -------------
        os.makedirs("data", exist_ok=True)
        self.config = self.load_config()

        # ----------- コマンド登録 -------------
        self.register_commands()
        self.register_sa_check_command()
        self.register_drive_show_command()
        asyncio.create_task(send_debug(self.bot, "ConfigManager 初期化完了"))

    # ---------------------------- 設定ロード ----------------------------
    def load_config(self):
        try:
            asyncio.create_task(send_debug(self.bot, f"Google Drive からファイル取得開始: {self.drive_file_id}"))
            file = self.drive.CreateFile({"id": self.drive_file_id})
            file.GetContentFile(CONFIG_LOCAL_PATH)
            with open(CONFIG_LOCAL_PATH, "r", encoding="utf-8") as f:
                config = json.load(f)
            asyncio.create_task(send_debug(self.bot, "Google Drive から設定を読み込みました"))
            return config
        except Exception as e:
            asyncio.create_task(send_debug(self.bot, f"Google Drive 読み込み失敗: {e}"))
            default = {"server_pairs": []}
            self.save_config(default)
            return default

    # ---------------------------- 設定保存 ----------------------------
    def save_config(self, data=None):
        if data:
            self.config = data
        with open(CONFIG_LOCAL_PATH, "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)
        try:
            file = self.drive.CreateFile({"id": self.drive_file_id})
            file.SetContentFile(CONFIG_LOCAL_PATH)
            file.Upload()
            asyncio.create_task(send_debug(self.bot, "Google Drive に設定をアップロードしました"))
        except Exception as e:
            asyncio.create_task(send_debug(self.bot, f"Google Drive へのアップロード失敗: {e}"))
            print(f"[WARN] Google Drive へのアップロード失敗: {e}")

    # ---------------------------- 管理者チェック ----------------------------
    def is_admin(self, guild_id, user_id):
        pair = self.get_pair_by_guild(guild_id)
        return pair and user_id in pair.get("ADMIN_IDS", [])

    def get_pair_by_guild(self, guild_id):
        for pair in self.config.get("server_pairs", []):
            if pair.get("A_ID") == guild_id or pair.get("B_ID") == guild_id:
                return pair
        return None

    # ---------------------------- 通常コマンド登録 ----------------------------
    def register_commands(self):
        bot = self.bot
        asyncio.create_task(send_debug(bot, "通常コマンド登録開始"))

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

        asyncio.create_task(send_debug(bot, "通常コマンド登録完了"))

    # ---------------------------- SA チェックコマンド ----------------------------
    def register_sa_check_command(self):
        bot = self.bot
        asyncio.create_task(send_debug(bot, "SA チェックコマンド登録開始"))

        @bot.command(name="check_sa")
        async def check_sa(ctx: commands.Context):
            await ctx.send("✅ SA コマンド実行")

        asyncio.create_task(send_debug(bot, "SA チェックコマンド登録完了"))

    # ---------------------------- Google Drive JSON 表示コマンド ----------------------------
    def register_drive_show_command(self):
        bot = self.bot
        asyncio.create_task(send_debug(bot, "Google Drive JSON 表示コマンド登録開始"))

        @bot.command(name="show")
        async def show_config(ctx: commands.Context):
            if not self.is_admin(ctx.guild.id, ctx.author.id):
                await ctx.send("❌ 管理者ではありません。")
                return

            try:
                asyncio.create_task(send_debug(bot, f"Google Drive からファイル取得開始: {self.drive_file_id}"))
                file = self.drive.CreateFile({"id": self.drive_file_id})
                file.GetContentFile(CONFIG_LOCAL_PATH)
                asyncio.create_task(send_debug(bot, f"ファイル取得成功: {CONFIG_LOCAL_PATH}"))

                with open(CONFIG_LOCAL_PATH, "r", encoding="utf-8") as f:
                    config = json.load(f)

                json_text = json.dumps(config, indent=2, ensure_ascii=False)
                if len(json_text) < 1900:
                    await ctx.send(f"✅ Google Drive 上の設定 JSON\n```json\n{json_text}\n```")
                else:
                    await ctx.send(f"✅ Google Drive 上の設定 JSON（先頭のみ表示）\n```json\n{json_text[:1900]}...\n```")
                asyncio.create_task(send_debug(bot, "show コマンド実行完了"))
            except Exception as e:
                asyncio.create_task(send_debug(bot, f"JSON 読み込みに失敗: {e}"))
                await ctx.send(f"⚠️ JSON 読み込みに失敗: {e}")
