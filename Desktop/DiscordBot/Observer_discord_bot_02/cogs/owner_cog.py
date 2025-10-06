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
            pair = self.config_manager.get_pair_by_guild(ctx.guild.id)
            if not pair:
                await ctx.send("[DEBUG] admin_only: configがNoneです")
                return False
            b_guild_id = pair["B_ID"]
            conf = self.config_manager.get_server_config(b_guild_id)
            admin_ids = conf.get("ADMIN_IDS", [])
            return ctx.author.id in admin_ids
        return commands.check(predicate)

    # ---------- Bot停止 ----------
    @commands.command(name="stopbot")
    @commands.check(admin_only)
    async def stopbot(self, ctx):
        await ctx.send("🛑 Bot を停止します…")
        await self.bot.close()

    # ---------- サーバー設定表示 ----------
    @commands.command(name="show_config")
    @commands.check(admin_only)
    async def show_config(self, ctx):
        pair = self.config_manager.get_pair_by_guild(ctx.guild.id)
        if not pair:
            await ctx.send("[DEBUG] show_config: configがNoneです")
            return

        b_guild_id = pair["B_ID"]
        conf = self.config_manager.get_server_config(b_guild_id)

        data_str = json.dumps(conf, indent=2, ensure_ascii=False)
        if len(data_str) > 1900:
            data_str = data_str[:1900] + "..."
        await ctx.send(f"🗂 サーバー設定:\n```json\n{data_str}\n```")

    # ---------- サーバー・チャンネル確認 ----------
    @commands.command(name="check")
    @commands.check(admin_only)
    async def check(self, ctx):
        pair = self.config_manager.get_pair_by_guild(ctx.guild.id)
        if not pair:
            await ctx.send("[DEBUG] check: configがNoneです")
            return

        b_guild_id = pair["B_ID"]
        conf = self.config_manager.get_server_config(b_guild_id)

        guild = self.bot.get_guild(b_guild_id)
        lines = [
            f"Server ({guild.id}): {guild.name}",
            f"SERVER_A_ID: {conf.get('A_ID')}",
            f"SERVER_B_ID: {conf.get('B_ID')}",
            "CHANNEL_MAPPING:"
        ]
        for src_id, dest_id in conf.get("CHANNEL_MAPPING", {}).get("A_TO_B", {}).items():
            src_ch = self.bot.get_channel(int(src_id))
            dest_ch = self.bot.get_channel(dest_id)
            lines.append(
                f"  {src_id} → {dest_id} | src: {getattr(src_ch, 'name', '不明')}, dest: {getattr(dest_ch, 'name', '不明')}"
            )

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
