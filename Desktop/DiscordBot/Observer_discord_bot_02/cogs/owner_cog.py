# cogs/owner_cog.py
from discord.ext import commands
from config_manager import ConfigManager
import json

class OwnerCog(commands.Cog):
    def __init__(self, bot: commands.Bot, config_manager: ConfigManager):
        self.bot = bot
        self.config_manager = config_manager

    # ---------- 管理者チェック ----------
    def admin_only(self):
        async def predicate(ctx):
            conf = self.config_manager.get_server_config(ctx.guild.id)
            await ctx.send(f"[DEBUG] admin_only: conf={conf}")
            if not conf:
                await ctx.send("[DEBUG] admin_only: configがNoneです")
                return False
            admin_ids = conf.get("ADMIN_IDS", [])
            await ctx.send(f"[DEBUG] admin_only: ADMIN_IDS={admin_ids}, author_id={ctx.author.id}")
            return ctx.author.id in admin_ids
        return commands.check(predicate)

    # ---------- Bot停止 ----------
    @commands.command()
    @commands.check(admin_only)
    async def stopbot(self, ctx):
        await ctx.send("🛑 Bot を停止します…")
        await self.bot.close()

    # ---------- サーバー設定表示 ----------
    @commands.command(name="show_config")
    @commands.check(admin_only)
    async def show_config(self, ctx):
        await ctx.send(f"[DEBUG] show_config 呼ばれた by {ctx.author}")

        # デバッグ1: config 全体
        await ctx.send(f"[DEBUG] 現在の config:\n```json\n{json.dumps(self.config_manager.config, indent=2, ensure_ascii=False)}\n```")

        # デバッグ2: guild_id
        await ctx.send(f"[DEBUG] ctx.guild.id: {ctx.guild.id}, type: {type(ctx.guild.id)}")

        conf = self.config_manager.get_server_config(ctx.guild.id)

        # デバッグ3: get_server_config の返り値
        await ctx.send(f"[DEBUG] get_server_config の返り値: {conf}")

        if not conf:
            await ctx.send("[DEBUG] show_config: configがNoneです")
            return

        try:
            data_str = json.dumps(conf, indent=2, ensure_ascii=False)
            if len(data_str) > 1900:
                data_str = data_str[:1900] + "..."
            await ctx.send(f"🗂 サーバー設定:\n```json\n{data_str}\n```")
        except Exception as e:
            await ctx.send(f"[DEBUG] show_config: エラー {e}")

    # ---------- サーバー・チャンネル確認 ----------
    @commands.command()
    @commands.check(admin_only)
    async def check(self, ctx):
        await ctx.send(f"[DEBUG] check 呼ばれた by {ctx.author}")

        # デバッグ1: config 全体
        await ctx.send(f"[DEBUG] 現在の config:\n```json\n{json.dumps(self.config_manager.config, indent=2, ensure_ascii=False)}\n```")

        # デバッグ2: guild_id
        await ctx.send(f"[DEBUG] ctx.guild.id: {ctx.guild.id}, type: {type(ctx.guild.id)}")

        conf = self.config_manager.get_server_config(ctx.guild.id)

        # デバッグ3: get_server_config の返り値
        await ctx.send(f"[DEBUG] get_server_config の返り値: {conf}")

        if not conf:
            await ctx.send("[DEBUG] check: configがNoneです")
            return

        guild = ctx.guild
        lines = [
            f"Server ({guild.id}): {guild.name}",
            f"SERVER_A_ID: {conf.get('A_ID')}",
            f"SERVER_B_ID: {conf.get('B_ID')}",
            "CHANNEL_MAPPING:"
        ]
        for src_id, dest_id in conf.get("CHANNEL_MAPPING", {}).get("A_TO_B", {}).items():
            src_ch = self.bot.get_channel(int(src_id))
            dest_ch = self.bot.get_channel(dest_id)
            lines.append(f"  {src_id} → {dest_id} | src: {getattr(src_ch, 'name', '不明')}, dest: {getattr(dest_ch, 'name', '不明')}")

        lines.append("ADMIN_IDS:")
        for aid in conf.get("ADMIN_IDS", []):
            user = self.bot.get_user(aid)
            lines.append(f"  {aid} → {user.name if user else 'ユーザー不在'}")

        await ctx.send("🧩 設定情報:\n```\n" + "\n".join(lines) + "\n```")

# ---------- Cogセットアップ ----------
async def setup(bot: commands.Bot):
    config_manager = getattr(bot, "config_manager", None)
    if not config_manager:
        raise RuntimeError("ConfigManager が bot にセットされていません")
    await bot.add_cog(OwnerCog(bot, config_manager))
