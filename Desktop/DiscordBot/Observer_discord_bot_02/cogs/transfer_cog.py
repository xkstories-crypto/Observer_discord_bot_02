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

        # デバッグ表示（必ずそのチャンネルに返す）
        await self.send_debug(
            f"受信: {message.guild.name} ({message.guild.id}) | {message.channel.name} ({message.channel.id}) | {message.content}",
            fallback_channel=message.channel
        )

        # 設定取得
        server_conf = self.config_manager.get_server_config_by_message(message)
        if not server_conf:
            await self.send_debug("サーバー設定が見つからなかった → commandsへ渡す", fallback_channel=message.channel)
            await self.bot.process_commands(message)
            return

        server_a_id = server_conf.get("SERVER_A_ID")
        server_b_id = server_conf.get("SERVER_B_ID")
        channel_mapping = server_conf.get("CHANNEL_MAPPING", {})

        # サーバーA以外は無視
        if message.guild.id != server_a_id:
            await self.send_debug("このサーバーはAじゃない → commandsへ渡す", fallback_channel=message.channel)
            await self.bot.process_commands(message)
            return

        # サーバーB取得
        guild_b = self.bot.get_guild(server_b_id)
        if not guild_b:
            await self.send_debug("Bサーバーが見つからない", fallback_channel=message.channel)
            await self.bot.process_commands(message)
            return

        # 転送先チャンネル
        dest_channel_id = channel_mapping.get(str(message.channel.id))
        if not dest_channel_id:
            await self.send_debug(f"チャンネルマッピングが存在しない: {message.channel.id}", fallback_channel=message.channel)
            await self.bot.process_commands(message)
            return

        dest_channel = guild_b.get_channel(dest_channel_id)
        if not dest_channel:
            await self.send_debug(f"転送先チャンネルが取得できない: {dest_channel_id}", fallback_channel=message.channel)
            await self.bot.process_commands(message)
            return

        # 転送（テキストのみ）
        try:
            await dest_channel.send(f"[転送] {message.author.display_name}: {message.content}")
            await self.send_debug(f"転送完了: {message.channel.id} → {dest_channel.id}", fallback_channel=message.channel)
        except Exception as e:
            await self.send_debug(f"転送失敗: {e}", fallback_channel=message.channel)

        await self.bot.process_commands(message)

    @commands.command(name="debug_test")
    async def debug_test(self, ctx):
        """デバッグ送信テスト"""
        await self.send_debug("⚡デバッグ送信テスト⚡", fallback_channel=ctx.channel)
        await ctx.send("デバッグ送信を実行しました")


async def setup(bot: commands.Bot):
    config_manager = getattr(bot, "config_manager", None)
    if not config_manager:
        raise RuntimeError("ConfigManager が bot にセットされていません")
    await bot.add_cog(TransferCog(bot, config_manager))
