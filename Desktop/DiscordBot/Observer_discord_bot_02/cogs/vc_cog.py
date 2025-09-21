import discord
from discord.ext import commands
from config import SERVER_A_ID, VC_LOG_CHANNEL

class VcCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ---------- VC参加/退出ログ ----------
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.guild.id != SERVER_A_ID:
            return

        vc_log_channel = self.bot.get_channel(VC_LOG_CHANNEL)
        if not vc_log_channel:
            return

        if before.channel is None and after.channel is not None:
            await vc_log_channel.send(f"🔊 {member.display_name} が {after.channel.name} に参加しました。")
        elif before.channel is not None and after.channel is None:
            await vc_log_channel.send(f"🔈 {member.display_name} が {before.channel.name} から退出しました。")

    # ---------- AサーバーのVC一覧を確認するコマンド ----------
    @commands.command()
    async def all_vc(self, ctx):
        if ctx.guild.id != SERVER_A_ID:
            await ctx.send("このコマンドはAサーバー専用です。")
            return

        vc_channels = ctx.guild.voice_channels
        result = []
        for ch in vc_channels:
            members = [m.display_name for m in ch.members]
            if members:
                result.append(f"{ch.name}: {', '.join(members)}")
            else:
                result.append(f"{ch.name}: (誰もいません)")
        await ctx.send("\n".join(result))


async def setup(bot):
    await bot.add_cog(VcCog(bot))
