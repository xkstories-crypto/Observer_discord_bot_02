# config_manager.py
import discord
from discord.ext import commands
import json
import os

# ⚠ 古いファイルを避けるため新しい保存先に変更
# ===== 後で元に戻す場合はこの1行をCONFIG_FILE = "config_data.json"に戻す =====
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
        # dataフォルダがなければ作成
        os.makedirs("data", exist_ok=True)

        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    self.config = json.load(f)
                print(f"[LOAD] {CONFIG_FILE} 読み込み成功")
            except Exception as e:
                print(f"[ERROR] 設定ファイルの読み込み失敗: {e}")
                self.config = {"server_pairs": []}
        else:
            self.config = {"server_pairs": []}
            self.save_config()
            print(f"[INIT] {CONFIG_FILE} 新規作成")

    def save_config(self):
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            print(f"[SAVE] {CONFIG_FILE} 保存完了")
        except Exception as e:
            print(f"[ERROR] 保存中にエラー: {e}")

    # ------------------------
    # ファイルリセット（後で安全に復旧可能）
    # ------------------------
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

    # ------------------------
    # get_server_config（OwnerCog 用）
    # ------------------------
    def get_server_config(self, guild_id):
        return self.get_pair_by_guild(guild_id)

    # ------------------------
    # 管理者判定
    # ------------------------
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

        # ---------------- adomin ----------------
        @bot.command(name="adomin")
        async def adomin(ctx: commands.Context):
            guild_id = ctx.guild.id
            if self.get_pair_by_guild(guild_id):
                await ctx.send("すでに管理者が登録されているサーバーです。")
                return

            new_pair = {
                "A_ID": None,
                "B_ID": guild_id,
                "CHANNEL_MAPPING": {"A_TO_B": {}},
                "ADMIN_IDS": [ctx.author.id]
            }
            self.config["server_pairs"].append(new_pair)
            self.save_config()
            await ctx.send(
                f"✅ 管理者として {ctx.author.display_name} を登録しました。\n"
                f"✅ このサーバーを B サーバーに設定しました。"
            )

        # ---------------- set_server ----------------
        @bot.command(name="set_server")
        async def set_server(ctx: commands.Context, server_a_id: int):
            guild_b_id = ctx.guild.id
            if not self.is_admin(guild_b_id, ctx.author.id):
                await ctx.send("[DEBUG] set_server: 管理者チェック失敗")
                await ctx.send("管理者のみ使用可能です。")
                return

            pair = self.get_pair_by_a(server_a_id)
            if pair is None:
                pair = {
                    "A_ID": server_a_id,
                    "B_ID": guild_b_id,
                    "CHANNEL_MAPPING": {"A_TO_B": {}},
                    "ADMIN_IDS": [ctx.author.id]
                }
                self.config["server_pairs"].append(pair)
            else:
                pair["B_ID"] = guild_b_id

            bot_guild_a = bot.get_guild(server_a_id)
            bot_guild_b = bot.get_guild(guild_b_id)
            if not bot_guild_a or not bot_guild_b:
                await ctx.send("[DEBUG] Botが両方のサーバーに参加していません。")
                await ctx.send("Botが両方のサーバーに参加しているか確認してください。")
                return

            # チャンネルコピー
            mapping = {}
            for ch in bot_guild_a.channels:
                if isinstance(ch, discord.TextChannel):
                    new_ch = await bot_guild_b.create_text_channel(name=ch.name)
                    mapping[str(ch.id)] = new_ch.id

            pair["CHANNEL_MAPPING"]["A_TO_B"] = mapping
            self.save_config()
            await ctx.send(
                f"✅ Aサーバー ({bot_guild_a.name}) → Bサーバー ({bot_guild_b.name}) のチャンネルコピー完了"
            )
