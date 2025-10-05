# cogs/owner_cog.py
from discord.ext import commands
import json
import os
from config_manager import ConfigManager

CONFIG_FILE = "config_data.json"  # ✅ main.py に合わせて統一
PRESETS_FILE = "presets.json"


class OwnerCog(commands.Cog):
    def __init__(self, bot: commands.Bot, config_manager: ConfigManager):
        self.bot = bot
        self.config_manager = config_manager

    # ---------- 管理者チェック ----------
    def admin_only(self):
        async def predicate(ctx):
            pair = self.config_manager.get_pair_by_guild(ctx.guild.id)
            if not pair:
                return False
            return ctx.author.id in pair.get("ADMIN_IDS", [])
        return commands.check(predicate)

    # ---------- Bot停止 ----------
    @commands.command()
    async def stopbot(self, ctx):
        pair = self.config_manager.get_pair_by_guild(ctx.guild.id)
        if not pair or ctx.author.id not in pair.get("ADMIN_IDS", []):
            await ctx.send("❌ あなたは管理者ではありません。")
            return
        await ctx.send("🛑 Bot を停止します…")
        await self.bot.close()

    # ---------- チャンネル再取得 ----------
    @commands.command()
    @commands.check(lambda ctx: True)  # 管理者チェック関数呼び出し修正
    async def reload(self, ctx):
        pair = self.config_manager.get_pair_by_guild(ctx.guild.id)
        if not pair or ctx.author.id not in pair.get("ADMIN_IDS", []):
            await ctx.send("❌ あなたは管理者ではありません。")
            return

        lines = []

        vc_log_channel = self.bot.get_channel(pair.get("VC_LOG_CHANNEL"))
        audit_log_channel = self.bot.get_channel(pair.get("AUDIT_LOG_CHANNEL"))
        other_channel = self.bot.get_channel(pair.get("OTHER_CHANNEL"))

        lines.append(f"VC_LOG_CHANNEL ({pair.get('VC_LOG_CHANNEL')}): {vc_log_channel.name if vc_log_channel else '不明'}")
        lines.append(f"AUDIT_LOG_CHANNEL ({pair.get('AUDIT_LOG_CHANNEL')}): {audit_log_channel.name if audit_log_channel else '不明'}")
        lines.append(f"OTHER_CHANNEL ({pair.get('OTHER_CHANNEL')}): {other_channel.name if other_channel else '不明'}")

        mapping = pair.get("CHANNEL_MAPPING", {}).get("A_TO_B", {})
        for src_id, dest_id in mapping.items():
            src_channel = self.bot.get_channel(src_id)
            dest_channel = self.bot.get_channel(dest_id)
            lines.append(f"{src_id} -> {dest_id} | src: {getattr(src_channel, 'name', '不明')} → dest: {getattr(dest_channel, 'name', '不明')}")

        await ctx.send("♻️ チャンネル情報を再取得しました:\n```\n" + "\n".join(lines) + "\n```")

    # ---------- サーバー・チャンネル確認 ----------
    @commands.command()
    async def check(self, ctx):
        pair = self.config_manager.get_pair_by_guild(ctx.guild.id)
        if not pair or ctx.author.id not in pair.get("ADMIN_IDS", []):
            await ctx.send("❌ あなたは管理者ではありません。")
            return

        guild = ctx.guild
        lines = [
            f"Server ({guild.id}): {guild.name}",
            f"A_ID: {pair.get('A_ID')}",
            f"B_ID: {pair.get('B_ID')}",
            "CHANNEL_MAPPING (A → B):"
        ]

        for src_id, dest_id in pair.get("CHANNEL_MAPPING", {}).get("A_TO_B", {}).items():
            src_ch = self.bot.get_channel(src_id)
            dest_ch = self.bot.get_channel(dest_id)
            lines.append(f"  {src_id} → {dest_id} | src: {getattr(src_ch, 'name', '不明')}, dest: {getattr(dest_ch, 'name', '不明')}")

        lines.append("ADMIN_IDS:")
        for aid in pair.get("ADMIN_IDS", []):
            user = self.bot.get_user(aid)
            lines.append(f"  {aid} → {user.name if user else 'ユーザー不在'}")

        await ctx.send("🧩 設定情報:\n```\n" + "\n".join(lines) + "\n```")

    # ---------- プリセット保存 ----------
    @commands.command()
    async def save_preset(self, ctx, preset_name: str):
        pair = self.config_manager.get_pair_by_guild(ctx.guild.id)
        if not pair or ctx.author.id not in pair.get("ADMIN_IDS", []):
            await ctx.send("❌ あなたは管理者ではありません。")
            return

        presets = {}
        if os.path.exists(PRESETS_FILE):
            with open(PRESETS_FILE, "r", encoding="utf-8") as f:
                presets = json.load(f)

        presets[preset_name] = pair.copy()

        with open(PRESETS_FILE, "w", encoding="utf-8") as f:
            json.dump(presets, f, indent=2, ensure_ascii=False)

        await ctx.send(f"💾 プリセット `{preset_name}` を保存しました。")

    # ---------- プリセット適用 ----------
    @commands.command()
    async def load_preset(self, ctx, preset_name: str):
        pair = self.config_manager.get_pair_by_guild(ctx.guild.id)
        if not pair or ctx.author.id not in pair.get("ADMIN_IDS", []):
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

        self.config_manager.set_pair_by_guild(ctx.guild.id, preset_conf)
        self.config_manager.save()
        await ctx.send(f"✅ プリセット `{preset_name}` をこのサーバーに適用しました。")


# ---------- Cogセットアップ ----------
async def setup(bot: commands.Bot):
    config_manager = getattr(bot, "config_manager", None)
    if not config_manager:
        raise RuntimeError("ConfigManager が bot にセットされていません")
    await bot.add_cog(OwnerCog(bot, config_manager))
