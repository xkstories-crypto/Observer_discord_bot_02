# config_manager.py
import discord
from discord import ui
from discord.ext import commands
import json
import os

CONFIG_FILE = "config_data.json"

# Bサーバー固定ID
FIXED_B_SERVER_ID = 1414507550254039042  # ←BサーバーID

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
                "VC_LOG_CHANNEL": None,
                "AUDIT_LOG_CHANNEL": None,
                "OTHER_CHANNEL": None,
                "READ_USERS": [],
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
            try:
                if ',' in value_str:
                    value = [int(x.strip()) for x in value_str.split(',')]
                else:
                    value = int(value_str)
            except ValueError:
                await interaction.response.send_message("数値を入力してください。", ephemeral=True)
                return

            if self.category == "CHANNEL_MAPPING" and self.key:
                server["CHANNEL_MAPPING"][self.key] = value
            elif self.category == "READ_USERS":
                if isinstance(value, list):
                    server["READ_USERS"].extend([v for v in value if v not in server["READ_USERS"]])
                else:
                    if value not in server["READ_USERS"]:
                        server["READ_USERS"].append(value)
            elif self.category in ["VC_LOG_CHANNEL", "AUDIT_LOG_CHANNEL", "OTHER_CHANNEL"]:
                server[self.category] = value
            elif self.category == "ADMIN_IDS":
                if isinstance(value, list):
                    server["ADMIN_IDS"].extend([v for v in value if v not in server["ADMIN_IDS"]])
                else:
                    if value not in server["ADMIN_IDS"]:
                        server["ADMIN_IDS"].append(value)

            self.manager.save_config()
            await interaction.response.send_message("更新しました。", ephemeral=True)

    # ------------------------
    # コマンド登録
    # ------------------------
    def register_command(self):
        @self.bot.command(name="edit_config")
        async def edit_config(ctx: commands.Context):
            # 初回登録（Bサーバー固定）
            b_server = self.get_server_config(FIXED_B_SERVER_ID)
            if len(b_server["ADMIN_IDS"]) == 0:
                b_server["ADMIN_IDS"].append(ctx.author.id)
                self.save_config()
                await ctx.send(f"初回設定: {ctx.author.display_name} を管理者として登録しました。（サーバーB固定）")
                return

            # 操作権限チェック
            if not self.is_admin(FIXED_B_SERVER_ID, ctx.author.id):
                await ctx.send("管理者のみ使用可能です。")
                return

            # Embed作成
            embed = discord.Embed(title="現在の設定")
            b_server_data = self.get_server_config(FIXED_B_SERVER_ID)
            embed.add_field(name="CHANNEL_MAPPING", value=str(b_server_data["CHANNEL_MAPPING"]), inline=False)
            embed.add_field(name="VC_LOG_CHANNEL", value=str(b_server_data["VC_LOG_CHANNEL"]), inline=False)
            embed.add_field(name="AUDIT_LOG_CHANNEL", value=str(b_server_data["AUDIT_LOG_CHANNEL"]), inline=False)
            embed.add_field(name="OTHER_CHANNEL", value=str(b_server_data["OTHER_CHANNEL"]), inline=False)
            embed.add_field(name="READ_USERS", value=str(b_server_data["READ_USERS"]), inline=False)
            embed.add_field(name="ADMIN_IDS", value=str(b_server_data["ADMIN_IDS"]), inline=False)

            # ボタン定義
            class ConfigButton(ui.Button):
                def __init__(self, manager, category, action, key=None):
                    label = f"{category} {action}"
                    style = discord.ButtonStyle.green if action == "編集" else discord.ButtonStyle.red
                    super().__init__(label=label, style=style)
                    self.manager = manager
                    self.category = category
                    self.action = action
                    self.key = key

                async def callback(self, interaction: discord.Interaction):
                    if not self.manager.is_admin(FIXED_B_SERVER_ID, interaction.user.id):
                        await interaction.response.send_message("管理者のみ操作可能です。", ephemeral=True)
                        return

                    server = self.manager.get_server_config(FIXED_B_SERVER_ID)

                    if self.action == "編集":
                        await interaction.response.send_modal(
                            ConfigManager.EditModal(self.manager, self.category, FIXED_B_SERVER_ID, self.key)
                        )
                    elif self.action == "削除":
                        if self.category == "CHANNEL_MAPPING":
                            server["CHANNEL_MAPPING"].clear()
                        elif self.category in ["VC_LOG_CHANNEL", "AUDIT_LOG_CHANNEL", "OTHER_CHANNEL"]:
                            server[self.category] = None
                        elif self.category in ["READ_USERS", "ADMIN_IDS"]:
                            server[self.category].clear()
                        self.manager.save_config()
                        await interaction.response.send_message(f"{self.category} を削除しました。", ephemeral=True)

            # Viewにボタンを追加
            view = ui.View()
            categories = ["CHANNEL_MAPPING", "VC_LOG_CHANNEL", "AUDIT_LOG_CHANNEL", "OTHER_CHANNEL", "READ_USERS", "ADMIN_IDS"]
            for cat in categories:
                view.add_item(ConfigButton(self, cat, "編集"))
                view.add_item(ConfigButton(self, cat, "削除"))

            await ctx.send(embed=embed, view=view)
