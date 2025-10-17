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

        # サービスアカウント構築
        key_lines = [os.getenv(f"SERVICE_KEY_LINE_{i:02}") for i in range(1,100) if os.getenv(f"SERVICE_KEY_LINE_{i:02}")]
        if not key_lines:
            raise ValueError("SERVICE_KEY_LINE_01 以降の環境変数が設定されていません。")
        private_key = "\n".join(key_lines)

        service_json = {
            "type": "service_account",
            "project_id": os.getenv("PROJECT_ID", "discord-bot-project-474420"),
            "private_key_id": os.getenv("PRIVATE_KEY_ID"),
            "private_key": private_key,
            "client_email": os.getenv("CLIENT_EMAIL"),
            "client_id": os.getenv("CLIENT_ID"),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": os.getenv("CLIENT_X509_CERT_URL"),
            "universe_domain": "googleapis.com"
        }

        self.gauth = GoogleAuth()
        scope = ["https://www.googleapis.com/auth/drive"]
        self.gauth.credentials = ServiceAccountCredentials.from_json_keyfile_dict(service_json, scopes=scope)
        self.drive = GoogleDrive(self.gauth)
        asyncio.create_task(send_debug(self.bot, "GoogleAuth 認証成功"))

        os.makedirs("data", exist_ok=True)
        self.config = self.load_config()

        # コマンド登録
        self.register_commands()
        self.register_set_server_command()
        self.register_sa_check_command()
        self.register_drive_show_command()

    # ------------------ 設定ロード/保存 ------------------
    def load_config(self):
        try:
            file = self.drive.CreateFile({"id": self.drive_file_id})
            file.GetContentFile(CONFIG_LOCAL_PATH)
            with open(CONFIG_LOCAL_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            default = {"server_pairs": []}
            self.save_config(default)
            return default

    def save_config(self, data=None):
        if data:
            self.config = data
        with open(CONFIG_LOCAL_PATH, "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)
        try:
            file = self.drive.CreateFile({"id": self.drive_file_id})
            file.SetContentFile(CONFIG_LOCAL_PATH)
            file.Upload()
        except:
            pass

    # ------------------ ヘルパー ------------------
    def get_pair_by_guild(self, guild_id):
        for pair in self.config.get("server_pairs", []):
            if pair.get("A_ID") == guild_id or pair.get("B_ID") == guild_id:
                return pair
        return None

    def is_admin(self, guild_id, user_id):
        pair = self.get_pair_by_guild(guild_id)
        return pair and user_id in pair.get("ADMIN_IDS", [])

    # ------------------ 通常コマンド ------------------
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
                    "CHANNEL_MAPPING": {},
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
                await ctx.send("⚠️ すでに管理者です。")
                return
            pair["ADMIN_IDS"].append(author_id)
            self.save_config()
            await ctx.send(f"✅ {ctx.author.name} を管理者登録しました。")

    # ------------------ !set_server ------------------
    def register_set_server_command(self):
        bot = self.bot
        @bot.command(name="set_server")
        async def set_server(ctx: commands.Context, server_a_id: int):
            if not self.is_admin(ctx.guild.id, ctx.author.id):
                await ctx.send("❌ 管理者のみ使用可能です。")
                return

            pair = self.get_pair_by_guild(ctx.guild.id)
            if not pair:
                pair = {"A_ID": server_a_id, "B_ID": ctx.guild.id, "CHANNEL_MAPPING": {}, "ADMIN_IDS": [ctx.author.id]}
                self.config["server_pairs"].append(pair)
            else:
                pair["A_ID"] = server_a_id
                pair["B_ID"] = ctx.guild.id

            self.save_config()

            guild_a = bot.get_guild(server_a_id)
            guild_b = bot.get_guild(ctx.guild.id)
            if not guild_a or not guild_b:
                await ctx.send("⚠️ Botが両方のサーバーに参加している必要があります。")
                return

            # チャンネルコピー
            for channel in guild_a.channels:
                if isinstance(channel, discord.CategoryChannel):
                    cat = await guild_b.create_category(name=channel.name)
                    pair["CHANNEL_MAPPING"][str(channel.id)] = cat.id
                elif isinstance(channel, discord.TextChannel):
                    category_id = pair["CHANNEL_MAPPING"].get(str(channel.category_id))
                    cat = guild_b.get_channel(category_id) if category_id else None
                    new_ch = await guild_b.create_text_channel(name=channel.name, category=cat)
                    pair["CHANNEL_MAPPING"][str(channel.id)] = new_ch.id
                elif isinstance(channel, discord.VoiceChannel):
                    category_id = pair["CHANNEL_MAPPING"].get(str(channel.category_id))
                    cat = guild_b.get_channel(category_id) if category_id else None
                    new_ch = await guild_b.create_voice_channel(name=channel.name, category=cat)
                    pair["CHANNEL_MAPPING"][str(channel.id)] = new_ch.id

            self.save_config()
            await ctx.send("✅ Aサーバーのチャンネル構造をBサーバーにコピーしました。")

    # ------------------ SA / JSON 表示 ------------------
    def register_sa_check_command(self):
        bot = self.bot
        @bot.command(name="check_sa")
        async def check_sa(ctx: commands.Context):
            await ctx.send("✅ SA チェック OK")

    def register_drive_show_command(self):
        bot = self.bot
        @bot.command(name="show")
        async def show_config(ctx: commands.Context):
            if not self.is_admin(ctx.guild.id, ctx.author.id):
                await ctx.send("❌ 管理者ではありません。")
                return
            await ctx.send(f"✅ Config JSON\n```json\n{json.dumps(self.config, indent=2, ensure_ascii=False)}\n```")
