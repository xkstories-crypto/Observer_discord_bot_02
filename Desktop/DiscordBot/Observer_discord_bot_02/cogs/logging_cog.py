# cogs/logging_cog.py
import discord
from discord.ext import commands
from config_manager import ConfigManager

class LoggingCog(commands.Cog):
    def __init__(self, bot: commands.Bot, config_manager: ConfigManager):
        self.bot = bot
        self.config_manager = config_manager

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        server_config = self.config_manager.get_server_config(message.guild.id)
        if not server_config:
            return

        log_channel_id = server_config.get("LOG_CHANNEL")
        if not log_channel_id:
            return

        channel = self.bot.get_channel(log_channel_id)
        if channel:
            await channel.send(f"[{message.author.display_name}] {message.content}")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if not member.guild:
            return

        server_config = self.config_manager.get_server_config(member.guild.id)
        if not server_config:
            return

        log_channel_id = server_config.get("LOG_CHANNEL")
        if not log_channel_id:
            return

        if before.channel != after.channel:
            channel = self.bot.get_channel(log_channel_id)
            if channel:
                before_name = before.channel.name if before.channel else "なし"
                after_name = after.channel.name if after.channel else "なし"
                await channel.send(f"{member.display_name} moved from {before_name} to {after_name}")

# ---------- Cogセットアップ ----------
async def setup(bot: commands.Bot):
    config_manager = getattr(bot, "config_manager", None)
    if not config_manager:
        raise RuntimeError("ConfigManager が bot にセットされていません")
    await bot.add_cog(LoggingCog(bot, config_manager))
