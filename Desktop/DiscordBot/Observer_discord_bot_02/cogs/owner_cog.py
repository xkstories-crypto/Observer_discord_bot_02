# cogs/owner_cog.py
from discord.ext import commands
from config import SERVER_A_ID, SERVER_B_ID, CHANNEL_MAPPING, VC_LOG_CHANNEL, AUDIT_LOG_CHANNEL, ADMIN_IDS, READ_USERS
import json
import os

CONFIG_FILE = "data/config_data.json"
PRESETS_FILE = "presets.json"

class OwnerCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # 管理者チェック用デコレーター
    def admin_only(self):
        async def predicate(ctx):
            return ctx.author.id in ADMIN_IDS
        return commands.check(predicate)

    # ---------- Bot停止 ----------
    @commands.command()
    async def stopbot(self, ctx):
        if ctx.author.id not in ADMIN_IDS:
            await ctx.send("あなたは管理者ではありません。")
            return
        await ctx.send("Bot を停止します…")
        await self.bot.close()

    # ---------- チャンネル再取得 ----------
    @commands.command()
    async def reload(self, ctx):
        if ctx.author.id not in ADMIN_IDS:
            await ctx.send("あなたは管理者ではありません。")
            return

        lines = []

        # ログチャンネル再取得
        vc_log_channel = self.bot.get_channel(VC_LOG_CHANNEL)
        audit_log_channel = self.bot.get_channel(AUDIT_LOG_CHANNEL)
        lines.append(f"VC_LOG_CHANNEL ({VC_LOG_CHANNEL}): {vc_log_channel.name if vc_log_channel else '不明'}")
        lines.append(f"AUDIT_LOG_CHANNEL ({AUDIT_LOG_CHANNEL}): {audit_log_channel.name if audit_log_channel else '不明'}")

        # チャンネルマッピング再取得
        for src_id, dest_id in CHANNEL_MAPPING.items():
            dest_channel = self.bot.get_channel(dest_id)
            lines.append(f"{src_id} -> {dest_channel.name if dest_channel else dest_id}")

        await ctx.send("チャンネル情報を再取得しました:\n```\n" + "\n".join(lines) + "\n```")

        # 自動で check コマンドを実行
        await self.check(ctx)

    # ---------- サーバー・チャンネル確認 ----------
    @commands.command()
    async def check(self, ctx):
        lines = []
        guild = ctx.guild

        if ctx.author.id in ADMIN_IDS:
            # 管理者は config の全情報表示
            guild_a = self.bot.get_guild(SERVER_A_ID)
            guild_b = self.bot.get_guild(SERVER_B_ID)
            lines.append(f"Server A ({SERVER_A_ID}): {guild_a.name if guild_a else '不明'}")
            lines.append(f"Server B ({SERVER_B_ID}): {guild_b.name if guild_b else '不明'}")

            vc_log_channel = self.bot.get_channel(VC_LOG_CHANNEL)
            audit_log_channel = self.bot.get_channel(AUDIT_LOG_CHANNEL)
            lines.append(f"VC_LOG_CHANNEL ({VC_LOG_CHANNEL}): {vc_log_channel.name if vc_log_channel else '不明'}")
            lines.append(f"AUDIT_LOG_CHANNEL ({AUDIT_LOG_CHANNEL}): {audit_log_channel.name if audit_log_channel else '不明'}")

            for src_id, dest_id in CHANNEL_MAPPING.items():
                dest_channel = self.bot.get_channel(dest_id)
                lines.append(f"{src_id} -> {dest_channel.name if dest_channel else dest_id}")

            lines.append("\nADMIN_IDS:")
            for admin_id in ADMIN_IDS:
                user = self.bot.get_user(admin_id)
                lines.append(f"{admin_id} -> {user.name if user else 'ユーザー不在'}")

            lines.append("\nREAD_USERS:")
            for user_id in READ_USERS:
                user = self.bot.get_user(user_id)
                lines.append(f"{user_id} -> {user.name if user else 'ユーザー不在'}")
        else:
            # 一般ユーザーはコマンドを使ったサーバーIDのみ
            lines.append(f"Server ({guild.id})")

        await ctx.send("```\n" + "\n".join(lines) + "\n```")

    # ---------- プリセット保存 ----------
    @commands.command()
    async def save_preset(self, ctx, preset_name: str):
        if ctx.author.id not in ADMIN_IDS:
            await ctx.send("管理者のみ使用可能です。")
            return

        # config_data.json 読み込み
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config_data = json.load(f)
        else:
            await ctx.send("サーバー設定が存在しません。まず /edit_config を実行してください。")
            return

        server_conf = config_data.get("servers", {}).get(str(ctx.guild.id))
        if not server_conf:
            await ctx.send("このサーバーの設定が存在しません。まず /edit_config を実行してください。")
            return

        # presets.json 読み込み
        if os.path.exists(PRESETS_FILE):
            with open(PRESETS_FILE, "r", encoding="utf-8") as f:
                presets = json.load(f)
        else:
            presets = {}

        presets[preset_name] = server_conf.copy()
        with open(PRESETS_FILE, "w", encoding="utf-8") as f:
            json.dump(presets, f, indent=2, ensure_ascii=False)

        await ctx.send(f"プリセット `{preset_name}` を保存しました。")

    # ---------- プリセット適用 ----------
    @commands.command()
    async def load_preset(self, ctx, preset_name: str):
        if ctx.author.id not in ADMIN_IDS:
            await ctx.send("管理者のみ使用可能です。")
            return

        if not os.path.exists(PRESETS_FILE):
            await ctx.send("プリセットが存在しません。")
            return

        with open(PRESETS_FILE, "r", encoding="utf-8") as f:
            presets = json.load(f)

        preset_conf = presets.get(preset_name)
        if not preset_conf:
            await ctx.send(f"プリセット `{preset_name}` が存在しません。")
            return

        # config_data.json に適用
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config_data = json.load(f)
        else:
            config_data = {"servers": {}}

        config_data["servers"][str(ctx.guild.id)] = preset_conf
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)

        await ctx.send(f"プリセット `{preset_name}` をこのサーバーに適用しました。")


async def setup(bot):
    await bot.add_cog(OwnerCog(bot))
