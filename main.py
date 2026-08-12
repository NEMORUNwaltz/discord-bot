import os
import json
import threading
from flask import Flask
import discord
from discord import app_commands
from discord.ext import commands

# --- Render & UptimeRobot 用のFlask Webサーバー ---
app = Flask('')

@app.route('/')
def home():
    return "Bot is alive!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = threading.Thread(target=run_flask)
    t.daemon = True
    t.start()

# --- 14タイトルの設定（SF6追加済み） ---
GAMES = {
    "apex": {"name": "Apex", "emoji": "🔫"},
    "ow2": {"name": "OW2", "emoji": "🛡️"},
    "valo": {"name": "VALO", "emoji": "🎯"},
    "mc_java": {"name": "MINECRAFT JAVA", "emoji": "⛏️"},
    "mc_be": {"name": "MINECRAFT BE", "emoji": "🧱"},
    "mahjong": {"name": "雀魂", "emoji": "🀄"},
    "lol": {"name": "LOL", "emoji": "⚔️"},
    "genshin": {"name": "原神", "emoji": "✨"},
    "fortnite": {"name": "FORTNITE", "emoji": "🪂"},
    "terraria": {"name": "TERRARIA", "emoji": "🌳"},
    "mh_wilds": {"name": "MH:WILDS", "emoji": "🐉"},
    "osu": {"name": "OSU!", "emoji": "🎵"},
    "eft": {"name": "EFT", "emoji": "🪖"},
    "sf6": {"name": "SF6", "emoji": "🥊"}
}

RECRUIT_CHANNEL_NAME = "❗募集一覧"
DATA_CHANNEL_NAME = "bot-data-store"

USER_TAGS = {key: set() for key in GAMES.keys()}

def get_user_tag_names(user_id: int) -> list:
    return [data["name"] for g_id, data in GAMES.items() if user_id in USER_TAGS.get(g_id, set())]

# --- データの自動保存・復元処理（バックアップ機能） ---
async def save_tags_to_discord(guild: discord.Guild):
    try:
        channel = discord.utils.get(guild.text_channels, name=DATA_CHANNEL_NAME)
        if not channel:
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
            }
            channel = await guild.create_text_channel(DATA_CHANNEL_NAME, overwrites=overwrites)

        data_to_save = {k: list(v) for k, v in USER_TAGS.items()}
        json_str = json.dumps(data_to_save)
        await channel.send(f"```json\n{json_str}\n```")
    except Exception as e:
        print(f"データ保存エラー: {e}")

async def load_tags_from_discord(guild: discord.Guild):
    try:
        channel = discord.utils.get(guild.text_channels, name=DATA_CHANNEL_NAME)
        if not channel:
            return
        async for msg in channel.history(limit=10):
            if msg.content.startswith("```json"):
                # 安全な取り除き方に修正（改行事故を完全に防止）
                raw_json = msg.content.strip().removeprefix("
