# cogs/voice_chat/vc_cog.py
from discord.ext import commands
import discord
from config_manager import ConfigManager
import asyncio

class VcCog(commands.Cog):
    def __init__(self, bot: commands.Bot, config_manager: ConfigManager):
        self.bot = bot
        self.config_manager = config_manager
        try:
            asyncio.create_task(self.send_debug("[DEBUG] VcCog loaded"))
        except Exception:
            print("[DEBUG] VcCog loaded")

    # -------------------- DEBUG送信 (Embed対応) --------------------
    async def send_debug(self, message: str = None, embed: discord.Embed = None, fallback_channel: discord.TextChannel = None):
        """
        message または embed を DEBUG_CHANNEL に送信
        """
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
                if embed:
                    await target_channel.send(embed=embed)
                elif message:
                    await target_channel.send(f"[DEBUG] {message}")
                return
            except Exception as e:
                print(f"[DEBUG送信失敗] {message or 'embed'} ({e})")

        print(f"[DEBUG] {message or 'embed'} (チャンネル未設定または送信失敗)")

    # -------------------- VC参加/退出ログ --------------------
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.bot or not member.guild:
            return

        # 受信確認用 DEBUG
        await self.send_debug(
            message=f"VC状態変化受信: member={member.display_name}, "
                    f"before={getattr(before.channel,'name',None)}, "
                    f"after={getattr(after.channel,'name',None)}"
        )

        try:
            embed = None
            if before.channel is None and after.channel is not None:
                # VC参加
                embed = discord.Embed(
                    title="VC参加",
                    description=f"🔊 **{member.display_name}** が **{after.channel.name}** に参加しました。",
                    color=discord.Color.green()
                )
            elif before.channel is not None and after.channel is None:
                # VC退出
                embed = discord.Embed(
                    title="VC退出",
                    description=f"🔈 **{member.display_name}** が **{before.channel.name}** から退出しました。",
                    color=discord.Color.red()
                )

            if embed:
                embed.set_footer(text=f"member id: {member.id}")
                # DEBUG_CHANNEL に送信
                await self.send_debug(embed=embed)

        except Exception as e:
            await self.send_debug(f"VCログ Embed生成失敗: {e}")

    # -------------------- BサーバーからAサーバーのVC一覧 --------------------
    @commands.command(name="debug_vc_full")
    async def debug_vc_full(self, ctx: commands.Context):
        await self.send_debug(f"!debug_vc_full コマンド実行 by {ctx.author.display_name}", fallback_channel=ctx.channel)

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
        for ch in vc_channels:
            members = [m.display_name for m in ch.members]
            desc = ", ".join(members) if members else "(誰もいません)"
            embed = discord.Embed(
                title=f"VC: {ch.name}",
                description=desc,
                color=discord.Color.blue()
            )
            try:
                await ctx.send(embed=embed)
            except Exception as e:
                await self.send_debug(f"VC一覧送信失敗: {e}", fallback_channel=ctx.channel)

# -------------------- Cogセットアップ --------------------
async def setup(bot: commands.Bot):
    config_manager = getattr(bot, "config_manager", None)
    if not config_manager:
        raise RuntimeError("ConfigManager が bot にセットされていません")
    await bot.add_cog(VcCog(bot, config_manager))
