# cogs/voice_chat/vc_cog.py

from discord.ext import commands
import discord
from discord.utils import get
from config_manager import ConfigManager
import asyncio
from datetime import datetime, timezone, timedelta

JST = timezone(timedelta(hours=9))


class VcCog(commands.Cog):
    def __init__(self, bot: commands.Bot, config_manager: ConfigManager):
        self.bot = bot
        self.config_manager = config_manager

        try:
            asyncio.create_task(self.send_debug("[DEBUG] VcCog loaded"))
        except Exception:
            print("[DEBUG] VcCog loaded")

    # ─────────────────────────────────────────────
    # デバッグ送信用
    # ─────────────────────────────────────────────
    async def send_debug(self, message: str, fallback_channel: discord.TextChannel = None):
        target_channel = fallback_channel

        # config の DEBUG_CHANNEL を探す
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

        # チャンネルに送信を試みる
        if target_channel:
            try:
                await target_channel.send(f"[DEBUG] {message}")
                return
            except Exception as e:
                print(f"[DEBUG送信失敗] {message} ({e})")

        print(f"[DEBUG] {message} (チャンネル未設定または送信失敗)")

    # ─────────────────────────────────────────────
    # Embed で VC ログを送信
    # ─────────────────────────────────────────────
    async def send_embed_vc_log(self, guild, member, before, after):
        try:
            server_conf = self.config_manager.get_server_config(guild.id)
            if not server_conf:
                return

            vc_log_ch_id = server_conf.get("VC_LOG_CHANNEL")
            vc_log_ch = guild.get_channel(vc_log_ch_id)
            if not vc_log_ch:
                await self.send_debug(f"VC_LOG_CHANNEL 見つからん id={vc_log_ch_id}")
                return

            # ── 参加 / 退出 / 移動 判定 ──
            if before.channel is None and after.channel is not None:
                title = "🟢 VC参加"
                description = f"**{member.display_name}** が **「{after.channel.name}」** に参加しました。"
                color = 0x2ECC71

            elif before.channel is not None and after.channel is None:
                title = "🔴 VC退出"
                description = f"**{member.display_name}** が **「{before.channel.name}」** から退出しました。"
                color = 0xE74C3C

            else:
                title = "🔁 VC移動"
                description = (
                    f"**{member.display_name}** が "
                    f"**「{before.channel.name}」 → 「{after.channel.name}」** に移動しました。"
                )
                color = 0x3498DB

            # ── Embed 作成 ──
            embed = discord.Embed(
                title=title,
                description=description,
                color=color,
                timestamp=datetime.now(JST)
            )

            embed.set_author(
                name=member.display_name,
                icon_url=member.display_avatar.url
            )

            embed.set_footer(text="VC Log")

            await vc_log_ch.send(embed=embed)

        except Exception as e:
            await self.send_debug(f"send_embed_vc_log エラー: {e}")

    # ─────────────────────────────────────────────
    # VC状態変化（メイン処理）
    # ─────────────────────────────────────────────
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.bot or not member.guild:
            return

        await self.send_debug(
            f"VC状態変化: member={member.display_name}, "
            f"before={getattr(before.channel, 'name', None)}, "
            f"after={getattr(after.channel, 'name', None)}"
        )

        server_conf = self.config_manager.get_server_config(member.guild.id)
        if not server_conf:
            await self.send_debug("このサーバー設定は見つからない")
            return

        # Aサーバー以外ではログ送らない
        if member.guild.id != server_conf.get("A_ID"):
            await self.send_debug(f"Aサーバーじゃない (guild={member.guild.id})")
            return

        # Embed版 VC ログを送信
        await self.send_embed_vc_log(member.guild, member, before, after)

    # ─────────────────────────────────────────────
    # コマンド：AサーバーのVC一覧参照
    # ─────────────────────────────────────────────
    @commands.command(name="debug_vc_full")
    async def debug_vc_full(self, ctx: commands.Context):
        await self.send_debug(
            f"!debug_vc_full 実行 by {ctx.author.display_name}",
            fallback_channel=ctx.channel
        )

        server_conf = self.config_manager.get_server_config(ctx.guild.id)
        if not server_conf:
            return await ctx.send("サーバー設定がない。")

        guild_a = self.bot.get_guild(server_conf.get("A_ID"))
        if not guild_a:
            return await ctx.send("Aサーバー見つからない。")

        vc_list = []
        for ch in guild_a.voice_channels:
            mems = ", ".join([m.display_name for m in ch.members]) or "(誰もいません)"
            vc_list.append(f"**{ch.name}**: {mems}")

        text = "\n".join(vc_list)
        await ctx.send(f"📋 **Aサーバー VC一覧：**\n{text}")

        await self.send_debug("VC一覧送信完了", fallback_channel=ctx.channel)


# ─────────────────────────────────────────────
# Cog セットアップ
# ─────────────────────────────────────────────
async def setup(bot: commands.Bot):
    config_manager = getattr(bot, "config_manager", None)
    if not config_manager:
        raise RuntimeError("ConfigManager が bot にセットされていません")
    await bot.add_cog(VcCog(bot, config_manager))
