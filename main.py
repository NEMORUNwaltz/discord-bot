import os
import json
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import discord
from discord import app_commands
from discord.ext import commands

# --- Render & UptimeRobot 用のダミーWebサーバー ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

def run_web_server():
    port = int(os.getenv("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    print(f"Webサーバーをポート {port} で起動しました。")
    server.serve_forever()

# バックグラウンドでWebサーバーを起動（Renderのタイムアウト回避）
threading.Thread(target=run_web_server, daemon=True).start()

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
                raw_json = msg.content.replace("```json\n", "").replace("\n```", "")
                data = json.loads(raw_json)
                for k, v in data.items():
                    if k in USER_TAGS:
                        USER_TAGS[k] = set(v)
                print("タグデータを正常に復元しました！")
                break
    except Exception as e:
        print(f"データ復元エラー: {e}")

# 募集用モーダル（ポップアップ）
class RecruitModal(discord.ui.Modal):
    def __init__(self, game_id: str):
        game_name = GAMES[game_id]["name"]
        super().__init__(title=f"{game_name} メンバー募集")
        self.game_id = game_id

        self.message_input = discord.ui.TextInput(
            label="募集内容・メッセージ",
            style=discord.TextStyle.paragraph,
            placeholder="例：今から@3募集！誰でもどうぞ！",
            required=True,
            max_length=200
        )
        self.add_item(self.message_input)

    async def on_submit(self, interaction: discord.Interaction):
        target_users = USER_TAGS.get(self.game_id, set())
        game_name = GAMES[self.game_id]["name"]

        if not target_users:
            await interaction.response.send_message(
                f"⚠️ 現在 `{game_name}` のタグを持っているユーザーがいません。", 
                ephemeral=True
            )
            return

        mentions = " ".join([f"<@{user_id}>" for user_id in target_users])
        content = f"📢 **【{game_name} 募集】** (送信者: {interaction.user.mention})\n" \
                  f"メッセージ: {self.message_input.value}\n\n" \
                  f"通知: {mentions}"

        guild = interaction.guild
        target_channel = discord.utils.get(guild.text_channels, name=RECRUIT_CHANNEL_NAME) if guild else None

        if target_channel:
            await target_channel.send(content)
            await interaction.response.send_message(
                f"✅ <#{target_channel.id}> に募集を投稿したよ！", 
                ephemeral=True
            )
        else:
            await interaction.response.send_message(content)

# --- 登録・解除の操作ボタンView ---
class TagActionView(discord.ui.View):
    def __init__(self, game_id: str):
        super().__init__(timeout=60)
        self.game_id = game_id

    @discord.ui.button(label="✅ 登録する", style=discord.ButtonStyle.success)
    async def add_tag(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        user_id = interaction.user.id
        USER_TAGS[self.game_id].add(user_id)
        
        if interaction.guild:
            await save_tags_to_discord(interaction.guild)

        my_tags = get_user_tag_names(user_id)
        tag_str = ", ".join(my_tags) if my_tags else "なし"
        game_name = GAMES[self.game_id]["name"]
        
        await interaction.followup.send(
            f"✅ `{game_name}` のタグを**登録**したよ！\n\n📋 **【あなたの所持タグ】**: {tag_str}",
            ephemeral=True
        )

    @discord.ui.button(label="❌ 解除する", style=discord.ButtonStyle.danger)
    async def remove_tag(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        user_id = interaction.user.id
        if user_id in USER_TAGS[self.game_id]:
            USER_TAGS[self.game_id].remove(user_id)
            
        if interaction.guild:
            await save_tags_to_discord(interaction.guild)

        my_tags = get_user_tag_names(user_id)
        tag_str = ", ".join(my_tags) if my_tags else "なし"
        game_name = GAMES[self.game_id]["name"]
        
        await interaction.followup.send(
            f"❌ `{game_name}` のタグを**解除**したよ！\n\n📋 **【あなたの所持タグ】**: {tag_str}",
            ephemeral=True
        )

# --- タグ選択用ドロップダウン ---
class TagSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label=info["name"], value=key, emoji=info["emoji"])
            for key, info in GAMES.items()
        ]
        options.append(discord.SelectOption(label="📋 自分の所持タグを確認する", value="check_my_tags", emoji="🔍"))
        super().__init__(placeholder="🎮 ゲームを選択してタグ設定...", min_values=1, max_values=1, options=options, custom_id="tag_select_v6")

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.edit_message(view=TagPanelView())
        
        selected = self.values[0]

        if selected == "check_my_tags":
            my_tags = get_user_tag_names(interaction.user.id)
            tag_str = ", ".join(my_tags) if my_tags else "なし"
            await interaction.followup.send(f"📋 **【現在所持しているタグ】**\n{tag_str}", ephemeral=True)
        else:
            game_name = GAMES[selected]["name"]
            await interaction.followup.send(
                f"🎮 **`{game_name}`** のタグ設定を選択してください：",
                view=TagActionView(selected),
                ephemeral=True
            )

class TagPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TagSelect())

# --- 募集専用ドロップダウン ---
class RecruitSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label=f"{info['name']} を募集する", value=key, emoji=info["emoji"])
            for key, info in GAMES.items()
        ]
        super().__init__(placeholder="📢 募集したいゲームを選択...", min_values=1, max_values=1, options=options, custom_id="recruit_select_v6")

    async def callback(self, interaction: discord.Interaction):
        game_id = self.values[0]
        await interaction.response.send_modal(RecruitModal(game_id))
        await interaction.message.edit(view=RecruitPanelView())

class RecruitPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(RecruitSelect())

# --- Bot本体 ---
class GameBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        self.add_view(TagPanelView())
        self.add_view(RecruitPanelView())
        await self.tree.sync()

bot = GameBot()

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    for guild in bot.guilds:
        await load_tags_from_discord(guild)

@bot.tree.command(name="setup_tag", description="タグ登録専用パネルを設置します")
@app_commands.checks.has_permissions(administrator=True)
async def setup_tag(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    embed = discord.Embed(
        title="🎮 ゲームタグ設定パネル",
        description="1. メニューからゲームを選択します。\n2. 「登録」または「解除」ボタンを押して設定します。\n※「📋 自分の所持タグを確認する」で一覧も確認できます。",
        color=discord.Color.blue()
    )
    await interaction.channel.send(embed=embed, view=TagPanelView())
    await interaction.followup.send("タグ設定パネルを設置したよ！", ephemeral=True)

@bot.tree.command(name="setup_recruit", description="メンバー募集専用パネルを設置します")
@app_commands.checks.has_permissions(administrator=True)
async def setup_recruit(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    embed = discord.Embed(
        title="📢 メンバー募集パネル",
        description="メニューからゲームを選択すると、募集入力フォームが開きます。",
        color=discord.Color.green()
    )
    await interaction.channel.send(embed=embed, view=RecruitPanelView())
    await interaction.followup.send("募集パネルを設置したよ！", ephemeral=True)

TOKEN = os.getenv("DISCORD_TOKEN")
if TOKEN:
    bot.run(TOKEN)
else:
    print("エラー: DISCORD_TOKEN が設定されていません。")
