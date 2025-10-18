# transfer_cog.py
from discord.ext import commands
import discord
import asyncio
from discord.utils import get

class TransferCog(commands.Cog):
    def __init__(self, bot: commands.Bot, config_manager):
        self.bot = bot
        self.config_manager = config_manager
        try:
            asyncio.create_task(self.config_manager.send_debug("[DEBUG] TransferCog loaded"))
        except Exception:
            print("[DEBUG] TransferCog loaded")

    async def send_debug(self, message: str, fallback_channel: discord.TextChannel = None):
        target_channel = fallback_channel
        if not target_channel:
            try:
                for pair in self.config_manager.config.get("server_pairs", []):
                    debug_id = pair.get("DEBUG_CHANNEL")
                    if debug_id:
                        target_channel = self.bot.get_channel(debug_id)
                        if target_channel:
                            break
            except Exception:
                target_channel = None

        if target_channel:
            try:
                await target_channel.send(f"[DEBUG] {message}")
                return
            except Exception as e:
                print(f"[DEBUG送信失敗] {message} ({e})")

        print(f"[DEBUG] {message} (チャンネル未設定または送信失敗)")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        # --- まずコマンドを優先処理 ---
        ctx = await self.bot.get_context(message)
        if ctx.valid:
            await self.bot.process_commands(message)
            # 転送処理も続けたい場合は return しない
            # return  ← 元の処理を止めたくなければコメントアウト

        await self.send_debug(
            f"受信: guild={message.guild.name} ({message.guild.id}), "
            f"channel={message.channel.name} ({message.channel.id}), "
            f"author={message.author.display_name}, content={message.content}",
            fallback_channel=message.channel
        )

        pair = self.config_manager.get_pair_by_a(message.guild.id)
        if not pair:
            await self.send_debug("このサーバーは転送ペアに登録されていません", fallback_channel=message.channel)
            return  # 転送処理はここで止める

        dest_id = pair.get("CHANNEL_MAPPING", {}).get(str(message.channel.id))
        if not dest_id:
            await self.send_debug("このチャンネルには対応する転送先が設定されていません", fallback_channel=message.channel)
            return

        dest_guild = self.bot.get_guild(pair.get("B_ID"))
        if not dest_guild:
            await self.send_debug(f"Bサーバーが見つかりません（ID: {pair.get('B_ID')}）", fallback_channel=message.channel)
            return

        dest_channel = dest_guild.get_channel(dest_id)
        if not dest_channel:
            await self.send_debug(f"転送先チャンネルが見つかりません（ID: {dest_id}）", fallback_channel=message.channel)
            return

        await self.send_debug(f"転送先チャンネル取得: {dest_channel.name} ({dest_channel.id})", fallback_channel=message.channel)

        try:
            # ===== Embed用テキスト生成 =====
            embed_text = message.content or " "
            for user in message.mentions:
                embed_text = embed_text.replace(f"<@{user.id}>", f"@{user.display_name}")
                embed_text = embed_text.replace(f"<@!{user.id}>", f"@{user.display_name}")
            for role in message.role_mentions:
                embed_text = embed_text.replace(f"<@&{role.id}>", f"@{role.name}")

            # ===== おしゃれEmbed生成（ユーザーごとに色変化） =====
            color_seed = (hash(message.author.id) % 0xFFFFFF)
            embed_color = discord.Color(color_seed)

            embed = discord.Embed(description=embed_text, color=embed_color)
            try:
                embed.set_author(
                    name=message.author.display_name,
                    icon_url=message.author.display_avatar.url
                )
            except Exception:
                embed.set_author(name=message.author.display_name)

            await dest_channel.send(embed=embed)
            await self.send_debug(f"Embed転送完了: {message.channel.id} → {dest_channel.id}", fallback_channel=message.channel)

            # ===== 添付ファイル（画像・動画など） =====
            for att in message.attachments:
                try:
                    file = await att.to_file()
                    await dest_channel.send(file=file)
                    await self.send_debug(f"添付ファイル転送完了: {att.filename}", fallback_channel=message.channel)
                except Exception as e:
                    await self.send_debug(f"添付ファイル送信失敗 ({att.filename}): {e}", fallback_channel=message.channel)

            # ===== メンション実際に通知 =====
            mention_parts = []

            # ユーザーメンション
            for user in message.mentions:
                member = dest_guild.get_member(user.id)
                if not member:
                    try:
                        member = await dest_guild.fetch_member(user.id)
                    except Exception:
                        member = None
                if member:
                    mention_parts.append(member.mention)

            # ロールメンション
            for role in message.role_mentions:
                dest_role = dest_guild.get_role(role.id)
                if not dest_role:
                    dest_role = get(dest_guild.roles, name=role.name)
                if dest_role:
                    mention_parts.append(dest_role.mention)

            if mention_parts:
                await dest_channel.send(" ".join(mention_parts))
                await self.send_debug(f"メンション通知転送完了: {' '.join(mention_parts)}", fallback_channel=message.channel)

        except Exception as e:
            await self.send_debug(f"転送失敗: {e}", fallback_channel=message.channel)

        # 最後にコマンドも再度処理
        await self.bot.process_commands(message)

    @commands.command(name="debug_test")
    async def debug_test(self, ctx: commands.Context):
        await self.send_debug("⚡デバッグ送信テスト⚡", fallback_channel=ctx.channel)
        await ctx.send("デバッグ送信を実行しました ✅")

async def setup(bot: commands.Bot):
    config_manager = getattr(bot, "config_manager", None)
    if not config_manager:
        raise RuntimeError("ConfigManager が bot にセットされていません")
    await bot.add_cog(TransferCog(bot, config_manager))
