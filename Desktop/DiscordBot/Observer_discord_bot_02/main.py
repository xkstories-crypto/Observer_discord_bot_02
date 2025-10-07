# main.py
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import discord
from discord.ext import commands
import traceback
import asyncio
from config_manager import ConfigManager

# ---------- 環境変数からトークン取得＆デバッグ ----------
token_env = os.getenv("DISCORD_TOKEN")
print("Raw token repr:", repr(token_env))  # 空白や改行も可視化
print("Token length:", len(token_env) if token_env else "No token found")

if token_env is None:
    raise ValueError("DISCORD_TOKEN が取得できません。Render の環境変数を確認してください。")
TOKEN = token_env.strip()

# ---------- Google Drive ファイルID ----------
DRIVE_FILE_ID = "1XKcqX--KPZ1qBSxYXhc_YRP-RSHqyszx"  # ←ここを自分のファイルIDに変更

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
        # ---------- ConfigManager ----------
        config_manager = ConfigManager(bot, DRIVE_FILE_ID)
        bot.config_manager = config_manager  # Cog で使用できるように属性追加

        # ---------- Cog のロード ----------
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

        # ---------- Bot 起動時イベント ----------
        @bot.event
        async def on_ready():
            print(f"[🟢] Bot logged in as {bot.user}")
            print(f"[ℹ] Loaded Cogs: {list(bot.cogs.keys())}")
            print("[ℹ] Registered Commands:")
            for cmd in bot.commands:
                print(f" - {cmd.name}")

        await bot.start(TOKEN)

# ---------- 非同期で実行 ----------
if __name__ == "__main__":
    asyncio.run(main())
