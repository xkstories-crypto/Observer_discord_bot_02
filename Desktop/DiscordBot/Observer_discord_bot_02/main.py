import discord
from discord.ext import commands
import os
from config import TOKEN

intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.members = True
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ロードするCog一覧
initial_cogs = [
    "cogs.http_cog",
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

bot.run(TOKEN)
