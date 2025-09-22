# main.py
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import discord
from discord.ext import commands
import traceback
import asyncio

from config import TOKEN
from config_manager import ConfigManager

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

# ---------- ConfigManager ----------
config_manager = ConfigManager(bot)

# ---------- Cog のロード ----------
async def main():
    async with bot:
        # ロードする Cog のリスト
        cogs = [
            "cogs.transfer_cog",
            "cogs.vc_cog",
            "cogs.audit_cog",
            "cogs.owner_cog",
        ]

        for cog_path in cogs:
            try:
                # Cog のロード
                await bot.load_extension(cog_path)
                print(f"[✅] Loaded {cog_path}")
            except Exception as e:
                print(f"[❌] Failed to load {cog_path}: {e}")
                traceback.print_exc()

        # ---------- Bot 起動時イベント ----------
        @bot.event
        async def on_ready():
            print(f"[🟢] Bot logged in as {bot.user}")
            print(f"[ℹ] Loaded Cogs: {list(bot.cogs.keys())}")
            print("[ℹ] Registered Commands:")
            for cmd in bot.commands:
                print(f" - {cmd.name}")

        # Bot を起動
        await bot.start(TOKEN)

# ---------- 非同期で実行 ----------
if __name__ == "__main__":
    asyncio.run(main())
