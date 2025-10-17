# transfer_cog.py
from discord.ext import commands
import discord

class TransferCog(commands.Cog):
    def __init__(self, bot: commands.Bot, config_manager):
        self.bot = bot
        self.config_manager = config_manager
        print("[DEBUG] TransferCog loaded")

    async def send_debug(self, text: str, fallback_channel: discord.TextChannel = None):
        """デバッグメッセージを送信（失敗時はコンソール出力）"""
        await self.bot.wait_until_ready()
        try:
            if fallback_channel:
                await fallback_channel.send(f"[DEBUG] {text}")
            else:
                print(f"[DEBUG LOG] {text}")
        except Exception as e:
            print(f"[DEBUG ERROR] {e}")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Aサーバー→Bサーバーのメッセージ転送処理"""
        if message.author.bot or not message.guild:
            return

        # 受信メッセージを受信チャンネルに出力
        debug_msg = (
            f"受信: guild={message.guild.name} ({message.guild.id}), "
            f"channel={message.channel.name} ({message.channel.id}), "
            f"author={message.author.display_name}, content={message.content}"
        )
        await self.send_debug(debug_msg, fallback_channel=message.channel)

        # サーバーペアを取得
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

        # Bサーバーと転送先チャンネルを取得
        dest_guild = self.bot.get_guild(pair.get("B_ID"))
        dest_channel = dest_guild.get_channel(dest_id) if dest_guild else None
        if not dest_channel:
            await message.channel.send(f"⚠️ 転送先チャンネルが見つかりません（ID: {dest_id}）")
            await self.bot.process_commands(message)
            return

        # 転送処理
        try:
            content = message.content.strip()
            if not content:
                return  # 空メッセージは転送しない

            # Bサーバーに転送
            await dest_channel.send(f"[転送] {message.author.display_name}: {content}")

            # 受信チャンネルにも転送完了通知
            await message.channel.send(f"✅ 転送完了 → {dest_channel.name} ({dest_channel.id})")

            # デバッグログ
            await self.send_debug(
                f"転送完了: {message.channel.id} → {dest_channel.id}",
                fallback_channel=message.channel
            )
        except Exception as e:
            await message.channel.send(f"⚠️ 転送失敗: {e}")
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
