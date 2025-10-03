# -------------------------
# transfer_cog.py
# -------------------------
import discord
from discord.ext import commands
from config_manager import ConfigManager

DEBUG_CHANNEL_ID = 1421826461597171733  # デバッグチャンネル

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

        server_conf = self.config_manager.get_server_config_by_message(message)
        if not server_conf:
            await self.bot.process_commands(message)
            return

        # 双方向転送 A↔B
        src_guild_id = message.guild.id
        server_a_id = server_conf.get("SERVER_A_ID")
        server_b_id = server_conf.get("SERVER_B_ID")
        channel_mapping = server_conf.get("CHANNEL_MAPPING", {})

        if src_guild_id == server_a_id:
            dest_guild = self.bot.get_guild(server_b_id)
        elif src_guild_id == server_b_id:
            dest_guild = self.bot.get_guild(server_a_id)
        else:
            await self.bot.process_commands(message)
            return

        dest_channel_id = channel_mapping.get(str(message.channel.id))
        if not dest_channel_id:
            await self.send_debug(f"チャンネルマッピングなし: {message.channel.id}")
            await self.bot.process_commands(message)
            return

        dest_channel = dest_guild.get_channel(dest_channel_id)
        if not dest_channel:
            await self.send_debug(f"転送先チャンネル取得失敗: {dest_channel_id}")
            await self.bot.process_commands(message)
            return

        await self.send_debug(f"{message.guild.name}:{message.channel.name} → {dest_guild.name}:{dest_channel.name}")

        # Embed作成
        embed = discord.Embed(description=message.content, color=discord.Color.blue())
        embed.set_author(name=message.author.display_name, icon_url=message.author.avatar.url if message.author.avatar else None)

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
                target_role = discord.utils.get(dest_guild.roles, name=role.name)
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
