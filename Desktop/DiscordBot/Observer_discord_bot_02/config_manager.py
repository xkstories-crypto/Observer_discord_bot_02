import discord
from discord.ext import commands
import json
import os

CONFIG_FILE = "server_config.json"

# ---------- 設定管理 ----------
class ConfigManager:
    def __init__(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                self.data = json.load(f)
        else:
            self.data = {}

    def save(self):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

    def get_server(self, server_id: int):
        sid = str(server_id)
        if sid not in self.data:
            self.data[sid] = {
                "ADMINS": [],
                "SERVER_A_ID": None,
                "SERVER_B_ID": None,
                "CHANNEL_MAPPING": {}
            }
        return self.data[sid]

    def set_admin(self, server_id: int, user_id: int):
        conf = self.get_server(server_id)
        if user_id not in conf["ADMINS"]:
            conf["ADMINS"].append(user_id)
        self.save()

    def is_admin(self, server_id: int, user_id: int):
        return user_id in self.get_server(server_id)["ADMINS"]


# ---------- Bot ----------
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)
config = ConfigManager()


# ---------- 管理者追加 ----------
@bot.command(name="adomin")
async def adomin(ctx):
    config.set_admin(ctx.guild.id, ctx.author.id)
    await ctx.send(f"✅ {ctx.author.mention} を管理者に追加しました。")


# ---------- サーバー同期 ----------
@bot.command(name="set_server")
async def set_server(ctx, server_a_id: int):
    server_b_id = ctx.guild.id

    if not config.is_admin(server_b_id, ctx.author.id):
        await ctx.send("⚠️ 管理者のみ使用可能です。")
        return

    guild_a = bot.get_guild(server_a_id)
    guild_b = bot.get_guild(server_b_id)

    if guild_a is None or guild_b is None:
        await ctx.send("⚠️ Botが両方のサーバーに参加している必要があります。")
        return

    # ---------- A/Bサーバーの設定を保存 ----------
    conf_a = config.get_server(server_a_id)
    conf_b = config.get_server(server_b_id)

    conf_a["SERVER_A_ID"] = server_a_id
    conf_a["SERVER_B_ID"] = server_b_id
    conf_b["SERVER_A_ID"] = server_a_id
    conf_b["SERVER_B_ID"] = server_b_id
    conf_b["CHANNEL_MAPPING"] = {}  # B側のマッピングを初期化

    config.save()

    # ---------- AのチャンネルをBにコピー ----------
    for channel in guild_a.channels:
        if isinstance(channel, discord.CategoryChannel):
            new_cat = await guild_b.create_category(name=channel.name)
            conf_b["CHANNEL_MAPPING"][str(channel.id)] = new_cat.id

        elif isinstance(channel, discord.TextChannel):
            cat_id = conf_b["CHANNEL_MAPPING"].get(str(channel.category_id))
            cat = guild_b.get_channel(cat_id) if cat_id else None
            new_ch = await guild_b.create_text_channel(name=channel.name, category=cat)
            conf_b["CHANNEL_MAPPING"][str(channel.id)] = new_ch.id

        elif isinstance(channel, discord.VoiceChannel):
            cat_id = conf_b["CHANNEL_MAPPING"].get(str(channel.category_id))
            cat = guild_b.get_channel(cat_id) if cat_id else None
            new_ch = await guild_b.create_voice_channel(name=channel.name, category=cat)
            conf_b["CHANNEL_MAPPING"][str(channel.id)] = new_ch.id

    config.save()
    await ctx.send("✅ サーバー同期完了！ Aのチャンネル構造をBにコピーしました。")


# ---------- 起動 ----------
@bot.event
async def on_ready():
    print(f"✅ ログインしました: {bot.user}")


# TOKENで起動
bot.run("YOUR_BOT_TOKEN")
