# config_manager.py
import os
import json
import asyncio
from discord.ext import commands
import discord
from google_api.sa_utils import build_service_account_json
from google_api.drive_handler import DriveHandler

CONFIG_LOCAL_PATH = os.path.join("data", "config_store.json")
ADMIN_CHANNEL_ID = int(os.getenv("ADMIN_CHANNEL_ID", 0))


class ConfigManager:
    """Bot設定を管理し、Google Driveと同期するクラス"""

    def __init__(self, bot: commands.Bot, drive_file_id: str):
        self.bot = bot
        self.drive_file_id = drive_file_id

        asyncio.create_task(self.send_debug("ConfigManager 初期化開始"))

        # --- Google Drive初期化 ---
        service_json = build_service_account_json()
        self.drive_handler = DriveHandler(service_json, self.drive_file_id)

        os.makedirs("data", exist_ok=True)
        self.config = self.load_config()

        # --- コマンド登録 ---
        self.register_commands()
        self.register_sa_check_command(service_json)
        self.register_drive_show_command()
        self.register_debug_all_full_command()

        asyncio.create_task(self.send_debug("ConfigManager 初期化完了"))

    # ------------------------ デバッグ送信 ------------------------
    async def send_debug(self, message: str):
        if ADMIN_CHANNEL_ID:
            channel = self.bot.get_channel(ADMIN_CHANNEL_ID)
            if channel:
                await channel.send(f"[DEBUG] {message}")
            else:
                print(f"[WARN] 管理者チャンネル取得失敗: {ADMIN_CHANNEL_ID}")
        else:
            print(f"[DEBUG] {message}")

    # ------------------------ 設定の読み書き ------------------------
    def load_config(self):
        try:
            self.drive_handler.download_config(CONFIG_LOCAL_PATH)
            with open(CONFIG_LOCAL_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            default = {"server_pairs": []}
            self.save_config(default)
            return default

    def save_config(self, data=None):
        if data is not None:
            self.config = data
        with open(CONFIG_LOCAL_PATH, "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)
        try:
            self.drive_handler.upload_config(CONFIG_LOCAL_PATH)
        except Exception as e:
            print(f"[WARN] Google Drive アップロード失敗: {e}")

    # ------------------------ データ取得ヘルパ ------------------------
    def get_pair_by_guild(self, guild_id: int):
        for pair in self.config.get("server_pairs", []):
            if pair.get("A_ID") == guild_id or pair.get("B_ID") == guild_id:
                return pair
        return None

    def get_pair_by_a(self, a_id: int):
        for pair in self.config.get("server_pairs", []):
            if pair.get("A_ID") == a_id:
                return pair
        return None

    # ------------------------ Discord コマンド登録 ------------------------
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
                await ctx.send("⚠️ すでに管理者として登録されています。")
                return

            pair["ADMIN_IDS"].append(author_id)
            self.save_config()
            await ctx.send(f"✅ {ctx.author.name} を管理者登録しました。")

        @bot.command(name="set_server")
        async def set_server(ctx: commands.Context, server_a_id: int):
            pair = self.get_pair_by_guild(ctx.guild.id)
            if not pair:
                await ctx.send("⚠️ このサーバーはまだペア登録されていません。まず adomin を使ってください。")
                return
            if ctx.author.id not in pair.get("ADMIN_IDS", []):
                await ctx.send("⚠️ 管理者のみ使用可能です。")
                return

            pair["A_ID"] = server_a_id
            self.save_config()
            await ctx.send(f"✅ SERVER_A_ID を {server_a_id} に設定しました。")

            guild_a = self.bot.get_guild(server_a_id)
            guild_b = self.bot.get_guild(pair["B_ID"])
            if not guild_a or not guild_b:
                await ctx.send("⚠️ Bot が両方のサーバーに参加しているか確認してください。")
                return

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

    # ---------------------------- SA チェックコマンド ----------------------------
    def register_sa_check_command(self, service_json: dict):
        asyncio.create_task(self.send_debug("SA チェックコマンド登録開始"))

        @self.bot.command(name="check_sa")
        async def check_sa(ctx: commands.Context):
            # 管理者チェックを削除
            await ctx.send(f"✅ SERVICE_ACCOUNT_JSON 内容\n```json\n{json.dumps(service_json, indent=2)}\n```")

        asyncio.create_task(self.send_debug("SA チェックコマンド登録完了"))

    # ---------------------------- Google Drive JSON 表示コマンド ----------------------------
    def register_drive_show_command(self):
        asyncio.create_task(self.send_debug("Google Drive JSON 表示コマンド登録開始"))

        @self.bot.command(name="show")
        async def show_config(ctx: commands.Context):
            # 管理者チェックを削除
            try:
                asyncio.create_task(self.send_debug(f"Google Drive からファイル取得開始: {self.drive_file_id}"))
                self.drive_handler.download_config(CONFIG_LOCAL_PATH)
                asyncio.create_task(self.send_debug(f"ファイル取得成功: {CONFIG_LOCAL_PATH}"))

                with open(CONFIG_LOCAL_PATH, "r", encoding="utf-8") as f:
                    config = json.load(f)

                json_text = json.dumps(config, indent=2, ensure_ascii=False)
                if len(json_text) < 1900:
                    await ctx.send(f"✅ Google Drive 上の設定 JSON\n```json\n{json_text}\n```")
                else:
                    await ctx.send(f"✅ Google Drive 上の設定 JSON（先頭のみ表示）\n```json\n{json_text[:1900]}...\n```")

                asyncio.create_task(self.send_debug("show コマンド実行完了"))
            except Exception as e:
                asyncio.create_task(self.send_debug(f"JSON 読み込みに失敗: {e}"))
                await ctx.send(f"⚠️ JSON 読み込みに失敗しました: {e}")

    # ---------------------------- debug_all_full コマンド ----------------------------
    def register_debug_all_full_command(self):
        asyncio.create_task(self.send_debug("debug_all_full コマンド登録開始"))

        @self.bot.command(name="debug_all_full")
        async def debug_all_full(ctx: commands.Context):
            # 管理者チェックを削除
            local_text = json.dumps(self.config, indent=2, ensure_ascii=False)

            # Google Drive 上の config
            try:
                self.drive_handler.download_config("tmp_config.json")
                with open("tmp_config.json", "r", encoding="utf-8") as f:
                    drive_config = json.load(f)
                drive_text = json.dumps(drive_config, indent=2, ensure_ascii=False)
            except Exception as e:
                drive_text = f"⚠️ Google Drive 読み込み失敗: {e}"

            CHUNK_SIZE = 1800

            await ctx.send("✅ **ローカル設定**")
            for i in range(0, len(local_text), CHUNK_SIZE):
                await ctx.send(f"```json\n{local_text[i:i+CHUNK_SIZE]}\n```")

            await ctx.send("✅ **Google Drive 設定**")
            for i in range(0, len(drive_text), CHUNK_SIZE):
                await ctx.send(f"```json\n{drive_text[i:i+CHUNK_SIZE]}\n```")

        asyncio.create_task(self.send_debug("debug_all_full コマンド登録完了"))
