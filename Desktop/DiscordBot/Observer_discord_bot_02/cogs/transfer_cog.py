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
    async def on_message(self, message):
        print(f"[DEBUG] on_message triggered: guild={getattr(message.guild, 'name', None)}, "
              f"guild_id={getattr(message.guild, 'id', None)}, "
              f"channel={getattr(message.channel, 'name', None)}, "
              f"channel_id={getattr(message.channel, 'id', None)}, "
              f"author={message.author}, bot={message.author.bot}")

        # BotメッセージやDMは無視
        if message.author.bot or not message.guild:
            print("[DEBUG] Ignored: bot message or no guild")
            return

        # サーバー設定取得
        server_conf = self.config_manager.get_server_config(message.guild.id)
        if not server_conf:
            print("[DEBUG] Ignored: no server config for this guild")
            await self.bot.process_commands(message)
            return

        server_a_id = server_conf.get("SERVER_A_ID")
        server_b_id = server_conf.get("SERVER_B_ID")
        channel_mapping = server_conf.get("CHANNEL_MAPPING", {})
        other_channel_id = server_conf.get("OTHER_CHANNEL")

        # intにキャスト
        try:
            server_a_id = int(server_a_id)
            server_b_id = int(server_b_id)
        except (TypeError, ValueError):
            print("[DEBUG] server_a_id or server_b_id not set or invalid")
            await self.bot.process_commands(message)
            return

        print(f"[DEBUG] server_a_id={server_a_id}, server_b_id={server_b_id}")

        # SERVER_A_ID以外のメッセージは無視
        if message.guild.id != server_a_id:
            print("[DEBUG] Ignored: message not from SERVER_A_ID")
            await self.bot.process_commands(message)
            return

        # SERVER_B取得
        guild_b = self.bot.get_guild(server_b_id)
        if not guild_b:
            print("[DEBUG] Guild B not found")
            await self.bot.process_commands(message)
            return

        # 転送先チャンネルID取得
        dest_channel_id = channel_mapping.get(str(message.channel.id)) \
                          or channel_mapping.get(message.channel.id) \
                          or other_channel_id

        if not dest_channel_id:
            print("[DEBUG] Dest channel ID not found for this message")
            await self.bot.process_commands(message)
            return

        dest_channel = guild_b.get_channel(dest_channel_id)
        if not dest_channel:
            print("[DEBUG] Dest channel object not found")
            await self.bot.process_commands(message)
            return

        print(f"[DEBUG] Dest channel found: {dest_channel.name} ({dest_channel.id})")

        # Embed作成
        description = message.content
        if str(message.channel.id) not in channel_mapping:
            description = f"**元チャンネル:** {message.channel.name}\n{message.content}"

        embed = discord.Embed(description=description, color=discord.Color.blue())
        embed.set_author(
            name=message.author.display_name,
            icon_url=message.author.avatar.url if message.author.avatar else None
        )

        # 画像添付をEmbedに
        first_image = next((a.url for a in message.attachments
                            if a.content_type and a.content_type.startswith("image/")), None)
        if first_image:
            embed.set_image(url=first_image)

        # Embed送信
        await dest_channel.send(embed=embed)
        print(f"[DEBUG] Embed sent to {dest_channel.name}")

        # 残りの添付ファイル
        for attach in message.attachments:
            if attach.url != first_image:
                await dest_channel.send(attach.url)
                print(f"[DEBUG] Attachment sent: {attach.url}")

        # 役職メンション
        if message.role_mentions:
            mentions = []
            for role in message.role_mentions:
                target_role = discord.utils.get(guild_b.roles, name=role.name)
                if target_role:
                    mentions.append(target_role.mention)
            if mentions:
                await dest_channel.send(" ".join(mentions))
                print(f"[DEBUG] Roles mentioned: {' '.join(mentions)}")

        # メッセージ内URL
        urls = [word for word in message.content.split() if word.startswith("http")]
        for url in urls:
            await dest_channel.send(url)
            print(f"[DEBUG] URL sent: {url}")

        await self.bot.process_commands(message)


async def setup(bot: commands.Bot):
    config_manager = getattr(bot, "config_manager", None)
    if not config_manager:
        raise RuntimeError("ConfigManager が bot にセットされていません")
    await bot.add_cog(TransferCog(bot, config_manager))
