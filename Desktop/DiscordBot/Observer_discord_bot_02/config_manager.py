        @bot.command(name="set_server")
        async def set_server(ctx: commands.Context, server_a_id: int):
            server_b_id = ctx.guild.id
            b_conf = self.get_server_config(server_b_id)

            if not self.is_admin(server_b_id, ctx.author.id):
                await ctx.send("⚠️ 管理者のみ使用可能です。")
                return

            await ctx.send(f"🚀 SERVER_A_ID を {server_a_id} に設定します。処理を開始します...")
            print(f"[DEBUG] set_server called: server_a_id={server_a_id}, server_b_id={server_b_id}")

            # ---------- ギルド取得 ----------
            guild_a = bot.get_guild(server_a_id)
            guild_b = bot.get_guild(server_b_id)
            print(f"[DEBUG] get_guild: guild_a={guild_a}, guild_b={guild_b}")
            if guild_a is None or guild_b is None:
                await ctx.send("⚠️ サーバーが見つかりません。Botが両方のサーバーに参加しているか確認してください。")
                print("[ERROR] サーバーが None")
                return
            await ctx.send(f"✅ サーバー取得完了: A={guild_a.name}, B={guild_b.name}")

            # ---------- ID設定 ----------
            a_conf = self.get_server_config(guild_a.id)
            b_conf["SERVER_A_ID"] = guild_a.id
            b_conf["SERVER_B_ID"] = guild_b.id
            a_conf["SERVER_A_ID"] = guild_a.id
            a_conf["SERVER_B_ID"] = guild_b.id
            await ctx.send("📝 サーバーIDを設定しました (保存は後で実行)")

            # ---------- Bにチャンネル生成 ----------
            await ctx.send("📂 チャンネルコピー処理を開始します...")
            temp_mapping = {}
            created = 0
            skipped = 0
            errors = []

            for channel in guild_a.channels:
                try:
                    a_key = str(channel.id)
                    if a_key in b_conf.get("CHANNEL_MAPPING", {}):
                        skipped += 1
                        msg = f"[SKIP] {channel.name} はすでにマッピング済み"
                        await ctx.send(msg)
                        print(msg)
                        continue

                    if isinstance(channel, discord.CategoryChannel):
                        new_cat = await guild_b.create_category(name=channel.name)
                        temp_mapping[a_key] = str(new_cat.id)
                        created += 1
                        msg = f"[作成] カテゴリ {channel.name} -> {new_cat.id}"
                        await ctx.send(msg)
                        print(f"[CREATE] Category {channel.name} -> {new_cat.id}")

                    elif isinstance(channel, discord.TextChannel):
                        cat_id = temp_mapping.get(str(channel.category_id))
                        cat = guild_b.get_channel(int(cat_id)) if cat_id else None
                        new_ch = await guild_b.create_text_channel(name=channel.name, category=cat)
                        temp_mapping[a_key] = str(new_ch.id)
                        created += 1
                        msg = f"[作成] テキスト {channel.name} -> {new_ch.id}"
                        await ctx.send(msg)
                        print(f"[CREATE] TextChannel {channel.name} -> {new_ch.id}")

                    elif isinstance(channel, discord.VoiceChannel):
                        cat_id = temp_mapping.get(str(channel.category_id))
                        cat = guild_b.get_channel(int(cat_id)) if cat_id else None
                        new_ch = await guild_b.create_voice_channel(name=channel.name, category=cat)
                        temp_mapping[a_key] = str(new_ch.id)
                        created += 1
                        msg = f"[作成] ボイス {channel.name} -> {new_ch.id}"
                        await ctx.send(msg)
                        print(f"[CREATE] VoiceChannel {channel.name} -> {new_ch.id}")

                except discord.Forbidden:
                    msg = f"⚠️ 権限不足で `{channel.name}` の作成に失敗しました"
                    errors.append(msg)
                    await ctx.send(msg)
                    print("[ERROR] Forbidden:", channel.name)
                except discord.HTTPException as e:
                    msg = f"⚠️ Discord API エラー `{channel.name}`: {e}"
                    errors.append(msg)
                    await ctx.send(msg)
                    print("[ERROR] HTTPException:", e)
                except Exception as e:
                    msg = f"⚠️ 不明なエラー `{channel.name}`: {e}"
                    errors.append(msg)
                    await ctx.send(msg)
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
            await ctx.send("💾 マッピングと設定を保存しました")
            print("[DEBUG] 設定保存完了")

            # ---------- レポート ----------
            report = f"🎉 完了: 作成 {created} 件、スキップ {skipped} 件、エラー {len(errors)} 件"
            await ctx.send(report)
            if errors:
                await ctx.send("⚠️ エラー詳細はコンソールログを確認してください")
            print(f"[REPORT] {report}")
