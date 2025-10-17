# transfer_cog.py
from discord.ext import commands
import discord
import asyncio

class TransferCog(commands.Cog):
    def __init__(self, bot: commands.Bot, config_manager):
        self.bot = bot
        self.config_manager = config_manager
        # Cogロード時のデバッグメッセージ
        asyncio.create_task(self.send_load_debug())

    async def send_load_debug(self):
        # fallback_channelなしでも print で確認可能
        await self.config_manager.send_debug("[DEBUG] TransferCog loaded")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        # デバッグ必ず返す
        await self.config_manager.send_debug(
            f"[DEBUG] メッセージ受信: {message.guild.name}({message.guild.id}) "
            f"#{message.channel.name}({message.channel.id}) {message.author.display_name}: {message.content}",
            fallback_channel=message.channel
        )

        pair = self.config_manager.get_pair_by_a(message.guild.id)
        if not pair:
            await message.channel.send("⚠️ 転送ペア未登録")
            await self.bot.process_commands(message)
            return

        dest_id = pair.get("CHANNEL_MAPPING", {}).get(str(message.channel.id))
        if not dest_id:
            await message.channel.send("⚠️ 転送先未設定")
            await self.bot.process_commands(message)
            return

        dest_guild = self.bot.get_guild(pair.get("B_ID"))
        if not dest_guild:
            await message.channel.send(f"⚠️ Bサーバーが見つかりません(ID:{pair.get('B_ID')})")
            await self.bot.process_commands(message)
            return

        dest_channel = dest_guild.get_channel(dest_id)
        if not dest_channel:
            await message.channel.send(f"⚠️ 転送先チャンネルが見つかりません(ID:{dest_id})")
            await self.bot.process_commands(message)
            return

        # 転送
        try:
            content = message.content.strip()
            if content:
                await dest_channel.send(f"[転送] {message.author.display_name}: {content}")
                await message.channel.send(f"✅ 転送完了 → {dest_channel.name}({dest_channel.id})")
                await self.config_manager.send_debug(
                    f"[DEBUG] 転送成功: {message.channel.id} → {dest_channel.id}",
                    fallback_channel=message.channel
                )
        except Exception as e:
            await message.channel.send(f"⚠️ 転送失敗: {e}")
            await self.config_manager.send_debug(f"[DEBUG] 転送失敗: {e}", fallback_channel=message.channel)

        await self.bot.process_commands(message)

    @commands.command(name="debug_test")
    async def debug_test(self, ctx: commands.Context):
        """デバッグ送信テスト"""
        await self.config_manager.send_debug(
            "⚡デバッグ送信テスト⚡", fallback_channel=ctx.channel
        )
        await ctx.send("✅ デバッグ送信完了")

async def setup(bot: commands.Bot):
    config_manager = getattr(bot, "config_manager", None)
    if not config_manager:
        raise RuntimeError("ConfigManager が bot にセットされていません")
    await bot.add_cog(TransferCog(bot, config_manager))
