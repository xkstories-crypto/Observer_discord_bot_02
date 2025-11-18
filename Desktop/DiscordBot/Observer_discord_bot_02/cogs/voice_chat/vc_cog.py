# cogs/voice_chat/vc_cog.py
from discord.ext import commands
import discord
from discord.utils import get
from config_manager import ConfigManager
import asyncio

class VcCog(commands.Cog):
    def __init__(self, bot: commands.Bot, config_manager: ConfigManager):
        self.bot = bot
        self.config_manager = config_manager
        asyncio.create_task(self.send_debug("[DEBUG] VcCog loaded"))

    async def send_debug(self, message: str, fallback_channel: discord.TextChannel = None):
        target_channel = fallback_channel
        if not target_channel:
            for pair in self.config_manager.config.get("server_pairs", []):
                debug_id = pair.get("DEBUG_CHANNEL")
                if debug_id:
                    target_channel = self.bot.get_channel(debug_id)
                    if target_channel:
                        break
        if target_channel:
            try:
                await target_channel.send(f"[DEBUG] {message}")
                return
            except Exception as e:
                print(f"[DEBUG送信失敗] {message} ({e})")
        print(f"[DEBUG] {message} (チャンネル未設定または送信失敗)")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.bot or not member.guild:
            return

        # すべての状態変化をEmbedにしてVC_LOG_CHANNELに送る
        server_conf = self.config_manager.get_server_config(member.guild.id)
        if not server_conf:
            await self.send_debug(f"このサーバーは転送ペアに登録されていません: {member.guild.id}")
            return

        server_a_id = server_conf.get("A_ID")
        vc_log_channel_id = server_conf.get("VC_LOG_CHANNEL")
        if member.guild.id != server_a_id:
            await self.send_debug(f"このサーバーはAサーバーではありません: {member.guild.id}")
            return

        # チャンネル取得（キャッシュなければ fetch）
        vc_log_channel = self.bot.get_channel(vc_log_channel_id)
        if not vc_log_channel:
            try:
                vc_log_channel = await self.bot.fetch_channel(vc_log_channel_id)
            except Exception as e:
                await self.send_debug(f"VC_LOG_CHANNEL 取得失敗: {vc_log_channel_id} ({e})")
                return

        before_name = getattr(before.channel, "name", None)
        after_name = getattr(after.channel, "name", None)

        embed = discord.Embed(
            title="VC状態変化",
            color=discord.Color.blurple()
        )
        embed.add_field(name="メンバー", value=member.display_name, inline=False)
        embed.add_field(name="前のVC", value=before_name or "(なし)", inline=True)
        embed.add_field(name="後のVC", value=after_name or "(なし)", inline=True)
        embed.add_field(name="Bot?", value=str(member.bot), inline=True)
        embed.set_footer(text=f"ID: {member.id}")

        try:
            await vc_log_channel.send(embed=embed)
            await self.send_debug(f"VCログ送信成功: {member.display_name} ({before_name} → {after_name})")
        except Exception as e:
            await self.send_debug(f"VCログ送信失敗: {e}")

    @commands.command(name="debug_vc_full")
    async def debug_vc_full(self, ctx: commands.Context):
        server_conf = self.config_manager.get_server_config(ctx.guild.id)
        if not server_conf:
            await ctx.send("サーバー設定が見つかりません。")
            return

        server_a_id = server_conf.get("A_ID")
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
        message_text = "\n".join(result)
        await ctx.send(f"📋 VC一覧:\n{message_text}")

# Cogセットアップ
async def setup(bot: commands.Bot):
    config_manager = getattr(bot, "config_manager", None)
    if not config_manager:
        raise RuntimeError("ConfigManager が bot にセットされていません")
    await bot.add_cog(VcCog(bot, config_manager))
