from discord.ext import commands
import discord

class TransferCog(commands.Cog):
    def __init__(self, bot: commands.Bot, config_manager):
        self.bot = bot
        self.config_manager = config_manager

    async def send_debug(self, text: str, fallback_channel: discord.TextChannel = None):
        await self.bot.wait_until_ready()
        try:
            if fallback_channel:
                await fallback_channel.send(f"[DEBUG] {text}")
            else:
                print(f"[DEBUG LOG] {text}")
        except Exception as e:
            print(f"[DEBUG ERROR] {e}")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        # A→B転送のみ
        pair = self.config_manager.get_pair_by_guild(message.guild.id)
        if not pair or message.guild.id != pair.get("A_ID"):
            return

        dest_id = pair.get("CHANNEL_MAPPING", {}).get(str(message.channel.id))
        if not dest_id:
            return

        dest_guild = self.bot.get_guild(pair.get("B_ID"))
        dest_channel = dest_guild.get_channel(dest_id) if dest_guild else None
        if not dest_channel:
            return

        try:
            content = message.content.strip()
            if not content:
                return
            await dest_channel.send(f"[転送] {message.author.display_name}: {content}")
        except Exception as e:
            await self.send_debug(f"転送失敗: {e}", fallback_channel=message.channel)

    @commands.command(name="debug_test")
    async def debug_test(self, ctx: commands.Context):
        await self.send_debug("⚡デバッグ送信テスト⚡", fallback_channel=ctx.channel)
        await ctx.send("デバッグ送信を実行しました ✅")

async def setup(bot: commands.Bot):
    config_manager = getattr(bot, "config_manager", None)
    if not config_manager:
        raise RuntimeError("ConfigManager が bot にセットされていません")
    await bot.add_cog(TransferCog(bot, config_manager))
