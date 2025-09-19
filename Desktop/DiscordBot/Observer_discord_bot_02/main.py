# main.py
import discord
from discord.ext import commands
import threading
from config import TOKEN
from cogs.http_cog import run_server  # Cog 内に run_server を定義しておく

# ---------- HTTPサーバー（Render用） ----------
# main.py 内でスレッドとして起動
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
initial_cogs = [
    "cogs.transfer_cog",
    "cogs.vc_cog",
    "cogs.audit_cog",
    "cogs.role_cog"
]

@bot.event
async def on_ready():
    print(f"{bot.user} でログインしました！")

for cog in initial_cogs:
    try:
        bot.load_extension(cog)
        print(f"Loaded {cog}")
    except Exception as e:
        print(f"Failed to load {cog}: {e}")

# ---------- Bot 起動 ----------
bot.run(TOKEN)
