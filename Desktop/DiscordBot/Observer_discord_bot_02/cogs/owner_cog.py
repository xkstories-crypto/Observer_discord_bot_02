# cogs/owner_cog.py
from discord.ext import commands
import json
import os
from config_manager import ConfigManager

CONFIG_FILE = "data/config_data.json"
PRESETS_FILE = "presets.json"

class OwnerCog(commands.Cog):
    def __init__(self, bot: commands.Bot, config_manager: ConfigManager):
        self.bot = bot
        self.config_manager = config_manager

    # ---------- 管理者チェック ----------
    def admin_only(self):
        async def predicate(ctx):
            server_conf = self.config_manager.get_server_config(ctx.guild.id)
            if not server_conf:
                return False
            return ctx.author.id in server_conf.get("ADMIN_IDS", [])
        return commands.check(predicate)

    # ---------- Bot停止 ----------
    @commands.command()
    async def stopbot(self, ctx):
        server_conf = self.config_manager.get_server_config(ctx.guild.id)
        if not server_conf or ctx.author.id not in server_conf.get("ADMIN_IDS", []):
            await ctx.send("あなたは管理者ではありません。")
            return
        await ctx.send("Bot を停止します…")
        await self.bot.close()

    # ---------- チャンネル再取得 ----------
    @commands.command()
    @commands.check(admin_only)
    async def reload(self, ctx):
        server_conf = self.config_manager.get_server_config(ctx.guild.id)
        lines = []

        # ログチャンネル再取得
        vc_log_channel = self.bot.get_channel(server_conf.get("VC_LOG_CHANNEL"))
        audit_log_channel = self.bot.get_channel(server_conf.get("AUDIT_LOG_CHANNEL"))
        other_channel = self.bot.get_channel(server_conf.get("OTHER_CHANNEL"))
        lines.append(f"VC_LOG_CHANNEL ({server_conf.get('VC_LOG_CHANNEL')}): {vc_log_channel.name if vc_log_channel else '不明'}")
        lines.append(f"AUDIT_LOG_CHANNEL ({server_conf.get('AUDIT_LOG_CHANNEL')}): {audit_log_channel.name if audit_log_channel else '不明'}")
        lines.append(f"OTHER_CHANNEL ({server_conf.get('OTHER_CHANNEL')}): {other_channel.name if other_channel else '不明'}")

        # チャンネルマッピング再取得
        mapping = server_conf.get("CHANNEL_MAPPING", {})
        for src_id, dest_id in mapping.items():
            src_channel = self.bot.get_channel(int(src_id))
            dest_channel = self.bot.get_channel(dest_id)
            lines.append(f"{src_id} -> {dest_id} | src_name: {getattr(src_channel, 'name', '不明')}, dest_name: {getattr(dest_channel, 'name', '不明')}")

        await ctx.send("チャンネル情報を再取得しました:\n```\n" + "\n".join(lines) + "\n```")

    # ---------- サーバー・チャンネル確認 ----------
    @commands.command()
    @commands.check(admin_only)
    async def check(self, ctx):
        lines = []
        guild = ctx.guild
        server_conf = self.config_manager.get_server_config(guild.id)

        lines.append(f"Server ({guild.id}): {guild.name}")

        # SERVER_A_ID / SERVER_B_ID
        lines.append(f"SERVER_A_ID: {server_conf.get('SERVER_A_ID')}")
        lines.append(f"SERVER_B_ID: {server_conf.get('SERVER_B_ID')}")

        # CHANNEL_MAPPING
        lines.append("CHANNEL_MAPPING:")
        for src_id, dest_id in server_conf.get("CHANNEL_MAPPING", {}).items():
            src_channel = self.bot.get_channel(int(src_id))
            dest_channel = self.bot.get_channel(dest_id)
            lines.append(f"  {src_id} -> {dest_id} | src_name: {getattr(src_channel, 'name', '不明')}, dest_name: {getattr(dest_channel, 'name', '不明')}")

        # READ_GROUPS
        lines.append("READ_GROUPS:")
        for group_name, group_ids in server_conf.get("READ_GROUPS", {}).items():
            lines.append(f"  {group_name}: {group_ids}")

        # ADMIN_IDS
        lines.append("ADMIN_IDS:")
        for admin_id in server_conf.get("ADMIN_IDS", []):
            user = self.bot.get_user(admin_id)
            lines.append(f"  {admin_id} -> {user.name if user else 'ユーザー不在'}")

        # ログチャンネル
        vc_log_channel = self.bot.get_channel(server_conf.get("VC_LOG_CHANNEL"))
        audit_log_channel = self.bot.get_channel(server_conf.get("AUDIT_LOG_CHANNEL"))
        other_channel = self.bot.get_channel(server_conf.get("OTHER_CHANNEL"))
        lines.append(f"VC_LOG_CHANNEL: {vc_log_channel.name if vc_log_channel else '不明'}")
        lines.append(f"AUDIT_LOG_CHANNEL: {audit_log_channel.name if audit_log_channel else '不明'}")
        lines.append(f"OTHER_CHANNEL: {other_channel.name if other_channel else '不明'}")

        # READ_USERS
        lines.append("READ_USERS:")
        for user_id in server_conf.get("READ_USERS", []):
            user = self.bot.get_user(user_id)
            lines.append(f"  {user_id} -> {user.name if user else 'ユーザー不在'}")

        await ctx.send("```\n" + "\n".join(lines) + "\n```")

    # ---------- プリセット保存 ----------
    @commands.command()
    @commands.check(admin_only)
    async def save_preset(self, ctx, preset_name: str):
        server_conf = self.config_manager.get_server_config(ctx.guild.id)
        presets = {}
        if os.path.exists(PRESETS_FILE):
            with open(PRESETS_FILE, "r", encoding="utf-8") as f:
                presets = json.load(f)
        presets[preset_name] = server_conf.copy()
        with open(PRESETS_FILE, "w", encoding="utf-8") as f:
            json.dump(presets, f, indent=2, ensure_ascii=False)
        await ctx.send(f"プリセット `{preset_name}` を保存しました。")

    # ---------- プリセット適用 ----------
    @commands.command()
    @commands.check(admin_only)
    async def load_preset(self, ctx, preset_name: str):
        if not os.path.exists(PRESETS_FILE):
            await ctx.send("プリセットが存在しません。")
            return
        with open(PRESETS_FILE, "r", encoding="utf-8") as f:
            presets = json.load(f)
        preset_conf = presets.get(preset_name)
        if not preset_conf:
            await ctx.send(f"プリセット `{preset_name}` が存在しません。")
            return
        self.config_manager.set_server_config(ctx.guild.id, preset_conf)
        self.config_manager.save()
        await ctx.send(f"プリセット `{preset_name}` をこのサーバーに適用しました。")

# ---------- Cogセットアップ ----------
async def setup(bot: commands.Bot):
    config_manager = getattr(bot, "config_manager", None)
    if not config_manager:
        raise RuntimeError("ConfigManager が bot にセットされていません")
    await bot.add_cog(OwnerCog(bot, config_manager))
