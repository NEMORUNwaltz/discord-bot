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

# ユーザーの所有タグ一覧を取得するヘルパー関数
def get_user_tag_names(user_id: int) -> list:
    return [GAMES[g_id] for g_id, users in USER_TAGS.items() if user_id in users]

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

        # タグを持っているユーザーがいない場合
        if not target_users:
            await interaction.response.send_message(
                f"⚠️ 現在 `{GAMES[self.game_id]}` のタグを持っているユーザーがいません。\n（※Botが再起動した場合はタグを登録し直してください）", 
                ephemeral=True
            )
            return

        # メンションを作成して投稿
        mentions = " ".join([f"<@{user_id}>" for user_id in target_users])
        content = f"📢 **【{GAMES[self.game_id]} 募集】** (送信者: {interaction.user.mention})\n" \
                  f"メッセージ: {self.message_input.value}\n\n" \
                  f"通知: {mentions}"

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
        
        my_tags = get_user_tag_names(user_id)
        tag_str = ", ".join(my_tags) if my_tags else "なし"
        
        await interaction.followup.send(
            f"✅ `{GAMES[self.game_id]}` のタグを**登録**したよ！\n\n📋 **【あなたの所持タグ】**: {tag_str}",
            ephemeral=True
        )

    @discord.ui.button(label="❌ 解除する", style=discord.ButtonStyle.danger)
    async def remove_tag(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        user_id = interaction.user.id
        if user_id in USER_TAGS[self.game_id]:
            USER_TAGS[self.game_id].remove(user_id)
            
        my_tags = get_user_tag_names(user_id)
        tag_str = ", ".join(my_tags) if my_tags else "なし"
        
        await interaction.followup.send(
            f"❌ `{GAMES[self.game_id]}` のタグを**解除**したよ！\n\n📋 **【あなたの所持タグ】**: {tag_str}",
            ephemeral=True
        )

# --- タグ選択用ドロップダウン ---
class TagSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label=name, value=key, emoji="🎮")
            for key, name in GAMES.items()
        ]
        options.append(discord.SelectOption(label="📋 自分の所持タグを確認する", value="check_my_tags", emoji="🔍"))
        super().__init__(placeholder="🎮 ゲームを選択してタグ設定...", min_values=1, max_values=1, options=options, custom_id="tag_select_v2")

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        selected = self.values[0]

        if selected == "check_my_tags":
            my_tags = get_user_tag_names(interaction.user.id)
            tag_str = ", ".join(my_tags) if my_tags else "なし"
            await interaction.followup.send(f"📋 **【現在所持しているタグ】**\n{tag_str}", ephemeral=True)
        else:
            game_name = GAMES[selected]
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
            discord.SelectOption(label=f"{name} を募集する", value=key, emoji="📢")
            for key, name in GAMES.items()
        ]
        super().__init__(placeholder="📢 募集したいゲームを選択...", min_values=1, max_values=1, options=options, custom_id="recruit_select_v2")

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
bot.run(TOKEN)
