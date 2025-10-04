@commands.command()
async def copy_channels(self, ctx, server_a_id: int, server_b_id: int):
    guild_a = self.bot.get_guild(server_a_id)
    guild_b = self.bot.get_guild(server_b_id)

    if not guild_a or not guild_b:
        await ctx.send("❌ サーバーが見つかりません。Botが両方のサーバーに参加しているか確認してください。")
        return

    print(f"[DEBUG] チャンネルコピー開始: {guild_a.name} → {guild_b.name}")

    # 設定取得
    a_conf = self.get_server_config(guild_a.id)
    b_conf = self.get_server_config(guild_b.id)

    # 互いのサーバーIDを設定
    a_conf["SERVER_B_ID"] = guild_b.id
    b_conf["SERVER_A_ID"] = guild_a.id

    # チャンネルマッピング初期化
    if "CHANNEL_MAPPING" not in a_conf:
        a_conf["CHANNEL_MAPPING"] = {}
    if "CHANNEL_MAPPING" not in b_conf:
        b_conf["CHANNEL_MAPPING"] = {}

    # Aサーバーのチャンネルをコピー
    for category in guild_a.categories:
        # カテゴリ作成
        new_category = await guild_b.create_category(name=category.name)
        print(f"[DEBUG] カテゴリ作成: {category.name} -> {new_category.name}")

        for channel in category.channels:
            # テキスト or ボイスチャンネルを判定して作成
            if isinstance(channel, discord.TextChannel):
                new_channel = await guild_b.create_text_channel(name=channel.name, category=new_category)
            elif isinstance(channel, discord.VoiceChannel):
                new_channel = await guild_b.create_voice_channel(name=channel.name, category=new_category)
            else:
                continue

            # マッピング保存（向き修正済み）
            a_conf["CHANNEL_MAPPING"][channel.id] = new_channel.id
            b_conf["CHANNEL_MAPPING"][new_channel.id] = channel.id

            # デバッグ出力
            print(f"[DEBUG] A→Bマッピング追加: {channel.name} ({channel.id}) → {new_channel.name} ({new_channel.id})")
            print(f"[DEBUG] B→Aマッピング追加: {new_channel.name} ({new_channel.id}) → {channel.name} ({channel.id})")

    # 保存
    self.save_server_config(guild_a.id, a_conf)
    self.save_server_config(guild_b.id, b_conf)

    print(f"[DEBUG] サーバー設定保存完了: {guild_a.name}, {guild_b.name}")
    await ctx.send(f"✅ Aサーバー ({guild_a.name}) → Bサーバー ({guild_b.name}) のチャンネルコピー完了、JSONも同期しました。")
