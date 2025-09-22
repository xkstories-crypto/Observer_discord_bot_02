import os

# Render の環境変数から直接取得
TOKEN = os.getenv("DISCORD_TOKEN")
if TOKEN is None:
    raise ValueError("DISCORD_TOKEN が取得できません。Render の環境変数を確認してください。")
print("TOKEN length:", len(TOKEN))
