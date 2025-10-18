from discord.ext import commands
import json
from google_api.sa_utils import build_service_account_json
from config_manager import ConfigManager

class SaCog(commands.Cog):
    """サービスアカウント関連コマンド"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.config_manager: ConfigManager = getattr(bot, "config_manager", None)
        if not self.config_manager:
            raise RuntimeError("ConfigManager が bot にセットされていません")
        self.service_json = build_service_account_json()

    @commands.command(name="check_sa")
    async def check_sa(self, ctx: commands.Context):
        """サービスアカウント JSON を表示"""
        await ctx.send(f"✅ SERVICE_ACCOUNT_JSON 内容\n```json\n{json.dumps(self.service_json, indent=2)}\n```")


async def setup(bot: commands.Bot):
    await bot.add_cog(SaCog(bot))
