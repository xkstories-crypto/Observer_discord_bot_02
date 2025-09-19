# main_sync.py
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import discord
from discord.ext import commands
from config import TOKEN, SERVER_A_ID, SERVER_B_ID, CHANNEL_MAPPING, VC_LOG_CHANNEL, AUDIT_LOG_CHANNEL

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

# ---------- Cog の同期ロード ----------
cogs = [
    "cogs.owner_cog",
    "cogs.transfer_cog",
    "cogs.vc_cog",
    "cogs.audit_cog",
    "cogs.role_cog"
]

for cog in cogs:
    try:
        bot.load_extension(cog)
        print(f"Loaded {cog}")
    except Exception as e:
        print(f"Failed to load {cog}: {e}")

# ---------- 起動時 ----------
@bot.event
async def on_ready():
    print(f"{bot.user} でログインしました！")

    guild_a = bot.get_guild(SERVER_A_ID)
    guild_b = bot.get_guild(SERVER_B_ID)
    print("Server A:", guild_a)
    print("Server B:", guild_b)

    vc_log_channel = bot.get_channel(VC_LOG_CHANNEL)
    audit_log_channel = bot.get_channel(AUDIT_LOG_CHANNEL)
    print("VC_LOG_CHANNEL:", VC_LOG_CHANNEL, "->", vc_log_channel)
    print("AUDIT_LOG_CHANNEL:", AUDIT_LOG_CHANNEL, "->", audit_log_channel)

    for src_id, dest_id in CHANNEL_MAPPING.items():
        dest_channel = bot.get_channel(dest_id)
        print(f"{src_id} -> {dest_id}: {dest_channel}")

# ---------- Bot 起動 ----------
bot.run(TOKEN)
