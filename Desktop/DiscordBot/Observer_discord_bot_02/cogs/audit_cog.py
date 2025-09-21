import discord
from discord.ext import commands
from config import SERVER_A_ID, AUDIT_LOG_CHANNEL

class AuditCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ---------- 監査ログ送信 ----------
    async def send_audit_embed(
        self, title, description, fields=None, color=0x00ff00, guild=None
    ):
        if guild and guild.id != SERVER_A_ID:
            return

        channel = self.bot.get_channel(AUDIT_LOG_CHANNEL)
        if channel:
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

    # ---------- メンバー関連 ----------
    @commands.Cog.listener()
    async def on_member_join(self, member):
        await self.send_audit_embed(
            "✅ メンバー参加",
            f"{member.display_name} がサーバーに参加しました",
            fields=[("ID", member.id, True)],
            guild=member.guild,
        )

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        await self.send_audit_embed(
            "❌ メンバー退出",
            f"{member.display_name} がサーバーから退出しました",
            fields=[("ID", member.id, True)],
            guild=member.guild,
        )

    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        await self.send_audit_embed(
            "⛔ メンバーBAN",
            f"{user.name} がBANされました",
            fields=[("ID", user.id, True)],
            color=0xFF0000,
            guild=guild,
        )

    @commands.Cog.listener()
    async def on_member_unban(self, guild, user):
        await self.send_audit_embed(
            "✅ メンバーBAN解除",
            f"{user.name} のBANが解除されました",
            fields=[("ID", user.id, True)],
            color=0x00FF00,
            guild=guild,
        )

    # ---------- メッセージ削除 ----------
@commands.Cog.listener()
async def on_message_delete(self, message):
    if not message.guild:
        return

    embed = discord.Embed(
        title="🗑 メッセージ削除",
        description=f"{message.author.display_name if message.author else '不明'} のメッセージが削除されました",
        color=0xFF4500,
        timestamp=discord.utils.utcnow()
    )

    # メッセージ内容
    embed.add_field(name="内容", value=message.content or "なし", inline=False)

    # 添付ファイル
    images = [a.url for a in message.attachments if a.content_type and a.content_type.startswith("image/")]
    videos = [a.url for a in message.attachments if a.content_type and a.content_type.startswith("video/")]
    others = [a.url for a in message.attachments if not (a.content_type and (a.content_type.startswith("image/") or a.content_type.startswith("video/")))]

    # 画像はEmbedに設定（最初の1枚だけ）
    if images:
        embed.set_image(url=images[0])
    # 他の画像はフィールドでリスト化
    if len(images) > 1:
        embed.add_field(name="添付画像(残り)", value="\n".join(images[1:]), inline=False)
    # 動画はフィールドで
    if videos:
        embed.add_field(name="添付動画", value="\n".join(videos), inline=False)
    # その他ファイル
    if others:
        embed.add_field(name="その他添付", value="\n".join(others), inline=False)

    channel = self.bot.get_channel(AUDIT_LOG_CHANNEL)
    if channel:
        await channel.send(embed=embed)


    # ---------- 招待リンク ----------
    @commands.Cog.listener()
    async def on_invite_create(self, invite):
        await self.send_audit_embed(
            "📨 招待作成",
            f"新しい招待コードが作成されました",
            fields=[
                ("招待コード", invite.code, True),
                ("チャンネル", invite.channel.name, True),
                ("作成者", invite.inviter.mention if invite.inviter else "不明", True),
                ("使用回数制限", invite.max_uses or "無制限", True),
                ("有効期限", f"{invite.max_age}秒" if invite.max_age else "無期限", True),
                ("一時メンバー", "はい" if invite.temporary else "いいえ", True),
            ],
            color=0x00FF7F,
            guild=invite.guild,
        )

    @commands.Cog.listener()
    async def on_invite_delete(self, invite):
        await self.send_audit_embed(
            "❌ 招待削除",
            f"招待コード `{invite.code}` が削除されました",
            color=0xFF0000,
            guild=invite.guild,
        )

    # ---------- サーバー設定変更 ----------
    @commands.Cog.listener()
    async def on_guild_update(self, before, after):
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
                guild=after,
            )

    # ---------- ロール操作コマンド ----------
    @commands.command()
    @commands.has_permissions(manage_roles=True)
    async def create_role(self, ctx, name: str, color: str = "0x3498db"):
        color_val = int(color, 16)
        await ctx.guild.create_role(name=name, color=discord.Color(color_val))
        await ctx.send(f"ロール {name} を作成しました。")

    @commands.command()
    @commands.has_permissions(manage_roles=True)
    async def delete_role(self, ctx, name: str):
        role = discord.utils.get(ctx.guild.roles, name=name)
        if role:
            await role.delete()
            await ctx.send(f"ロール {name} を削除しました。")
        else:
            await ctx.send("ロールが見つかりません。")


async def setup(bot):
    await bot.add_cog(AuditCog(bot))
