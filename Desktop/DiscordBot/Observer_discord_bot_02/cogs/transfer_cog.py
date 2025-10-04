from discord.ext import commands
import discord
from config_manager import ConfigManager

class TransferCog(commands.Cog):
    def __init__(self, bot: commands.Bot, config_manager: ConfigManager):
        self.bot = bot
        self.config_manager = config_manager
        print("[DEBUG] TransferCog (A→B only) loaded")

    async def send_debug(self, text: str, fallback_channel: discord.TextChannel):
        try:
            await fallback_channel.send(f"[DEBUG] {text}")
        except Exception as e:
            print(f"[DEBUG ERROR] {e}")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        await self.send_debug(
            f"受信: {message.guild.name} ({message.guild.id}) | {message.channel.name} ({message.channel.id}) | {message.content}",
            fallback_channel=message.channel
        )

        # Aサーバー設定を取得
        config = self.config_manager.get_server_config(message.guild.id)
        if not config:
            await self.send_debug("このサーバーはAサーバーとして登録されていません", message.channel)
            return

        dest_guild_id = config.get("DEST_SERVER_ID")
        mapping = config.get("CHANNEL_MAPPING", {})

        dest_channel_id = mapping.get(str(message.channel.id))
        if not dest_channel_id:
            await self.send_debug("このチャンネルは転送対象ではありません", message.channel)
            return

        dest_guild = self.bot.get_guild(dest_guild_id)
        if not dest_guild:
            await self.send_debug("転送先サーバーが見つかりません", message.channel)
            return

        dest_channel = dest_guild.get_channel(dest_channel_id)
        if not dest_channel:
            await self.send_debug(f"転送先チャンネルが見つからない: {dest_channel_id}", message.channel)
            return

        # 転送
        try:
            await dest_channel.send(f"[転送] {message.author.display_name}: {message.content}")
            await self.send_debug(f"転送成功: {message.channel.name} → {dest_channel.name}", message.channel)
        except Exception as e:
            await self.send_debug(f"転送失敗: {e}", message.channel)

    @commands.command(name="debug_test")
    async def debug_test(self, ctx):
        await self.send_debug("⚡デバッグ送信テスト⚡", ctx.channel)
        await ctx.send("デバッグ送信を実行しました")


async def setup(bot: commands.Bot):
    config_manager = getattr(bot, "config_manager", None)
    if not config_manager:
        raise RuntimeError("ConfigManager が bot にセットされていません")
    await bot.add_cog(TransferCog(bot, config_manager))
