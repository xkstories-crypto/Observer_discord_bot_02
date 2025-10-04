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
            self.config = {"servers": {}}

    def save_config(self):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)

    # ------------------------
    # サーバーごとの設定取得
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

    def is_admin(self, guild_id, user_id):
        server = self.get_server_config(guild_id)
        return user_id in server["ADMIN_IDS"]

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
                    f"✅ 管理者として {ctx.author.display_name} を登録しました。\n"
                    f"✅ このサーバー ({ctx.guild.id}) を SERVER_B_ID に設定しました。"
                )
            else:
                await ctx.send("すでに管理者が登録されています。")

        # -------- !set_server --------
        @bot.command(name="set_server")
        async def set_server(ctx: commands.Context, server_a_id: int):
            server_b_id = ctx.guild.id
            server_b_conf = self.get_server_config(server_b_id)

            if not self.is_admin(server_b_id, ctx.author.id):
                await ctx.send("管理者のみ使用可能です。")
                return

            await ctx.send(f"✅ SERVER_A_ID を {server_a_id} に設定中…")

            # ---------- ギルド取得 ----------
            guild_a = bot.get_guild(server_a_id)
            guild_b = bot.get_guild(server_b_id)
            if guild_a is None or guild_b is None:
                await ctx.send("⚠️ サーバーが見つかりません。Botが両方のサーバーに参加しているか確認してください。")
                return

            # ---------- Bにチャンネル生成 & CHANNEL_MAPPING ----------
            a_conf = self.get_server_config(guild_a.id)
            b_conf = self.get_server_config(guild_b.id)
            temp_mapping = {}  # AチャンネルID → BチャンネルID

            for channel in guild_a.channels:
                if isinstance(channel, discord.CategoryChannel):
                    new_cat = await guild_b.create_category(name=channel.name)
                    temp_mapping[channel.id] = new_cat.id
                    print(f"[DEBUG] カテゴリ生成: {channel.name} ({channel.id}) → {new_cat.name} ({new_cat.id})")
                elif isinstance(channel, discord.TextChannel):
                    cat_id = temp_mapping.get(channel.category_id)
                    cat = guild_b.get_channel(cat_id) if cat_id else None
                    new_ch = await guild_b.create_text_channel(name=channel.name, category=cat)
                    temp_mapping[channel.id] = new_ch.id
                    print(f"[DEBUG] テキスト生成: {channel.name} ({channel.id}) → {new_ch.name} ({new_ch.id})")
                elif isinstance(channel, discord.VoiceChannel):
                    cat_id = temp_mapping.get(channel.category_id)
                    cat = guild_b.get_channel(cat_id) if cat_id else None
                    new_ch = await guild_b.create_voice_channel(name=channel.name, category=cat)
                    temp_mapping[channel.id] = new_ch.id
                    print(f"[DEBUG] ボイス生成: {channel.name} ({channel.id}) → {new_ch.name} ({new_ch.id})")

            # ---------- マッピングを両方に保存 ----------
            for a_id, b_id in temp_mapping.items():
                a_conf["CHANNEL_MAPPING"][str(a_id)] = b_id  # A -> B
                b_conf["CHANNEL_MAPPING"][str(b_id)] = a_id  # B -> A

            # ---------- サーバーIDを両方に設定 ----------
            a_conf["SERVER_A_ID"] = guild_a.id
            a_conf["SERVER_B_ID"] = guild_b.id
            b_conf["SERVER_A_ID"] = guild_a.id
            b_conf["SERVER_B_ID"] = guild_b.id

            # ---------- 保存 ----------
            self.save_config()

            # ---------- 完了通知 ----------
            await ctx.send(f"✅ Aサーバー ({guild_a.name}) → Bサーバー ({guild_b.name}) のチャンネルコピー完了、JSONも同期しました。")
