# config_manager.py
import os
import json
import discord
from discord.ext import commands
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
import io

class ConfigManager:
    def __init__(self, bot: commands.Bot, drive_file_id: str):
        """
        bot: Discord Bot オブジェクト
        drive_file_id: Google Drive 上の設定ファイルID
        """
        self.bot = bot
        self.drive_file_id = drive_file_id
        self.config = {"server_pairs": []}

        # ---------- Google Drive 認証（環境変数使用） ----------
        service_json_str = os.getenv("SERVICE_ACCOUNT_JSON")
        if not service_json_str:
            raise ValueError("SERVICE_ACCOUNT_JSON が環境変数に設定されていません。")
        
        # JSON文字列を読み込んで一時的なファイルオブジェクトに変換
        service_file = io.StringIO(service_json_str)

        self.gauth = GoogleAuth()
        self.gauth.LoadServiceConfigFile = lambda *args, **kwargs: None  # 無効化
        self.gauth.ServiceAuth = lambda *args, **kwargs: None  # 無効化

        # 認証情報を直接ロード
        self.gauth.credentials = None
        self.gauth.service_account_json = json.load(service_file)
        self.drive = GoogleDrive(self.gauth)

        # 設定ロードとコマンド登録
        self.load_config()
        self.register_commands()

    # ------------------------
    # 設定ロード/保存
    # ------------------------
    def load_config(self):
        try:
            file_obj = self.drive.CreateFile({'id': self.drive_file_id})
            file_obj.FetchMetadata()
            content = file_obj.GetContentString()
            self.config = json.loads(content)
            print("[LOAD] Google Drive から読み込み成功")
        except Exception as e:
            print(f"[ERROR] Drive から読み込み失敗: {e}, 新規作成します")
            self.config = {"server_pairs": []}
            self.save_config()

    def save_config(self):
        try:
            file_obj = self.drive.CreateFile({'id': self.drive_file_id})
            file_obj.SetContentString(json.dumps(self.config, indent=2, ensure_ascii=False))
            file_obj.Upload()
            print("[SAVE] Google Drive に保存完了")
        except Exception as e:
            print(f"[ERROR] Drive に保存できませんでした: {e}")

    def reset_config(self):
        self.config = {"server_pairs": []}
        self.save_config()
        print("[RESET] 設定ファイルを初期化しました")

    # ------------------------
    # サーバーペア取得
    # ------------------------
    def get_pair_by_a(self, guild_a_id):
        for pair in self.config["server_pairs"]:
            if pair["A_ID"] == guild_a_id:
                return pair
        return None

    def get_pair_by_guild(self, guild_id):
        for pair in self.config["server_pairs"]:
            if guild_id in (pair.get("A_ID"), pair.get("B_ID")):
                return pair
        return None

    def is_admin(self, guild_id, user_id):
        pair = self.get_pair_by_guild(guild_id)
        if not pair:
            return False
        return user_id in pair.get("ADMIN_IDS", [])

    # ------------------------
    # コマンド登録（例: 管理者登録 & サーバー設定）
    # ------------------------
    def register_commands(self):
        bot = self.bot

        @bot.command(name="adomin")
        async def adomin(ctx: commands.Context):
            guild_id = ctx.guild.id
            existing = self.get_pair_by_guild(guild_id)
            if existing:
                await ctx.send("すでに管理者が登録されています")
                return

            new_pair = {
                "A_ID": None,
                "B_ID": guild_id,
                "CHANNEL_MAPPING": {"A_TO_B": {}},
                "ADMIN_IDS": [ctx.author.id],
                "DEBUG_CHANNEL": None,
                "VC_LOG_CHANNEL": None,
                "AUDIT_LOG_CHANNEL": None,
                "OTHER_CHANNEL": None,
                "READ_USERS": []
            }
            self.config["server_pairs"].append(new_pair)

            # デバッグ用チャンネル作成
            debug_ch = await ctx.guild.create_text_channel("debug-channel")
            new_pair["DEBUG_CHANNEL"] = debug_ch.id

            # VCカテゴリ作成
            vc_category = await ctx.guild.create_category("VCカテゴリ")
            vc_channel = await ctx.guild.create_voice_channel("VC-ボイス", category=vc_category)
            vc_text_channel = await ctx.guild.create_text_channel("VC-チャット", category=vc_category)
            new_pair["VC_LOG_CHANNEL"] = vc_channel.id

            self.save_config()
            await ctx.send(f"✅ {ctx.author.display_name} を管理者登録しました。")
