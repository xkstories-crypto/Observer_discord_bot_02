# cogs/owner_cog.py
import discord
from discord.ext import commands
from config_manager import ConfigManager
import json

class OwnerCog(commands.Cog):
    def __init__(self, bot: commands.Bot, config_manager: ConfigManager):
        self.bot = bot
        self.config_manager = config_manager

    @commands.command(name="check")
    async def check(self, ctx: commands.Context):
        guild_id = ctx.guild.id
        pair = self.config_manager.get_server_config(guild_id)
        if not pair:
            await ctx.send("このサーバーはまだ登録されていません。")
            return

        a_guild = self.bot.get_guild(pair.get("A_ID"))
        b_guild = self.bot.get_guild(pair.get("B_ID"))

        a_name = a_guild.name if a_guild else f"Aサーバー ({pair.get('A_ID')}) 未取得"
        b_name = b_guild.name if b_guild else f"Bサーバー ({pair.get('B_ID')}) 未取得"

        channel_mapping = pair.get("CHANNEL_MAPPING", {}).get("A_TO_B", {})
        mapping_text = "\n".join([f"{a_id} → {b_id}" for a_id, b_id in channel_mapping.items()]) or "なし"

        admin_ids = pair.get("ADMIN_IDS", [])
        admin_mentions = ", ".join([f"<@{uid}>" for uid in admin_ids]) or "なし"

        embed = discord.Embed(title="サーバー設定確認", color=discord.Color.blue())
        embed.add_field(name="Aサーバー", value=a_name, inline=False)
        embed.add_field(name="Bサーバー", value=b_name, inline=False)
        embed.add_field(name="チャンネルマッピング (A → B)", value=mapping_text, inline=False)
        embed.add_field(name="管理者", value=admin_mentions, inline=False)

        await ctx.send(embed=embed)

    @commands.command(name="show_config")
    async def show_config(self, ctx: commands.Context):
        try:
            with open("config_data.json", "r", encoding="utf-8") as f:
                data = json.load(f)
            pretty_json = json.dumps(data, indent=2, ensure_ascii=False)
            if len(pretty_json) > 1900:
                await ctx.send("config_data.json が長すぎるため、ファイルとして送信します。")
                with open("config_data.json", "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                await ctx.send(file=discord.File("config_data.json"))
            else:
                await ctx.send(f"```json\n{pretty_json}\n```")
        except FileNotFoundError:
            await ctx.send("config_data.json が存在しません。")

def setup(bot: commands.Bot, config_manager: ConfigManager):
    bot.add_cog(OwnerCog(bot, config_manager))
