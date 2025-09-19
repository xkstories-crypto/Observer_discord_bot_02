import discord
from discord.ext import commands

class LoggingCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        log_channel_id = 1234567890  # ← config.py から import しても良い
        channel = self.bot.get_channel(log_channel_id)
        if channel:
            await channel.send(f"[{message.author}] {message.content}")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        log_channel_id = 1234567890
        channel = self.bot.get_channel(log_channel_id)
        if channel:
            if before.channel != after.channel:
                await channel.send(f"{member} moved from {before.channel} to {after.channel}")

async def setup(bot):
    await bot.add_cog(LoggingCog(bot))
