import os
import json
import dropbox
import discord
from discord.ext import commands
from discord.utils import get

CONFIG_LOCAL_PATH = os.path.join("data", "config_store.json")
DROPBOX_PATH = "/config_store.json"
DROPBOX_ACCESS_TOKEN = os.getenv("DROPBOX_ACCESS_TOKEN")


class ConfigManager:
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.DROPBOX_PATH = DROPBOX_PATH
        self.dbx = dropbox.Dropbox(DROPBOX_ACCESS_TOKEN)

        os.makedirs("data", exist_ok=True)
        self.config = self.load_config()

        self.register_commands()
        self.register_drive_show_command()

    # ------------------------
    # 設定ロード/保存
    # ------------------------
    def load_config(self):
        try:
            metadata, res = self.dbx.files_download(self.DROPBOX_PATH)
            with open(CONFIG_LOCAL_PATH, "wb") as f:
                f.write(res.content)
            with open(CONFIG_LOCAL_PATH, "r", encoding="utf-8") as f:
                config = json.load(f)
            if "server_pairs" not in config:
                config["server_pairs"] = []
            # ensure keys valid
            return config
        except dropbox.exceptions.ApiError:
            default = {"server_pairs": []}
            # write default locally and to dropbox
            self.config = default
            self._upload_local_config(default)
            return default
        except Exception as e:
            # fallback to local if any other error
            if os.path.exists(CONFIG_LOCAL_PATH):
                with open(CONFIG_LOCAL_PATH, "r", encoding="utf-8") as f:
                    return json.load(f)
            default = {"server_pairs": []}
            self.config = default
            return default

    def save_config(self, data=None):
        if data:
            self.config = data
        # local write
        with open(CONFIG_LOCAL_PATH, "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)
        # upload to dropbox
        try:
            self._upload_local_config(self.config)
        except Exception as e:
            print(f"[WARN] Dropbox へのアップロード失敗: {e}")

    def _upload_local_config(self, config_data):
        # helper: write local and upload to dropbox (overwrite)
        with open(CONFIG_LOCAL_PATH, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)
        with open(CONFIG_LOCAL_PATH, "rb") as f:
            self.dbx.files_upload(f.read(), self.DROPBOX_PATH, mode=dropbox.files.WriteMode.overwrite)

    # ------------------------
    # 管理者チェック・ペア取得
    # ------------------------
    def is_admin(self, guild_id, user_id):
        pair = self.get_pair_by_guild(guild_id)
        return pair and user_id in pair.get("ADMIN_IDS", [])

    def get_pair_by_guild(self, guild_id):
        for pair in self.config.get("server_pairs", []):
            if pair.get("A_ID") == guild_id or pair.get("B_ID") == guild_id:
                return pair
        return None

    def _find_or_create_pair(self, a_id, b_id):
        # returns the pair dict inside self.config (creates if not exist)
        for pair in self.config.get("server_pairs", []):
            if pair.get("A_ID") == a_id and pair.get("B_ID") == b_id:
                return pair
        new_pair = {
            "A_ID": a_id,
            "B_ID": b_id,
            "CHANNEL_MAPPING": {"A_TO_B": {}, "B_TO_A": {}},
            "ADMIN_IDS": [],
            "DEBUG_CHANNEL": None,
            "VC_LOG_CHANNEL": None,
            "AUDIT_LOG_CHANNEL": None,
            "OTHER_CHANNEL": None,
            "READ_USERS": []
        }
        self.config.setdefault("server_pairs", []).append(new_pair)
        return new_pair

    # ------------------------
    # コマンド登録
    # ------------------------
    def register_commands(self):
        bot = self.bot

        # 管理者登録
        @bot.command(name="adomin")
        async def adomin(ctx: commands.Context):
            guild_id = ctx.guild.id
            author_id = ctx.author.id
            pair = self.get_pair_by_guild(guild_id)
            if not pair:
                pair = {
                    "A_ID": None,
                    "B_ID": guild_id,
                    "CHANNEL_MAPPING": {"A_TO_B": {}, "B_TO_A": {}},
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

        # -------------------------------
        # set_server: A->B コピー＆マッピング作成
        # -------------------------------
        @bot.command(name="set_server")
        async def set_server(ctx: commands.Context, target_guild_id: int):
            guild_b = ctx.guild
            guild_b_id = guild_b.id
            guild_a_id = target_guild_id

            # get pair (by B guild)
            pair = self.get_pair_by_guild(guild_b_id)
            if not pair:
                await ctx.send("⚠️ このサーバーはまだ登録されていません。まず `!adomin` を実行してください。")
                return

            if not self.is_admin(guild_b_id, ctx.author.id):
                await ctx.send("❌ 管理者権限がありません。")
                return

            if guild_b_id != pair.get("B_ID"):
                await ctx.send("⚠️ このサーバーからは対応サーバーの設定を行えません。")
                return

            # set A_ID in local pair
            pair["A_ID"] = guild_a_id

            # ensure mapping structure exists locally
            pair.setdefault("CHANNEL_MAPPING", {})
            pair["CHANNEL_MAPPING"].setdefault("A_TO_B", {})
            pair["CHANNEL_MAPPING"].setdefault("B_TO_A", {})

            # make sure debug/log channel fields exist (don't overwrite if present)
            pair.setdefault("DEBUG_CHANNEL", None)
            pair.setdefault("VC_LOG_CHANNEL", None)
            pair.setdefault("AUDIT_LOG_CHANNEL", None)
            pair.setdefault("OTHER_CHANNEL", None)

            # --- fetch guild objects ---
            guild_a = self.bot.get_guild(guild_a_id)
            if guild_a is None:
                await ctx.send("⚠️ Aサーバーが取得できません。BotがAサーバーに参加しているか確認してください。")
                return

            # --- create debug/log categories & channels on B if not exist ---
            created_debug = False
            created_log = False
            # Try to reuse existing categories named "debug" / "log" (case-insensitive)
            debug_cat = None
            log_cat = None
            for c in guild_b.categories:
                if c.name.lower() == "debug":
                    debug_cat = c
                if c.name.lower() == "log":
                    log_cat = c

            if debug_cat is None:
                debug_cat = await guild_b.create_category("debug")
                created_debug = True
            if log_cat is None:
                log_cat = await guild_b.create_category("log")
                created_log = True

            # helper to create or reuse channel by name in category
            def find_channel_by_name_in_category(guild, name, category):
                for ch in guild.text_channels:
                    if ch.name == name and ch.category and ch.category.id == category.id:
                        return ch
                return None

            # create debug/log channels if not exist and set pair fields (do not overwrite if already set)
            # debug -> bot-debug
            if pair.get("DEBUG_CHANNEL") is None:
                existing = find_channel_by_name_in_category(guild_b, "bot-debug", debug_cat)
                if existing:
                    pair["DEBUG_CHANNEL"] = existing.id
                else:
                    new_ch = await guild_b.create_text_channel("bot-debug", category=debug_cat)
                    pair["DEBUG_CHANNEL"] = new_ch.id

            # log -> vc-log
            if pair.get("VC_LOG_CHANNEL") is None:
                existing = find_channel_by_name_in_category(guild_b, "vc-log", log_cat)
                if existing:
                    pair["VC_LOG_CHANNEL"] = existing.id
                else:
                    new_ch = await guild_b.create_text_channel("vc-log", category=log_cat)
                    pair["VC_LOG_CHANNEL"] = new_ch.id

            # audit -> audit-log
            if pair.get("AUDIT_LOG_CHANNEL") is None:
                existing = find_channel_by_name_in_category(guild_b, "audit-log", log_cat)
                if existing:
                    pair["AUDIT_LOG_CHANNEL"] = existing.id
                else:
                    new_ch = await guild_b.create_text_channel("audit-log", category=log_cat)
                    pair["AUDIT_LOG_CHANNEL"] = new_ch.id

            # other -> other-log
            if pair.get("OTHER_CHANNEL") is None:
                existing = find_channel_by_name_in_category(guild_b, "other-log", log_cat)
                if existing:
                    pair["OTHER_CHANNEL"] = existing.id
                else:
                    new_ch = await guild_b.create_text_channel("other-log", category=log_cat)
                    pair["OTHER_CHANNEL"] = new_ch.id

            # --- load dropbox config (fresh) and find/create pair there ---
            try:
                metadata, res = self.dbx.files_download(self.DROPBOX_PATH)
                dropbox_config = json.loads(res.content.decode("utf-8"))
            except Exception as e:
                await ctx.send(f"⚠️ Dropbox 読み込み失敗: {e}")
                return

            dropbox_config.setdefault("server_pairs", [])
            db_pair = None
            for p in dropbox_config["server_pairs"]:
                if p.get("A_ID") == guild_a_id and p.get("B_ID") == guild_b_id:
                    db_pair = p
                    break
            if db_pair is None:
                db_pair = {
                    "A_ID": guild_a_id,
                    "B_ID": guild_b_id,
                    "CHANNEL_MAPPING": {"A_TO_B": {}, "B_TO_A": {}},
                    "ADMIN_IDS": pair.get("ADMIN_IDS", []),
                    "DEBUG_CHANNEL": pair.get("DEBUG_CHANNEL"),
                    "VC_LOG_CHANNEL": pair.get("VC_LOG_CHANNEL"),
                    "AUDIT_LOG_CHANNEL": pair.get("AUDIT_LOG_CHANNEL"),
                    "OTHER_CHANNEL": pair.get("OTHER_CHANNEL"),
                    "READ_USERS": pair.get("READ_USERS", [])
                }
                dropbox_config["server_pairs"].append(db_pair)
            else:
                # ensure keys exist
                db_pair.setdefault("CHANNEL_MAPPING", {})
                db_pair["CHANNEL_MAPPING"].setdefault("A_TO_B", {})
                db_pair["CHANNEL_MAPPING"].setdefault("B_TO_A", {})
                db_pair.setdefault("DEBUG_CHANNEL", pair.get("DEBUG_CHANNEL"))
                db_pair.setdefault("VC_LOG_CHANNEL", pair.get("VC_LOG_CHANNEL"))
                db_pair.setdefault("AUDIT_LOG_CHANNEL", pair.get("AUDIT_LOG_CHANNEL"))
                db_pair.setdefault("OTHER_CHANNEL", pair.get("OTHER_CHANNEL"))

            # --- copy channels from A -> B, creating mapping entries only for not-mapped channels ---
            a_to_b = db_pair["CHANNEL_MAPPING"]["A_TO_B"]
            b_to_a = db_pair["CHANNEL_MAPPING"]["B_TO_A"]

            # Helper: try reusing existing channel in B by exact name+category if mapping absent (avoid duplicates).
            def find_text_in_category_by_name(guild, name, category):
                for ch in guild.text_channels:
                    if ch.name == name and ch.category and ch.category.id == (category.id if category else None):
                        return ch
                return None

            # First: categories (keep order)
            created_categories = {}  # a_cat_id (str) -> b_cat_id (int)
            for a_cat in guild_a.categories:
                a_cat_id_s = str(a_cat.id)
                if a_cat_id_s in a_to_b:
                    created_categories[a_cat_id_s] = a_to_b[a_cat_id_s]
                    continue
                # try to find same-named category in B
                existing_cat = get(guild_b.categories, name=a_cat.name)
                if existing_cat:
                    b_cat = existing_cat
                else:
                    b_cat = await guild_b.create_category(a_cat.name)
                a_to_b[a_cat_id_s] = b_cat.id
                b_to_a[str(b_cat.id)] = a_cat.id
                created_categories[a_cat_id_s] = b_cat.id

            # Channels without category (top-level) we will place under None
            # Process text channels
            created_text = 0
            for a_text in guild_a.text_channels:
                a_text_id_s = str(a_text.id)
                if a_text_id_s in a_to_b:
                    continue  # already mapped
                # determine target category in B
                a_cat = a_text.category
                b_cat_obj = None
                if a_cat:
                    b_cat_id = a_to_b.get(str(a_cat.id))
                    if b_cat_id:
                        b_cat_obj = guild_b.get_channel(int(b_cat_id))
                # try to reuse existing channel in B with same name & category
                existing_ch = None
                if b_cat_obj:
                    existing_ch = find_text_in_category_by_name(guild_b, a_text.name, b_cat_obj)
                else:
                    # top-level text channel
                    existing_ch = get(guild_b.text_channels, name=a_text.name, category=None)
                if existing_ch:
                    b_ch = existing_ch
                else:
                    b_ch = await guild_b.create_text_channel(a_text.name, category=b_cat_obj)
                a_to_b[a_text_id_s] = b_ch.id
                b_to_a[str(b_ch.id)] = a_text.id
                created_text += 1

            # Process voice channels (and create corresponding text channel under same category)
            created_voice = 0
            created_voice_text = 0
            for a_vc in guild_a.voice_channels:
                a_vc_id_s = str(a_vc.id)
                if a_vc_id_s in a_to_b:
                    continue
                # determine target category in B
                a_cat = a_vc.category
                b_cat_obj = None
                if a_cat:
                    b_cat_id = a_to_b.get(str(a_cat.id))
                    if b_cat_id:
                        b_cat_obj = guild_b.get_channel(int(b_cat_id))
                # create voice channel in B (or reuse same-name voice channel)
                existing_vc = None
                if b_cat_obj:
                    existing_vc = None
                    for vc in guild_b.voice_channels:
                        if vc.name == a_vc.name and vc.category and vc.category.id == b_cat_obj.id:
                            existing_vc = vc
                            break
                else:
                    # top-level voice channel
                    for vc in guild_b.voice_channels:
                        if vc.name == a_vc.name and vc.category is None:
                            existing_vc = vc
                            break
                if existing_vc:
                    b_vc = existing_vc
                else:
                    b_vc = await guild_b.create_voice_channel(a_vc.name, category=b_cat_obj)
                a_to_b[a_vc_id_s] = b_vc.id
                b_to_a[str(b_vc.id)] = a_vc.id
                created_voice += 1

                # create a same-name text channel under the same category for the VC
                # (if such text channel not already mapped/exists)
                # We will try to reuse existing text channel with same name & category
                text_exists = None
                if b_cat_obj:
                    text_exists = find_text_in_category_by_name(guild_b, a_vc.name, b_cat_obj)
                else:
                    text_exists = get(guild_b.text_channels, name=a_vc.name, category=None)
                if text_exists:
                    b_text = text_exists
                else:
                    b_text = await guild_b.create_text_channel(a_vc.name, category=b_cat_obj)
                # map the A text? There is no separate A->text for VC; user asked to create same-name text under VC.
                # We still map it if A has a text channel with same id/name; otherwise just map the newly created text with a pseudo-key?
                # Best approach: if A side has a text channel with the same name in same category, map that; else create mapping for a_vc_text_key
                # Try find A text channel with same name & category
                corresponding_a_text = None
                for ch in guild_a.text_channels:
                    if ch.name == a_vc.name and ((ch.category and a_vc.category and ch.category.id == a_vc.category.id) or (ch.category is None and a_vc.category is None)):
                        corresponding_a_text = ch
                        break
                if corresponding_a_text:
                    a_text_id_s = str(corresponding_a_text.id)
                    if a_text_id_s not in a_to_b:
                        a_to_b[a_text_id_s] = b_text.id
                        b_to_a[str(b_text.id)] = corresponding_a_text.id
                        created_voice_text += 1
                else:
                    # create a synthetic mapping for the text channel using a special key derived from vc id + "_text"
                    synthetic_key = f"{a_vc.id}_text"
                    if synthetic_key not in a_to_b:
                        a_to_b[synthetic_key] = b_text.id
                        b_to_a[str(b_text.id)] = synthetic_key
                        created_voice_text += 1

            # Update local pair and dropbox pair fields for debug/log channels
            pair["DEBUG_CHANNEL"] = pair.get("DEBUG_CHANNEL") or db_pair.get("DEBUG_CHANNEL") or pair.get("DEBUG_CHANNEL")
            pair["VC_LOG_CHANNEL"] = pair.get("VC_LOG_CHANNEL") or db_pair.get("VC_LOG_CHANNEL") or pair.get("VC_LOG_CHANNEL")
            pair["AUDIT_LOG_CHANNEL"] = pair.get("AUDIT_LOG_CHANNEL") or db_pair.get("AUDIT_LOG_CHANNEL") or pair.get("AUDIT_LOG_CHANNEL")
            pair["OTHER_CHANNEL"] = pair.get("OTHER_CHANNEL") or db_pair.get("OTHER_CHANNEL") or pair.get("OTHER_CHANNEL")

            db_pair["CHANNEL_MAPPING"]["A_TO_B"] = a_to_b
            db_pair["CHANNEL_MAPPING"]["B_TO_A"] = b_to_a
            db_pair["DEBUG_CHANNEL"] = pair["DEBUG_CHANNEL"]
            db_pair["VC_LOG_CHANNEL"] = pair["VC_LOG_CHANNEL"]
            db_pair["AUDIT_LOG_CHANNEL"] = pair["AUDIT_LOG_CHANNEL"]
            db_pair["OTHER_CHANNEL"] = pair["OTHER_CHANNEL"]

            # save local config and upload dropbox
            try:
                # Update local self.config pair to reflect db_pair (merge)
                # Find and replace/update the corresponding pair in self.config
                updated = False
                for p in self.config.get("server_pairs", []):
                    if p.get("A_ID") == guild_a_id and p.get("B_ID") == guild_b_id:
                        p.update(db_pair)
                        updated = True
                        break
                if not updated:
                    self.config.setdefault("server_pairs", []).append(db_pair)
                # save/upload
                self._upload_local_config(self.config)
                # also ensure dropbox_config stored
                with open(CONFIG_LOCAL_PATH, "w", encoding="utf-8") as f:
                    json.dump(dropbox_config, f, indent=2, ensure_ascii=False)
                with open(CONFIG_LOCAL_PATH, "rb") as f:
                    self.dbx.files_upload(f.read(), self.DROPBOX_PATH, mode=dropbox.files.WriteMode.overwrite)
            except Exception as e:
                await ctx.send(f"⚠️ 保存に失敗しました: {e}")
                return

            # reply summary
            await ctx.send(
                "✅ 対応サーバーを `{}` に設定しました。\n"
                "✅ カテゴリ・チャンネル構造のコピーとマッピングを作成しました。\n"
                f" - 作成カテゴリ数: {len(created_categories)} (マッピング済み含む)\n"
                f" - 作成テキストチャンネル数: {created_text}\n"
                f" - 作成ボイスチャンネル数: {created_voice}\n"
                f" - 作成ボイス下テキスト数: {created_voice_text}\n"
                "✅ debug / log チャンネルを作成・設定しました。"
            .format(guild_a_id))

        # 個別チャンネル設定（直接セット、上書き可）
        @bot.command(name="set_channel")
        async def set_channel(ctx: commands.Context, channel_type: str, channel_id: int = None):
            guild_id = ctx.guild.id
            pair = self.get_pair_by_guild(guild_id)
            if not pair:
                await ctx.send("⚠️ サーバーが未登録です。まず !adomin を実行してください。")
                return

            if not self.is_admin(guild_id, ctx.author.id):
                await ctx.send("❌ 管理者権限がありません。")
                return

            if not channel_id:
                channel_id = ctx.channel.id

            field_map = {
                "DEBUG": "DEBUG_CHANNEL",
                "VC_LOG": "VC_LOG_CHANNEL",
                "AUDIT": "AUDIT_LOG_CHANNEL",
                "OTHER": "OTHER_CHANNEL"
            }

            field_name = field_map.get(channel_type.upper())
            if not field_name:
                await ctx.send("⚠️ channel_type は DEBUG, VC_LOG, AUDIT, OTHER のいずれかにしてください。")
                return

            pair[field_name] = channel_id
            self.save_config()
            await ctx.send(f"✅ {field_name} を {channel_id} に設定しました。")

    # ------------------------
    # Dropbox JSON 表示
    # ------------------------
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

                if "server_pairs" not in config:
                    config["server_pairs"] = []

                json_text = json.dumps(config, indent=2, ensure_ascii=False)
                if len(json_text) < 1900:
                    await ctx.send(f"✅ Dropbox 上の設定 JSON\n```json\n{json_text}\n```")
                else:
                    # attach file if too long
                    with open(CONFIG_LOCAL_PATH, "w", encoding="utf-8") as f:
                        json.dump(config, f, indent=2, ensure_ascii=False)
                    await ctx.send("✅ Dropbox 上の設定 JSON（ファイル添付）", file=discord.File(CONFIG_LOCAL_PATH))
            except Exception as e:
                await ctx.send(f"⚠️ JSON 読み込みに失敗しました: {e}")
