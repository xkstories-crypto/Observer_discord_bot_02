# -------- !set_server --------
@bot.command(name="set_server")
async def set_server(ctx: commands.Context, server_a_id: int):
    server = self.get_server_config(ctx.guild.id)

    if not self.is_admin(ctx.guild.id, ctx.author.id):
        await ctx.send("管理者のみ使用可能です。")
        return

    server["SERVER_A_ID"] = server_a_id
    self.save_config()
    await ctx.send(f"✅ SERVER_A_ID を {server_a_id} に設定しました。")

    # --- チャンネルコピー処理 ---
    guild_a = bot.get_guild(server_a_id)
    guild_b = bot.get_guild(server["SERVER_B_ID"])

    if guild_a is None or guild_b is None:
        await ctx.send("⚠️ サーバーが見つかりません。Botが両方のサーバーに参加しているか確認してください。")
        return

    # チャンネル構造コピー
    for channel in guild_a.channels:
        if isinstance(channel, discord.CategoryChannel):
            cat = await guild_b.create_category(name=channel.name)
            server["CHANNEL_MAPPING"][str(channel.id)] = cat.id

        elif isinstance(channel, discord.TextChannel):
            category_id = server["CHANNEL_MAPPING"].get(str(channel.category_id))
            cat = guild_b.get_channel(category_id) if category_id else None
            new_ch = await guild_b.create_text_channel(name=channel.name, category=cat)
            server["CHANNEL_MAPPING"][str(channel.id)] = new_ch.id

        elif isinstance(channel, discord.VoiceChannel):
            category_id = server["CHANNEL_MAPPING"].get(str(channel.category_id))
            cat = guild_b.get_channel(category_id) if category_id else None
            new_ch = await guild_b.create_voice_channel(name=channel.name, category=cat)
            server["CHANNEL_MAPPING"][str(channel.id)] = new_ch.id

    self.save_config()
    await ctx.send("✅ Aサーバーのチャンネル構造をBサーバーにコピーしました。")
