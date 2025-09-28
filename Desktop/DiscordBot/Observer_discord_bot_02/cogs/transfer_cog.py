# cogs/transfer_debug_cog.py
from discord.ext import commands
import discord
from config_manager import ConfigManager

class TransferDebugCog(commands.Cog):
    def __init__(self, bot: commands.Bot, config_manager: ConfigManager):
        self.bot = bot
        self.config_manager = config_manager
        print("[DEBUG] TransferDebugCog loaded")

    @commands.Cog.listener()
    async def on_message(self, message):
        # Bot 自身のメッセージは無視
        if message.author.bot or not message.guild:
            return

        # ConfigManager からサーバー設定取得
        server_conf = self.config_manager.get_server_config(message.guild.id)
        if not server_conf:
            await message.channel.send(f"[DEBUG] このサーバーの設定がありません: guild={message.guild.id}")
            return

        server_a_id = server_conf.get("SERVER_A_ID")
        server_b_id = server_conf.get("SERVER_B_ID")
        channel_mapping = server_conf.get("CHANNEL_MAPPING", {})

        # int にキャスト（保存時に文字列だった場合に対応）
        try:
            server_a_id = int(server_a_id)
        except (TypeError, ValueError):
            server_a_id = None
        try:
            server_b_id = int(server_b_id)
        except (TypeError, ValueError):
            server_b_id = None

        debug_text = (
            f"[DEBUG] on_message triggered\n"
            f"guild={message.guild.name} ({message.guild.id})\n"
            f"channel={message.channel.name} ({message.channel.id})\n"
            f"author={message.author} ({message.author.id})\n"
            f"server_a_id={server_a_id}, server_b_id={server_b_id}"
        )
        await message.channel.send(debug_text)

        # SERVER_A_ID チェック
        if message.guild.id != server_a_id:
            await message.channel.send(f"[DEBUG] このメッセージは SERVER_A_ID ではありません。")
            return

        # 転送先ギルド取得
        guild_b = self.bot.get_guild(server_b_id)
        if not guild_b:
            await message.channel.send(f"[DEBUG] SERVER_B_ID のギルドが見つかりません: {server_b_id}")
            return

        # 転送先チャンネル ID 取得
        dest_channel_id = channel_mapping.get(str(message.channel.id), channel_mapping.get("a_other"))
        if not dest_channel_id:
            await message.channel.send(f"[DEBUG] チャンネルマッピングがありません: {message.channel.id}")
            return

        dest_channel = guild_b.get_channel(dest_channel_id)
        if not dest_channel:
            await message.channel.send(f"[DEBUG] 転送先チャンネルが見つかりません: {dest_channel_id}")
            return

        # Embed 作成
        description = message.content
        if str(message.channel.id) not in channel_mapping:
            description = f"**元チャンネル:** {message.channel.name}\n{message.content}"

        embed = discord.Embed(description=description, color=discord.Color.blue())
        embed.set_author(
            name=message.author.display_name,
            icon_url=message.author.avatar.url if message.author.avatar else None
        )

        # 添付画像を Embed に
        first_image = next((a.url for a in message.attachments
                            if a.content_type and a.content_type.startswith("image/")), None)
        if first_image:
            embed.set_image(url=first_image)

        # 転送内容を Discord 上で確認用に送信
        debug_embed_text = f"[DEBUG] Embed 送信予定: {embed.description[:100]}..."  # 長すぎる場合は省略
        await message.channel.send(debug_embed_text)

        # その他添付ファイル
        for attach in message.attachments:
            if attach.url != first_image:
                await message.channel.send(f"[DEBUG] 添付ファイル: {attach.url}")

        # 役職メンション
        if message.role_mentions:
            mentions = [role.name for role in message.role_mentions]
            await message.channel.send(f"[DEBUG] 役職メンション: {', '.join(mentions)}")

        # メッセージ内 URL
        urls = [word for word in message.content.split() if word.startswith("http")]
        if urls:
            await message.channel.send(f"[DEBUG] URL: {', '.join(urls)}")

        # 最後にコマンド処理
        await self.bot.process_commands(message)


# ---------- Cog セットアップ ----------
async def setup(bot: commands.Bot):
    config_manager = getattr(bot, "config_manager", None)
    if not config_manager:
        raise RuntimeError("ConfigManager が bot にセットされていません")
    await bot.add_cog(TransferDebugCog(bot, config_manager))
