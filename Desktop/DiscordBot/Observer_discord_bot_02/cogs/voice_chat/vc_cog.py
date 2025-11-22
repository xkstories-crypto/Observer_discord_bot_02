# cogs/voice_chat/vc_cog.py
from discord.ext import commands
import discord
import asyncio
from config_manager import ConfigManager

class VcCog(commands.Cog):
    def __init__(self, bot: commands.Bot, config_manager: ConfigManager):
        self.bot = bot
        self.config_manager = config_manager
        # Bot起動完了後に初期DEBUGログを送信
        self.bot.loop.create_task(self.wait_until_ready_debug())

    async def wait_until_ready_debug(self):
        await self.bot.wait_until_ready()
        await self.send_debug("[DEBUG] VcCog loaded")

    # ---------------- DEBUG送信 ----------------
    async def send_debug(self, message: str = None, fallback_channel: discord.TextChannel = None):
        target_channel = fallback_channel
        if not target_channel:
            # JSON設定からDEBUG_CHANNELを取得
            for pair in self.config_manager.config.get("server_pairs", []):
                debug_id = pair.get("DEBUG_CHANNEL")
                if debug_id:
                    target_channel = self.bot.get_channel(debug_id)
                    if target_channel:
                        break

        if target_channel and message:
            try:
                await target_channel.send(f"[DEBUG] {message}")
            except Exception as e:
                print(f"[DEBUG送信失敗] {message} ({e})")
        else:
            print(f"[DEBUG] {message} (チャンネル未設定または送信失敗)")

    # ---------------- VC_LOG送信（Embed用） ----------------
    async def send_vc_log(self, embed: discord.Embed, fallback_channel: discord.TextChannel = None):
        target_channel = fallback_channel
        if not target_channel:
            # JSON設定からVC_LOG_CHANNELを取得
            for pair in self.config_manager.config.get("server_pairs", []):
                vc_log_id = pair.get("VC_LOG_CHANNEL")
                if vc_log_id:
                    target_channel = self.bot.get_channel(vc_log_id)
                    if target_channel:
                        break

        if target_channel:
            try:
                await target_channel.send(embed=embed)
            except Exception as e:
                print(f"[VC_LOG送信失敗] embed ({e})")
        else:
            print(f"[VC_LOG] embed (チャンネル未設定または送信失敗)")

    # ---------------- VC参加/退出イベント ----------------
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.bot or not member.guild:
            return

        # ---------------- DEBUG_CHANNEL にテキスト送信 ----------------
        await self.send_debug(
            f"VC状態変化受信: member={member.display_name}, "
            f"before={getattr(before.channel,'name',None)}, "
            f"after={getattr(after.channel,'name',None)}"
        )

        # ---------------- VC_LOG_CHANNEL に Embed送信 ----------------
        embed = None
        channel_name = getattr(after.channel if after.channel else before.channel, "name", None)
        if before.channel is None and after.channel is not None:
            # VC参加
            embed = discord.Embed(
                title="通話開始",
                color=discord.Color.green()
            )
            embed.add_field(name="チャンネル", value=channel_name, inline=True)
            embed.add_field(name="始めた人", value=member.display_name, inline=True)
            embed.add_field(name="開始時間", value=str(after.channel.created_at), inline=True)
        elif before.channel is not None and after.channel is None:
            # VC退出
            embed = discord.Embed(
                title="通話終了",
                color=discord.Color.red()
            )
            embed.add_field(name="チャンネル", value=channel_name, inline=True)
            embed.add_field(name="退出した人", value=member.display_name, inline=True)
            embed.add_field(name="終了時間", value=str(after.channel.created_at), inline=True)

        if embed:
            embed.set_footer(text=f"member id: {member.id}")
            # 本人アイコンを右に表示（サムネイル）
            if member.avatar:
                embed.set_thumbnail(url=member.avatar.url)
            await self.send_vc_log(embed=embed)

# ---------------- Cogセットアップ ----------------
async def setup(bot: commands.Bot):
    config_manager = getattr(bot, "config_manager", None)
    if not config_manager:
        raise RuntimeError("ConfigManager が bot にセットされていません")
    await bot.add_cog(VcCog(bot, config_manager))
