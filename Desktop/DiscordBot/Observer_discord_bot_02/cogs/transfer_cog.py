# transfer_cog.py
from discord.ext import commands
import discord
import asyncio
from discord.utils import get

class TransferCog(commands.Cog):
    def __init__(self, bot: commands.Bot, config_manager):
        self.bot = bot
        self.config_manager = config_manager
        # Cogロード時にDEBUG送信（元の send_debug を使う）
        # config_manager に send_debug がある想定。なければ個別実装にフォールバックされます。
        try:
            asyncio.create_task(self.config_manager.send_debug("[DEBUG] TransferCog loaded"))
        except Exception:
            # 万が一 config_manager.send_debug がない場合はコンソール出力
            print("[DEBUG] TransferCog loaded")

    async def send_debug(self, message: str, fallback_channel: discord.TextChannel = None):
        """DEBUGメッセージを送信。fallback_channel がなければ ConfigManager の DEBUG_CHANNEL を使う"""
        # まず渡されたチャンネルを優先
        target_channel = fallback_channel
        if not target_channel:
            # ConfigManager の DEBUG_CHANNEL を探す（最初に見つかったもの）
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

        # 最終フォールバック：コンソール
        print(f"[DEBUG] {message} (チャンネル未設定または送信失敗)")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Aサーバー→Bサーバーのメッセージ転送処理（必要最低限の変更のみ）"""
        if message.author.bot or not message.guild:
            return

        # ログ（受信）
        await self.send_debug(
            f"受信: guild={message.guild.name} ({message.guild.id}), "
            f"channel={message.channel.name} ({message.channel.id}), "
            f"author={message.author.display_name}, content={message.content}",
            fallback_channel=message.channel
        )

        # サーバーペアを取得（AサーバーIDで）
        pair = self.config_manager.get_pair_by_a(message.guild.id)
        if not pair:
            await self.send_debug("このサーバーは転送ペアに登録されていません", fallback_channel=message.channel)
            await self.bot.process_commands(message)
            return

        # 転送先チャンネルIDを取得
        dest_id = pair.get("CHANNEL_MAPPING", {}).get(str(message.channel.id))
        if not dest_id:
            await self.send_debug("このチャンネルには対応する転送先が設定されていません", fallback_channel=message.channel)
            await self.bot.process_commands(message)
            return

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

        # ---------------------- 転送処理 ----------------------
        try:
            content = message.content or ""
            # --- Embed 内用テキスト作成（メンションは見た目用に名前へ置換） ---
            # Replace user mentions like <@123> -> @DisplayName
            embed_text = content if content.strip() else " "  # Embed が空だと見栄えが悪いので空白を入れる
            # user mentions: replace <@id> and <@!id>
            for user in message.mentions:
                # Replace both forms if present
                embed_text = embed_text.replace(f"<@{user.id}>", f"@{user.display_name}")
                embed_text = embed_text.replace(f"<@!{user.id}>", f"@{user.display_name}")

            # role mentions: replace <@&id> with @RoleName
            for role in message.role_mentions:
                embed_text = embed_text.replace(f"<@&{role.id}>", f"@{role.name}")

            # 1) Embed送信（テキスト・リンク・見た目用メンション）
            if embed_text.strip():
                embed = discord.Embed(description=embed_text)
                # set_author with avatar (works regardless of server)
                try:
                    avatar_url = message.author.display_avatar.url
                except Exception:
                    avatar_url = None
                if avatar_url:
                    embed.set_author(name=message.author.display_name, icon_url=avatar_url)
                else:
                    embed.set_author(name=message.author.display_name)
                await dest_channel.send(embed=embed)
                await self.send_debug(f"Embed転送完了: {message.channel.id} → {dest_channel.id}", fallback_channel=message.channel)

            # 2) 添付ファイルは順番に別送信（Embed の後）
            for att in message.attachments:
                try:
                    file = await att.to_file()
                    await dest_channel.send(file=file)
                    await self.send_debug(f"添付ファイル転送完了: {att.filename}", fallback_channel=message.channel)
                except Exception as e:
                    await self.send_debug(f"添付ファイル送信失敗 ({att.filename}): {e}", fallback_channel=message.channel)

            # 3) 実際のメンション通知は転送先に存在するものだけ送信（ID で検索、なければ name で検索）
            mention_parts = []

            # users: check presence in dest_guild (try cache then fetch fallback)
            for user in message.mentions:
                member = dest_guild.get_member(user.id)
                if not member:
                    # try fetch (may raise if not found or no perms)
                    try:
                        member = await dest_guild.fetch_member(user.id)
                    except Exception:
                        member = None
                if member:
                    mention_parts.append(member.mention)

            # roles: prefer same ID; if not present, try find by name
            for role in message.role_mentions:
                dest_role = dest_guild.get_role(role.id)
                if not dest_role:
                    # fallback: search by exact name match (case-sensitive)
                    dest_role = get(dest_guild.roles, name=role.name)
                if dest_role:
                    mention_parts.append(dest_role.mention)

            if mention_parts:
                # join with spaces and send (this will actually ping)
                mention_text = " ".join(mention_parts)
                await dest_channel.send(mention_text)
                await self.send_debug(f"メンション通知転送完了: {mention_text}", fallback_channel=message.channel)

        except Exception as e:
            await self.send_debug(f"転送失敗: {e}", fallback_channel=message.channel)

        # 最後にコマンド処理も忘れず
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
