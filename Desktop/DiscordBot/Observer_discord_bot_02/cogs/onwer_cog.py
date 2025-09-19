# cogs/owner_cog.py
from discord.ext import commands
from config import SERVER_A_ID, SERVER_B_ID, CHANNEL_MAPPING, VC_LOG_CHANNEL, AUDIT_LOG_CHANNEL, ADMIN_IDS

class OwnerCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # 管理者チェック用デコレーター
    def admin_only():
        async def predicate(ctx):
            return ctx.author.id in ADMIN_IDS
        return commands.check(predicate)

    # ---------- Bot停止 ----------
    @commands.command()
    @admin_only()
    async def stopbot(self, ctx):
        await ctx.send("Bot を停止します…")
        await self.bot.close()

    # ---------- チャンネル再取得 ----------
    @commands.command()
    @admin_only()
    async def reload(self, ctx):
        lines = []

        vc_log_channel = self.bot.get_channel(VC_LOG_CHANNEL)
        audit_log_channel = self.bot.get_channel(AUDIT_LOG_CHANNEL)
        lines.append(f"VC_LOG_CHANNEL ({VC_LOG_CHANNEL}): {vc_log_channel}")
        lines.append(f"AUDIT_LOG_CHANNEL ({AUDIT_LOG_CHANNEL}): {audit_log_channel}")

        for src_id, dest_id in CHANNEL_MAPPING.items():
            dest_channel = self.bot.get_channel(dest_id)
            lines.append(f"{src_id} -> {dest_channel}")

        await ctx.send(
            "チャンネル情報を再取得しました:\n```\n" + "\n".join(lines) + "\n```"
        )

    # ---------- サーバー・チャンネル確認 ----------
    @commands.command()
    @admin_only()
    async def check(self, ctx):
        lines = []
        guild_a = self.bot.get_guild(SERVER_A_ID)
        guild_b = self.bot.get_guild(SERVER_B_ID)
        lines.append(f"Server A ({SERVER_A_ID}): {guild_a}")
        lines.append(f"Server B ({SERVER_B_ID}): {guild_b}")

        vc_log_channel = self.bot.get_channel(VC_LOG_CHANNEL)
        audit_log_channel = self.bot.get_channel(AUDIT_LOG_CHANNEL)
        lines.append(f"VC_LOG_CHANNEL ({VC_LOG_CHANNEL}): {vc_log_channel}")
        lines.append(f"AUDIT_LOG_CHANNEL ({AUDIT_LOG_CHANNEL}): {audit_log_channel}")

        for src_id, dest_id in CHANNEL_MAPPING.items():
            dest_channel = self.bot.get_channel(dest_id)
            lines.append(f"{src_id} -> {dest_channel}")

        await ctx.send("```\n" + "\n".join(lines) + "\n```")


async def setup(bot):
    await bot.add_cog(OwnerCog(bot))
