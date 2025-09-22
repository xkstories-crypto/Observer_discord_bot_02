import discord
from discord.ext import commands

intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# 保存用データ
server_settings = {}  # {a_server_id: {"b_server": id, "channels": {}, "admins": set(), "watch": set()}}

def get_settings(guild_id):
    if guild_id not in server_settings:
        server_settings[guild_id] = {"b_server": None, "channels": {}, "admins": set(), "watch": set()}
    return server_settings[guild_id]

@bot.event
async def on_ready():
    print(f"起動完了: {bot.user}")

# 初回登録: 実行者を管理者に、B鯖を固定
@bot.command()
async def init(ctx, b_server_id: int):
    settings = get_settings(ctx.guild.id)
    if settings["b_server"] is None:
        settings["b_server"] = b_server_id
        settings["admins"].add(ctx.author.id)
        await ctx.send(f"✅ 初回登録完了\nBサーバー: {b_server_id}\n管理者: {ctx.author}")
    else:
        await ctx.send("⚠️ すでに初期化済みです。")

# チャンネルセット追加
@bot.command()
async def addset(ctx, source_id: int, dest_id: int):
    settings = get_settings(ctx.guild.id)
    if ctx.author.id not in settings["admins"]:
        return await ctx.send("権限がありません。")
    settings["channels"][source_id] = dest_id
    await ctx.send(f"✅ チャンネルセット追加\nA:{source_id} → B:{dest_id}")

# チャンネルセット削除
@bot.command()
async def delset(ctx, source_id: int):
    settings = get_settings(ctx.guild.id)
    if ctx.author.id not in settings["admins"]:
        return await ctx.send("権限がありません。")
    if source_id in settings["channels"]:
        del settings["channels"][source_id]
        await ctx.send(f"🗑️ セット削除: {source_id}")
    else:
        await ctx.send("⚠️ そのチャンネルは登録されていません。")

# 管理者追加/削除
@bot.command()
async def admin(ctx, action: str, member: discord.Member):
    settings = get_settings(ctx.guild.id)
    if ctx.author.id not in settings["admins"]:
        return await ctx.send("権限がありません。")
    if action == "add":
        settings["admins"].add(member.id)
        await ctx.send(f"✅ 管理者追加: {member}")
    elif action == "remove":
        settings["admins"].discard(member.id)
        await ctx.send(f"🗑️ 管理者削除: {member}")
    else:
        await ctx.send("⚠️ `add` or `remove` を指定してください。")

# 監視ユーザー追加/削除
@bot.command()
async def watch(ctx, action: str, member: discord.Member):
    settings = get_settings(ctx.guild.id)
    if ctx.author.id not in settings["admins"]:
        return await ctx.send("権限がありません。")
    if action == "add":
        settings["watch"].add(member.id)
        await ctx.send(f"👀 監視追加: {member}")
    elif action == "remove":
        settings["watch"].discard(member.id)
        await ctx.send(f"🗑️ 監視削除: {member}")
    else:
        await ctx.send("⚠️ `add` or `remove` を指定してください。")

# 転送処理
@bot.event
async def on_message(message):
    if message.author.bot:
        return
    settings = get_settings(message.guild.id)
    if message.channel.id in settings["channels"]:
        b_server = bot.get_guild(settings["b_server"])
        if b_server:
            dest_ch = b_server.get_channel(settings["channels"][message.channel.id])
            if dest_ch:
                # embedを避けてテキスト転送のみ
                await dest_ch.send(f"[{message.author}] {message.content}")
    await bot.process_commands(message)

bot.run("YOUR_TOKEN")
