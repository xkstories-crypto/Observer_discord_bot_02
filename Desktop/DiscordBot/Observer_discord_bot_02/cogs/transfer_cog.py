# transfer_cog.py
from discord.ext import commands
import discord
import asyncio

class TransferCog(commands.Cog):
    def __init__(self, bot: commands.Bot, config_manager):
        self.bot = bot
        self.config_manager = config_manager
        # Cogロード時にDEBUG送信
        asyncio.create_task(self.config_manager.send_debug("[DEBUG] TransferCog loaded"))

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Aサーバー→Bサーバーのメッセージ転送処理"""
        if message.author.bot or not message.guild:
            return

        await self.config_manager.send_debug(
            f"受信: guild={message.guild.name} ({message.guild.id}), "
            f"channel={message.channel.name} ({message.channel.id}), "
            f"author={message.author.display_name}, content={message.content}",
            fallback_channel=message.channel
        )

        # サーバーペアを取得（AサーバーIDで）
        pair = self.config_manager.get_pair_by_a(message.guild.id)
        if not pair:
            await message.channel.send("⚠️ このサーバーは転送ペアに登録されていません。")
            await self.bot.process_commands(message)
            return

        # 転送先チャンネルIDを取得
        dest_id = pair.get("CHANNEL_MAPPING", {}).get(str(message.channel.id))
        if not dest_id:
            await message.channel.send("⚠️ このチャンネルには対応する転送先が設定されていません。")
            await self.bot.process_commands(message)
            return

        dest_guild = self.bot.get_guild(pair.get("B_ID"))
        if not dest_guild:
            await message.channel.send(f"⚠️ Bサーバーが見つかりません（ID: {pair.get('B_ID')}）")
            await self.bot.process_commands(message)
            return

        dest_channel = dest_guild.get_channel(dest_id)
        if not dest_channel:
            await message.channel.send(f"⚠️ 転送先チャンネルが見つかりません（ID: {dest_id}）")
            await self.bot.process_commands(message)
            return

        await self.config_manager.send_debug(
            f"転送先チャンネル取得: {dest_channel.name} ({dest_channel.id})",
            fallback_channel=message.channel
        )

        # ---------------------- 転送処理 ----------------------
        try:
            # 1. message.content がある場合 → Embed 送信
            if message.content.strip():
                embed = discord.Embed(description=message.content)
                embed.set_author(
                    name=message.author.display_name,
                    icon_url=message.author.display_avatar.url
                )
                await dest_channel.send(embed=embed)
                await self.config_manager.send_debug(
                    f"テキスト転送完了: {message.channel.id} → {dest_channel.id}",
                    fallback_channel=message.channel
                )

            # 2. 添付ファイルは Embed とは別で送信
            for att in message.attachments:
                file = await att.to_file()
                await dest_channel.send(file=file)
                await self.config_manager.send_debug(
                    f"添付ファイル転送完了: {att.filename}",
                    fallback_channel=message.channel
                )

        except Exception as e:
            await message.channel.send(f"⚠️ 転送失敗: {e}")
            await self.config_manager.send_debug(f"転送失敗: {e}", fallback_channel=message.channel)

        await self.bot.process_commands(message)

    @commands.command(name="debug_test")
    async def debug_test(self, ctx: commands.Context):
        """デバッグ送信テストコマンド"""
        await self.config_manager.send_debug("⚡デバッグ送信テスト⚡", fallback_channel=ctx.channel)
        await ctx.send("デバッグ送信を実行しました ✅")

async def setup(bot: commands.Bot):
    """Cogセットアップ"""
    config_manager = getattr(bot, "config_manager", None)
    if not config_manager:
        raise RuntimeError("ConfigManager が bot にセットされていません")
    await bot.add_cog(TransferCog(bot, config_manager))
