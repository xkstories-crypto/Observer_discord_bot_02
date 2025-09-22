# cogs/audit_cog.py
import discord
from discord.ext import commands
from config_manager import ConfigManager  # ConfigManager を import

class AuditCog(commands.Cog):
    def __init__(self, bot: commands.Bot, config_manager: ConfigManager):
        self.bot = bot
        self.config_manager = config_manager
        # {message_id: {"content": str, "author": str, "attachments": [{"url": str, "type": str}]}}
        self.message_cache = {}

    # ---------- 監査ログ送信 ----------
    async def send_audit_embed(
        self, title: str, description: str, fields=None, color=0x00ff00, guild: discord.Guild = None
    ):
        if not guild:
            return

        server_config = self.config_manager.get_server_config(guild.id)
        if not server_config:
            return

        audit_channel_id = server_config.get("AUDIT_LOG_CHANNEL")
        if not audit_channel_id:
            return

        channel = self.bot.get_channel(audit_channel_id)
        if not channel:
            return

        embed = discord.Embed(
            title=title,
            description=description,
            color=color,
            timestamp=discord.utils.utcnow(),
        )
        if fields:
            for name, value, inline in fields:
                embed.add_field(name=name, value=value, inline=inline)

        await channel.send(embed=embed)

    # ---------- メッセージをキャッシュ ----------
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild:
            return

        server_config = self.config_manager.get_server_config(message.guild.id)
        if not server_config:
            return

        monitored_channels = server_config.get("MONITORED_CHANNELS", [])
        if message.channel.id not in monitored_channels:
            return

        self.message_cache[message.id] = {
            "content": message.content,
            "author": message.author.display_name,
            "attachments": [
                {"url": a.url, "type": a.content_type} for a in message.attachments
            ],
        }

    # ---------- メッセージ削除 ----------
    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if not message.guild:
            return

        info = self.message_cache.get(message.id)
        if not info:
            return  # キャッシュにない場合は諦める

        images = [a["url"] for a in info["attachments"] if a["type"] and a["type"].startswith("image/")]
        videos = [a["url"] for a in info["attachments"] if a["type"] and a["type"].startswith("video/")]
        others = [a["url"] for a in info["attachments"] if not (a["type"] and (a["type"].startswith("image/") or a["type"].startswith("video/")))]

        embed = discord.Embed(
            title="🗑 メッセージ削除",
            description=f"{info['author']} のメッセージが削除されました",
            color=0xFF4500,
            timestamp=discord.utils.utcnow(),
        )

        embed.add_field(name="内容", value=info["content"] or "なし", inline=False)
        if images:
            embed.set_image(url=images[0])
        if len(images) > 1:
            embed.add_field(name="添付画像(残り)", value="\n".join(images[1:]), inline=False)
        if videos:
            embed.add_field(name="添付動画", value="\n".join(videos), inline=False)
        if others:
            embed.add_field(name="その他添付", value="\n".join(others), inline=False)

        await self.send_audit_embed(
            title="🗑 メッセージ削除",
            description=f"{info['author']} のメッセージが削除されました",
            guild=message.guild,
            fields=[],
            color=0xFF4500
        )

    # ---------- メンバーイベント ----------
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        await self.send_audit_embed(
            "✅ メンバー参加",
            f"{member.display_name} がサーバーに参加しました",
            fields=[("ID", member.id, True)],
            guild=member.guild
        )

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        await self.send_audit_embed(
            "❌ メンバー退出",
            f"{member.display_name} がサーバーから退出しました",
            fields=[("ID", member.id, True)],
            guild=member.guild
        )

    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User):
        await self.send_audit_embed(
            "⛔ メンバーBAN",
            f"{user.name} がBANされました",
            fields=[("ID", user.id, True)],
            color=0xFF0000,
            guild=guild
        )

    @commands.Cog.listener()
    async def on_member_unban(self, guild: discord.Guild, user: discord.User):
        await self.send_audit_embed(
            "✅ メンバーBAN解除",
            f"{user.name} のBANが解除されました",
            fields=[("ID", user.id, True)],
            color=0x00FF00,
            guild=guild
        )

    # ---------- 招待イベント ----------
    @commands.Cog.listener()
    async def on_invite_create(self, invite: discord.Invite):
        await self.send_audit_embed(
            "📨 招待作成",
            f"新しい招待コードが作成されました",
            fields=[
                ("招待コード", invite.code, True),
                ("チャンネル", invite.channel.name, True),
                ("作成者", invite.inviter.mention if invite.inviter else "不明", True),
                ("使用回数制限", invite.max_uses or "無制限", True),
                ("有効期限", f"{invite.max_age}秒" if invite.max_age else "無期限", True),
                ("一時メンバー", "はい" if invite.temporary else "いいえ", True)
            ],
            color=0x00FF7F,
            guild=invite.guild
        )

    @commands.Cog.listener()
    async def on_invite_delete(self, invite: discord.Invite):
        await self.send_audit_embed(
            "❌ 招待削除",
            f"招待コード `{invite.code}` が削除されました",
            color=0xFF0000,
            guild=invite.guild
        )

    # ---------- サーバー更新 ----------
    @commands.Cog.listener()
    async def on_guild_update(self, before: discord.Guild, after: discord.Guild):
        changes = []
        if before.name != after.name:
            changes.append(f"サーバー名: `{before.name}` → `{after.name}`")
        if before.icon != after.icon:
            changes.append("サーバーアイコンが変更されました")
        if before.verification_level != after.verification_level:
            changes.append(f"認証レベル: `{before.verification_level}` → `{after.verification_level}`")
        if before.explicit_content_filter != after.explicit_content_filter:
            changes.append(f"不適切コンテンツフィルター: `{before.explicit_content_filter}` → `{after.explicit_content_filter}`")

        if changes:
            await self.send_audit_embed(
                "⚙ サーバー設定変更",
                "サーバー設定が変更されました",
                fields=[("変更内容", "\n".join(changes), False)],
                color=0xFFA500,
                guild=after
            )

    # ---------- ロール操作コマンド ----------
    @commands.command()
    @commands.has_permissions(manage_roles=True)
    async def create_role(self, ctx: commands.Context, name: str, color: str = "0x3498db"):
        color_val = int(color, 16)
        await ctx.guild.create_role(name=name, color=discord.Color(color_val))
        await ctx.send(f"ロール {name} を作成しました。")

    @commands.command()
    @commands.has_permissions(manage_roles=True)
    async def delete_role(self, ctx: commands.Context, name: str):
        role = discord.utils.get(ctx.guild.roles, name=name)
        if role:
            await role.delete()
            await ctx.send(f"ロール {name} を削除しました。")
        else:
            await ctx.send("ロールが見つかりません。")

# ---------- Cogセットアップ ----------
async def setup(bot: commands.Bot):
    config_manager = getattr(bot, "config_manager", None)
    if not config_manager:
        raise RuntimeError("ConfigManager が bot にセットされていません")
    await bot.add_cog(AuditCog(bot, config_manager))
