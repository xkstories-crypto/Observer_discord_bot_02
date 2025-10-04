import discord
from discord.ext import commands
import json
import os
import threading
from datetime import datetime

CONFIG_FILE = "config_data.json"

class ConfigManager:
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._save_lock = threading.Lock()
        self.load_config()
        self.register_commands()

    # ------------------------
    # 設定ロード/保存（原子書き込み＋バックアップ）
    # ------------------------
    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                self.config = json.load(f)
        else:
            self.config = {"servers": {}}

    def save_config(self):
        with self._save_lock:
            try:
                if os.path.exists(CONFIG_FILE):
                    bak_name = f"{CONFIG_FILE}.bak.{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}"
                    try:
                        os.replace(CONFIG_FILE, bak_name)
                    except Exception:
                        import shutil
                        shutil.copy2(CONFIG_FILE, bak_name)
            except Exception as e:
                print(f"[SAVE] backup failed: {e}")

            tmp_name = CONFIG_FILE + ".tmp"
            try:
                with open(tmp_name, "w", encoding="utf-8") as f:
                    json.dump(self.config, f, indent=2, ensure_ascii=False)
                os.replace(tmp_name, CONFIG_FILE)
                print("[SAVE] config saved atomically")
            except Exception as e:
                print(f"[SAVE] failed to write config: {e}")

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
    # メッセージベースでサーバー設定を取得
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
            b_conf = self.get_server_config(server_b_id)

            if not self.is_admin(server_b_id, ctx.author.id):
                await ctx.send("管理者のみ使用可能です。")
                return

            await ctx.send(f"✅ SERVER_A_ID を {server_a_id} に設定中… (詳細はこのチャンネルに表示します)")

            guild_a = bot.get_guild(server_a_id)
            guild_b = bot.get_guild(server_b_id)
            if guild_a is None or guild_b is None:
                await ctx.send("⚠️ サーバーが見つかりません。Botが両方のサーバーに参加しているか確認してください。")
                return

            a_conf = self.get_server_config(guild_a.id)
            b_conf["SERVER_A_ID"] = guild_a.id
            b_conf["SERVER_B_ID"] = guild_b.id
            a_conf["SERVER_A_ID"] = guild_a.id
            a_conf["SERVER_B_ID"] = guild_b.id

            temp_mapping = {}  # str(a_id) -> str(b_id)
            created = 0
            skipped = 0
            errors = []

            for channel in guild_a.channels:
                try:
                    a_key = str(channel.id)
                    if a_key in b_conf.get("CHANNEL_MAPPING", {}):
                        skipped += 1
                        continue

                    # 鍵部屋（admin-only）は作らない
                    if channel.name.startswith("🔒"):
                        await ctx.send(f"[SKIP] 鍵部屋 {channel.name} をスキップ")
                        skipped += 1
                        continue

                    if isinstance(channel, discord.CategoryChannel):
                        new_cat = await guild_b.create_category(name=channel.name)
                        temp_mapping[a_key] = str(new_cat.id)
                        created += 1
                        await ctx.send(f"[作成] カテゴリ `{channel.name}` -> `{new_cat.id}`")
                    elif isinstance(channel, discord.TextChannel):
                        cat_id = temp_mapping.get(str(channel.category_id))
                        cat = guild_b.get_channel(int(cat_id)) if cat_id else None
                        new_ch = await guild_b.create_text_channel(name=channel.name, category=cat)
                        temp_mapping[a_key] = str(new_ch.id)
                        created += 1
                        await ctx.send(f"[作成] テキスト `{channel.name}` -> `{new_ch.id}`")
                    elif isinstance(channel, discord.VoiceChannel):
                        cat_id = temp_mapping.get(str(channel.category_id))
                        cat = guild_b.get_channel(int(cat_id)) if cat_id else None
                        new_ch = await guild_b.create_voice_channel(name=channel.name, category=cat)
                        temp_mapping[a_key] = str(new_ch.id)
                        created += 1
                        await ctx.send(f"[作成] ボイス `{channel.name}` -> `{new_ch.id}`")

                except discord.Forbidden:
                    msg = f"権限不足で `{channel.name}` の作成に失敗しました"
                    errors.append(msg)
                    await ctx.send(f"⚠️ {msg}")
                except discord.HTTPException as e:
                    msg = f"Discord API エラーで `{channel.name}` の作成に失敗: {e}"
                    errors.append(msg)
                    await ctx.send(f"⚠️ {msg}")
                except Exception as e:
                    msg = f"不明なエラーで `{channel.name}` の作成に失敗: {e}"
                    errors.append(msg)
                    await ctx.send(f"⚠️ {msg}")
                    print(f"[ERROR] creating channel {channel.name}: {e}")

            # ---------- マッピング保存 ----------
            if "CHANNEL_MAPPING" not in b_conf:
                b_conf["CHANNEL_MAPPING"] = {}
            if "CHANNEL_MAPPING" not in a_conf:
                a_conf["CHANNEL_MAPPING"] = {}

            for a_id, b_id in temp_mapping.items():
                b_conf["CHANNEL_MAPPING"][str(a_id)] = str(b_id)
                a_conf["CHANNEL_MAPPING"][str(a_id)] = str(b_id)

            self.save_config()

            report = f"✅ 完了: 作成 {created} 件、スキップ {skipped} 件、エラー {len(errors)} 件"
            await ctx.send(report)
            if errors:
                await ctx.send("エラー詳細はコンソールを確認してください。")

        # -------- !check --------
        @bot.command(name="check")
        async def check(ctx: commands.Context):
            server = self.get_server_config(ctx.guild.id)
            guild = ctx.guild
            await ctx.send(f"Server ({guild.id}): {guild.name}")
            await ctx.send(f"SERVER_A_ID: {server.get('SERVER_A_ID')}")
            await ctx.send(f"SERVER_B_ID: {server.get('SERVER_B_ID')}")
            await ctx.send("CHANNEL_MAPPING:")
            for a_id, b_id in server.get("CHANNEL_MAPPING", {}).items():
                src_ch = bot.get_guild(server["SERVER_A_ID"]).get_channel(int(a_id)) if server.get("SERVER_A_ID") else None
                dest_ch = bot.get_guild(server["SERVER_B_ID"]).get_channel(int(b_id)) if server.get("SERVER_B_ID") else None
                src_name = src_ch.name if src_ch else "不明"
                dest_name = dest_ch.name if dest_ch else "不明"
                await ctx.send(f"  {a_id} -> {b_id} | src_name: {src_name}, dest_name: {dest_name}")
            await ctx.send(f"READ_GROUPS: {server.get('READ_GROUPS')}")
            await ctx.send(f"ADMIN_IDS: {server.get('ADMIN_IDS')}")
            await ctx.send(f"VC_LOG_CHANNEL: {server.get('VC_LOG_CHANNEL') or '不明'}")
            await ctx.send(f"AUDIT_LOG_CHANNEL: {server.get('AUDIT_LOG_CHANNEL') or '不明'}")
            await ctx.send(f"OTHER_CHANNEL: {server.get('OTHER_CHANNEL') or '不明'}")
            await ctx.send(f"READ_USERS: {server.get('READ_USERS')}")
