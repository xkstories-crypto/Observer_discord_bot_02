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

    # -------------------- DEBUG送信（テキスト用） --------------------
    async def send_debug(self, message: str = None, fallback_channel: discord.TextChannel = None):
        """簡易テキストログを DEBUG_CHANNEL に送信"""
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
                if message:
                    await target_channel.send(f"[DEBUG] {message}")
                return
            except Exception as e:
                print(f"[DEBUG送信失敗] {message} ({e})")

        print(f"[DEBUG] {message} (チャンネル未設定または送信失敗)")

    # -------------------- VC_LOG送信（Embed用） --------------------
    async def send_vc_log(self, embed: discord.Embed, file: discord.File = None, fallback_channel: discord.TextChannel = None):
        """Embedを VC_LOG_CHANNEL に送信"""
        target_channel = fallback_channel
        if not target_channel:
            for pair in self.config_manager.config.get("server_pairs", []):
                vc_log_id = pair.get("VC_LOG_CHANNEL")
                if vc_log_id:
                    target_channel = self.bot.get_channel(vc_log_id)
                    if target_channel:
                        break

        if target_channel:
            try:
                if file:
                    await target_channel.send(embed=embed, file=file)
                else:
                    await target_channel.send(embed=embed)
                return
            except Exception as e:
                print(f"[VC_LOG送信失敗] embed ({e})")

        print(f"[VC_LOG] embed (チャンネル未設定または送信失敗)")

    # -------------------- VC参加/退出ログ --------------------
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.bot or not member.guild:
            return

        # 簡易ログを DEBUG_CHANNEL に送信
        await self.send_debug(
            f"VC状態変化受信: member={member.display_name}, "
            f"before={getattr(before.channel,'name',None)}, "
            f"after={getattr(after.channel,'name',None)}"
        )

        try:
            embed = None
            file = None
            thumbnail_path = "通話アイコン.png"  # 任意のアイコン画像パス

            if before.channel is None and after.channel is not None:
                # VC参加
                embed = discord.Embed(
                    title="通話開始",
                    color=discord.Color.green()
                )
                embed.add_field(name="チャンネル", value=after.channel.name, inline=True)
                embed.add_field(name="始めた人", value=member.display_name, inline=True)
                embed.add_field(name="開始時間", value=str(after.channel.created_at), inline=True)
            elif before.channel is not None and after.channel is None:
                # VC退出
                embed = discord.Embed(
                    title="通話終了",
                    color=discord.Color.red()
                )
                embed.add_field(name="チャンネル", value=before.channel.name, inline=True)
                embed.add_field(name="退出した人", value=member.display_name, inline=True)
                embed.add_field(name="終了時間", value=str(after.channel.created_at), inline=True)

            if embed:
                embed.set_footer(text=f"member id: {member.id}")
                # アイコン添付
                try:
                    file = discord.File(thumbnail_path, filename="通話アイコン.png")
                    embed.set_thumbnail(url="attachment://通話アイコン.png")
                except Exception as e:
                    await self.send_debug(f"サムネイル添付失敗: {e}")
                await self.send_vc_log(embed=embed, file=file)
        except Exception as e:
            await self.send_debug(f"VCログ Embed生成失敗: {e}")
