import os
import json
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
from oauth2client.service_account import ServiceAccountCredentials
from discord.ext import commands

CONFIG_LOCAL_PATH = os.path.join("data", "config_store.json")

class ConfigManager:
    def __init__(self, bot: commands.Bot, drive_file_id: str):
        self.bot = bot
        self.drive_file_id = drive_file_id

        print("[DEBUG] ConfigManager 初期化開始")

        # ----------- サービスアカウント認証情報 -------------
        key_lines = []
        i = 1
        while True:
            env_name = f"SERVICE_KEY_LINE_{i}"
            line = os.getenv(env_name)
            if line is None:
                break
            key_lines.append(line)
            i += 1

        if not key_lines:
            raise ValueError("SERVICE_ACCOUNT_KEY_1 以降の環境変数が設定されていません。")
        print(f"[DEBUG] {len(key_lines)} 行の鍵を取得")

        private_key = "\n".join(key_lines)
        print(f"[DEBUG] private_key length: {len(private_key)}")
        print(f"[DEBUG] private_key startswith: {private_key.startswith('-----BEGIN PRIVATE KEY-----')}")
        print(f"[DEBUG] private_key endswith: {private_key.endswith('-----END PRIVATE KEY-----')}")

        # 他の情報と結合
        service_json = {
            "type": "service_account",
            "project_id": "discord-bot-project-474420",
            "private_key_id": "e719591d1b99197d5eb0cede954efcb1caf67e7a",
            "private_key": private_key,
            "client_email": "discord-bot-drive@discord-bot-project-474420.iam.gserviceaccount.com",
            "client_id": "106826889279899095896",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/discord-bot-drive@discord-bot-project-474420.iam.gserviceaccount.com",
            "universe_domain": "googleapis.com"
        }

        # ----------- Google Drive 認証処理 -------------
        try:
            self.gauth = GoogleAuth()
            scope = ["https://www.googleapis.com/auth/drive"]
            self.gauth.credentials = ServiceAccountCredentials.from_json_keyfile_dict(service_json, scopes=scope)
            self.drive = GoogleDrive(self.gauth)
            print("[DEBUG] GoogleAuth 認証成功")
        except Exception as e:
            print(f"[ERROR] GoogleAuth 認証失敗: {e}")
            raise

        # ----------- 設定ロード -------------
        os.makedirs("data", exist_ok=True)
        self.config = self.load_config()

        # ----------- コマンド登録 -------------
        self.register_commands()
        self.register_sa_check_command()
        self.register_drive_show_command()
        print("[DEBUG] ConfigManager 初期化完了")

    # ---------------------------- 設定ロード ----------------------------
    def load_config(self):
        try:
            print(f"[DEBUG] Google Drive からファイル取得開始: {self.drive_file_id}")
            file = self.drive.CreateFile({"id": self.drive_file_id})
            file.GetContentFile(CONFIG_LOCAL_PATH)
            with open(CONFIG_LOCAL_PATH, "r", encoding="utf-8") as f:
                config = json.load(f)
            print("[LOAD] Google Drive から設定を読み込みました")
            return config
        except Exception as e:
            print(f"[WARN] Google Drive 読み込み失敗: {e}")
            default = {"server_pairs": []}
            self.save_config(default)
            return default

    # ---------------------------- 設定保存 ----------------------------
    def save_config(self, data=None):
        if data:
            self.config = data
        with open(CONFIG_LOCAL_PATH, "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)
        try:
            file = self.drive.CreateFile({"id": self.drive_file_id})
            file.SetContentFile(CONFIG_LOCAL_PATH)
            file.Upload()
            print("[SAVE] Google Drive に設定をアップロードしました")
        except Exception as e:
            print(f"[ERROR] Google Drive へのアップロード失敗: {e}")

    # ---------------------------- 管理者チェック ----------------------------
    def is_admin(self, guild_id, user_id):
        pair = self.get_pair_by_guild(guild_id)
        return pair and user_id in pair.get("ADMIN_IDS", [])

    def get_pair_by_guild(self, guild_id):
        for pair in self.config["server_pairs"]:
            if pair.get("A_ID") == guild_id or pair.get("B_ID") == guild_id:
                return pair
        return None

    # ---------------------------- 通常コマンド登録 ----------------------------
    def register_commands(self):
        bot = self.bot
        print("[DEBUG] 通常コマンド登録開始")

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

        print("[DEBUG] 通常コマンド登録完了")

    # ---------------------------- 管理者限定 SA チェックコマンド ----------------------------
    def register_sa_check_command(self):
        bot = self.bot
        print("[DEBUG] SA チェックコマンド登録開始")

        @bot.command(name="check_sa")
        async def check_sa(ctx: commands.Context):
            if not self.is_admin(ctx.guild.id, ctx.author.id):
                await ctx.send("❌ 管理者ではありません。")
                return

            key_lines = []
            i = 1
            while True:
                env_name = f"SERVICE_KEY_LINE_{i}"
                line = os.getenv(env_name)
                if line is None:
                    break
                key_lines.append(line)
                i += 1

            if not key_lines:
                await ctx.send("❌ SERVICE_KEY_LINE が設定されていません。")
                return

            private_key = "\n".join(key_lines)

            service_json = {
                "type": "service_account",
                "project_id": "discord-bot-project-474420",
                "private_key_id": "e719591d1b99197d5eb0cede954efcb1caf67e7a",
                "client_email": "discord-bot-drive@discord-bot-project-474420.iam.gserviceaccount.com",
                "client_id": "106826889279899095896",
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/discord-bot-drive@discord-bot-project-474420.iam.gserviceaccount.com",
                "universe_domain": "googleapis.com"
            }

            await ctx.send(f"✅ SERVICE_ACCOUNT_JSON 内容（private_key 省略）\n```json\n{json.dumps(service_json, indent=2)}\n```")

        print("[DEBUG] SA チェックコマンド登録完了")

    # ---------------------------- Google Drive JSON 表示コマンド ----------------------------
    def register_drive_show_command(self):
        bot = self.bot  # ← ここが重要
        print("[DEBUG] Google Drive JSON 表示コマンド登録開始")

        @bot.command(name="show")
        async def show_config(ctx: commands.Context):
            if not self.is_admin(ctx.guild.id, ctx.author.id):
                await ctx.send("❌ 管理者ではありません。")
                return

            try:
                print(f"[DEBUG] Google Drive からファイル取得開始: {self.drive_file_id}")
                file = self.drive.CreateFile({"id": self.drive_file_id})
                file.GetContentFile(CONFIG_LOCAL_PATH)
                print(f"[DEBUG] ファイル取得成功: {CONFIG_LOCAL_PATH}")

                with open(CONFIG_LOCAL_PATH, "r", encoding="utf-8") as f:
                    config = json.load(f)

                json_text = json.dumps(config, indent=2, ensure_ascii=False)
                if len(json_text) < 1900:
                    await ctx.send(f"✅ Google Drive 上の設定 JSON\n```json\n{json_text}\n```")

