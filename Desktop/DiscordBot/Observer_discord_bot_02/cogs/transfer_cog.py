import discord
from discord.ext import commands
from config import SERVER_A_ID, SERVER_B_ID, CHANNEL_MAPPING

class TransferCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        if message.guild.id != SERVER_A_ID:
            await self.bot.process_commands(message)
            return

        guild_b = self.bot.get_guild(SERVER_B_ID)
        dest_channel_id = CHANNEL_MAPPING.get(message.channel.id, CHANNEL_MAPPING.get("a_other"))
        dest_channel = guild_b.get_channel(dest_channel_id) if guild_b else None

        if dest_channel:
            embed = discord.Embed(description=message.content, color=discord.Color.blue())
            embed.set_author(
                name=message.author.display_name,
                icon_url=message.author.avatar.url if message.author.avatar else None
            )

            # 画像だけEmbedに
            first_image = next((a.url for a in message.attachments if a.content_type and a.content_type.startswith("image/")), None)
            if first_image:
                embed.set_image(url=first_image)

            await dest_channel.send(embed=embed)

            # 動画や残りの添付ファイルは普通に送信
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

        await self.bot.process_commands(message)

async def setup(bot):
    await bot.add_cog(TransferCog(bot))
