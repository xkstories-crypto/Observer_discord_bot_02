# 修正版 transfer_cog.py
from discord.ext import commands
import discord

class TransferCog(commands.Cog):
    def __init__(self, bot: commands.Bot, config_manager):
        self.bot = bot
        self.config_manager = config_manager
        print("[DEBUG] TransferCog loaded")

    async def send_debug(self, text: str, fallback_channel: discord.TextChannel):
        await self.bot.wait_until_ready()
        try:
            await fallback_channel.send(f"[DEBUG] {text}")
        except Exception as e:
            print(f"[DEBUG ERROR] {e}")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        await self.send_debug(
            f"受信: guild={message.guild.name} ({message.guild.id}), channel={message.channel.name} ({message.channel.id}), author={message.author.display_name}, content={message.content}",
            fallback_channel=message.channel
        )

        # サーバーペアを取得（Aサーバーから探す）
        pair = self.config_manager.get_pair_by_a(message.guild.id)
        if not pair:
            await self.bot.process_commands(message)
            return

        # CHANNEL_MAPPINGから転送先チャンネルを取得
        dest_id = pair["CHANNEL_MAPPING"].get(str(message.channel.id))
        if not dest_id:
            await self.bot.process_commands(message)
            return

        # Bサーバーと転送先チャンネルを取得
        dest_guild = self.bot.get_guild(pair["B_ID"])
        dest_channel = dest_guild.get_channel(dest_id) if dest_guild else None
        if not dest_channel:
            await self.bot.process_commands(message)
            return

        try:
            await dest_channel.send(f"[転送] {message.author.display_name}: {message.content}")
            await self.send_debug(f"転送完了: {message.channel.id} → {dest_channel.id}", fallback_channel=message.channel)
        except Exception as e:
            await self.send_debug(f"転送失敗: {e}", fallback_channel=message.channel)

        await self.bot.process_commands(message)

    @commands.command(name="debug_test")
    async def debug_test(self, ctx):
        await self.send_debug("⚡デバッグ送信テスト⚡", fallback_channel=ctx.channel)
        await ctx.send("デバッグ送信を実行しました")

async def setup(bot: commands.Bot):
    config_manager = getattr(bot, "config_manager", None)
    if not config_manager:
        raise RuntimeError("ConfigManager が bot にセットされていません")
    await bot.add_cog(TransferCog(bot, config_manager))
