import os
import json
import dropbox
from discord.ext import commands

CONFIG_LOCAL_PATH = os.path.join("data", "config_store.json")
DROPBOX_PATH = "/config_store.json"  # Dropbox 内の保存場所
DROPBOX_ACCESS_TOKEN = os.getenv("DROPBOX_ACCESS_TOKEN")  # 環境変数からトークン取得

class ConfigManager:
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.DROPBOX_PATH = DROPBOX_PATH  # 追加：インスタンス属性として保持
        self.dbx = dropbox.Dropbox(DROPBOX_ACCESS_TOKEN)

        # 設定ロード
        os.makedirs("data", exist_ok=True)
        self.config = self.load_config()

        # コマンド登録
        self.register_commands()
        self.register_drive_show_command()  # 名前はそのままでもOK

    # 設定ロード
    def load_config(self):
        try:
            metadata, res = self.dbx.files_download(self.DROPBOX_PATH)
            with open(CONFIG_LOCAL_PATH, "wb") as f:
                f.write(res.content)
            with open(CONFIG_LOCAL_PATH, "r", encoding="utf-8") as f:
                config = json.load(f)
            # server_pairs がなければ初期化
            if "server_pairs" not in config:
                config["server_pairs"] = []
            return config
        except dropbox.exceptions.ApiError:
            # ファイルがなければデフォルト生成
            default = {"server_pairs": []}
            self.save_config(default)
            return default

    # 設定保存
    def save_config(self, data=None):
        if data:
            self.config = data
        with open(CONFIG_LOCAL_PATH, "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)
        try:
            with open(CONFIG_LOCAL_PATH, "rb") as f:
                self.dbx.files_upload(f.read(), self.DROPBOX_PATH, mode=dropbox.files.WriteMode.overwrite)
        except Exception as e:
            print(f"[WARN] Dropbox へのアップロード失敗: {e}")

    # 管理者チェック
    def is_admin(self, guild_id, user_id):
        pair = self.get_pair_by_guild(guild_id)
        return pair and user_id in pair.get("ADMIN_IDS", [])

    def get_pair_by_guild(self, guild_id):
        for pair in self.config.get("server_pairs", []):
            if pair.get("A_ID") == guild_id or pair.get("B_ID") == guild_id:
                return pair
        return None

    # 通常コマンド
    def register_commands(self):
        bot = self.bot

        @bot.command(name="adomin")
        async def adomin(ctx: commands.Context):
            guild_id = ctx.guild.id
            author_id = ctx.author.id
            pair = self.get_pair_by_guild(guild_id)
            if not pair:
                pair = {
                    "A_ID": None,
                    "B_ID": guild_id,
                    "CHANNEL_MAPPING": {"A_TO_B": {}},
                    "ADMIN_IDS": [author_id],
                    "DEBUG_CHANNEL": ctx.channel.id,
                    "VC_LOG_CHANNEL": None,
                    "AUDIT_LOG_CHANNEL": None,
                    "OTHER_CHANNEL": None,
                    "READ_USERS": []
                }
                self.config["server_pairs"].append(pair)
                self.save_config()
                await ctx.send(f"✅ {ctx.author.name} を管理者登録しました。")
                return

            if author_id in pair.get("ADMIN_IDS", []):
                await ctx.send("⚠️ すでに管理者として登録されています。")
                return

            pair["ADMIN_IDS"].append(author_id)
            self.save_config()
            await ctx.send(f"✅ {ctx.author.name} を管理者登録しました。")

        @bot.command(name="set_server")
        async def set_server(ctx: commands.Context, target_guild_id: int):
            guild_id = ctx.guild.id
            pair = self.get_pair_by_guild(guild_id)

            if not pair:
                await ctx.send("⚠️ このサーバーはまだ登録されていません。まず `!adomin` を実行してください。")
                return

            if not self.is_admin(guild_id, ctx.author.id):
                await ctx.send("❌ 管理者権限がありません。")
                return

            if guild_id == pair.get("B_ID"):
                pair["A_ID"] = target_guild_id
                self.save_config()
                await ctx.send(f"✅ 対応サーバーを `{target_guild_id}` に設定しました。")
            else:
                await ctx.send("⚠️ このサーバーからは対応サーバーの設定を行えません。")

    # Dropbox JSON 表示コマンド
    def register_drive_show_command(self):
        bot = self.bot

        @bot.command(name="show")
        async def show_config(ctx: commands.Context):
            if not self.is_admin(ctx.guild.id, ctx.author.id):
                await ctx.send("❌ 管理者ではありません。")
                return

            try:
                metadata, res = self.dbx.files_download(self.DROPBOX_PATH)
                config = json.loads(res.content.decode("utf-8"))

                # server_pairs がなければ初期化
                if "server_pairs" not in config:
                    config["server_pairs"] = []

                json_text = json.dumps(config, indent=2, ensure_ascii=False)
                if len(json_text) < 1900:
                    await ctx.send(f"✅ Dropbox 上の設定 JSON\n```json\n{json_text}\n```")
                else:
                    await ctx.send(f"✅ Dropbox 上の設定 JSON（先頭のみ表示）\n```json\n{json_text[:1900]}...\n```")

            except Exception as e:
                await ctx.send(f"⚠️ JSON 読み込みに失敗しました: {e}")
