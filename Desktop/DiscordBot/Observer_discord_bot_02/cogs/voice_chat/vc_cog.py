from discord.ext import commands
import json
from config_manager import ConfigManager

class VcCog(commands.Cog):
    def __init__(self, bot: commands.Bot, config_manager: ConfigManager):
        self.bot = bot
        self.config_manager = config_manager

    # ---------- VC参加/退出ログ ----------
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        print(f"[DEBUG] voice_state_update: {member}, before={before.channel}, after={after.channel}")
        if not member.guild:
            return

        server_conf = self.config_manager.get_server_config(member.guild.id)
        if not server_conf:
            return

        server_a_id = server_conf.get("A_ID")
        vc_log_channel_id = server_conf.get("VC_LOG_CHANNEL")

        if member.guild.id != server_a_id:
            return

        vc_log_channel = self.bot.get_channel(vc_log_channel_id)
        if not vc_log_channel:
            return

        if before.channel is None and after.channel is not None:
            await vc_log_channel.send(f"🔊 {member.display_name} が {after.channel.name} に参加しました。")
        elif before.channel is not None and after.channel is None:
            await vc_log_channel.send(f"🔈 {member.display_name} が {before.channel.name} から退出しました。")

    # ---------- デバッグ用: VC設定全表示 ----------
    @commands.command(name="debug_vc_full")
    async def debug_vc_full(self, ctx: commands.Context):
        guild_id = ctx.guild.id
        author_id = ctx.author.id

        # 管理者チェック
        server_conf = self.config_manager.get_server_config(guild_id)
        if not server_conf:
            await ctx.send("❌ このサーバーは設定されていません")
            return
        if author_id not in server_conf.get("ADMIN_IDS", []):
            await ctx.send("❌ 管理者ではありません")
            return

        # ローカル config
        local_config = server_conf
        local_text = json.dumps(local_config, indent=2, ensure_ascii=False)

        # Google Drive 上の config
        try:
            self.config_manager.drive_handler.download_config("tmp_config.json")
            with open("tmp_config.json", "r", encoding="utf-8") as f:
                drive_config = json.load(f)
            drive_text = json.dumps(drive_config, indent=2, ensure_ascii=False)
        except Exception as e:
            drive_text = f"⚠️ Google Drive 読み込み失敗: {e}"

        CHUNK_SIZE = 1800

        await ctx.send("✅ **ローカル VC 設定**")
        for i in range(0, len(local_text), CHUNK_SIZE):
            await ctx.send(f"```json\n{local_text[i:i+CHUNK_SIZE]}\n```")

        await ctx.send("✅ **Google Drive VC 設定**")
        for i in range(0, len(drive_text), CHUNK_SIZE):
            await ctx.send(f"```json\n{drive_text[i:i+CHUNK_SIZE]}\n```")

        await ctx.send("✅ VC デバッグ完了")

# ---------- Cogセットアップ ----------
async def setup(bot: commands.Bot):
    config_manager = getattr(bot, "config_manager", None)
    if not config_manager:
        raise RuntimeError("ConfigManager が bot にセットされていません")
    await bot.add_cog(VcCog(bot, config_manager))
