# config_manager.py
import discord
from discord.ext import commands
import json
import os

CONFIG_FILE = "config_data.json"

class ConfigManager:
    def __init__(self, bot: commands.Bot, debug_channel_id: int = None):
        self.bot = bot
        self.debug_channel_id = debug_channel_id
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
            self.config = {"servers": {}}

    def save_config(self):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)

    # ------------------------
    # サーバー設定取得
    # ------------------------
    def get_server_config(self, guild_id: int):
        sid = str(guild_id)
        if sid not in self.config["servers"]:
            self.config["servers"][sid] = {
                "SERVER_A_ID": None,
                "SERVER_B_ID": None,
                "CHANNEL_MAPPING": {},
                "READ_GROUPS": {},
                "ADMIN_IDS": [],
                "VC_LOG_CHANNEL": None,
                "AUDIT_LOG_CHANNEL": None,
                "OTHER_CHANNEL": None,
                "READ_USERS": []
            }
        return self.config["servers"][sid]

    def is_admin(self, guild_id: int, user_id: int):
        return user_id in self.get_server_config(guild_id)["ADMIN_IDS"]

    # ------------------------
    # メッセージベースでサーバー設定取得
    # ------------------------
    def get_server_config_by_message(self, message: discord.Message):
        guild_id = message.guild.id
        conf = self.config["servers"].get(str(guild_id))
        if conf:
            return conf
        for s_conf in self.config["servers"].values():
            if s_conf.get("SERVER_A_ID") == guild_id:
                return s_conf
        return None

    # ------------------------
    # デバッグ送信
    # ------------------------
    async def send_debug(self, text: str):
        if self.debug_channel_id:
            debug_ch = self.bot.get_channel(self.debug_channel_id)
            if debug_ch:
                try:
                    await debug_ch.send(f"[DEBUG] {text}")
                except Exception as e:
                    print(f"[DEBUG ERROR] {e}")

    # ------------------------
    # コマンド登録
    # ------------------------
    def register_commands(self):
        bot = self.bot

        # -------- !adomin --------
        @bot.command(name="adomin")
        async def adomin(ctx: commands.Context):
            server = self.get_server_config(ctx.guild.id)
            if len(server["ADMIN_IDS"]) == 0:
                server["ADMIN_IDS"].append(ctx.author.id)
                server["SERVER_B_ID"] = ctx.guild.id
                self.save_config()
                await ctx.send(
                    f"✅ 管理者登録完了: {ctx.author.display_name}\n"
                    f"✅ このサーバーを SERVER_B_ID に設定しました"
                )
            else:
                await ctx.send("管理者は既に登録済みです")

        # -------- !set_server <AのID> --------
        @bot.command(name="set_server")
        async def set_server(ctx: commands.Context, server_a_id: int):
            server_b_id = ctx.guild.id
            if not self.is_admin(server_b_id, ctx.author.id):
                await ctx.send("管理者のみ使用可能です")
                return

            server_b_conf = self.get_server_config(server_b_id)
            server_a_conf = self.get_server_config(server_a_id)

            # A/B サーバーの固定割り当て
            server_b_conf["SERVER_A_ID"] = server_a_id
            server_b_conf["SERVER_B_ID"] = server_b_id
            server_a_conf["SERVER_B_ID"] = server_b_id
            self.save_config()

            guild_a = bot.get_guild(server_a_id)
            guild_b = bot.get_guild(server_b_id)
            if not guild_a or not guild_b:
                await ctx.send("⚠️ 両方のサーバーにBotが参加しているか確認してください")
                return

            # チャンネル構造コピーとマッピング
            for channel in guild_a.channels:
                if isinstance(channel, discord.CategoryChannel):
                    cat_b = await guild_b.create_category(name=channel.name)
                    server_b_conf["CHANNEL_MAPPING"][str(channel.id)] = cat_b.id
                    server_a_conf["CHANNEL_MAPPING"][str(cat_b.id)] = channel.id
                elif isinstance(channel, discord.TextChannel):
                    cat_id = server_b_conf["CHANNEL_MAPPING"].get(str(channel.category_id))
                    cat_b = guild_b.get_channel(cat_id) if cat_id else None
                    new_ch = await guild_b.create_text_channel(name=channel.name, category=cat_b)
                    server_b_conf["CHANNEL_MAPPING"][str(channel.id)] = new_ch.id
                    server_a_conf["CHANNEL_MAPPING"][str(new_ch.id)] = channel.id
                elif isinstance(channel, discord.VoiceChannel):
                    cat_id = server_b_conf["CHANNEL_MAPPING"].get(str(channel.category_id))
                    cat_b = guild_b.get_channel(cat_id) if cat_id else None
                    new_ch = await guild_b.create_voice_channel(name=channel.name, category=cat_b)
                    server_b_conf["CHANNEL_MAPPING"][str(channel.id)] = new_ch.id
                    server_a_conf["CHANNEL_MAPPING"][str(new_ch.id)] = channel.id

            self.save_config()
            await ctx.send("✅ A→B のチャンネルマッピング作成と JSON 同期完了")
