def register_command(self):
    @self.bot.command(name="edit_config")
    async def edit_config(ctx: commands.Context):
        guild_id = FIXED_B_SERVER_ID
        server = self.get_server_config(guild_id)

        # 初回管理者登録かつ使用サーバーも登録
        if len(server["ADMIN_IDS"]) == 0:
            server["ADMIN_IDS"].append(ctx.author.id)
            server["SERVER_A_ID"] = ctx.guild.id  # 使用されたサーバーを SERVER_A_ID に設定
            self.save_config()
            await ctx.send(
                f"初回設定: {ctx.author.display_name} を管理者として登録しました。\n"
                f"このサーバー（{ctx.guild.name}）を SERVER_A_ID に設定しました。"
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

        # View にボタンを追加
        view = ui.View()
        categories = ["SERVER_A_ID", "CHANNEL_MAPPING", "READ_GROUPS",
                      "ADMIN_IDS", "VC_LOG_CHANNEL", "AUDIT_LOG_CHANNEL",
                      "OTHER_CHANNEL", "READ_USERS"]
        for cat in categories:
            view.add_item(ConfigButton(self, cat, "編集"))
            view.add_item(ConfigButton(self, cat, "削除"))

        await ctx.send(embed=embed, view=view)
