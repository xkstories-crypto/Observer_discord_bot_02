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

    # ---------- 管理者チェック ----------
    def is_admin(self, ctx):
        conf = self.config_manager.get_server_config(ctx.guild.id)
        return ctx.author.id in conf.get("ADMIN_IDS", [])

    # ---------- Bot停止 ----------
    @commands.command()
    async def stopbot(self, ctx):
        if not self.is_admin(ctx):
            await ctx.send("❌ あなたは管理者ではありません。")
            return
        await ctx.send(f"[DEBUG] stopbot 呼び出し: guild={ctx.guild.name} ({ctx.guild.id}), author={ctx.author}")
        await ctx.send("🛑 Bot を停止します…")
        await self.bot.close()

    # ---------- サーバー設定表示 ----------
    @commands.command(name="show_config")
    async def show_config(self, ctx):
        if not self.is_admin(ctx):
            await ctx.send("❌ あなたは管理者ではありません。")
            return

        conf = self.config_manager.get_server_config(ctx.guild.id)
        await ctx.send(f"[DEBUG] show_config 呼び出し: guild={ctx.guild.name} ({ctx.guild.id}), author={ctx.author}")

        try:
            data_str = json.dumps(conf, indent=2, ensure_ascii=False)
            if len(data_str) > 1900:
                data_str = data_str[:1900] + "..."
            await ctx.send(f"🗂 サーバー設定:\n```json\n{data_str}\n```")
        except Exception as e:
            await ctx.send(f"エラー: {e}")

    # ---------- チャンネル情報再取得 ----------
    @commands.command()
    async def reload(self, ctx):
        if not self.is_admin(ctx):
            await ctx.send("❌ あなたは管理者ではありません。")
            return

        conf = self.config_manager.get_server_config(ctx.guild.id)
        await ctx.send(f"[DEBUG] reload 呼び出し: guild={ctx.guild.name} ({ctx.guild.id}), author={ctx.author}")

        lines = []

        vc_log_channel = self.bot.get_channel(conf.get("VC_LOG_CHANNEL"))
        audit_log_channel = self.bot.get_channel(conf.get("AUDIT_LOG_CHANNEL"))
        other_channel = self.bot.get_channel(conf.get("OTHER_CHANNEL"))

        lines.append(f"VC_LOG_CHANNEL: {vc_log_channel.name if vc_log_channel else '不明'}")
        lines.append(f"AUDIT_LOG_CHANNEL: {audit_log_channel.name if audit_log_channel else '不明'}")
        lines.append(f"OTHER_CHANNEL: {other_channel.name if other_channel else '不明'}")

        mapping = conf.get("CHANNEL_MAPPING", {})
        for src_id, dest_id in mapping.items():
            src_ch = self.bot.get_channel(int(src_id))
            dest_ch = self.bot.get_channel(dest_id)
            lines.append(f"{src_id} -> {dest_id} | src: {getattr(src_ch, 'name', '不明')} → dest: {getattr(dest_ch, 'name', '不明')}")

        await ctx.send("♻️ チャンネル情報を再取得しました:\n```\n" + "\n".join(lines) + "\n```")

    # ---------- サーバー・チャンネル確認 ----------
    @commands.command()
    async def check(self, ctx):
        if not self.is_admin(ctx):
            await ctx.send("❌ あなたは管理者ではありません。")
            return

        conf = self.config_manager.get_server_config(ctx.guild.id)
        await ctx.send(f"[DEBUG] check 呼び出し: guild={ctx.guild.name} ({ctx.guild.id}), author={ctx.author}")

        guild = ctx.guild
        lines = [
            f"Server ({guild.id}): {guild.name}",
            f"SERVER_A_ID: {conf.get('SERVER_A_ID')}",
            f"SERVER_B_ID: {conf.get('SERVER_B_ID')}",
            "CHANNEL_MAPPING:"
        ]
        for src_id, dest_id in conf.get("CHANNEL_MAPPING", {}).items():
            src_ch = self.bot.get_channel(int(src_id))
            dest_ch = self.bot.get_channel(dest_id)
            lines.append(f"  {src_id} → {dest_id} | src: {getattr(src_ch, 'name', '不明')}, dest: {getattr(dest_ch, 'name', '不明')}")

        lines.append("ADMIN_IDS:")
        for aid in conf.get("ADMIN_IDS", []):
            user = self.bot.get_user(aid)
            lines.append(f"  {aid} → {user.name if user else 'ユーザー不在'}")

        await ctx.send("🧩 設定情報:\n```\n" + "\n".join(lines) + "\n```")

    # ---------- プリセット保存 ----------
    @commands.command()
    async def save_preset(self, ctx, preset_name: str):
        if not self.is_admin(ctx):
            await ctx.send("❌ あなたは管理者ではありません。")
            return

        conf = self.config_manager.get_server_config(ctx.guild.id)
        await ctx.send(f"[DEBUG] save_preset 呼び出し: {preset_name} by {ctx.author}")

        presets = {}
        if os.path.exists(PRESETS_FILE):
            with open(PRESETS_FILE, "r", encoding="utf-8") as f:
                presets = json.load(f)

        presets[preset_name] = conf.copy()
        with open(PRESETS_FILE, "w", encoding="utf-8") as f:
            json.dump(presets, f, indent=2, ensure_ascii=False)

        await ctx.send(f"💾 プリセット `{preset_name}` を保存しました。")

    # ---------- プリセット適用 ----------
    @commands.command()
    async def load_preset(self, ctx, preset_name: str):
        if not self.is_admin(ctx):
            await ctx.send("❌ あなたは管理者ではありません。")
            return

        if not os.path.exists(PRESETS_FILE):
            await ctx.send("プリセットファイルが存在しません。")
            return

        with open(PRESETS_FILE, "r", encoding="utf-8") as f:
            presets = json.load(f)

        preset_conf = presets.get(preset_name)
        if not preset_conf:
            await ctx.send(f"プリセット `{preset_name}` が見つかりません。")
            return

        self.config_manager.set_server_config(ctx.guild.id, preset_conf)
        await ctx.send(f"[DEBUG] load_preset 適用: {preset_name} by {ctx.author}")
        await ctx.send(f"✅ プリセット `{preset_name}` をこのサーバーに適用しました。")


# ---------- Cogセットアップ ----------
async def setup(bot: commands.Bot):
    config_manager = getattr(bot, "config_manager", None)
    if not config_manager:
        raise RuntimeError("ConfigManager が bot にセットされていません")
    await bot.add_cog(OwnerCog(bot, config_manager))
