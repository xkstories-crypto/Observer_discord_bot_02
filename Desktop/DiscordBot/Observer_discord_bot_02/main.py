# main.py
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import discord
from discord.ext import commands
import traceback
import asyncio
from config_manager import ConfigManager

# ---------- 環境変数からトークン取得 ----------
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise ValueError("DISCORD_TOKEN が取得できません。")
TOKEN = TOKEN.strip()
print(f"Raw token repr: {repr(TOKEN)}")
print(f"Token length: {len(TOKEN)}")

# ---------- Google Drive ファイルID ----------
DRIVE_FILE_ID = os.getenv("DRIVE_FILE_ID")
if not DRIVE_FILE_ID:
    raise ValueError("DRIVE_FILE_ID が取得できません。")

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
        # ConfigManager 初期化（環境変数から JSON をロード）
        config_manager = ConfigManager(bot, DRIVE_FILE_ID)
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
