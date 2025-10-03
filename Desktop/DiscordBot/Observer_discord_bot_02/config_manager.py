# config_manager.py
import discord
from discord.ext import commands
import json
import os

CONFIG_FILE = "config_data.json"
DEBUG_CHANNEL_ID = 1421826461597171733  # デバッグ用チャンネルID

class ConfigManager:
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.load_config()
        self.register_commands()

    # ------------------------ 設定ロード/保存 ------------------------
    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                self.config = json.load(f)
        else:
            self.config = {"servers": {}}

    def save_config(self):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)

    # ------------------------ サーバー設定取得 ------------------------
    def get_server_config(self, guild_id: int):
        sid = str(guild_id)
        if sid not in self.config["servers"]:
            self.config["servers"][sid] = {
                "SERVER_A_ID": None,
                "SERVER_B_ID": None,
                "CHANNEL_MAPPING": {},
                "READ_GROUPS": {},
                "ADMIN_IDS": [],
                "VC_LOG_CHANNEL": None,
                "AUDIT_LOG_CHANNEL": None,
                "OTHER_CHANNEL": None,
                "READ_USERS": []
            }
        return self.config["servers"][sid]

    def is_admin(self, guild_id, user_id):
        server = self.get_server_config(guild_id)
        return user_id in server["ADMIN_IDS"]

    # ------------------------ メッセージベースで設定取得 ------------------------
    def get_server_config_by_message(self, message: discord.Message):
        guild_id = message.guild.id
        conf = self.config["servers"].get(str(guild_id))
        if conf:
            return conf
        for s_conf in self.config["servers"].values():
            if s_conf.get("SERVER_A_ID") == guild_id:
                return s_conf
        return None

    # ------------------------ コマンド登録 ------------------------
    def register_commands(self):
        bot = self.bot

        @bot.command(name="adomin")
        async def adomin(ctx: commands.Context):
            server = self.get_server_config(ctx.guild.id)
            if len(server["ADMIN_IDS"]) == 0:
                server["ADMIN_IDS"].append(ctx.author.id)
                server["SERVER_B_ID"] = ctx.guild.id
                self.save_config()
                await ctx.send(f"✅ 管理者登録完了: {ctx.author.display_name}\n✅ このサーバーを SERVER_B_ID に設定しました")
            else:
                await ctx.send("管理者は既に登録済みです")

        @bot.command(name="set_server")
        async def set_server(ctx: commands.Context, server_a_id: int):
            server_b_id = ctx.guild.id
            server_b_conf = self.get_server_config(server_b_id)

            if not self.is_admin(server_b_id, ctx.author.id):
                await ctx.send("管理者のみ使用可能です")
                return

            server_b_conf["SERVER_A_ID"] = server_a_id
            guild_a = bot.get_guild(server_a_id)
            guild_b = bot.get_guild(server_b_id)
            if guild_a is None or guild_b is None:
                await ctx.send("⚠️ Botが両方のサーバーに参加しているか確認してください")
                return

            a_conf = self.get_server_config(guild_a.id)
            a_conf["SERVER_B_ID"] = guild_b.id

            # ---------------- チャンネル構造コピー ----------------
            for channel in guild_a.channels:
                if isinstance(channel, discord.CategoryChannel):
                    cat = await guild_b.create_category(name=channel.name)
                    server_b_conf["CHANNEL_MAPPING"][str(channel.id)] = cat.id
                    a_conf["CHANNEL_MAPPING"][str(cat.id)] = channel.id
                elif isinstance(channel, discord.TextChannel):
                    category_id = server_b_conf["CHANNEL_MAPPING"].get(str(channel.category_id))
                    cat = guild_b.get_channel(category_id) if category_id else None
                    new_ch = await guild_b.create_text_channel(name=channel.name, category=cat)
                    server_b_conf["CHANNEL_MAPPING"][str(channel.id)] = new_ch.id
                    a_conf["CHANNEL_MAPPING"][str(new_ch.id)] = channel.id
                elif isinstance(channel, discord.VoiceChannel):
                    category_id = server_b_conf["CHANNEL_MAPPING"].get(str(channel.category_id))
                    cat = guild_b.get_channel(category_id) if category_id else None
                    new_ch = await guild_b.create_voice_channel(name=channel.name, category=cat)
                    server_b_conf["CHANNEL_MAPPING"][str(channel.id)] = new_ch.id
                    a_conf["CHANNEL_MAPPING"][str(new_ch.id)] = channel.id

            self.save_config()
            await ctx.send("✅ Aサーバーのチャンネル構造を B にコピーし、両方のJSONに反映しました")

