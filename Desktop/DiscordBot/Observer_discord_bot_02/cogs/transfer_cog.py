# cogs/transfer_cog.py
from discord.ext import commands
import discord
from config_manager import ConfigManager

class TransferCog(commands.Cog):
    def __init__(self, bot: commands.Bot, config_manager: ConfigManager):
        self.bot = bot
        self.config_manager = config_manager

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return

        # 設定取得
        server_conf = self.config_manager.get_server_config(message.guild.id)
        server_a_id = server_conf.get("SERVER_A_ID")
        server_b_id = server_conf.get("SERVER_B_ID")
        channel_mapping = server_conf.get("CHANNEL_MAPPING", {})

        # Aサーバー以外は無視
        if message.guild.id != server_a_id:
            await self.bot.process_commands(message)
            return

        # Bサーバー取得
        guild_b = self.bot.get_guild(server_b_id)
        if not guild_b:
            print("Guild B not found")
            await self.bot.process_commands(message)
            return

        # 送信先チャンネル取得
        dest_channel_id = channel_mapping.get(str(message.channel.id), channel_mapping.get("a_other"))
        print(f"Source: {message.channel.name} ({message.channel.id}) -> Dest: {dest_channel_id}")

        dest_channel = guild_b.get_channel(dest_channel_id) if dest_channel_id else None
        if not dest_channel:
            print("Dest channel not found in B server")
            await self.bot.process_commands(message)
            return

        # Embed作成
        description = message.content
        if str(message.channel.id) not in channel_mapping:
            description = f"**元チャンネル:** {message.channel.name}\n{message.content}"

        embed = discord.Embed(description=description, color=discord.Color.blue())
        embed.set_author(
            name=message.author.display_name,
            icon_url=message.author.avatar.url if message.author.avatar else None
        )

        # 添付画像をEmbedに
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

        # メッセージ内URLも個別送信
        urls = [word for word in message.content.split() if word.startswith("http")]
        for url in urls:
            await dest_channel.send(url)

        # 最後にコマンド処理
        await self.bot.process_commands(message)


# ---------- Cogセットアップ ----------
async def setup(bot: commands.Bot):
    config_manager = getattr(bot, "config_manager", None)
    if not config_manager:
        raise RuntimeError("ConfigManager が bot にセットされていません")
    await bot.add_cog(TransferCog(bot, config_manager))
