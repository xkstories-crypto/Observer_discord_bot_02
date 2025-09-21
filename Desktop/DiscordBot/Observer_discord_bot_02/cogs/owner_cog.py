# cogs/owner_cog.py
from discord.ext import commands
from config import SERVER_A_ID, SERVER_B_ID, CHANNEL_MAPPING, VC_LOG_CHANNEL, AUDIT_LOG_CHANNEL, ADMIN_IDS

class OwnerCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ---------- Bot停止 ----------
    @commands.command()
    async def stopbot(self, ctx):
        if ctx.author.id not in ADMIN_IDS:
            await ctx.send("あなたは管理者ではありません。")
            return
        await ctx.send("Bot を停止します…")
        await self.bot.close()

    # ---------- チャンネル再取得 ----------
    @commands.command()
    async def reload(self, ctx):
        if ctx.author.id not in ADMIN_IDS:
            await ctx.send("あなたは管理者ではありません。")
            return

        lines = []

        vc_log_channel = self.bot.get_channel(VC_LOG_CHANNEL)
        audit_log_channel = self.bot.get_channel(AUDIT_LOG_CHANNEL)
        lines.append(f"VC_LOG_CHANNEL ({VC_LOG_CHANNEL}): {vc_log_channel}")
        lines.append(f"AUDIT_LOG_CHANNEL ({AUDIT_LOG_CHANNEL}): {audit_log_channel}")

        for src_id, dest_id in CHANNEL_MAPPING.items():
            dest_channel = self.bot.get_channel(dest_id)
            lines.append(f"{src_id} -> {dest_channel}")

        await ctx.send("チャンネル情報を再取得しました:\n```\n" + "\n".join(lines) + "\n```")

        # 自動で check の内容も表示
        await self.check(ctx)

    # ---------- サーバー・チャンネル確認 ----------
    @commands.command()
    async def check(self, ctx):
        lines = []

        # 管理者ならADMIN_IDSとVC/AUDITチャンネルも表示
        if ctx.author.id in ADMIN_IDS:
            lines.append("ADMIN_IDS:")
            for admin_id in ADMIN_IDS:
                member = ctx.guild.get_member(admin_id)
                if member:
                    lines.append(f"{admin_id} -> {member}")
                else:
                    lines.append(f"{admin_id} -> ユーザー不在")

            vc_log_channel = self.bot.get_channel(VC_LOG_CHANNEL)
            audit_log_channel = self.bot.get_channel(AUDIT_LOG_CHANNEL)
            lines.append(f"VC_LOG_CHANNEL ({VC_LOG_CHANNEL}): {vc_log_channel}")
            lines.append(f"AUDIT_LOG_CHANNEL ({AUDIT_LOG_CHANNEL}): {audit_log_channel}")

        # コマンド実行サーバーの情報は全員に表示
        guild = ctx.guild
        lines.append(f"Server ({guild.id}): {guild.name}")

        # このサーバーに関連するチャンネルのみ表示
        for src_key, dest_id in CHANNEL_MAPPING.items():
            dest_channel = self.bot.get_channel(dest_id)
            if dest_channel and dest_channel.guild.id == guild.id:
                lines.append(f"{src_key} -> {dest_channel.name}")

        await ctx.send("```\n" + "\n".join(lines) + "\n```")


async def setup(bot):
    await bot.add_cog(OwnerCog(bot))
