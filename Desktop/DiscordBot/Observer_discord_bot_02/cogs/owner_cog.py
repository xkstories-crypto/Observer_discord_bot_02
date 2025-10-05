# cogs/owner_cog.py
from discord.ext import commands
from config_manager import ConfigManager
import json
import os

CONFIG_FILE = "config_data.json"
PRESETS_FILE = "presets.json"

class OwnerCog(commands.Cog):
    def __init__(self, bot: commands.Bot, config_manager: ConfigManager):
        self.bot = bot
        self.config_manager = config_manager

    def admin_only(self):
        async def predicate(ctx):
            conf = self.config_manager.get_server_config(ctx.guild.id)
            return ctx.author.id in conf.get("ADMIN_IDS", [])
        return commands.check(predicate)

    @commands.command()
    @commands.check(admin_only)
    async def stopbot(self, ctx):
        print(f"[DEBUG] stopbot by {ctx.author} ({ctx.author.id}) in guild {ctx.guild.name}")
        await ctx.send("🛑 Bot を停止します…")
        await self.bot.close()

    @commands.command(name="show_config")
    @commands.check(admin_only)
    async def show_config(self, ctx):
        conf = self.config_manager.get_server_config(ctx.guild.id)
        print(f"[DEBUG] show_config for guild {ctx.guild.name}: {conf}")

        try:
            lines = []
            for k, v in conf.items():
                if isinstance(v, dict) and not v:
                    v_display = "なし"
                elif isinstance(v, list) and not v:
                    v_display = "なし"
                elif v is None or v == "":
                    v_display = "未設定"
                else:
                    v_display = v
                lines.append(f"{k}: {v_display}")

            content = "🗂 サーバー設定:\n```\n" + "\n".join(lines) + "\n```"
            if len(content) > 2000:
                content = content[:1990] + "\n...```"
            await ctx.send(content)
        except Exception as e:
            print(f"[ERROR] show_config failed: {e}")
            await ctx.send(f"エラー: {e}")

    @commands.command()
    @commands.check(admin_only)
    async def check(self, ctx):
        conf = self.config_manager.get_server_config(ctx.guild.id)
        print(f"[DEBUG] check for guild {ctx.guild.name}: {conf}")

        guild = ctx.guild
        lines = [
            f"Server ({guild.id}): {guild.name}",
            f"SERVER_A_ID: {conf.get('SERVER_A_ID') or '未設定'}",
            f"SERVER_B_ID: {conf.get('SERVER_B_ID') or '未設定'}",
            "CHANNEL_MAPPING:"
        ]

        mapping = conf.get("CHANNEL_MAPPING", {})
        if not mapping:
            lines.append("  なし")
        else:
            for src_id, dest_id in mapping.items():
                src_ch = self.bot.get_channel(int(src_id))
                dest_ch = self.bot.get_channel(dest_id)
                lines.append(f"  {src_id} → {dest_id} | src: {getattr(src_ch, 'name', '未取得')} → dest: {getattr(dest_ch, 'name', '未取得')}")

        admin_ids = conf.get("ADMIN_IDS", [])
        lines.append("ADMIN_IDS:")
        if not admin_ids:
            lines.append("  なし")
        else:
            for aid in admin_ids:
                user = self.bot.get_user(aid)
                lines.append(f"  {aid} → {user.name if user else 'ユーザー不在'}")

        content = "🧩 設定情報:\n```\n" + "\n".join(lines) + "\n```"
        if len(content) > 2000:
            content = content[:1990] + "\n...```"
        await ctx.send(content)

# Cog setup
async def setup(bot: commands.Bot):
    config_manager = getattr(bot, "config_manager", None)
    if not config_manager:
        raise RuntimeError("ConfigManager が bot にセットされていません")
    await bot.add_cog(OwnerCog(bot, config_manager))
