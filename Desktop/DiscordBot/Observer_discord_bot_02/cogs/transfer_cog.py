# cogs/transfer_cog.py
from discord.ext import commands
import discord
from config_manager import ConfigManager

class TransferCog(commands.Cog):
    def __init__(self, bot: commands.Bot, config_manager: ConfigManager):
        self.bot = bot
        self.config_manager = config_manager
        print("[DEBUG] TransferCog loaded")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return  # Bot メッセージや DM は無視

        server_conf = self.config_manager.get_server_config(message.guild.id)
        if not server_conf:
            return

        server_a_id = server_conf.get("SERVER_A_ID")
        server_b_id = server_conf.get("SERVER_B_ID")
        channel_mapping = server_conf.get("CHANNEL_MAPPING", {})
        other_channel_id = server_conf.get("OTHER_CHANNEL")

        # 型変換：JSON 保存時に文字列だった場合に対応
        try:
            server_a_id = int(server_a_id)
        except (TypeError, ValueError):
            server_a_id = None
        try:
            server_b_id = int(server_b_id)
        except (TypeError, ValueError):
            server_b_id = None

        if not server_a_id or not server_b_id:
            return

        # メッセージが送られたサーバーが SERVER_A_ID か確認
        if message.guild.id != server_a_id:
            return

        guild_b = self.bot.get_guild(server_b_id)
        if not guild_b:
            return

        # 転送先チャンネル決定
        dest_channel_id = channel_mapping.get(message.channel.id, other_channel_id)
        if not dest_channel_id:
            return
        dest_channel = guild_b.get_channel(dest_channel_id)
        if not dest_channel:
            return

        # Embed 作成
        description = message.content
        if message.channel.id not in channel_mapping:
            description = f"**元チャンネル:** {message.channel.name}\n{message.content}"

        embed = discord.Embed(description=description, color=discord.Color.blue())
        embed.set_author(
            name=message.author.display_name,
            icon_url=message.author.avatar.url if message.author.avatar else None
        )

        # 添付画像を Embed に
        first_image = next((a.url for a in message.attachments
                            if a.content_type and a.content_type.startswith("image/")), None)
        if first_image:
            embed.set_image(url=first_image)

        await dest_channel.send(embed=embed)

        # その他添付ファイル
        for attach in message.attachments:
            if attach.url != first_image:
                await dest_channel.send(attach.url)

        # 役職メンション
        if message.role_mentions:
            mentions = []
            for role in message.role_mentions:
                target_role = discord.utils.get(guild_b.roles, name=role.name)
                if target_role:
                    mentions.append(target_role.mention)
            if mentions:
                await dest_channel.send(" ".join(mentions))

        # メッセージ内 URL
        urls = [word for word in message.content.split() if word.startswith("http")]
        for url in urls:
            await dest_channel.send(url)

        await self.bot.process_commands(message)


# Cog セットアップ
async def setup(bot: commands.Bot):
    config_manager = getattr(bot, "config_manager", None)
    if not config_manager:
        raise RuntimeError("ConfigManager が bot にセットされていません")
    await bot.add_cog(TransferCog(bot, config_manager))
