# cogs/owner_cog.py
from discord.ext import commands
import json
from config_manager import ConfigManager

class OwnerCog(commands.Cog):
    def __init__(self, bot: commands.Bot, config_manager: ConfigManager):
        self.bot = bot
        self.config_manager = config_manager

    # 管理者チェック
    def admin_only(self):
        async def predicate(ctx):
            pair = self.config_manager.get_pair_by_guild(ctx.guild.id)
            if not pair:
                return False
            return ctx.author.id in pair.get("ADMIN_IDS", [])
        return commands.check(predicate)

    # ---------- check コマンド ----------
    @commands.command()
    @commands.check(admin_only)
    async def check(self, ctx):
        pair = self.config_manager.get_pair_by_guild(ctx.guild.id)
        if not pair:
            await ctx.send("このサーバーはペア設定されていません。")
            return

        lines = []
        guild = ctx.guild
        lines.append(f"Server ({guild.id}): {guild.name}")
        lines.append(f"A_ID: {pair['A_ID']}")
        lines.append(f"B_ID: {pair['B_ID']}")
        lines.append("CHANNEL_MAPPING (A → B):")
        for src_id, dest_id in pair.get("CHANNEL_MAPPING", {}).get("A_TO_B", {}).items():
            src_ch = self.bot.get_channel(src_id)
            dest_ch = self.bot.get_channel(dest_id)
            lines.append(f"  {src_id} -> {dest_id} | src: {getattr(src_ch, 'name', '不明')}, dest: {getattr(dest_ch, 'name', '不明')}")
        lines.append("ADMIN_IDS:")
        for aid in pair.get("ADMIN_IDS", []):
            user = self.bot.get_user(aid)
            lines.append(f"  {aid} -> {user.name if user else 'ユーザー不在'}")

        await ctx.send("```\n" + "\n".join(lines) + "\n```")

    # ---------- show_config コマンド ----------
    @commands.command()
    @commands.check(admin_only)
    async def show_config(self, ctx):
        data = self.config_manager.get_all_pairs()
        await ctx.send(f"```json\n{json.dumps(data, indent=2, ensure_ascii=False)}\n```")

# Cog setup
async def setup(bot: commands.Bot):
    config_manager = getattr(bot, "config_manager", None)
    if not config_manager:
        raise RuntimeError("ConfigManager が bot にセットされていません")
    await bot.add_cog(OwnerCog(bot, config_manager))
