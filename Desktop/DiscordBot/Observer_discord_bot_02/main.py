# main.py
import discord
from discord.ext import commands
import threading
from config import TOKEN

# ---------- HTTPサーバー（Render用） ----------
# main.py 内でスレッドとして起動
def run_http():
    from http.server import HTTPServer, BaseHTTPRequestHandler

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")

    server = HTTPServer(("0.0.0.0", 10000), Handler)
    server.serve_forever()

threading.Thread(target=run_http, daemon=True).start()

# ---------- Discord Bot ----------
intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.members = True
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ---------- Cog のリスト ----------
initial_cogs = [
    "cogs.owner_cog",   # ← これを追加
    "cogs.transfer_cog",
    "cogs.vc_cog",
    "cogs.audit_cog",
    "cogs.role_cog"
]


# ---------- Cog を非同期でロード ----------
async def load_all_cogs():
    for cog in initial_cogs:
        try:
            await bot.load_extension(cog)
            print(f"Loaded {cog}")
        except Exception as e:
            print(f"Failed to load {cog}: {e}")

# ---------- Bot 起動イベント ----------
@bot.event
async def on_ready():
    print(f"{bot.user} でログインしました！")
    await load_all_cogs()

# ---------- Bot 起動 ----------
bot.run(TOKEN)
