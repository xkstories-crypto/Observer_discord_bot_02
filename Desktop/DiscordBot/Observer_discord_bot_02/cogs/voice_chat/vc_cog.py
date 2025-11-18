# cogs/voice_chat/vc_cog.py
from discord.ext import commands
import discord
import asyncio
from config_manager import ConfigManager

class VcCog(commands.Cog):
    def __init__(self, bot: commands.Bot, config_manager: ConfigManager):
        self.bot = bot
        self.config_manager = config_manager
        try:
            asyncio.create_task(self.send_debug("[DEBUG] VcCog loaded"))
        except Exception:
            print("[DEBUG] VcCog loaded")

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

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.bot or not member.guild:
            return

        await self.send_debug(f"VC状態変化受信: member={member.display_name}, "
                              f"before={getattr(before.channel,'name',None)}, "
                              f"after={getattr(after.channel,'name',None)}")

        server_conf = self.config_manager.get_server_config(member.guild.id)
        await self.send_debug(f"server_conf: {server_conf}")

        if not server_conf:
            await self.send_debug("このサーバーは転送ペアに登録されていません")
            return

        server_a_id = server_conf.get("A_ID")
        vc_log_channel_id = server_conf.get("VC_LOG_CHANNEL")
        await self.send_debug(f"A_ID={server_a_id}, VC_LOG_CHANNEL={vc_log_channel_id}")

        if member.guild.id != server_a_id:
            await self.send_debug(f"Aサーバーではないのでログスキップ (guild_id={member.guild.id})")
            return

        vc_log_channel = self.bot.get_channel(vc_log_channel_id)
        await self.send_debug(f"vc_log_channel={vc_log_channel}")

        if not vc_log_channel:
            await self.send_debug(f"VC_LOG_CHANNEL が取得できません (id={vc_log_channel_id})")
            return

        try:
            if before.channel is None and after.channel is not None:
                embed = discord.Embed(
                    title="VC参加",
                    description=f"{member.display_name} が {after.channel.name} に参加しました。",
                    color=discord.Color.green()
                )
                embed.set_footer(text=f"member_id={member.id}")
                await vc_log_channel.send(embed=embed)
                await self.send_debug(f"VC参加ログ送信成功: {member.display_name} → {after.channel.name}")
            elif before.channel is not None and after.channel is None:
                embed = discord.Embed(
                    title="VC退出",
                    description=f"{member.display_name} が {before.channel.name} から退出しました。",
                    color=discord.Color.red()
                )
                embed.set_footer(text=f"member_id={member.id}")
                await vc_log_channel.send(embed=embed)
                await self.send_debug(f"VC退出ログ送信成功: {member.display_name} → {before.channel.name}")
            else:
                await self.send_debug(f"VC状態変化が上記条件に該当しません (before={before.channel}, after={after.channel})")
        except Exception as e:
            await self.send_debug(f"VCログ送信失敗: {e}")

# ---------- Cogセットアップ ----------
async def setup(bot: commands.Bot):
    config_manager = getattr(bot, "config_manager", None)
    if not config_manager:
        raise RuntimeError("ConfigManager が bot にセットされていません")
    await bot.add_cog(VcCog(bot, config_manager))