# --------------------------------------------------------------------------
# TransferCog: A→B 転送 + デバッグ
# --------------------------------------------------------------------------
class TransferCog(commands.Cog):
    def __init__(self, bot: commands.Bot, config_manager: ConfigManager):
        self.bot = bot
        self.config_manager = config_manager
        print("[DEBUG] TransferCog loaded")

    async def send_debug(self, text: str):
        debug_ch = self.bot.get_channel(DEBUG_CHANNEL_ID)
        if debug_ch:
            try:
                await debug_ch.send(f"[DEBUG] {text}")
            except Exception as e:
                print(f"[DEBUG ERROR] {e}")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        await self.send_debug(f"受信: {message.guild.name} ({message.guild.id}) | {message.channel.name} ({message.channel.id}) | {message.content}")

        server_conf = self.config_manager.get_server_config_by_message(message)
        if not server_conf:
            await self.send_debug("サーバー設定が見つからなかった → commandsへ渡す")
            await self.bot.process_commands(message)
            return

        server_a_id = server_conf.get("SERVER_A_ID")
        server_b_id = server_conf.get("SERVER_B_ID")
        channel_mapping = server_conf.get("CHANNEL_MAPPING", {})

        # Aサーバー以外は無視
        if message.guild.id != server_a_id:
            await self.send_debug("このサーバーはAではない → commandsへ渡す")
            await self.bot.process_commands(message)
            return

        guild_b = self.bot.get_guild(server_b_id)
        if not guild_b:
            await self.send_debug("Bサーバーが見つからない")
            await self.bot.process_commands(message)
            return

        dest_channel_id = channel_mapping.get(str(message.channel.id))
        if not dest_channel_id:
            await self.send_debug(f"チャンネルマッピングが存在しない: {message.channel.id}")
            await self.bot.process_commands(message)
            return

        dest_channel = guild_b.get_channel(dest_channel_id)
        if not dest_channel:
            await self.send_debug(f"転送先チャンネルが取得できない: {dest_channel_id}")
            await self.bot.process_commands(message)
            return

        await self.send_debug(f"転送開始: {message.channel.id} → {dest_channel.id}")

        # Embed作成
        description = message.content
        embed = discord.Embed(description=description, color=discord.Color.blue())
        embed.set_author(
            name=message.author.display_name,
            icon_url=message.author.avatar.url if message.author.avatar else None
        )

        # 添付画像
        first_image = next((a.url for a in message.attachments if a.content_type and a.content_type.startswith("image/")), None)
        if first_image:
            embed.set_image(url=first_image)
        await dest_channel.send(embed=embed)

        # その他添付
        for attach in message.attachments:
            if attach.url != first_image:
                await dest_channel.send(attach.url)

        # URL
        urls = [word for word in message.content.split() if word.startswith("http")]
        for url in urls:
            await dest_channel.send(url)

        # 役職メンション
        if message.role_mentions:
            mentions = []
            for role in message.role_mentions:
                target_role = discord.utils.get(guild_b.roles, name=role.name)
                if target_role:
                    mentions.append(target_role.mention)
            if mentions:
                await dest_channel.send(" ".join(mentions))

        await self.send_debug("転送完了")
        await self.bot.process_commands(message)

# --------------------------------------------------------------------------
# Cogセットアップ
# --------------------------------------------------------------------------
async def setup(bot: commands.Bot):
    config_manager = getattr(bot, "config_manager", None)
    if not config_manager:
        raise RuntimeError("ConfigManager が bot にセットされていません")
    await bot.add_cog(TransferCog(bot, config_manager))
