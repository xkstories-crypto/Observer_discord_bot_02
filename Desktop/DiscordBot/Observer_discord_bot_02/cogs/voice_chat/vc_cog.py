# cogs/vc_cog.py
from discord.ext import commands
import discord
from config_manager import ConfigManager

class VcCog(commands.Cog):
    def __init__(self, bot: commands.Bot, config_manager: ConfigManager):
        self.bot = bot
        self.config_manager = config_manager

    # ---------- VC参加/退出ログ ----------
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if not member.guild:
            return

        server_conf = self.config_manager.get_server_config(member.guild.id)
        if not server_conf:
            return

        server_a_id = server_conf.get("SERVER_A_ID")
        vc_log_channel_id = server_conf.get("VC_LOG_CHANNEL")

        if member.guild.id != server_a_id:
            return

        vc_log_channel = self.bot.get_channel(vc_log_channel_id)
        if not vc_log_channel:
            return

        if before.channel is None and after.channel is not None:
            await vc_log_channel.send(f"🔊 {member.display_name} が {after.channel.name} に参加しました。")
        elif before.channel is not None and after.channel is None:
            await vc_log_channel.send(f"🔈 {member.display_name} が {before.channel.name} から退出しました。")

    # ---------- BサーバーからAサーバーのVC一覧を確認 ----------
    @commands.command()
    async def all_vc(self, ctx):
        server_conf = self.config_manager.get_server_config(ctx.guild.id)
        if not server_conf:
            await ctx.send("サーバー設定が見つかりません。")
            return

        server_a_id = server_conf.get("SERVER_A_ID")
        guild_a = self.bot.get_guild(server_a_id)
        if not guild_a:
            await ctx.send("Aサーバーが見つかりません。")
            return

        vc_channels = guild_a.voice_channels
        result = []
        for ch in vc_channels:
            members = [m.display_name for m in ch.members]
            if members:
                result.append(f"{ch.name}: {', '.join(members)}")
            else:
                result.append(f"{ch.name}: (誰もいません)")
        await ctx.send("\n".join(result))

# ---------- Cogセットアップ ----------
async def setup(bot: commands.Bot):
    config_manager = getattr(bot, "config_manager", None)
    if not config_manager:
        raise RuntimeError("ConfigManager が bot にセットされていません")
    await bot.add_cog(VcCog(bot, config_manager))
