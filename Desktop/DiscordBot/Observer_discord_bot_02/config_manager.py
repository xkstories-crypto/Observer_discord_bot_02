import os
import json
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
from discord.ext import commands

CONFIG_LOCAL_PATH = os.path.join("data", "config_store.json")

class ConfigManager:
    def __init__(self, bot: commands.Bot, drive_file_id: str):
        self.bot = bot
        self.drive_file_id = drive_file_id

        service_json_env = os.getenv("SERVICE_ACCOUNT_JSON")
        if not service_json_env:
            raise ValueError("SERVICE_ACCOUNT_JSON が環境変数に設定されていません。")

        os.makedirs("data", exist_ok=True)
        self.service_json_path = "service_account.json"
        with open(self.service_json_path, "w", encoding="utf-8") as f:
            f.write(service_json_env)

        # Google Drive 認証
        self.gauth = GoogleAuth()
        self.gauth.LoadServiceConfigFile(self.service_json_path)
        self.gauth.ServiceAuth()
        self.drive = GoogleDrive(self.gauth)

        # 設定ファイルをロード
        self.config = self.load_config()
        self.register_commands()

    # ----------------------------------------------------
    # Google Drive から設定を読み込み
    # ----------------------------------------------------
    def load_config(self):
        try:
            file = self.drive.CreateFile({"id": self.drive_file_id})
            file.GetContentFile(CONFIG_LOCAL_PATH)
            with open(CONFIG_LOCAL_PATH, "r", encoding="utf-8") as f:
                config = json.load(f)
            print("[LOAD] Google Drive から設定を読み込みました")
            return config
        except Exception as e:
            print(f"[WARN] Google Drive 読み込み失敗: {e}")
            default = {
                "server_pairs": []
            }
            self.save_config(default)
            return default

    # ----------------------------------------------------
    # Google Drive に保存
    # ----------------------------------------------------
    def save_config(self, data=None):
        if data:
            self.config = data
        with open(CONFIG_LOCAL_PATH, "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)
        file = self.drive.CreateFile({"id": self.drive_file_id})
        file.SetContentFile(CONFIG_LOCAL_PATH)
        file.Upload()
        print("[SAVE] Google Drive に設定をアップロードしました")

    # ----------------------------------------------------
    # 管理者判定
    # ----------------------------------------------------
    def is_admin(self, guild_id, user_id):
        pair = self.get_pair_by_guild(guild_id)
        if not pair:
            return False
        return user_id in pair.get("ADMIN_IDS", [])

    # ----------------------------------------------------
    # ギルドに対応するペアを取得
    # ----------------------------------------------------
    def get_pair_by_guild(self, guild_id):
        for pair in self.config["server_pairs"]:
            if pair.get("A_ID") == guild_id or pair.get("B_ID") == guild_id:
                return pair
        return None

    # ----------------------------------------------------
    # コマンド登録
    # ----------------------------------------------------
    def register_commands(self):
        bot = self.bot

        # ------------------------------
        # 管理者登録コマンド
        # ------------------------------
        @bot.command(name="adomin")
        async def adomin(ctx: commands.Context):
            guild_id = ctx.guild.id
            author_id = ctx.author.id

            # サーバーペアを取得
            pair = self.get_pair_by_guild(guild_id)
            if not pair:
                # 新規作成
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

            # すでに登録済みの場合
            if author_id in pair.get("ADMIN_IDS", []):
                await ctx.send("⚠️ すでに管理者として登録されています。")
                return

            pair["ADMIN_IDS"].append(author_id)
            self.save_config()
            await ctx.send(f"✅ {ctx.author.name} を管理者登録しました。")

        # ------------------------------
        # 対応サーバー設定コマンド
        # ------------------------------
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

            # B側サーバーから設定する
            if guild_id == pair.get("B_ID"):
                pair["A_ID"] = target_guild_id
                self.save_config()
                await ctx.send(f"✅ 対応サーバーを `{target_guild_id}` に設定しました。")
            else:
                await ctx.send("⚠️ このサーバーからは対応サーバーの設定を行えません。")
