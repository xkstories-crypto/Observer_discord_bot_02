# transfer_cog.py
from discord.ext import commands
import discord
import asyncio

class TransferCog(commands.Cog):
    def __init__(self, bot: commands.Bot, config_manager):
        self.bot = bot
        self.config_manager = config_manager
        # Cogロード時にDEBUG送信
        asyncio.create_task(self.send_debug("[DEBUG] TransferCog loaded"))

    async def send_debug(self, message: str, fallback_channel: discord.TextChannel = None):
        """DEBUGメッセージを送信。fallback_channel がなければ ConfigManager の DEBUG_CHANNEL を使う"""
        target_channel = fallback_channel
        if not target_channel:
            # ConfigManager の DEBUG_CHANNEL を探す
            for pair in self.config_manager.config.get("server_pairs", []):
                debug_id = pair.get("DEBUG_CHANNEL")
                if debug_id:
                    target_channel = self.bot.get_channel(debug_id)
                    break

        if target_channel:
            try:
                await target_channel.send(f"[DEBUG] {message}")
            except Exception as e:
                print(f"[DEBUG送信失敗] {message} ({e})")
        else:
            print(f"[DEBUG] {message} (チャンネル未設定)")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Aサーバー→Bサーバーのメッセージ転送処理"""
        if message.author.bot or not message.guild:
            return

        await self.send_debug(
            f"受信: guild={message.guild.name} ({message.guild.id}), "
            f"channel={message.channel.name} ({message.channel.id}), "
            f"author={message.author.display_name}, content={message.content}",
            fallback_channel=message.channel
        )

        # サーバーペアを取得（AサーバーIDで）
        pair = self.config_manager.get_pair_by_a(message.guild.id)
        if not pair:
            await self.send_debug(f"このサーバーは転送ペアに登録されていません", fallback_channel=message.channel)
            await self.bot.process_commands(message)
            return

        await self.send_debug(f"ペア取得: A_ID={pair.get('A_ID')} → B_ID={pair.get('B_ID')}", fallback_channel=message.channel)

        # 転送先チャンネルIDを取得
        dest_id = pair.get("CHANNEL_MAPPING", {}).get(str(message.channel.id))
        if not dest_id:
            await self.send_debug("このチャンネルには対応する転送先が設定されていません", fallback_channel=message.channel)
            await self.bot.process_commands(message)
            return

        await self.send_debug(f"転送先チャンネルID: {dest_id}", fallback_channel=message.channel)

        # Bサーバーと転送先チャンネルを取得
        dest_guild = self.bot.get_guild(pair.get("B_ID"))
        if not dest_guild:
            await self.send_debug(f"Bサーバーが見つかりません（ID: {pair.get('B_ID')}）", fallback_channel=message.channel)
            await self.bot.process_commands(message)
            return

        dest_channel = dest_guild.get_channel(dest_id)
        if not dest_channel:
            await self.send_debug(f"転送先チャンネルが見つかりません（ID: {dest_id}）", fallback_channel=message.channel)
            await self.bot.process_commands(message)
            return

        await self.send_debug(f"転送先チャンネル取得: {dest_channel.name} ({dest_channel.id})", fallback_channel=message.channel)

        # 転送処理
        try:
            content = message.content.strip()
            if not content:
                await self.send_debug("空メッセージのため転送しません", fallback_channel=message.channel)
                return
            await dest_channel.send(f"[転送] {message.author.display_name}: {content}")
            await self.send_debug(f"転送完了 → {dest_channel.name} ({dest_channel.id})", fallback_channel=message.channel)
        except Exception as e:
            await self.send_debug(f"転送失敗: {e}", fallback_channel=message.channel)

        await self.bot.process_commands(message)

    @commands.command(name="debug_test")
    async def debug_test(self, ctx: commands.Context):
        """デバッグ送信テストコマンド"""
        await self.send_debug("⚡デバッグ送信テスト⚡", fallback_channel=ctx.channel)
        await ctx.send("デバッグ送信を実行しました ✅")

async def setup(bot: commands.Bot):
    """Cogセットアップ"""
    config_manager = getattr(bot, "config_manager", None)
    if not config_manager:
        raise RuntimeError("ConfigManager が bot にセットされていません")
    await bot.add_cog(TransferCog(bot, config_manager))
