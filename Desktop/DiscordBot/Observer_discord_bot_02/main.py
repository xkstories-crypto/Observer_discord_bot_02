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
config_manager = ConfigManager(bot)  # Botを渡す
bot.config_manager = config_manager  # Cog で使用できるように属性追加

# ---------- 一時確認コマンド（管理者限定） ----------
@bot.command(name="show_config")
async def show_config(ctx):
    # 管理者だけ許可
    server_conf = bot.config_manager.get_server_config(ctx.guild.id)
    admin_ids = server_conf.get("ADMIN_IDS", [])
    if ctx.author.id not in admin_ids:
        await ctx.send("❌ 管理者のみ使用可能です。")
        return

    try:
        with open("config_data.json", "r", encoding="utf-8") as f:
            data = f.read()
        if len(data) > 1900:
            data = data[:1900] + "..."
        await ctx.send(f"```json\n{data}\n```")
    except Exception as e:
        await ctx.send(f"エラー: {e}")

# ---------- Cog のロード ----------
async def main():
    async with bot:
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
