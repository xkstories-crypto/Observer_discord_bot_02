import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import discord
from discord.ext import commands
from config import TOKEN, SERVER_A_ID, SERVER_B_ID, CHANNEL_MAPPING, VC_LOG_CHANNEL, AUDIT_LOG_CHANNEL

# ---------- HTTPサーバー（Render用にポート開放） ----------
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running!")

def run_server():
    port = int(os.environ.get("PORT", 10000))  # Render が自動で指定するポート
    server = HTTPServer(("0.0.0.0", port), Handler)
    server.serve_forever()

threading.Thread(target=run_server, daemon=True).start()

# ---------- Discord Bot ----------
intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.members = True
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"{bot.user} でログインしました！")

# ---------- 以下、あなたの既存コードをそのまま ----------
@bot.event
async def on_message(message):
    if message.author.bot:
        return
    if message.guild.id != SERVER_A_ID:
        await bot.process_commands(message)
        return
    guild_b = bot.get_guild(SERVER_B_ID)
    dest_channel_name = CHANNEL_MAPPING.get(message.channel.name, CHANNEL_MAPPING.get("a_other"))
    dest_channel = discord.utils.get(guild_b.text_channels, name=dest_channel_name)
    if dest_channel:
        embed = discord.Embed(
            description=message.content,
            color=discord.Color.blue()
        )
        embed.set_author(name=message.author.display_name, icon_url=message.author.avatar.url if message.author.avatar else None)
        await dest_channel.send(embed=embed)
    await bot.process_commands(message)

# VCログ
@bot.event
async def on_voice_state_update(member, before, after):
    log_channel = discord.utils.get(member.guild.text_channels, name=VC_LOG_CHANNEL)
    if not log_channel:
        return
    if before.channel is None and after.channel is not None:
        await log_channel.send(f"🔊 {member.display_name} が {after.channel.name} に参加しました。")
    elif before.channel is not None and after.channel is None:
        await log_channel.send(f"🔈 {member.display_name} が {before.channel.name} から退出しました。")

# VC表示コマンド
@bot.command()
async def vc(ctx, channel_name: str):
    channel = discord.utils.get(ctx.guild.voice_channels, name=channel_name)
    if not channel:
        await ctx.send("チャンネルが見つかりません。")
        return
    members = [member.display_name for member in channel.members]
    if members:
        await ctx.send(f"{channel.name} にいるメンバー: {', '.join(members)}")
    else:
        await ctx.send(f"{channel.name} にメンバーはいません。")

# 監査ログ
@bot.event
async def on_member_join(member):
    log_channel = discord.utils.get(member.guild.text_channels, name=AUDIT_LOG_CHANNEL)
    if log_channel:
        await log_channel.send(f"✅ {member.display_name} がサーバーに参加しました。")

@bot.event
async def on_member_remove(member):
    log_channel = discord.utils.get(member.guild.text_channels, name=AUDIT_LOG_CHANNEL)
    if log_channel:
        await log_channel.send(f"❌ {member.display_name} がサーバーから退出しました。")

@bot.event
async def on_member_ban(guild, user):
    log_channel = discord.utils.get(guild.text_channels, name=AUDIT_LOG_CHANNEL)
    if log_channel:
        await log_channel.send(f"⛔ {user.name} がBANされました。")

@bot.event
async def on_member_unban(guild, user):
    log_channel = discord.utils.get(guild.text_channels, name=AUDIT_LOG_CHANNEL)
    if log_channel:
        await log_channel.send(f"✅ {user.name} のBANが解除されました。")

# ロール操作
@bot.command()
@commands.has_permissions(manage_roles=True)
async def create_role(ctx, name: str, color: str = "0x3498db"):
    color_val = int(color, 16)
    await ctx.guild.create_role(name=name, color=discord.Color(color_val))
    await ctx.send(f"ロール {name} を作成しました。")

@bot.command()
@commands.has_permissions(manage_roles=True)
async def delete_role(ctx, name: str):
    role = discord.utils.get(ctx.guild.roles, name=name)
    if role:
        await role.delete()
        await ctx.send(f"ロール {name} を削除しました。")
    else:
        await ctx.send("ロールが見つかりません。")

bot.run(TOKEN)


# ---------- VC入退出ログ ----------
@bot.event
async def on_voice_state_update(member, before, after):
    log_channel = discord.utils.get(member.guild.text_channels, name=VC_LOG_CHANNEL)
    if not log_channel:
        return

    if before.channel is None and after.channel is not None:
        await log_channel.send(f"🔊 {member.display_name} が {after.channel.name} に参加しました。")
    elif before.channel is not None and after.channel is None:
        await log_channel.send(f"🔈 {member.display_name} が {before.channel.name} から退出しました。")

# ---------- 現在VCにいる人表示 ----------
@bot.command()
async def vc(ctx, channel_name: str):
    channel = discord.utils.get(ctx.guild.voice_channels, name=channel_name)
    if not channel:
        await ctx.send("チャンネルが見つかりません。")
        return

    members = [member.display_name for member in channel.members]
    if members:
        await ctx.send(f"{channel.name} にいるメンバー: {', '.join(members)}")
    else:
        await ctx.send(f"{channel.name} にメンバーはいません。")

# ---------- 監査ログ ----------
@bot.event
async def on_member_join(member):
    log_channel = discord.utils.get(member.guild.text_channels, name=AUDIT_LOG_CHANNEL)
    if log_channel:
        await log_channel.send(f"✅ {member.display_name} がサーバーに参加しました。")

@bot.event
async def on_member_remove(member):
    log_channel = discord.utils.get(member.guild.text_channels, name=AUDIT_LOG_CHANNEL)
    if log_channel:
        await log_channel.send(f"❌ {member.display_name} がサーバーから退出しました。")

@bot.event
async def on_member_ban(guild, user):
    log_channel = discord.utils.get(guild.text_channels, name=AUDIT_LOG_CHANNEL)
    if log_channel:
        await log_channel.send(f"⛔ {user.name} がBANされました。")

@bot.event
async def on_member_unban(guild, user):
    log_channel = discord.utils.get(guild.text_channels, name=AUDIT_LOG_CHANNEL)
    if log_channel:
        await log_channel.send(f"✅ {user.name} のBANが解除されました。")

# ---------- サーバー設定変更・ロール操作 雛形 ----------
@bot.command()
@commands.has_permissions(manage_roles=True)
async def create_role(ctx, name: str, color: str = "0x3498db"):
    color_val = int(color, 16)
    await ctx.guild.create_role(name=name, color=discord.Color(color_val))
    await ctx.send(f"ロール {name} を作成しました。")

@bot.command()
@commands.has_permissions(manage_roles=True)
async def delete_role(ctx, name: str):
    role = discord.utils.get(ctx.guild.roles, name=name)
    if role:
        await role.delete()
        await ctx.send(f"ロール {name} を削除しました。")
    else:
        await ctx.send("ロールが見つかりません。")

bot.run(TOKEN)
print("DISCORD_TOKEN:", TOKEN)

