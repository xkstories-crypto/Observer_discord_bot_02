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
config_manager = ConfigManager()
bot.config_manager = config_manager  # Cog で使用できるように属性追加

# ---------- 一時確認コマンド（管理者限定） ----------
@bot.command(name="show_config")
async def show_config(ctx):
    # サーバーIDでペアを検索
    pair = None
    for p in bot.config_manager.pairs:  # pairs 属性にすべてのペアを保持している想定
        if ctx.guild.id in (p["A_ID"], p["B_ID"]):
            pair = p
            break

    if not pair:
        await ctx.send("⚠️ このサーバーはペア設定されていません。")
        return

    # 管理者チェック
    if ctx.author.id not in pair.get("ADMIN_IDS", []):
        await ctx.send("❌ 管理者のみ使用可能です。")
        return

    # JSON 出力（チャンネルマッピングも表示）
    lines = []
    lines.append(f"Pair: A={pair['A_ID']}, B={pair['B_ID']}")
    lines.append("CHANNEL_MAPPING:")
    for direction, mapping in pair["CHANNEL_MAPPING"].items():
        lines.append(f"  {direction}:")
        for src, dest in mapping.items():
            lines.append(f"    {src} -> {dest}")

    lines.append("ADMIN_IDS:")
    for admin_id in pair.get("ADMIN_IDS", []):
        user = bot.get_user(admin_id)
        lines.append(f"  {admin_id} -> {user.name if user else 'ユーザー不在'}")

    await ctx.send("```\n" + "\n".join(lines) + "\n```")

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
