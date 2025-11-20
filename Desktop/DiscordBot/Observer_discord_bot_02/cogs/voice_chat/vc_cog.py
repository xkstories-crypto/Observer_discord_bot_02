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
            asyncio.create_task(self.force_debug("VcCog loaded"))
        except:
            print("[DEBUG] VcCog loaded")

    # ------------------------------------------------------
    # DEBUG_CHANNEL に強制送信（失敗しても print）
    # ------------------------------------------------------
    async def force_debug(self, message: str):
        for pair in self.config_manager.config.get("server_pairs", []):
            debug_id = pair.get("DEBUG_CHANNEL")
            if not debug_id:
                continue

            ch = self.bot.get_channel(debug_id)
            if ch is None:
                try:
                    ch = await self.bot.fetch_channel(debug_id)
                    await ch.send(f"[DEBUG] {message}")
                    return
                except Exception as e:
                    print(f"[DEBUG強制送信失敗: fetch_channel] {e}")
                    continue

            try:
                await ch.send(f"[DEBUG] {message}")
                return
            except Exception as e:
                print(f"[DEBUG強制送信失敗: send] {e}")
                continue

        print(f"[DEBUG未送信] {message}")

    # ------------------------------------------------------
    # VC状態変化を全ログする
    # ------------------------------------------------------
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.bot:
            return

        # ① まず受信確認
        await self.force_debug(
            f"VC STATE UPDATE: member={member} "
            f"before={getattr(before.channel, 'name', None)} "
            f"after={getattr(after.channel, 'name', None)}"
        )

        guild_id = member.guild.id
        server_conf = self.config_manager.get_server_config(guild_id)

        if not server_conf:
            await self.force_debug(f"サーバー設定なし guild={guild_id}")
            return

        server_a_id = server_conf.get("A_ID")
        vc_log_id = server_conf.get("VC_LOG_CHANNEL")

        # ② Aサーバー以外は無視
        if guild_id != server_a_id:
            await self.force_debug(f"Aサーバーではない guild={guild_id}")
            return

        # ③ VCログチャンネル取得（get_channel → fetch_channel）
        vc_log_channel = None

        # --- get_channel 試行 ---
        vc_log_channel = self.bot.get_channel(vc_log_id)
        await self.force_debug(
            f"get_channel({vc_log_id}) → {vc_log_channel}"
        )

        # --- fetch_channel fallback ---
        if vc_log_channel is None:
            try:
                vc_log_channel = await self.bot.fetch_channel(vc_log_id)
                await self.force_debug(
                    f"fetch_channel({vc_log_id}) 成功 → {vc_log_channel}"
                )
            except Exception as e:
                await self.force_debug(
                    f"fetch_channel({vc_log_id}) 失敗: {type(e).__name__}: {e}"
                )
                return

        # ④ VC参加 / VC退出の条件判定
        try:
            # 参加
            if before.channel is None and after.channel is not None:
                await self.force_debug("判定: VC参加ログを送信します")
                embed = discord.Embed(
                    title="VC参加",
                    description=f"🔊 **{member.display_name}** が **{after.channel.name}** に参加しました。",
                    color=discord.Color.green()
                )
                embed.set_footer(text=f"member id: {member.id}")
                await vc_log_channel.send(embed=embed)
                await self.force_debug("VC参加ログ送信完了")

            # 退出
            elif before.channel is not None and after.channel is None:
                await self.force_debug("判定: VC退出ログを送信します")
                embed = discord.Embed(
                    title="VC退出",
                    description=f"🔈 **{member.display_name}** が **{before.channel.name}** から退出しました。",
                    color=discord.Color.red()
                )
                embed.set_footer(text=f"member id: {member.id}")
                await vc_log_channel.send(embed=embed)
                await self.force_debug("VC退出ログ送信完了")

            else:
                await self.force_debug(
                    f"参加/退出に該当しないイベント: before={before.channel}, after={after.channel}"
                )

        except Exception as e:
            await self.force_debug(f"VCログ送信失敗: {type(e).__name__}: {e}")

    # ------------------------------------------------------
    # Aサーバーの VC 一覧を返すコマンド
    # ------------------------------------------------------
    @commands.command(name="debug_vc_full")
    async def debug_vc_full(self, ctx: commands.Context):
        await self.force_debug(f"!debug_vc_full 実行 by {ctx.author}")

        server_conf = self.config_manager.get_server_config(ctx.guild.id)
        if not server_conf:
            return await ctx.send("サーバー設定が見つかりません")

        server_a_id = server_conf.get("A_ID")
        guild_a = self.bot.get_guild(server_a_id)

        if not guild_a:
            return await ctx.send("Aサーバーが取得できません")

        for ch in guild_a.voice_channels:
            members = [m.display_name for m in ch.members]
            desc = ", ".join(members) if members else "(誰もいません)"

            embed = discord.Embed(
                title=f"VC: {ch.name}",
                description=desc,
                color=discord.Color.blue()
            )
            await ctx.send(embed=embed)

# ------------------------------------------------------
# Cog セットアップ
# ------------------------------------------------------
async def setup(bot: commands.Bot):
    config_manager = getattr(bot, "config_manager", None)
    if not config_manager:
        raise RuntimeError("ConfigManager が bot にセットされていません")
    await bot.add_cog(VcCog(bot, config_manager))
