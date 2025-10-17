# transfer_cog.py
from discord.ext import commands
import discord
import asyncio

class TransferCog(commands.Cog):
    def __init__(self, bot: commands.Bot, config_manager):
        self.bot = bot
        self.config_manager = config_manager
        # 起動時はコンソールに出すだけ
        print("[DEBUG] TransferCog loaded")

    async def send_debug(self, message: str, channel: discord.TextChannel):
        """必ず指定したチャンネルにデバッグを送る"""
        try:
            await channel.send(f"[DEBUG] {message}")
        except Exception as e:
            print(f"[DEBUG送信失敗] {message} ({e})")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        # デバッグ表示
        await self.send_debug(
            f"受信: guild={message.guild.name} ({message.guild.id}), "
            f"channel={message.channel.name} ({message.channel.id}), "
            f"author={message.author.display_name}, content={message.content}",
            message.channel
        )

        # 以降は既存の転送処理を同様に message.channel をデバッグ出力先として使う
        pair = self.config_manager.get_pair_by_a(message.guild.id)
        if not pair:
            await self.send_debug("このサーバーは転送ペアに登録されていません", message.channel)
            await self.bot.process_commands(message)
            return

        dest_id = pair.get("CHANNEL_MAPPING", {}).get(str(message.channel.id))
        if not dest_id:
            await self.send_debug("転送先チャンネル未設定", message.channel)
            await self.bot.process_commands(message)
            return

        dest_guild = self.bot.get_guild(pair.get("B_ID"))
        if not dest_guild:
            await self.send_debug(f"Bサーバーが見つかりません（ID: {pair.get('B_ID')}）", message.channel)
            await self.bot.process_commands(message)
            return

        dest_channel = dest_guild.get_channel(dest_id)
        if not dest_channel:
            await self.send_debug(f"転送先チャンネルが見つかりません（ID: {dest_id}）", message.channel)
            await self.bot.process_commands(message)
            return

        try:
            content = message.content.strip()
            if content:
                await dest_channel.send(f"[転送] {message.author.display_name}: {content}")
                await self.send_debug(f"転送完了: {message.channel.id} → {dest_channel.id}", message.channel)
        except Exception as e:
            await self.send_debug(f"転送失敗: {e}", message.channel)

        await self.bot.process_commands(message)

    @commands.command(name="debug_test")
    async def debug_test(self, ctx: commands.Context):
        await self.send_debug("⚡デバッグ送信テスト⚡", ctx.channel)
        await ctx.send("デバッグ送信を実行しました ✅")
