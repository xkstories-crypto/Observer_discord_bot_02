from discord.ext import commands
import discord
from config_manager import ConfigManager

class TransferCog(commands.Cog):
    def __init__(self, bot: commands.Bot, config_manager: ConfigManager):
        self.bot = bot
        self.config_manager = config_manager
        print("[DEBUG] TransferCog loaded")

    async def send_debug(self, text: str, fallback_channel: discord.TextChannel):
        """その場でデバッグ表示"""
        await self.bot.wait_until_ready()
        try:
            await fallback_channel.send(f"[DEBUG] {text}")
        except Exception as e:
            print(f"[DEBUG ERROR] {e}")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        pair = self.config_manager.get_pair_by_guild(message.guild.id)
        if not pair:
            await self.send_debug("このサーバーはペア登録されていません。", message.channel)
            return

        # 転送方向決定
        if message.guild.id == pair["A_ID"]:
            dest_guild = self.bot.get_guild(pair["B_ID"])
            mapping = pair["CHANNEL_MAPPING"]["A_TO_B"]
        else:
            dest_guild = self.bot.get_guild(pair["A_ID"])
            mapping = pair["CHANNEL_MAPPING"]["B_TO_A"]

        if not dest_guild:
            await self.send_debug("転送先サーバーが見つかりません。", message.channel)
            return

        dest_channel_id = mapping.get(str(message.channel.id))
        if not dest_channel_id:
            await self.send_debug(f"転送先チャンネルが存在しません ({message.channel.id})", message.channel)
            return

        dest_channel = dest_guild.get_channel(dest_channel_id)
        if not dest_channel:
            await self.send_debug("転送先チャンネル取得失敗。", message.channel)
            return

        await dest_channel.send(f"[転送] {message.author.display_name}: {message.content}")
        await self.send_debug(f"転送成功: {message.channel.id} → {dest_channel.id}", message.channel)
