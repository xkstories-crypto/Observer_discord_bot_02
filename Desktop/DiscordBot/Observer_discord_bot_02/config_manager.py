# config_manager.py
import discord
from discord import ui
from discord.ext import commands
import json
import os

CONFIG_FILE = "config_data.json"

class ConfigManager:
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.load_config()
        self.register_command()

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
                "CHANNEL_MAPPING": {},
                "READ_GROUPS": {},
                "CHANNEL_GROUPS": {},
                "ADMIN_IDS": []
            }
        return self.config["servers"][sid]

    def is_admin(self, guild_id, user_id):
        server = self.get_server_config(guild_id)
        return user_id in server["ADMIN_IDS"]

    # ------------------------
    # モーダル
    # ------------------------
    class EditModal(ui.Modal):
        def __init__(self, manager, category, guild_id, key=None):
            super().__init__(title=f"{category} 編集")
            self.manager = manager
            self.category = category
            self.guild_id = guild_id
            self.key = key

            self.input1 = ui.TextInput(
                label="新しい値",
                placeholder="チャンネルID, ユーザーID, またはカンマ区切り"
            )
            self.add_item(self.input1)

        async def on_submit(self, interaction: discord.Interaction):
            server = self.manager.get_server_config(self.guild_id)
            value_str = self.input1.value.strip()
            # 数値のリストに変換
            try:
                if ',' in value_str:
                    value = [int(x.strip()) for x in value_str.split(',')]
                else:
                    value = int(value_str)
            except ValueError:
                await interaction.response.send_message("数値を入力してください。", ephemeral=True)
                return

            if self.category == "channel_mapping" and self.key:
                server["CHANNEL_MAPPING"][self.key] = value
            elif self.category == "read_groups":
                server["READ_GROUPS"][value_str.split()[0]] = value if isinstance(value, list) else [value]
            elif self.category == "channel_groups":
                server["CHANNEL_GROUPS"][value_str.split()[0]] = value if isinstance(value, list) else [value]
            elif self.category == "admin_ids":
                if isinstance(value, list):
                    server["ADMIN_IDS"].extend([v for v in value if v not in server["ADMIN_IDS"]])
                else:
                    if value not in server["ADMIN_IDS"]:
                        server["ADMIN_IDS"].append(value)

            self.manager.save_config()
            await interaction.response.send_message("更新しました。", ephemeral=True)

    # ------------------------
    # セレクトメニュー
    # ------------------------
    class SelectMenu(ui.Select):
        def __init__(self, manager, category, guild_id):
            self.manager = manager
            self.category = category
            self.guild_id = guild_id

            server = manager.get_server_config(guild_id)
            options = []

            if category == "channel_mapping":
                options = [discord.SelectOption(label=f"{src} → {dst}", value=str(src))
                           for src, dst in server["CHANNEL_MAPPING"].items()]
            elif category == "read_groups":
                options = [discord.SelectOption(label=name, value=name) for name in server["READ_GROUPS"].keys()]
            elif category == "channel_groups":
                options = [discord.SelectOption(label=name, value=name) for name in server["CHANNEL_GROUPS"].keys()]
            elif category == "admin_ids":
                options = [discord.SelectOption(label=str(uid), value=str(uid)) for uid in server["ADMIN_IDS"]]

            super().__init__(placeholder=f"{category} を選択", options=options, max_values=1)

        async def callback(self, interaction: discord.Interaction):
            key = self.values[0]
            await interaction.response.send_message(
                f"{self.category} {key} を選択しました。操作ボタンで選んでください。",
                ephemeral=True,
                view=ConfigManager.ActionView(self.manager, self.category, self.guild_id, key)
            )

    # ------------------------
    # ボタンビュー
    # ------------------------
    class ActionView(ui.View):
        def __init__(self, manager, category, guild_id, key=None):
            super().__init__(timeout=None)
            self.manager = manager
            self.category = category
            self.guild_id = guild_id
            self.key = key

        async def interaction_check(self, interaction: discord.Interaction) -> bool:
            if not self.manager.is_admin(interaction.guild.id, interaction.user.id):
                await interaction.response.send_message("管理者のみ操作可能です。", ephemeral=True)
                return False
            return True

        @ui.button(label="編集", style=discord.ButtonStyle.green)
        async def edit_button(self, interaction: discord.Interaction, button: ui.Button):
            await interaction.response.send_modal(
                ConfigManager.EditModal(self.manager, self.category, interaction.guild.id, self.key)
            )

        @ui.button(label="削除", style=discord.ButtonStyle.red)
        async def delete_button(self, interaction: discord.Interaction, button: ui.Button):
            server = self.manager.get_server_config(interaction.guild.id)
            if self.category == "channel_mapping" and self.key:
                server["CHANNEL_MAPPING"].pop(self.key, None)
            elif self.category == "read_groups" and self.key in server["READ_GROUPS"]:
                server["READ_GROUPS"].pop(self.key)
            elif self.category == "channel_groups" and self.key in server["CHANNEL_GROUPS"]:
                server["CHANNEL_GROUPS"].pop(self.key)
            elif self.category == "admin_ids" and int(self.key) in server["ADMIN_IDS"]:
                server["ADMIN_IDS"].remove(int(self.key))
            self.manager.save_config()
            await interaction.response.send_message("削除しました。", ephemeral=True)

    # ------------------------
    # /edit_config コマンド登録
    # ------------------------
    def register_command(self):
        @self.bot.tree.command(name="edit_config", description="Bot設定を管理")
        async def edit_config(interaction: discord.Interaction):
            server = self.get_server_config(interaction.guild.id)

            # 初回管理者登録
            if len(server["ADMIN_IDS"]) == 0:
                server["ADMIN_IDS"].append(interaction.user.id)
                self.save_config()
                await interaction.response.send_message(
                    f"初回設定: {interaction.user.display_name} を管理者として登録しました。",
                    ephemeral=True
                )
                return

            # 管理者チェック
            if not self.is_admin(interaction.guild.id, interaction.user.id):
                await interaction.response.send_message("管理者のみ使用可能です。", ephemeral=True)
                return

            # Embed + ボタン
            embed = discord.Embed(title="現在の設定")
            embed.add_field(name="CHANNEL_MAPPING", value=str(server["CHANNEL_MAPPING"]), inline=False)
            embed.add_field(name="READ_GROUPS", value=str(server["READ_GROUPS"]), inline=False)
            embed.add_field(name="CHANNEL_GROUPS", value=str(server["CHANNEL_GROUPS"]), inline=False)
            embed.add_field(name="ADMIN_IDS", value=str(server["ADMIN_IDS"]), inline=False)

            view = ui.View()
            view.add_item(ui.Button(label="チャンネル編集", style=discord.ButtonStyle.blurple, custom_id="channel_mapping"))
            view.add_item(ui.Button(label="読み上げグループ編集", style=discord.ButtonStyle.blurple, custom_id="read_groups"))
            view.add_item(ui.Button(label="チャンネルグループ編集", style=discord.ButtonStyle.blurple, custom_id="channel_groups"))
            view.add_item(ui.Button(label="管理者編集", style=discord.ButtonStyle.blurple, custom_id="admin_ids"))
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
