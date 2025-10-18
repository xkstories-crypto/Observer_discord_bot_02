from discord.ext import commands
import json
from config_manager import ConfigManager

CONFIG_LOCAL_PATH = "data/config_store.json"

class DriveCog(commands.Cog):
    """Google Drive 関連コマンド"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.config_manager: ConfigManager = getattr(bot, "config_manager", None)
        if not self.config_manager:
            raise RuntimeError("ConfigManager が bot にセットされていません")

    @commands.command(name="show_show")
    async def show(self, ctx: commands.Context):
        """Google Drive 上の設定 JSON を表示"""
        if not self.config_manager.is_admin(ctx.guild.id, ctx.author.id):
            await ctx.send("❌ 管理者ではありません。")
            return

        try:
            self.config_manager.drive_handler.download_config(CONFIG_LOCAL_PATH)
            with open(CONFIG_LOCAL_PATH, "r", encoding="utf-8") as f:
                config = json.load(f)

            json_text = json.dumps(config, indent=2, ensure_ascii=False)
            if len(json_text) < 1900:
                await ctx.send(f"✅ Google Drive 上の設定 JSON\n```json\n{json_text}\n```")
            else:
                await ctx.send(f"✅ Google Drive 上の設定 JSON（先頭のみ表示）\n```json\n{json_text[:1900]}...\n```")
        except Exception as e:
            await ctx.send(f"⚠️ JSON 読み込みに失敗しました: {e}")


async def setup(bot: commands.Bot):
    await bot.add_cog(DriveCog(bot))
