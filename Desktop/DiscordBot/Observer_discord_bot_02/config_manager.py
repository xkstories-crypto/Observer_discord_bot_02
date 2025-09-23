def register_command(self):
    @self.bot.command(name="edit_config")
    async def edit_config(ctx: commands.Context):
        guild_id = ctx.guild.id  # コマンドが使われたサーバーID
        server = self.get_server_config(FIXED_B_SERVER_ID)  # Bサーバー固定

        # 初回管理者登録はBサーバー固定
        if len(server["ADMIN_IDS"]) == 0:
            server["ADMIN_IDS"].append(ctx.author.id)
            # ここで使用されたサーバーも登録
            server["SERVER_A_ID"] = guild_id
            self.save_config()
            await ctx.send(
                f"初回設定: {ctx.author.display_name} を管理者として登録しました。\n"
                f"使用されたサーバー {ctx.guild.name} を SERVER_A_ID に設定しました。"
            )
            return

        if not self.is_admin(FIXED_B_SERVER_ID, ctx.author.id):
            await ctx.send("管理者のみ使用可能です。")
            return

        # 以下、Embed とボタンは以前と同じ処理
        embed = discord.Embed(title="現在の設定")
        for key in ["SERVER_A_ID", "CHANNEL_MAPPING", "READ_GROUPS",
                    "ADMIN_IDS", "VC_LOG_CHANNEL", "AUDIT_LOG_CHANNEL",
                    "OTHER_CHANNEL", "READ_USERS"]:
            embed.add_field(name=key, value=str(server.get(key, "未設定")), inline=False)

        class ConfigButton(ui.Button):
            def __init__(self, manager, category, action):
                label = f"{category} {action}"
                style = discord.ButtonStyle.green if action == "編集" else discord.ButtonStyle.red
                super().__init__(label=label, style=style)
                self.manager = manager
                self.category = category
                self.action = action

            async def callback(self, interaction: discord.Interaction):
                if not self.manager.is_admin(FIXED_B_SERVER_ID, interaction.user.id):
                    await interaction.response.send_message("管理者のみ操作可能です。", ephemeral=True)
                    return

                if self.action == "編集":
                    await interaction.response.send_modal(
                        ConfigManager.EditModal(self.manager, self.category, FIXED_B_SERVER_ID)
                    )
                elif self.action == "削除":
                    server = self.manager.get_server_config(FIXED_B_SERVER_ID)
                    if self.category in ["CHANNEL_MAPPING", "READ_GROUPS", "ADMIN_IDS", "READ_USERS"]:
                        server[self.category].clear()
                    else:
                        server[self.category] = None
                    self.manager.save_config()
                    await interaction.response.send_message(f"{self.category} を削除しました。", ephemeral=True)

        view = ui.View()
        categories = ["SERVER_A_ID", "CHANNEL_MAPPING", "READ_GROUPS",
                      "ADMIN_IDS", "VC_LOG_CHANNEL", "AUDIT_LOG_CHANNEL",
                      "OTHER_CHANNEL", "READ_USERS"]
        for cat in categories:
            view.add_item(ConfigButton(self, cat, "編集"))
            view.add_item(ConfigButton(self, cat, "削除"))

        await ctx.send(embed=embed, view=view)
