# cogs/voice_chat/vc_cog.py
from discord.ext import commands
import discord
import asyncio
from config_manager import ConfigManager
from datetime import datetime

class VcCog(commands.Cog):
    def __init__(self, bot: commands.Bot, config_manager: ConfigManager):
        self.bot = bot
        self.config_manager = config_manager
        self.bot.loop.create_task(self.wait_until_ready_debug())

    async def wait_until_ready_debug(self):
        await self.bot.wait_until_ready()
        await self.send_debug("[DEBUG] VcCog loaded")

    # ---------------- DEBUG送信 ----------------
    async def send_debug(self, message: str = None, fallback_channel: discord.TextChannel = None, mention_everyone: bool = False):
        target_channel = fallback_channel
        if not target_channel:
            for pair in self.config_manager.config.get("server_pairs", []):
                debug_id = pair.get("DEBUG_CHANNEL")
                if debug_id:
                    target_channel = self.bot.get_channel(debug_id)
                    if target_channel:
                        break

        if target_channel and message:
            try:
                if mention_everyone:
                    await target_channel.send(f"@everyone {message}")
                else:
                    await target_channel.send(message)
            except Exception as e:
                print(f"[DEBUG送信失敗] {message} ({e})")
        else:
            print(f"[DEBUG] {message} (チャンネル未設定または送信失敗)")

    # ---------------- VC_LOG送信（Embed用） ----------------
    async def send_vc_log(self, embed: discord.Embed, fallback_channel: discord.TextChannel = None, mention_everyone: bool = False):
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
                if mention_everyone:
                    await target_channel.send("@everyone", embed=embed)
                else:
                    await target_channel.send(embed=embed)
            except Exception as e:
                print(f"[VC_LOG送信失敗] embed ({e})")
        else:
            print(f"[VC_LOG] embed (チャンネル未設定または送信失敗)")

    # ---------------- VC参加/退出/移動イベント ----------------
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.bot or not member.guild:
            return

        await self.send_debug(
            f"VC状態変化受信: member={member.display_name}, "
            f"before={getattr(before.channel,'name',None)}, "
            f"after={getattr(after.channel,'name',None)}"
        )

        embed = None
        if before.channel != after.channel:
            timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

            if before.channel is None and after.channel is not None:
                embed = discord.Embed(title="通話開始", color=discord.Color.green(), timestamp=datetime.utcnow())
                embed.add_field(name="チャンネル", value=after.channel.name, inline=True)
                embed.add_field(name="始めた人", value=member.display_name, inline=True)
                embed.add_field(name="開始時間", value=timestamp, inline=True)

            elif before.channel is not None and after.channel is None:
                embed = discord.Embed(title="通話終了", color=discord.Color.red(), timestamp=datetime.utcnow())
                embed.add_field(name="チャンネル", value=before.channel.name, inline=True)
                embed.add_field(name="退出した人", value=member.display_name, inline=True)
                embed.add_field(name="終了時間", value=timestamp, inline=True)

            elif before.channel is not None and after.channel is not None:
                embed = discord.Embed(title="VC移動", color=discord.Color.orange(), timestamp=datetime.utcnow())
                embed.add_field(name="移動元", value=before.channel.name, inline=True)
                embed.add_field(name="移動先", value=after.channel.name, inline=True)
                embed.add_field(name="メンバー", value=member.display_name, inline=True)

        if embed:
            embed.set_footer(text=f"member id: {member.id}")
            if member.avatar:
                embed.set_thumbnail(url=member.avatar.url)
            await self.send_vc_log(embed=embed)

    # ---------------- VC状況確認コマンド ----------------
    @commands.command(name="vc_here")
    async def vc_here(self, ctx: commands.Context):
        forbidden_server_ids = [pair.get("A_SERVER_ID") for pair in self.config_manager.config.get("server_pairs", [])]

        # Aサーバーで使われた場合は禁止
        if ctx.guild.id in forbidden_server_ids:
            message = f"{ctx.author.display_name} が {ctx.guild.name} で !vc_here を使用しました（禁止）。"
            await self.send_debug(message, mention_everyone=True)
            await ctx.send("このサーバーでは使用できません。")
            return

        # Bサーバーでの通常処理：Aサーバー全VC状況取得
        for pair in self.config_manager.config.get("server_pairs", []):
            server_id = pair.get("A_SERVER_ID")
            server = self.bot.get_guild(server_id)
            if not server:
                continue

            for vc in server.voice_channels:
                members = vc.members
                member_count = len(members)
                if member_count == 0:
                    continue

                embed = discord.Embed(
                    title=f"{vc.name}（{member_count}人）",
                    description="現在の通話参加者一覧",
                    timestamp=datetime.utcnow(),
                    color=discord.Color.blue()
                )
                for m in members:
                    embed.add_field(name=m.display_name, value=f"ID: {m.id}", inline=False)
                if members and members[0].avatar:
                    embed.set_thumbnail(url=members[0].avatar.url)

                vc_log_id = pair.get("DEBUG_CHANNEL")
                target_channel = self.bot.get_channel(vc_log_id)
                if target_channel:
                    await target_channel.send(embed=embed)

# ---------------- Cogセットアップ ----------------
async def setup(bot: commands.Bot):
    config_manager = getattr(bot, "config_manager", None)
    if not config_manager:
        raise RuntimeError("ConfigManager が bot にセットされていません")
    await bot.add_cog(VcCog(bot, config_manager))
