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

    # -------------------- DEBUG送信 --------------------
    async def send_debug(self, message: str, fallback_channel: discord.TextChannel = None):
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
                await target_channel.send(f"[DEBUG] {message}")
                return
            except Exception as e:
                print(f"[DEBUG送信失敗] {message} ({e})")

        print(f"[DEBUG] {message} (チャンネル未設定または送信失敗)")

    # -------------------- VC参加/退出ログ --------------------
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.bot or not member.guild:
            return

        # ✅ イベント受信ログ
        await self.send_debug(
            f"VC状態変化受信: member={member.display_name}, "
            f"before={getattr(before.channel,'name',None)}, "
            f"after={getattr(after.channel,'name',None)}"
        )

        # ✅ イベント発生元(A側)設定取得
        server_conf_a = self.config_manager.get_server_config(member.guild.id)
        if not server_conf_a:
            await self.send_debug("A側設定が取得できません")
            return

        # ✅ B側ID取得
        server_b_id = server_conf_a.get("B_ID")
        server_conf_b = self.config_manager.get_server_config(server_b_id)

        if not server_conf_b:
            await self.send_debug("B側設定が取得できません")
            return

        vc_log_channel_id = server_conf_b.get("VC_LOG_CHANNEL")

        # ✅ B側VCログチャンネル取得
        vc_log_channel = self.bot.get_channel(vc_log_channel_id)
        if not vc_log_channel:
            try:
                vc_log_channel = await self.bot.fetch_channel(vc_log_channel_id)
            except Exception as e:
                await self.send_debug(f"B側 VC_LOG_CHANNEL取得失敗: {e}")
                return

        # ✅ 入退室メッセージ送信（embedなし）
        try:
            if before.channel is None and after.channel is not None:
                await vc_log_channel.send(
                    f"✅ **{member.display_name}** が **{after.channel.name}** に参加しました"
                )
            elif before.channel is not None and after.channel is None:
                await vc_log_channel.send(
                    f"🚪 **{member.display_name}** が **{before.channel.name}** から退出しました"
                )
        except Exception as e:
            await self.send_debug(f"B側VCログ送信失敗: {e}")

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
            try:
                await ctx.send(f"VC: {ch.name}\n{desc}")
            except Exception as e:
                await self.send_debug(f"VC一覧送信失敗: {e}", fallback_channel=ctx.channel)

# -------------------- Cogセットアップ --------------------
async def setup(bot: commands.Bot):
    config_manager = getattr(bot, "config_manager", None)
    if not config_manager:
        raise RuntimeError("ConfigManager が bot にセットされていません")
    await bot.add_cog(VcCog(bot, config_manager))
