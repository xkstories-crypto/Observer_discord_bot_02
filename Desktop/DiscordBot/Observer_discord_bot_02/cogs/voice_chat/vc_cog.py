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

    async def send_debug(self, message: str, fallback_channel: discord.TextChannel = None):
        """ DEBUG チャンネル or フォールバックチャンネルに送信 """
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

    async def send_vc_log(self, message: str, color: discord.Color = discord.Color.blue()):
        """ VC_LOG_CHANNEL に Embed で送信 """
        try:
            # Aサーバーのペアを探す
            for pair in self.config_manager.config.get("server_pairs", []):
                vc_channel_id = pair.get("VC_LOG_CHANNEL")
                guild_a_id = pair.get("A_ID")
                guild_a = self.bot.get_guild(guild_a_id)
                if not guild_a:
                    continue

                channel = guild_a.get_channel(vc_channel_id)
                if not channel:
                    try:
                        # キャッシュにない場合は fetch
                        channel = await guild_a.fetch_channel(vc_channel_id)
                    except Exception:
                        await self.send_debug(f"VC_LOG_CHANNEL が取得できません (ID: {vc_channel_id})")
                        continue

                if isinstance(channel, discord.TextChannel):
                    embed = discord.Embed(description=message, color=color)
                    await channel.send(embed=embed)
                    return
        except Exception as e:
            await self.send_debug(f"VCログ送信失敗: {e}")

    # ---------- VC参加/退出ログ ----------
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.bot or not member.guild:
            return

        # デバッグ送信
        await self.send_debug(
            f"VC状態変化受信: member={member.display_name}, before={getattr(before.channel,'name',None)}, after={getattr(after.channel,'name',None)}"
        )

        server_conf = self.config_manager.get_server_config(member.guild.id)
        if not server_conf:
            await self.send_debug("このサーバーは転送ペアに登録されていません")
            return

        server_a_id = server_conf.get("A_ID")
        if member.guild.id != server_a_id:
            await self.send_debug(f"このサーバーはAサーバーではありません (guild_id={member.guild.id})")
            return

        # Embed色分けとメッセージ
        try:
            if before.channel is None and after.channel is not None:
                msg = f"🔊 **{member.display_name}** が **{after.channel.name}** に参加しました。"
                await self.send_vc_log(msg, color=discord.Color.green())
                await self.send_debug(f"VC参加ログ送信: {member.display_name} → {after.channel.name}")
            elif before.channel is not None and after.channel is None:
                msg = f"🔈 **{member.display_name}** が **{before.channel.name}** から退出しました。"
                await self.send_vc_log(msg, color=discord.Color.red())
                await self.send_debug(f"VC退出ログ送信: {member.display_name} → {before.channel.name}")
            else:
                # 移動などの特殊ケースも
                msg = f"🔄 **{member.display_name}** が VC 移動: {getattr(before.channel,'name',None)} → {getattr(after.channel,'name',None)}"
                await self.send_vc_log(msg, color=discord.Color.orange())
                await self.send_debug(f"VC移動ログ送信: {member.display_name} → {getattr(after.channel,'name',None)}")
        except Exception as e:
            await self.send_debug(f"VCログ送信失敗: {e}")

# ---------- Cogセットアップ ----------
async def setup(bot: commands.Bot):
    config_manager = getattr(bot, "config_manager", None)
    if not config_manager:
        raise RuntimeError("ConfigManager が bot にセットされていません")
    await bot.add_cog(VcCog(bot, config_manager))
