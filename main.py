import os
import discord
from discord import app_commands
from discord.ext import commands

# 13タイトルの設定
GAMES = {
    "apex": "Apex",
    "ow2": "OW2",
    "valo": "VALO",
    "mc_java": "MINECRAFT JAVA",
    "mc_be": "MINECRAFT BE",
    "mahjong": "雀魂",
    "lol": "LOL",
    "genshin": "原神",
    "fortnite": "FORTNITE",
    "terraria": "TERRARIA",
    "mh_wilds": "MH:WILDS",
    "osu": "OSU!",
    "eft": "EFT"
}

# タグ保存用の辞書データ
USER_TAGS = {key: set() for key in GAMES.keys()}

# 募集用モーダル（ポップアップ）
class RecruitModal(discord.ui.Modal):
    def __init__(self, game_id: str):
        super().__init__(title=f"{GAMES[game_id]} メンバー募集")
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

        if not target_users:
            await interaction.response.send_message(
                f"⚠️ 現在 `{GAMES[self.game_id]}` のタグを持っているユーザーがいません。", 
                ephemeral=True
            )
            return

        mentions = " ".join([f"<@{user_id}>" for user_id in target_users])
        content = f"📢 **【{GAMES[self.game_id]} 募集】** (送信者: {interaction.user.mention})\n" \
                  f"メッセージ: {self.message_input.value}\n\n" \
                  f"通知: {mentions}"

        await interaction.response.send_message(content)

# --- ① タグ専用コンポーネント ---
class TagSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label=name, value=key, emoji="🎮")
            for key, name in GAMES.items()
        ]
        super().__init__(placeholder="🎮 タグを登録/解除するゲームを選択...", min_values=1, max_values=1, options=options, custom_id="tag_select_only")

    async def callback(self, interaction: discord.Interaction):
        game_id = self.values[0]
        user_id = interaction.user.id
        if user_id in USER_TAGS[game_id]:
            USER_TAGS[game_id].remove(user_id)
            await interaction.response.send_message(f"❌ `{GAMES[game_id]}` のタグを外したよ！", ephemeral=True)
        else:
            USER_TAGS[game_id].add(user_id)
            await interaction.response.send_message(f"✅ `{GAMES[game_id]}` のタグを登録したよ！", ephemeral=True)

class TagPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TagSelect())

# --- ② 募集専用コンポーネント ---
class RecruitSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label=f"{name} を募集する", value=key, emoji="📢")
            for key, name in GAMES.items()
        ]
        super().__init__(placeholder="📢 募集したいゲームを選択...", min_values=1, max_values=1, options=options, custom_id="recruit_select_only")

    async def callback(self, interaction: discord.Interaction):
        game_id = self.values[0]
        await interaction.response.send_modal(RecruitModal(game_id))

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

# コマンド①：タグ登録パネル設置（タイムアウト防止対策済み）
@bot.tree.command(name="setup_tag", description="タグ登録専用パネルを設置します")
@app_commands.checks.has_permissions(administrator=True)
async def setup_tag(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)  # 即座に処理中レスポンスを返す
    embed = discord.Embed(
        title="🎮 ゲームタグ設定パネル",
        description="メニューからゲームを選択すると、タグの登録/解除ができます。（押すごとに切り替え）",
        color=discord.Color.blue()
    )
    await interaction.channel.send(embed=embed, view=TagPanelView())
    await interaction.followup.send("タグ設定パネルを設置したよ！")

# コマンド②：メンバー募集パネル設置（タイムアウト防止対策済み）
@bot.tree.command(name="setup_recruit", description="メンバー募集専用パネルを設置します")
@app_commands.checks.has_permissions(administrator=True)
async def setup_recruit(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)  # 即座に処理中レスポンスを返す
    embed = discord.Embed(
        title="📢 メンバー募集パネル",
        description="メニューからゲームを選択すると、募集入力フォームが開きます。",
        color=discord.Color.green()
    )
    await interaction.channel.send(embed=embed, view=RecruitPanelView())
    await interaction.followup.send("募集パネルを設置したよ！")

TOKEN = os.getenv("DISCORD_TOKEN")
bot.run(TOKEN)
