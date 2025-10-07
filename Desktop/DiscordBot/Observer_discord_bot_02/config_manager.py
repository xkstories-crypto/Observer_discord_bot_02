# config_manager.py
import discord
from discord.ext import commands
import json
import os

CONFIG_FILE = os.path.join("data", "config_store.json")

class ConfigManager:
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.load_config()
        self.register_commands()

    # ------------------------
    # 設定ロード/保存
    # ------------------------
    def load_config(self):
        os.makedirs("data", exist_ok=True)
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    self.config = json.load(f)
                print(f"[LOAD] {CONFIG_FILE} 読み込み成功")
            except Exception as e:
                print(f"[ERROR] 設定ファイル読み込み失敗: {e}")
                self.config = {"server_pairs": []}
        else:
            self.config = {"server_pairs": []}
            self.save_config()
            print(f"[INIT] {CONFIG_FILE} 新規作成")

    def save_config(self):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)
        print(f"[SAVE] {CONFIG_FILE} 保存完了")

    def reset_config(self):
        self.config = {"server_pairs": []}
        self.save_config()
        print(f"[RESET] {CONFIG_FILE} を初期化しました。")

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

    def get_server_config(self, guild_id):
        return self.get_pair_by_guild(guild_id)

    def is_admin(self, guild_id, user_id):
        pair = self.get_pair_by_guild(guild_id)
        if not pair:
            return False
        return user_id in pair.get("ADMIN_IDS", [])

    # ------------------------
    # コマンド登録
    # ------------------------
    def register_commands(self):
        bot = self.bot

        # ---------- adomin ----------
        @bot.command(name="adomin")
        async def adomin(ctx: commands.Context):
            guild_id = ctx.guild.id
            existing = self.get_pair_by_guild(guild_id)
            if existing:
                await ctx.send("すでに管理者が登録されています")
                return

            # 新規Bサーバーペア作成
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

            # ---------- デバッグ用チャンネル作成 ----------
            debug_ch = await ctx.guild.create_text_channel("debug-channel")
            new_pair["DEBUG_CHANNEL"] = debug_ch.id

            # ---------- VCカテゴリ作成 ----------
            vc_category = await ctx.guild.create_category("VCカテゴリ")
            vc_channel = await ctx.guild.create_voice_channel("VC-ボイス", category=vc_category)
            vc_text_channel = await ctx.guild.create_text_channel("VC-チャット", category=vc_category)
            new_pair["VC_LOG_CHANNEL"] = vc_channel.id

            self.save_config()
            await ctx.send(f"✅ {ctx.author.display_name} を管理者登録しました。デバッグ用チャンネルとVCカテゴリも作成済みです。")

        # ---------- set_server ----------
        @bot.command(name="set_server")
        async def set_server(ctx: commands.Context, server_a_id: int):
            guild_b_id = ctx.guild.id
            if not self.is_admin(guild_b_id, ctx.author.id):
                await ctx.send("管理者のみ使用可能です。")
                return

            pair = self.get_pair_by_a(server_a_id)
            if not pair:
                pair = {
                    "A_ID": server_a_id,
                    "B_ID": guild_b_id,
                    "CHANNEL_MAPPING": {"A_TO_B": {}},
                    "ADMIN_IDS": [ctx.author.id],
                    "DEBUG_CHANNEL": None,
                    "VC_LOG_CHANNEL": None,
                    "AUDIT_LOG_CHANNEL": None,
                    "OTHER_CHANNEL": None,
                    "READ_USERS": []
                }
                self.config["server_pairs"].append(pair)
            else:
                pair["B_ID"] = guild_b_id

            bot_guild_a = bot.get_guild(server_a_id)
            bot_guild_b = bot.get_guild(guild_b_id)
            if not bot_guild_a or not bot_guild_b:
                await ctx.send("Botが両方のサーバーに参加していません")
                return

            # ---------- チャンネル全削除（あとで消す） ----------
            for ch in bot_guild_b.channels:
                if ch.name not in ["debug-channel"]:
                    await ch.delete()

            # ---------- チャンネルマッピング ----------
            mapping = pair["CHANNEL_MAPPING"]["A_TO_B"]
            for ch in bot_guild_a.channels:
                if isinstance(ch, discord.TextChannel):
                    if str(ch.id) not in mapping:
                        new_ch = await bot_guild_b.create_text_channel(name=ch.name)
                        mapping[str(ch.id)] = new_ch.id

            pair["CHANNEL_MAPPING"]["A_TO_B"] = mapping
            self.save_config()
            await ctx.send(f"✅ Aサーバー → Bサーバー のチャンネルマッピング完了")
