# main.py
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import discord
from discord.ext import commands
import traceback
import asyncio
import json
from config_manager import ConfigManager  # Google Drive対応版

# ---------- 環境変数からトークン取得 ----------
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise ValueError("DISCORD_TOKEN が取得できません。")
TOKEN = TOKEN.strip()

# ---------- HTTPサーバー（Render用） ----------
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running!")

def run_server():
    port = int(os.environ.get("PORT", 10000))
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()

threading.Thread(target=run_server, daemon=True).start()

# ---------- Discord Bot ----------
intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.members = True
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ---------- 非同期でBot起動 ----------
async def main():
    async with bot:
        # ConfigManager 初期化
        DRIVE_FILE_ID = os.getenv("DRIVE_FILE_ID")
        if not DRIVE_FILE_ID:
            raise ValueError("DRIVE_FILE_ID が取得できません。")

        config_manager = ConfigManager(bot, drive_file_id=DRIVE_FILE_ID)
        bot.config_manager = config_manager

        # Cog のロード
        cogs = [
            "cogs.transfer_cog",
            "cogs.vc_cog",
            "cogs.audit_cog",
            "cogs.owner_cog",
        ]
        for cog_path in cogs:
            try:
                await bot.load_extension(cog_path)
                print(f"[✅] Loaded {cog_path}")
            except Exception as e:
                print(f"[❌] Failed to load {cog_path}: {e}")
                traceback.print_exc()

        # ---------- デバッグ用コマンド ----------
        @bot.command(name="debug_all_full")
        async def debug_all_full(ctx: commands.Context):
            """管理者向け: ConfigManager全データを完全に返す"""
            guild_id = ctx.guild.id
            author_id = ctx.author.id
            if not bot.config_manager.is_admin(guild_id, author_id):
                await ctx.send("❌ 管理者ではありません。")
                return

            # ローカル config
            local_config = bot.config_manager.config
            local_text = json.dumps(local_config, indent=2, ensure_ascii=False)

            # Google Drive 上の config
            try:
                bot.config_manager.drive_handler.download_config("tmp_config.json")
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

            await ctx.send("✅ 全データ送信完了")

        # Bot 起動時イベント
        @bot.event
        async def on_ready():
            print(f"[🟢] Bot logged in as {bot.user}")
            print(f"[ℹ] Loaded Cogs: {list(bot.cogs.keys())}")
            print("[ℹ] Registered Commands:")
            for cmd in bot.commands:
                print(f" - {cmd.name}")

        await bot.start(TOKEN)

# ---------- 実行 ----------
if __name__ == "__main__":
    asyncio.run(main())
