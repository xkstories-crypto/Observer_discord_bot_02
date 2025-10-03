from discord.ext import commands
import discord
from config_manager import ConfigManager

DEBUG_CHANNEL_ID = 1421826461597171733  # デバッグ用チャンネルのID

class TransferCog(commands.Cog):
    def __init__(self, bot: commands.Bot, config_manager: ConfigManager):
        self.bot = bot
        self.config_manager = config_manager
        print("[DEBUG] TransferCog loaded")

    async def send_debug(self, text: str):
        """デバッグチャンネルにログを送信"""
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

        if message.guild.id != server_a_id:
            await self.send_debug("このサーバーはAじゃない → commandsへ渡す")
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


async def setup(bot: commands.Bot):
    config_manager = getattr(bot, "config_manager", None)
    if not config_manager:
        raise RuntimeError("ConfigManager が bot にセットされていません")
    await bot.add_cog(TransferCog(bot, config_manager))
