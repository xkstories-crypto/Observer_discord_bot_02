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
    def admin_only(self):
        async def predicate(ctx):
            conf = self.config_manager.get_server_config(ctx.guild.id)
            return ctx.author.id in conf.get("ADMIN_IDS", [])
        return commands.check(predicate)

    # ---------- Bot停止 ----------
    @commands.command()
    @commands.check(admin_only)
    async def stopbot(self, ctx):
        print(f"[DEBUG] stopbot by {ctx.author} ({ctx.author.id}) in guild {ctx.guild.name}")
        await ctx.send("🛑 Bot を停止します…")
        await self.bot.close()

    # ---------- サーバー設定表示 ----------
    @commands.command(name="show_config")
    @commands.check(admin_only)
    async def show_config(self, ctx):
        conf = self.config_manager.get_server_config(ctx.guild.id)
        print(f"[DEBUG] show_config for guild {ctx.guild.name}: {conf}")  # デバッグ出力
        try:
            display_conf = {}
            for k, v in conf.items():
                if isinstance(v, dict) and not v:
                    display_conf[k] = "なし"
                elif v is None or v == "":
                    display_conf[k] = "未設定"
                else:
                    display_conf[k] = v

            data_str = json.dumps(display_conf, indent=2, ensure_ascii=False)
            if len(data_str) > 1900:
                data_str = data_str[:1900] + "..."
            await ctx.send(f"🗂 サーバー設定:\n```json\n{data_str}\n```")
        except Exception as e:
            print(f"[ERROR] show_config failed: {e}")
            await ctx.send(f"エラー: {e}")

    # ---------- チャンネル情報再取得 ----------
    @commands.command()
    @commands.check(admin_only)
    async def reload(self, ctx):
        conf = self.config_manager.get_server_config(ctx.guild.id)
        print(f"[DEBUG] reload channels for guild {ctx.guild.name}: {conf.get('CHANNEL_MAPPING')}")
        lines = []

        vc_log_channel = self.bot.get_channel(conf.get("VC_LOG_CHANNEL"))
        audit_log_channel = self.bot.get_channel(conf.get("AUDIT_LOG_CHANNEL"))
        other_channel = self.bot.get_channel(conf.get("OTHER_CHANNEL"))

        lines.append(f"VC_LOG_CHANNEL: {vc_log_channel.name if vc_log_channel else '未設定'}")
        lines.append(f"AUDIT_LOG_CHANNEL: {audit_log_channel.name if audit_log_channel else '未設定'}")
        lines.append(f"OTHER_CHANNEL: {other_channel.name if other_channel else '未設定'}")

        mapping = conf.get("CHANNEL_MAPPING", {})
        if not mapping:
            lines.append("CHANNEL_MAPPING: なし")
        else:
            for src_id, dest_id in mapping.items():
                src_ch = self.bot.get_channel(int(src_id))
                dest_ch = self.bot.get_channel(dest_id)
                lines.append(f"{src_id} -> {dest_id} | src: {getattr(src_ch, 'name', '不明')} → dest: {getattr(dest_ch, 'name', '不明')}")

        await ctx.send("♻️ チャンネル情報を再取得しました:\n```\n" + "\n".join(lines) + "\n```")

    # ---------- サーバー・チャンネル確認 ----------
    @commands.command()
    @commands.check(admin_only)
    async def check(self, ctx):
        conf = self.config_manager.get_server_config(ctx.guild.id)
        print(f"[DEBUG] check server/channels for guild {ctx.guild.name}: {conf}")  # デバッグ出力
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
                lines.append(f"  {src_id} → {dest_id} | src: {getattr(src_ch, 'name', '不明')}, dest: {getattr(dest_ch, 'name', '不明')}")

        admin_ids = conf.get("ADMIN_IDS", [])
        lines.append("ADMIN_IDS:")
        if not admin_ids:
            lines.append("  なし")
        else:
            for aid in admin_ids:
                user = self.bot.get_user(aid)
                lines.append(f"  {aid} → {user.name if user else 'ユーザー不在'}")

        await ctx.send("🧩 設定情報:\n```\n" + "\n".join(lines) + "\n```")

    # ---------- プリセット保存 ----------
    @commands.command()
    @commands.check(admin_only)
    async def save_preset(self, ctx, preset_name: str):
        conf = self.config_manager.get_server_config(ctx.guild.id)
        print(f"[DEBUG] save_preset {preset_name} for guild {ctx.guild.name}")
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
    @commands.check(admin_only)
    async def load_preset(self, ctx, preset_name: str):
        print(f"[DEBUG] load_preset {preset_name} for guild {ctx.guild.name}")
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
        await ctx.send(f"✅ プリセット `{preset_name}` をこのサーバーに適用しました。")


# ---------- Cogセットアップ ----------
async def setup(bot: commands.Bot):
    config_manager = getattr(bot, "config_manager", None)
    if not config_manager:
        raise RuntimeError("ConfigManager が bot にセットされていません")
    await bot.add_cog(OwnerCog(bot, config_manager))
