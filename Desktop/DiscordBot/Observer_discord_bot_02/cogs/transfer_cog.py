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

        pair = self.config_manager.get_pair_by_a(message.guild.id)
        if not pair:
            await self.send_debug("このサーバーは転送ペアに登録されていません", fallback_channel=message.channel)
            await self.bot.process_commands(message)
            return

        dest_id = pair.get("CHANNEL_MAPPING", {}).get(str(message.channel.id))
        if not dest_id:
            await self.send_debug("このチャンネルには対応する転送先が設定されていません", fallback_channel=message.channel)
            await self.bot.process_commands(message)
            return

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

        # ---------------------- 転送処理 ----------------------
        try:
            content = message.content.strip()

            # Embed 内用テキスト作成（メンションは名前だけに置換）
            embed_text = content or " "
            for role in message.role_mentions:
                embed_text = embed_text.replace(f"<@&{role.id}>", f"@{role.name}")
            for user in message.mentions:
                embed_text = embed_text.replace(f"<@{user.id}>", f"@{user.display_name}")

            # 1. Embed送信（テキスト・リンク・見た目用メンション）
            if embed_text.strip():
                embed = discord.Embed(description=embed_text)
                embed.set_author(name=message.author.display_name, icon_url=message.author.display_avatar.url)
                await dest_channel.send(embed=embed)
                await self.send_debug(f"Embed転送完了: {message.channel.id} → {dest_channel.id}", fallback_channel=message.channel)

            # 2. 添付ファイルは別で転送
            for att in message.attachments:
                file = await att.to_file()
                await dest_channel.send(file=file)
                await self.send_debug(f"添付ファイル転送完了: {att.filename}", fallback_channel=message.channel)

            # 3. 実際のメンション通知は別で送信
            mention_text = ""
            for user in message.mentions:
                mention_text += user.mention + " "
            for role in message.role_mentions:
                mention_text += role.mention + " "
            if mention_text:
                await dest_channel.send(mention_text.strip())
                await self.send_debug(f"メンション通知転送完了: {mention_text}", fallback_channel=message.channel)

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
