# cogs/transfer_cog_b_only.py
from discord.ext import commands
import discord
from config_manager import ConfigManager

class TransferCogBOnly(commands.Cog):
    def __init__(self, bot: commands.Bot, config_manager: ConfigManager):
        self.bot = bot
        self.config_manager = config_manager
        print("[DEBUG] TransferCogBOnly loaded")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return

        # Bサーバー側で設定されている全設定を取得
        all_configs = self.config_manager.get_all_configs()  # サーバー単位ではなく全体取得
        for conf in all_configs.values():
            try:
                server_a_id = int(conf.get("SERVER_A_ID"))
                server_b_id = int(conf.get("SERVER_B_ID"))
                channel_mapping = conf.get("CHANNEL_MAPPING", {})
            except Exception:
                continue

            # メッセージのサーバーIDがAサーバーIDと一致する場合に転送
            if message.guild.id != server_a_id:
                continue

            guild_b = self.bot.get_guild(server_b_id)
            if not guild_b:
                continue

            dest_channel_id = channel_mapping.get(str(message.channel.id), channel_mapping.get("a_other"))
            dest_channel = guild_b.get_channel(int(dest_channel_id)) if dest_channel_id else None
            if not dest_channel:
                continue

            # Embed作成
            description = message.content
            if str(message.channel.id) not in channel_mapping:
                description = f"**元チャンネル:** {message.channel.name}\n{message.content}"

            embed = discord.Embed(description=description, color=discord.Color.blue())
            embed.set_author(
                name=message.author.display_name,
                icon_url=message.author.avatar.url if message.author.avatar else None
            )

            first_image = next((a.url for a in message.attachments
                                if a.content_type and a.content_type.startswith("image/")), None)
            if first_image:
                embed.set_image(url=first_image)

            await dest_channel.send(embed=embed)

            # 残り添付
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

            # URL送信
            urls = [word for word in message.content.split() if word.startswith("http")]
            for url in urls:
                await dest_channel.send(url)

        await self.bot.process_commands(message)

# Cogセットアップ
async def setup(bot: commands.Bot):
    config_manager = getattr(bot, "config_manager", None)
    if not config_manager:
        raise RuntimeError("ConfigManager が bot にセットされていません")
    await bot.add_cog(TransferCogBOnly(bot, config_manager))
