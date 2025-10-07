# owner_cog.py
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
            if not conf:
                await ctx.send("[DEBUG] admin_only: configがNoneです")
                return False
            return ctx.author.id in conf.get("ADMIN_IDS", [])
        return commands.check(predicate)

    # ---------- Bot停止 ----------
    @commands.command()
    @commands.check(admin_only)
    async def stopbot(self, ctx):
        await ctx.send("🛑 Bot を停止します…")
        await self.bot.close()

    # ---------- サーバー設定表示（JSON全体） ----------
    @commands.command(name="show_config")
    @commands.check(admin_only)
    async def show_config(self, ctx):
        conf = self.config_manager.get_server_config(ctx.guild.id)
        if not conf:
            await ctx.send("[DEBUG] show_config: configがNoneです")
            return

        # JSON全体を表示（長い場合は省略）
        data_str = json.dumps(conf, indent=2, ensure_ascii=False)
        chunks = [data_str[i:i+1900] for i in range(0, len(data_str), 1900)]
        for chunk in chunks:
            await ctx.send(f"🗂 サーバー設定:\n```json\n{chunk}\n```")

    # ---------- サーバー・チャンネル確認 ----------
    @commands.command()
    @commands.check(admin_only)
    async def check(self, ctx):
        conf = self.config_manager.get_server_config(ctx.guild.id)
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
        mapping = conf.get("CHANNEL_MAPPING", {}).get("A_TO_B", {})
        if mapping:
            for src_id, dest_id in mapping.items():
                src_ch = self.bot.get_channel(int(src_id))
                dest_ch = self.bot.get_channel(dest_id)
                lines.append(f"  {src_id} → {dest_id} | src: {getattr(src_ch, 'name', '不明')}, dest: {getattr(dest_ch, 'name', '不明')}")
        else:
            lines.append("  （チャンネルマッピングなし）")

        # 管理者
        lines.append("ADMIN_IDS:")
        for aid in conf.get("ADMIN_IDS", []):
            user = self.bot.get_user(aid)
            lines.append(f"  {aid} → {user.name if user else 'ユーザー不在'}")

        # 追加チャンネル
        for key in ["DEBUG_CHANNEL", "VC_LOG_CHANNEL", "AUDIT_LOG_CHANNEL", "OTHER_CHANNEL"]:
            ch_id = conf.get(key)
            ch = self.bot.get_channel(ch_id) if ch_id else None
            lines.append(f"{key}: {ch.name if ch else ch_id}")

        # 読み取りユーザー
        read_users = []
        for uid in conf.get("READ_USERS", []):
            user = self.bot.get_user(uid)
            read_users.append(user.name if user else str(uid))
        lines.append(f"READ_USERS: {read_users}")

        # Discord 文字制限対応
        chunk_size = 1900
        output = "\n".join(lines)
        for i in range(0, len(output), chunk_size):
            await ctx.send("🧩 設定情報:\n```\n" + output[i:i+chunk_size] + "\n```")

    # ---------- 設定初期化 ----------
    @commands.command()
    @commands.check(admin_only)
    async def reset_config(self, ctx):
        self.config_manager.reset_config()
        await ctx.send("⚠ 設定ファイルを初期化しました（server_pairs は空です）")

# ---------- Cogセットアップ ----------
async def setup(bot: commands.Bot):
    config_manager = getattr(bot, "config_manager", None)
    if not config_manager:
        raise RuntimeError("ConfigManager が bot にセットされていません")
    await bot.add_cog(OwnerCog(bot, config_manager))
