import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import discord
from discord.ext import commands
from config import TOKEN

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

# ---------- Cog のロード ----------
cogs = [
    "cogs.transfer_cog",
    "cogs.vc_cog",
    "cogs.audit_cog",
    "cogs.owner_cog",
]

for cog in cogs:
    try:
        bot.load_extension(cog)
        print(f"Loaded {cog}")
    except Exception as e:
        print(f"Failed to load {cog}: {e}")

# ---------- Bot起動 ----------
bot.run(TOKEN)
