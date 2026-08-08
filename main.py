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

# パネルのボタン設定
class ControlPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        # タグ登録ボタンを作成
        for key, name in GAMES.items():
            btn = discord.ui.Button(label=f"🎮 {name}", style=discord.ButtonStyle.secondary, custom_id=f"tag_{key}")
            btn.callback = self.make_tag_callback(key)
            self.add_item(btn)

        # 募集ボタンを作成
        for key, name in GAMES.items():
            btn = discord.ui.Button(label=f"📢 {name}募集", style=discord.ButtonStyle.success, custom_id=f"recruit_{key}")
            btn.callback = self.make_recruit_callback(key)
            self.add_item(btn)

    def make_tag_callback(self, game_id):
        async def callback(interaction: discord.Interaction):
            user_id = interaction.user.id
            if user_id in USER_TAGS[game_id]:
                USER_TAGS[game_id].remove(user_id)
                await interaction.response.send_message(f"❌ `{GAMES[game_id]}` のタグを外したよ！", ephemeral=True)
            else:
                USER_TAGS[game_id].add(user_id)
                await interaction.response.send_message(f"✅ `{GAMES[game_id]}` のタグを登録したよ！", ephemeral=True)
        return callback

    def make_recruit_callback(self, game_id):
        async def callback(interaction: discord.Interaction):
            await interaction.response.send_modal(RecruitModal(game_id))
        return callback

class GameBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        self.add_view(ControlPanelView())
        await self.tree.sync()

bot = GameBot()

@bot.tree.command(name="setup", description="コントロールパネルを設置します")
@app_commands.checks.has_permissions(administrator=True)
async def setup(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🎮 ゲームタグ設定 ＆ メンバー募集パネル",
        description="・**グレーのボタン**: タグの登録/解除（押すたびに切り替わります）\n"
                    "・**緑色のボタン**: 該当ゲームのプレイヤー全員にメンション募集を飛ばします",
        color=discord.Color.blue()
    )
    await interaction.channel.send(embed=embed, view=ControlPanelView())
    await interaction.response.send_message("パネルを設置したよ！", ephemeral=True)

TOKEN = os.getenv("DISCORD_TOKEN")
bot.run(TOKEN)
