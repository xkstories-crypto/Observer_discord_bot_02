import discord
from discord.ext import commands
import json
import os

CONFIG_FILE = "config_data.json"

class ConfigManager:
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.load_config()
        self.register_commands()

    # ------------------------
    # 設定ロード/保存
    # ------------------------
    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                self.config = json.load(f)
        else:
            self.config = {"server_pairs": []}

    def save_config(self):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)

    # ------------------------
    # ペア取得 / 作成
    # ------------------------
    def get_pair_by_guild(self, guild_id: int):
        for pair in self.config["server_pairs"]:
            if pair["A_ID"] == guild_id or pair["B_ID"] == guild_id:
                return pair
        return None

    def create_pair(self, server_a_id: int, server_b_id: int):
        new_pair = {
            "A_ID": server_a_id,
            "B_ID": server_b_id,
            "CHANNEL_MAPPING": {"A_TO_B": {}, "B_TO_A": {}},
            "ADMIN_IDS": [],
            "VC_LOG_CHANNEL": None,
            "AUDIT_LOG_CHANNEL": None,
            "OTHER_CHANNEL": None
        }
        self.config["server_pairs"].append(new_pair)
        self.save_config()
        return new_pair

    # ------------------------
    # 管理者チェック
    # ------------------------
    def is_admin(self, guild_id, user_id):
        pair = self.get_pair_by_guild(guild_id)
        if not pair:
            return False
        return user_id in pair["ADMIN_IDS"]

    # ------------------------
    # コマンド登録
    # ------------------------
    def register_commands(self):
        bot = self.bot

        # -------- !adomin --------
        @bot.command(name="adomin")
        async def adomin(ctx: commands.Context):
            pair = self.get_pair_by_guild(ctx.guild.id)
            if pair is None:
                # 新規ペアの仮登録（B側として）
                pair = {
                    "A_ID": None,
                    "B_ID": ctx.guild.id,
                    "CHANNEL_MAPPING": {"A_TO_B": {}, "B_TO_A": {}},
                    "ADMIN_IDS": [],
                    "VC_LOG_CHANNEL": None,
                    "AUDIT_LOG_CHANNEL": None,
                    "OTHER_CHANNEL": None
                }
                self.config["server_pairs"].append(pair)

            if ctx.author.id not in pair["ADMIN_IDS"]:
                pair["ADMIN_IDS"].append(ctx.author.id)
                self.save_config()
                await ctx.send(f"✅ {ctx.author.display_name} を管理者として登録しました。")
            else:
                await ctx.send("⚠️ すでに管理者です。")

        # -------- !set_server --------
        @bot.command(name="set_server")
        async def set_server(ctx: commands.Context, server_a_id: int):
            guild_b_id = ctx.guild.id
            if not self.is_admin(guild_b_id, ctx.author.id):
                await ctx.send("⚠️ 管理者のみ使用可能です。")
                return

            # 既存ペア確認 or 新規作成
            pair = self.get_pair_by_guild(guild_b_id)
            if pair is None:
                pair = self.create_pair(server_a_id, guild_b_id)
            else:
                pair["A_ID"] = server_a_id
                pair["B_ID"] = guild_b_id

            await ctx.send(f"✅ サーバーペア登録: A={server_a_id}, B={guild_b_id}")

            guild_a = bot.get_guild(server_a_id)
            guild_b = bot.get_guild(guild_b_id)
            if guild_a is None or guild_b is None:
                await ctx.send("⚠️ Botが両方のサーバーにいません。")
                return

            temp_mapping_A_to_B = {}
            temp_mapping_B_to_A = {}

            for channel in guild_a.channels:
                if isinstance(channel, discord.CategoryChannel):
                    new_cat = await guild_b.create_category(name=channel.name)
                    temp_mapping_A_to_B[channel.id] = new_cat.id
                    await ctx.send(f"[DEBUG] カテゴリ生成: {channel.name}")
                elif isinstance(channel, discord.TextChannel):
                    cat_id = temp_mapping_A_to_B.get(channel.category_id)
                    cat = guild_b.get_channel(cat_id) if cat_id else None
                    new_ch = await guild_b.create_text_channel(name=channel.name, category=cat)
                    temp_mapping_A_to_B[channel.id] = new_ch.id
                    await ctx.send(f"[DEBUG] テキスト生成: {channel.name}")
                elif isinstance(channel, discord.VoiceChannel):
                    cat_id = temp_mapping_A_to_B.get(channel.category_id)
                    cat = guild_b.get_channel(cat_id) if cat_id else None
                    new_ch = await guild_b.create_voice_channel(name=channel.name, category=cat)
                    temp_mapping_A_to_B[channel.id] = new_ch.id
                    await ctx.send(f"[DEBUG] ボイス生成: {channel.name}")

            # 逆方向マッピングも構築
            for a, b in temp_mapping_A_to_B.items():
                temp_mapping_B_to_A[b] = a

            pair["CHANNEL_MAPPING"]["A_TO_B"] = temp_mapping_A_to_B
            pair["CHANNEL_MAPPING"]["B_TO_A"] = temp_mapping_B_to_A
            self.save_config()

            await ctx.send(f"✅ チャンネルコピー完了 & ペア設定保存完了。")
