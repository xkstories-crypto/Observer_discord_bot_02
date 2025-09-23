def register_command(self):
    @self.bot.command(name="edit_config")
    async def edit_config(ctx: commands.Context):
        guild_id = ctx.guild.id  # 実行サーバー
        server = self.get_server_config(guild_id)

        # 初回設定処理
        if len(server["ADMIN_IDS"]) == 0 or "SERVER_B_ID" not in server:
            if ctx.author.id not in server["ADMIN_IDS"]:
                server["ADMIN_IDS"].append(ctx.author.id)

            server["SERVER_B_ID"] = guild_id  # BサーバーID登録

            self.save_config()
            await ctx.send(
                f"初回設定完了:\n管理者 → {ctx.author.display_name}\nBサーバーID → {guild_id}"
            )
            return

        # 管理者チェック
        if not self.is_admin(guild_id, ctx.author.id):
            await ctx.send("管理者のみ使用可能です。")
            return

        # Embed 作成
        embed = discord.Embed(title="現在の設定")
        for key in [
            "SERVER_A_ID",
            "SERVER_B_ID",  # 表示はする
            "CHANNEL_MAPPING",
            "ADMIN_IDS",
            "VC_LOG_CHANNEL",
            "AUDIT_LOG_CHANNEL",
            "OTHER_CHANNEL",
            "READ_USERS",
        ]:
            embed.add_field(name=key, value=str(server.get(key, "未設定")), inline=False)

        # ボタン定義
        class ConfigButton(ui.Button):
            def __init__(self, manager, category, action):
                label = f"{category} {action}"
                style = (
                    discord.ButtonStyle.green
                    if action == "編集"
                    else discord.ButtonStyle.red
                )
                super().__init__(label=label, style=style)
                self.manager = manager
                self.category = category
                self.action = action

            async def callback(self, interaction: discord.Interaction):
                if not self.manager.is_admin(interaction.guild.id, interaction.user.id):
                    await interaction.response.send_message(
                        "管理者のみ操作可能です。", ephemeral=True
                    )
                    return

                # SERVER_B_ID は編集禁止
                if self.category == "SERVER_B_ID":
                    await interaction.response.send_message(
                        "SERVER_B_ID は編集できません。", ephemeral=True
                    )
                    return

                if self.action == "編集":
                    await interaction.response.send_modal(
                        ConfigManager.EditModal(
                            self.manager, self.category, interaction.guild.id
                        )
                    )
                elif self.action == "削除":
                    server = self.manager.get_server_config(interaction.guild.id)
                    if self.category in [
                        "CHANNEL_MAPPING",
                        "READ_GROUPS",
                        "ADMIN_IDS",
                        "READ_USERS",
                    ]:
                        server[self.category].clear()
                    else:
                        server[self.category] = None
                    self.manager.save_config()
                    await interaction.response.send_message(
                        f"{self.category} を削除しました。", ephemeral=True
                    )

        # View にボタンを追加
        view = ui.View()
        categories = [
            "SERVER_A_ID",
            "SERVER_B_ID",  # ここは表示専用
            "CHANNEL_MAPPING",
            "ADMIN_IDS",
            "VC_LOG_CHANNEL",
            "AUDIT_LOG_CHANNEL",
            "OTHER_CHANNEL",
            "READ_USERS",
        ]
        for cat in categories:
            if cat == "SERVER_B_ID":
                continue  # ボタンは追加しない
            view.add_item(ConfigButton(self, cat, "編集"))
            view.add_item(ConfigButton(self, cat, "削除"))

        await ctx.send(embed=embed, view=view)
