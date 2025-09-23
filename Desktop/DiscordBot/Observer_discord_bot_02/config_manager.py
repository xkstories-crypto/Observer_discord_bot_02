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
                "SERVER_A_ID": None,
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
                placeholder="チャンネルID, ユーザーID, サーバーIDなど"
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
            elif self.category in ["READ_GROUPS", "READ_USERS", "ADMIN_IDS"]:
                if isinstance(value, list):
                    if self.category == "ADMIN_IDS":
                        server["ADMIN_IDS"].extend([v for v in value if v not in server["ADMIN_IDS"]])
                    elif self.category == "READ_USERS":
                        server["READ_USERS"].extend([v for v in value if v not in server["READ_USERS"]])
                    else:
                        server[self.category][value_str.split()[0]] = value
                else:
                    if self.category == "ADMIN_IDS" and value not in server["ADMIN_IDS"]:
                        server["ADMIN_IDS"].append(value)
                    elif self.category == "READ_USERS" and value not in server["READ_USERS"]:
                        server["READ_USERS"].append(value)
                    else:
                        server[self.category][value_str.split()[0]] = [value]
            else:
                server[self.category] = value

            self.manager.save_config()
            await interaction.response.send_message("更新しました。", ephemeral=True)

    # ------------------------
    # !edit_config コマンド登録
    # ------------------------
    def register_command(self):
        @self.bot.command(name="edit_config")
        async def edit_config(ctx: commands.Context):
            guild_id = ctx.guild.id
            server = self.get_server_config(guild_id)

            # 初回管理者登録
            if len(server["ADMIN_IDS"]) == 0:
                server["ADMIN_IDS"].append(ctx.author.id)

                # 使用されたサーバーを SERVER_B_ID に設定
                server["SERVER_B_ID"] = ctx.guild.id

                self.save_config()
                await ctx.send(
                    f"初回設定: {ctx.author.display_name} を管理者として登録しました。\n"
                    f"使用サーバー: {ctx.guild.id} を SERVER_B_ID に設定しました。"
                )
                return

            # 管理者チェック
            if not self.is_admin(guild_id, ctx.author.id):
                await ctx.send("管理者のみ使用可能です。")
                return

            # Embed 作成
            embed = discord.Embed(title="現在の設定")
            for key in ["SERVER_A_ID", "CHANNEL_MAPPING", "READ_GROUPS",
                        "ADMIN_IDS", "VC_LOG_CHANNEL", "AUDIT_LOG_CHANNEL",
                        "OTHER_CHANNEL", "READ_USERS"]:
                embed.add_field(name=key, value=str(server.get(key, "未設定")), inline=False)

            # ボタン定義
            class ConfigButton(ui.Button):
                def __init__(self, manager, category, action):
                    label = f"{category} {action}"
                    style = discord.ButtonStyle.green if action == "編集" else discord.ButtonStyle.red
                    super().__init__(label=label, style=style)
                    self.manager = manager
                    self.category = category
                    self.action = action

                async def callback(self, interaction: discord.Interaction):
                    if not self.manager.is_admin(interaction.guild.id, interaction.user.id):
                        await interaction.response.send_message("管理者のみ操作可能です。", ephemeral=True)
                        return

                    if self.action == "編集":
                        await interaction.response.send_modal(
                            ConfigManager.EditModal(self.manager, self.category, interaction.guild.id)
                        )
                    elif self.action == "削除":
                        server = self.manager.get_server_config(interaction.guild.id)
                        if self.category in ["CHANNEL_MAPPING", "READ_GROUPS", "ADMIN_IDS", "READ_USERS"]:
                            server[self.category].clear()
                        else:
                            server[self.category] = None
                        self.manager.save_config()
                        await interaction.response.send_message(f"{self.category} を削除しました。", ephemeral=True)

            # View にボタンを追加
            view = ui.View()
            categories = ["SERVER_A_ID", "CHANNEL_MAPPING", "READ_GROUPS",
                          "ADMIN_IDS", "VC_LOG_CHANNEL", "AUDIT_LOG_CHANNEL",
                          "OTHER_CHANNEL", "READ_USERS"]
            for cat in categories:
                view.add_item(ConfigButton(self, cat, "編集"))
                view.add_item(ConfigButton(self, cat, "削除"))

            await ctx.send(embed=embed, view=view)
