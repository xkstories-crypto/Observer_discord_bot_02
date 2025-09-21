# cogs/owner_cog.py
from discord.ext import commands
from config import SERVER_A_ID, SERVER_B_ID, CHANNEL_MAPPING, VC_LOG_CHANNEL, AUDIT_LOG_CHANNEL, ADMIN_IDS, READ_USERS

class OwnerCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def admin_only(self):
        async def predicate(ctx):
            return ctx.author.id in ADMIN_IDS
        return commands.check(predicate)

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

        # チャンネル情報表示
        lines = []
        vc_log_channel = self.bot.get_channel(VC_LOG_CHANNEL)
        audit_log_channel = self.bot.get_channel(AUDIT_LOG_CHANNEL)
        lines.append(f"VC_LOG_CHANNEL ({VC_LOG_CHANNEL}): {vc_log_channel}")
        lines.append(f"AUDIT_LOG_CHANNEL ({AUDIT_LOG_CHANNEL}): {audit_log_channel}")
        for src_id, dest_id in CHANNEL_MAPPING.items():
            dest_channel = self.bot.get_channel(dest_id)
            lines.append(f"{src_id} -> {dest_channel}")

        await ctx.send("チャンネル情報を再取得しました:\n```\n" + "\n".join(lines) + "\n```")

        # 自動で check を実行
        await self.check(ctx)

   @commands.command()
async def check(self, ctx):
    lines = []
    guild = ctx.guild

    if ctx.author.id in ADMIN_IDS:
        # サーバー情報
        guild_a = self.bot.get_guild(SERVER_A_ID)
        guild_b = self.bot.get_guild(SERVER_B_ID)
        lines.append(f"Server A ({SERVER_A_ID}): {guild_a.name if guild_a else '不明'}")
        lines.append(f"Server B ({SERVER_B_ID}): {guild_b.name if guild_b else '不明'}")

        # ログチャンネル
        vc_log_channel = self.bot.get_channel(VC_LOG_CHANNEL)
        audit_log_channel = self.bot.get_channel(AUDIT_LOG_CHANNEL)
        lines.append(f"VC_LOG_CHANNEL ({VC_LOG_CHANNEL}): {vc_log_channel.name if vc_log_channel else '不明'}")
        lines.append(f"AUDIT_LOG_CHANNEL ({AUDIT_LOG_CHANNEL}): {audit_log_channel.name if audit_log_channel else '不明'}")

        # チャンネルマッピング
        for src_id, dest_id in CHANNEL_MAPPING.items():
            dest_channel = self.bot.get_channel(dest_id)
            lines.append(f"{src_id} -> {dest_channel.name if dest_channel else dest_id}")

        # ADMIN_IDS
        lines.append("\nADMIN_IDS:")
        for admin_id in ADMIN_IDS:
            user = self.bot.get_user(admin_id)
            lines.append(f"{admin_id} -> {user.name if user else 'ユーザー不在'}")

        # READ_USERS
        lines.append("\nREAD_USERS:")
        for user_id in READ_USERS:
            user = self.bot.get_user(user_id)
            lines.append(f"{user_id} -> {user.name if user else 'ユーザー不在'}")

    else:
        # 一般ユーザーはコマンドを使ったサーバーのみ
        lines.append(f"Server ({guild.id})")

    await ctx.send("```\n" + "\n".join(lines) + "\n```")


async def setup(bot):
    await bot.add_cog(OwnerCog(bot))
