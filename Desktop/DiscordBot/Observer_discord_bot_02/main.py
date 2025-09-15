# main.py
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

# ---------- 起動時 ----------
@bot.event
async def on_ready():
    print(f"{bot.user} でログインしました！")

    # サーバー取得
    guild_a = bot.get_guild(SERVER_A_ID)
    guild_b = bot.get_guild(SERVER_B_ID)
    print("Server A:", guild_a)
    print("Server B:", guild_b)

    # VCログ・監査ログチャンネル取得
    vc_log_channel = bot.get_channel(VC_LOG_CHANNEL)
    audit_log_channel = bot.get_channel(AUDIT_LOG_CHANNEL)
    print("VC_LOG_CHANNEL:", VC_LOG_CHANNEL, "->", vc_log_channel)
    print("AUDIT_LOG_CHANNEL:", AUDIT_LOG_CHANNEL, "->", audit_log_channel)

    # メッセージマッピングチャンネル確認
    for src_id, dest_id in CHANNEL_MAPPING.items():
        if src_id == "a_other":
            dest_channel = bot.get_channel(dest_id)
            print("a_other ->", dest_id, "->", dest_channel)
        else:
            src_channel = bot.get_channel(src_id)
            dest_channel = bot.get_channel(dest_id)
            print(src_id, "->", dest_id, ":", src_channel, "->", dest_channel)

# ---------- メッセージ転送 ----------
@bot.event
async def on_message(message):
    if message.author.bot:
        return
    if message.guild.id != SERVER_A_ID:
        await bot.process_commands(message)
        return

    guild_b = bot.get_guild(SERVER_B_ID)
    dest_channel_id = CHANNEL_MAPPING.get(message.channel.id, CHANNEL_MAPPING.get("a_other"))
    dest_channel = guild_b.get_channel(dest_channel_id) if guild_b else None

    if dest_channel:
        embed = discord.Embed(
            description=message.content,
            color=discord.Color.blue()
        )
        embed.set_author(name=message.author.display_name, icon_url=message.author.avatar.url if message.author.avatar else None)
        await dest_channel.send(embed=embed)

    await bot.process_commands(message)

# ---------- VC入退出ログ ----------
@bot.event
async def on_voice_state_update(member, before, after):
    log_channel = member.guild.get_channel(VC_LOG_CHANNEL)
    if not log_channel:
        return

    if before.channel is None and after.channel is not None:
        await log_channel.send(f"🔊 {member.display_name} が {after.channel.name} に参加しました。")
    elif before.channel is not None and after.channel is None:
        await log_channel.send(f"🔈 {member.display_name} が {before.channel.name} から退出しました。")

# ---------- VCにいる人を全チャンネルで確認 ----------
@bot.command()
async def all_vc(ctx):
    """サーバー内全VCの状況を確認"""
    vc_channels = ctx.guild.voice_channels
    result = []
    for ch in vc_channels:
        members = [m.display_name for m in ch.members]
        if members:
            result.append(f"{ch.name}: {', '.join(members)}")
        else:
            result.append(f"{ch.name}: (誰もいません)")
    await ctx.send("\n".join(result))

# ---------- 監査ログ ----------
@bot.event
async def on_member_join(member):
    log_channel = member.guild.get_channel(AUDIT_LOG_CHANNEL)
    if log_channel:
        await log_channel.send(f"✅ {member.display_name} がサーバーに参加しました。")

@bot.event
async def on_member_remove(member):
    log_channel = member.guild.get_channel(AUDIT_LOG_CHANNEL)
    if log_channel:
        await log_channel.send(f"❌ {member.display_name} がサーバーから退出しました。")

@bot.event
async def on_member_ban(guild, user):
    log_channel = guild.get_channel(AUDIT_LOG_CHANNEL)
    if log_channel:
        await log_channel.send(f"⛔ {user.name} がBANされました。")

@bot.event
async def on_member_unban(guild, user):
    log_channel = guild.get_channel(AUDIT_LOG_CHANNEL)
    if log_channel:
        await log_channel.send(f"✅ {user.name} のBANが解除されました。")

# ---------- ロール操作 ----------
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

# ---------- Bot停止コマンド ----------
@bot.command()
@commands.is_owner()
async def stopbot(ctx):
    await ctx.send("Bot を停止します…")
    await bot.close()

# ---------- サーバー・チャンネル確認コマンド ----------
@bot.command()
async def check_channels(ctx):
    """サーバーとチャンネルがBotから見えているか確認"""
    lines = []

    # サーバー確認
    guild_a = bot.get_guild(SERVER_A_ID)
    guild_b = bot.get_guild(SERVER_B_ID)
    lines.append(f"Server A ({SERVER_A_ID}): {guild_a}")
    lines.append(f"Server B ({SERVER_B_ID}): {guild_b}")

    # VCログ・監査ログチャンネル確認
    vc_log_channel = bot.get_channel(VC_LOG_CHANNEL)
    audit_log_channel = bot.get_channel(AUDIT_LOG_CHANNEL)
    lines.append(f"VC_LOG_CHANNEL ({VC_LOG_CHANNEL}): {vc_log_channel}")
    lines.append(f"AUDIT_LOG_CHANNEL ({AUDIT_LOG_CHANNEL}): {audit_log_channel}")

    # メッセージマッピングチャンネル確認
    for src_id, dest_id in CHANNEL_MAPPING.items():
        if src_id == "a_other":
            dest_channel = bot.get_channel(dest_id)
            lines.append(f"a_other -> {dest_id} -> {dest_channel}")
        else:
            src_channel = bot.get_channel(src_id)
            dest_channel = bot.get_channel(dest_id)
            lines.append(f"{src_id} -> {dest_id}: {src_channel} -> {dest_channel}")

    await ctx.send("```\n" + "\n".join(lines) + "\n```")

# ---------- Bot起動 ----------
bot.run(TOKEN)
