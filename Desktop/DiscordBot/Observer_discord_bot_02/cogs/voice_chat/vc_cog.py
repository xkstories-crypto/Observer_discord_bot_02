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

        # デバッグチャンネルの探索
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

        # 送信処理
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

        # 受信確認
        await self.send_debug(
            f"VC STATE UPDATE: member={member.display_name} before={getattr(before.channel, 'name', None)} after={getattr(after.channel, 'name', None)}"
        )

        server_conf = self.config_manager.get_server_config(member.guild.id)
        if not server_conf:
            await self.send_debug("サーバー設定なし（転送ペア未登録）")
            return

        server_a_id = server_conf.get("A_ID")
        vc_log_channel_id = server_conf.get("VC_LOG_CHANNEL")

        if member.guild.id != server_a_id:
            await self.send_debug(f"Aサーバーではない（guild_id={member.guild.id}）")
            return

        # ---------- VC_LOG_CHANNEL の取得 ----------
        vc_log_channel = self.bot.get_channel(vc_log_channel_id)

        if not vc_log_channel:
            await self.send_debug(f"[ERROR] VC_LOG_CHANNEL 取得できず (ID={vc_log_channel_id}) → fetch_channel 試行")

            try:
                vc_log_channel = await self.bot.fetch_channel(vc_log_channel_id)
            except Exception as e:
                await self.send_debug(f"[ERROR] fetch_channel 失敗: {e}")
                return

            if not vc_log_channel:
                await self.send_debug("[ERROR] fetch_channel 後も VC_LOG_CHANNEL None")
                return

        # ---------- 送信 ----------
        try:
            if before.channel is None and after.channel is not None:
                embed = discord.Embed(
                    title="VC参加",
                    description=f"🔊 **{member.display_name}** が **{after.channel.name}** に参加しました。",
                    color=discord.Color.green()
                )
                embed.set_footer(text=f"member id: {member.id}")
                await vc_log_channel.send(embed=embed)

            elif before.channel is not None and after.channel is None:
                embed = discord.Embed(
                    title="VC退出",
                    description=f"🔈 **{member.display_name}** が **{before.channel.name}** から退出しました。",
                    color=discord.Color.red()
                )
                embed.set_footer(text=f"member id: {member.id}")
                await vc_log_channel.send(embed=embed)

        except Exception as e:
            await self.send_debug(f"[ERROR] VC_LOG_CHANNEL 送信失敗: {e}")

# -------------------- Cogセットアップ --------------------
async def setup(bot: commands.Bot):
    config_manager = getattr(bot, "config_manager", None)
    if not config_manager:
        raise RuntimeError("ConfigManager が bot にセットされていません")
    await bot.add_cog(VcCog(bot, config_manager))
