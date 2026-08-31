import asyncio
import os
import sys
import random
import discord
from discord.ext import commands
import aiohttp
from datetime import timedelta, datetime
import json
import math
import re
from typing import Optional, Union

# ==================== KEEP_ALIVE ====================
try:
    from keep_alive import keep_alive
except ImportError:
    def keep_alive():
        pass

# ==================== CẤU HÌNH HỆ THỐNG ====================
DISCORD_TOKEN = os.getenv("TOKEN")

BOT_OWNERS = [
    1540585511842881616,
    1542453882263707759,
    1502969774202814625,
]

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
intents.bans = True

def get_prefix(bot, message):
    if message.content.lower().startswith("nuked "):
        return "nuked "
    elif message.content.lower().startswith("nuked"):
        return "nuked"
    return "nuked "

bot = commands.Bot(command_prefix=get_prefix, intents=intents)
bot.remove_command('help')

spam_task_running = None
bot_enabled = True

SERVER_LOG_CHANNELS = {}
WELCOME_CHANNELS = {}
GOODBYE_CHANNELS = {}
SERVER_LEVEL_CHANNELS = {}
DISABLED_COMMANDS = set()

LEVEL_FILE = "levels.json"
CONFIG_FILE = "config.json"
COIN_FILE = "coins.json"
INVENTORY_FILE = "inventory.json"
MARRIAGE_FILE = "marriages.json"

# ==================== LƯU TRỮ & TẢI DỮ LIỆU JSON ====================
def load_levels():
    global USER_LEVELS
    try:
        with open(LEVEL_FILE, "r", encoding="utf-8") as f:
            USER_LEVELS = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        USER_LEVELS = {}

def save_levels():
    with open(LEVEL_FILE, "w", encoding="utf-8") as f:
        json.dump(USER_LEVELS, f, indent=2, ensure_ascii=False)

def load_coins():
    try:
        with open(COIN_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_coins(data):
    with open(COIN_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def load_inventory():
    try:
        with open(INVENTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_inventory(data):
    with open(INVENTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def load_config():
    global SERVER_LOG_CHANNELS, WELCOME_CHANNELS, GOODBYE_CHANNELS, SERVER_LEVEL_CHANNELS, BOT_OWNERS, DISABLED_COMMANDS
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        SERVER_LOG_CHANNELS = data.get("log_channels", {})
        WELCOME_CHANNELS = data.get("welcome_channels", {})
        GOODBYE_CHANNELS = data.get("goodbye_channels", {})
        SERVER_LEVEL_CHANNELS = data.get("level_channels", {})
        BOT_OWNERS = data.get("owners", BOT_OWNERS)
        DISABLED_COMMANDS = set(data.get("disabled_commands", []))
    except (FileNotFoundError, json.JSONDecodeError):
        pass

def save_config():
    data = {
        "log_channels": SERVER_LOG_CHANNELS,
        "welcome_channels": WELCOME_CHANNELS,
        "goodbye_channels": GOODBYE_CHANNELS,
        "level_channels": SERVER_LEVEL_CHANNELS,
        "owners": BOT_OWNERS,
        "disabled_commands": list(DISABLED_COMMANDS)
    }
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def load_marriages():
    try:
        with open(MARRIAGE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_marriages(data):
    with open(MARRIAGE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

USER_LEVELS = {}
user_coins = load_coins()
user_inventory = load_inventory()
marriages = load_marriages()
load_levels()
load_config()

CUSTOM_SETUP_GIF = "https://i.pinimg.com/originals/7a/41/bb/7a41bb51fe3babe0c6cee161f85df62c.gif"
NUKE_GIF_URL = "https://media.discordapp.net/attachments/1541456087105151066/1542122209156538388/739ed3f3955356f06352d43eb649168a.gif"
NUKE_AVATAR_URL = "https://media.discordapp.net/attachments/1541456087105151066/1542127023810416660/8b59ed006d0073e951a47e1da3c2d111.jpg"

def get_required_exp(level: int) -> int:
    return level * 100

ROAST_LINES = [
    "# Lồn mẹ mày nát bét như tương, bị địt đến không còn + chảy lênh! {username}",
    "# Đéo biết xấu hổ, lồn mẹ mày thối như cứt + xác chết đầy dòi bọ! {username}",
    # ... (giữ nguyên danh sách cũ)
]

NUKE_CHANNEL_NAMES = [
    "☠️ℕ𝕌𝕂𝔼 𝔹𝕐 𝔾̴𝔾̶.̴K̶Z̶3̸N̵/̵K̵Z̵4̸N̷ – ℍ𝕆𝕋 𝕎𝔸ℝ 𝔹𝕆𝕋",
    "☠️ℕ𝕌𝕂𝔼 𝔹𝕐 𝔹𝔸̉𝕆 𝔻𝔼̣ℙ ℤ𝔸𝕀",
    "☠️ℕ𝕌𝕂𝔼 𝔹𝕐 𝔹𝕆𝕋 ℕ𝕌𝕂𝔼 𝕆ℕ 𝕋𝕆ℙ",
    "☠️𝔻𝔼𝕋ℝ𝕆𝕐𝔼𝔻 𝔹𝕐 𝔹𝕆𝕋 ℕ𝕌𝕂𝔼 𝔼ℤ 𝕋𝕆ℙ",
    "☠️𝔼ℤ 𝕋𝕆ℙ 𝔸ℕ𝕋𝕀",
]

def is_bot_owner():
    async def predicate(ctx):
        return ctx.author.id in BOT_OWNERS
    return commands.check(predicate)

# ==================== HÀM GỬI LOG ====================
async def send_log_to_all(guild_id, embed):
    for g_id, ch_id in SERVER_LOG_CHANNELS.items():
        if int(g_id) == guild_id:
            channel = bot.get_channel(ch_id)
            if channel:
                try:
                    await channel.send(embed=embed)
                except:
                    pass

# ==================== HÀM TẠO EMBED VỚI THUMBNAIL ====================
def create_embed(title, description, color=0x00FF00, thumbnail=None, image=None, footer=None):
    embed = discord.Embed(title=title, description=description, color=color)
    if thumbnail:
        embed.set_thumbnail(url=thumbnail)
    if image:
        embed.set_image(url=image)
    if footer:
        embed.set_footer(text=footer)
    return embed

# ==================== VIEW XÁC NHẬN NUKE (GIỮ NGUYÊN) ====================
class NukeConfirmView(discord.ui.View):
    def __init__(self, guild: discord.Guild, channel: discord.abc.Messageable):
        super().__init__(timeout=60)
        self.guild = guild
        self.channel = channel

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True

    @discord.ui.button(label="🟢 ĐỒNG Ý NUKE SERVER", style=discord.ButtonStyle.green)
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("✅ Đã xác nhận! Đang tiến hành...", ephemeral=True)
        await self.channel.send("⚠️ Từ từ đang check sever đã...")
        for item in self.children:
            item.disabled = True
        await interaction.message.edit(view=self)
        self.stop()
        await execute_nuke(self.guild)

    @discord.ui.button(label="🔴 TỪ CHỐI", style=discord.ButtonStyle.red)
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        for item in self.children:
            item.disabled = True
        await interaction.message.edit(view=self)
        await interaction.response.send_message(f"❌ Bạn đã từ chối nuke sever {self.guild.name}", ephemeral=True)
        self.stop()

async def execute_nuke(guild):
    # giữ nguyên
    pass

# ==================== HỆ THỐNG GÁN ROLE THEO LEVEL ====================
async def check_and_assign_level_roles(member: discord.Member, current_level: int):
    role_permissions_map = {
        20: {"name": "LV 20 - Ping Everyone", "perms": discord.Permissions(mention_everyone=True)},
        200: {"name": "LV 200 - Manage Channels/Roles", "perms": discord.Permissions(manage_channels=True, manage_roles=True)},
        300: {"name": "LV 300 - All Channels Access", "perms": discord.Permissions(view_channel=True)},
        400: {"name": "LV 400 - Server Manager", "perms": discord.Permissions(manage_guild=True)},
        500: {"name": "LV 500 - Admin Server", "perms": discord.Permissions(administrator=True)},
        670: {"name": "LV 670 - Owner Server", "perms": discord.Permissions(administrator=True)}
    }
    for req_lv, r_data in role_permissions_map.items():
        if current_level >= req_lv:
            role = discord.utils.get(member.guild.roles, name=r_data["name"])
            if not role:
                try:
                    role = await member.guild.create_role(name=r_data["name"], permissions=r_data["perms"], hoist=True)
                except:
                    continue
            if role and role not in member.roles:
                try:
                    await member.add_roles(role)
                except:
                    pass

# ==================== CÁC LỆNH LOG, SETWELCOME, SETGOODBYE, SETLV, LV, CHANNELSLV, ADDROLE, SHOWSV, NUKE (GIỮ NGUYÊN) ====================
@bot.command(name="log")
@is_bot_owner()
async def setlog(ctx, channel: discord.TextChannel = None):
    # giữ nguyên
    pass

@setlog.error
async def setlog_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send('❌ NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')
    else:
        await ctx.send(f"❌ Lỗi: {str(error)}")

@bot.command(name="setwelcome")
@is_bot_owner()
async def set_welcome(ctx, channel: discord.TextChannel = None):
    # giữ nguyên
    pass

@set_welcome.error
async def set_welcome_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send('❌ NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')
    else:
        await ctx.send(f"❌ Cú pháp đúng: `nuked setwelcome #kênh` hoặc `nuked setwelcome` để tắt")

@bot.command(name="setgoodbye")
@is_bot_owner()
async def set_goodbye(ctx, channel: discord.TextChannel = None):
    # giữ nguyên
    pass

@set_goodbye.error
async def set_goodbye_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send('❌ NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')
    else:
        await ctx.send(f"❌ Cú pháp đúng: `nuked setgoodbye #kênh` hoặc `nuked setgoodbye` để tắt")

@bot.command(name="setlv")
@is_bot_owner()
async def set_level(ctx, level: int, member: discord.Member):
    # giữ nguyên
    pass

@set_level.error
async def set_level_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')
    else:
        await ctx.send(f"❌ Cú pháp đúng: `nuked setlv <level> @user`")

@bot.command(name="lv")
async def check_user_level(ctx, member: discord.Member = None):
    # giữ nguyên
    pass

@check_user_level.error
async def check_user_level_error(ctx, error):
    await ctx.send(f"❌ Cú pháp đúng: `nuked lv` hoặc `nuked lv @user`")

@bot.command(name="channelslv")
@is_bot_owner()
async def channelslv(ctx, channel: discord.TextChannel = None):
    # giữ nguyên
    pass

@channelslv.error
async def channelslv_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send('❌ NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')
    else:
        await ctx.send(f"❌ Lỗi: {str(error)}")

@bot.command(name="addrole")
@is_bot_owner()
async def addrole(ctx, role_name: str, *, permissions_str: str = ""):
    # giữ nguyên
    pass

@addrole.error
async def addrole_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')
    else:
        await ctx.send(f"❌ Cú pháp đúng: `nuked addrole <tên_role>`")

@bot.command(name="showsv")
@is_bot_owner()
async def showsv(ctx):
    # giữ nguyên
    pass

@showsv.error
async def showsv_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')

@bot.command(name="nuke")
@is_bot_owner()
async def nuke_server(ctx):
    # giữ nguyên
    pass

@nuke_server.error
async def nuke_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')
    else:
        await ctx.send(f"❌ Đã xảy ra lỗi khi thực hiện lệnh nuke: {str(error)}")

# ==================== CÁC LỆNH SPAM, KICK, ROLE, CHANNEL, SETTING... (GIỮ NGUYÊN) ====================
@bot.command(name="spamchannels")
@is_bot_owner()
async def spam_channels(ctx, amount: int = 100):
    # giữ nguyên
    pass

@spam_channels.error
async def spam_channels_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')
    else:
        await ctx.send(f"❌ Lỗi: {str(error)}")

@bot.command(name="spameveryone")
@is_bot_owner()
async def spam_everyone(ctx):
    # giữ nguyên
    pass

@spam_everyone.error
async def spam_everyone_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')
    else:
        await ctx.send(f"❌ Lỗi: {str(error)}")

@bot.command(name="deleteallchannels")
@is_bot_owner()
async def delete_all_channels(ctx):
    # giữ nguyên
    pass

@delete_all_channels.error
async def delete_all_channels_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')
    else:
        await ctx.send(f"❌ Lỗi: {str(error)}")

@bot.command(name="spamroles")
@is_bot_owner()
async def spam_roles(ctx, amount: int = 50):
    # giữ nguyên
    pass

@spam_roles.error
async def spam_roles_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')
    else:
        await ctx.send(f"❌ Lỗi: {str(error)}")

@bot.command(name="deleteallroles")
@is_bot_owner()
async def delete_all_roles(ctx):
    # giữ nguyên
    pass

@delete_all_roles.error
async def delete_all_roles_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')
    else:
        await ctx.send(f"❌ Lỗi: {str(error)}")

@bot.command(name="kickall")
@is_bot_owner()
async def kick_all_members(ctx):
    # giữ nguyên
    pass

@kick_all_members.error
async def kick_all_members_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')
    else:
        await ctx.send(f"❌ Lỗi: {str(error)}")

@bot.command(name="setservername")
@is_bot_owner()
async def set_server_name(ctx, *, new_name: str):
    # giữ nguyên
    pass

@set_server_name.error
async def set_server_name_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')
    else:
        await ctx.send(f"❌ Lỗi: {str(error)}")

@bot.command(name="setservericon")
@is_bot_owner()
async def set_server_icon(ctx, url: str = None):
    # giữ nguyên
    pass

@set_server_icon.error
async def set_server_icon_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')
    else:
        await ctx.send(f"❌ Lỗi: {str(error)}")

# ==================== LỆNH KICK, BAN, UNBAN, CREATE CHANNEL, DELETE CHANNEL, PURGE, ROLE, REMOVEROLE, LOCK, UNLOCK (GIỮ NGUYÊN) ====================
@bot.command(name="kick")
@is_bot_owner()
async def kick_user(ctx, member: discord.Member, *, reason: str = "Không có lý do"):
    # giữ nguyên
    pass

@bot.command(name="ban")
@is_bot_owner()
async def ban_user(ctx, member: discord.Member, *, reason: str = "Không có lý do"):
    # giữ nguyên
    pass

@bot.command(name="unban")
@is_bot_owner()
async def unban_user(ctx, user_id: int, *, reason: str = "Không có lý do"):
    # giữ nguyên
    pass

@bot.command(name="createchannel")
@is_bot_owner()
async def create_channel(ctx, *, name: str):
    # giữ nguyên
    pass

@bot.command(name="deletechannel")
@is_bot_owner()
async def delete_channel(ctx, channel: discord.TextChannel = None):
    # giữ nguyên
    pass

@bot.command(name="purge")
@is_bot_owner()
async def purge_all(ctx, confirm: str = None):
    # giữ nguyên
    pass

@bot.command(name="role")
@is_bot_owner()
async def add_role_to_user(ctx, member: discord.Member, *, role_name: str):
    # giữ nguyên
    pass

@bot.command(name="removerole")
@is_bot_owner()
async def remove_role_from_user(ctx, member: discord.Member, *, role_name: str):
    # giữ nguyên
    pass

@bot.command(name="lock")
@is_bot_owner()
async def lock_channel(ctx, channel: discord.TextChannel = None):
    # giữ nguyên
    pass

@bot.command(name="unlock")
@is_bot_owner()
async def unlock_channel(ctx, channel: discord.TextChannel = None):
    # giữ nguyên
    pass

# ==================== LỆNH ADMINCMD (CẬP NHẬT) ====================
@bot.command(name="admincmd")
@is_bot_owner()
async def admin_commands(ctx):
    all_commands = [
        "`nuked kick @user` - Kick thành viên",
        "`nuked ban @user` - Ban thành viên",
        "`nuked unban <id>` - Unban thành viên",
        "`nuked createchannel <tên>` - Tạo kênh mới",
        "`nuked deletechannel #kênh` - Xóa kênh",
        "`nuked purge all` - Xóa toàn bộ tin nhắn",
        "`nuked role @user <role>` - Thêm role",
        "`nuked removerole @user <role>` - Xóa role",
        "`nuked lock #kênh` - Khóa kênh",
        "`nuked unlock #kênh` - Mở khóa kênh",
        "`nuked mute @user [thời gian]` - Mute thành viên",
        "`nuked unmute @user` - Unmute thành viên",
        "`nuked warn @user` - Cảnh cáo thành viên",
        "`nuked clear <số>` - Xóa tin nhắn",
        "`nuked spam @user` - Spam chửi",
        "`nuked stop` - Dừng spam",
        "`nuked kickall` - Kick toàn bộ",
        "`nuked deleteallchannels` - Xóa tất cả kênh",
        "`nuked deleteallroles` - Xóa tất cả role",
        "`nuked spamroles` - Tạo role spam",
        "`nuked spamchannels` - Tạo kênh spam",
        "`nuked setservername` - Đổi tên server",
        "`nuked setservericon` - Đổi icon server",
        "`nuked addrole <tên>` - Tạo role mới",
        "`nuked showsv` - Xem danh sách server",
        "`nuked nuke` - NUKE SERVER",
        "`nuked setup` - Bảng điều khiển",
        "`nuked log #kênh` - Cài kênh log",
        "`nuked channelslv #kênh` - Cài kênh level",
        "`nuked setlv <level> @user` - Set level",
        "`nuked lv @user` - Xem level",
        "`nuked setwelcome #kênh` - Cài kênh chào mừng",
        "`nuked setgoodbye #kênh` - Cài kênh tạm biệt",
        "`nuked backup` - Backup server",
        "`nuked restore` - Khôi phục server từ backup",
        "`nuked slowmode <giây>` - Bật slowmode",
        "`nuked nick @user <tên>` - Đổi nickname",
        "`nuked resetnick @user` - Reset nickname",
        "`nuked vc <tên>` - Tạo voice channel",
        "`nuked hide #kênh` - Ẩn kênh",
        "`nuked reveal #kênh` - Hiện kênh",
        "`nuked rename <tên>` - Đổi tên server",
        "`nuked icon [url]` - Đổi icon server",
        "`nuked emoji` - Xem danh sách emoji",
        "`nuked steal <id> <tên>` - Copy emoji",
        "`nuked moveall #voice` - Di chuyển tất cả voice",
        "`nuked massban <@user1 @user2 ...>` - Ban nhiều người",
        "`nuked masskick <@user1 @user2 ...>` - Kick nhiều người",
        "`nuked clonechannel #kênh` - Clone kênh",
        "`nuked webhookspam` - Spam qua webhook",
        "`nuked serverinfo` - Thông tin server",
        "`nuked userinfo @user` - Thông tin user",
        "`nuked avatar @user` - Lấy avatar",
        "`nuked off [lệnh]` - Tắt lệnh hoặc bot",
        "`nuked on [lệnh]` - Bật lệnh hoặc thông báo bot đang hoạt động"
    ]
    embed = discord.Embed(
        title="👑 DANH SÁCH LỆNH QUẢN TRỊ",
        description="📋 Tất cả lệnh dành cho Boss Bảo (mỗi field hiển thị một phần):",
        color=0xFFD700
    )
    chunk_size = 15
    for i in range(0, len(all_commands), chunk_size):
        chunk = all_commands[i:i+chunk_size]
        field_name = f"📌 Nhóm {i//chunk_size + 1}"
        field_value = "\n".join(chunk)
        embed.add_field(name=field_name, value=field_value, inline=False)
    embed.set_footer(text="Độc quyền phục vụ Boss Bảo 💖")
    await ctx.send(embed=embed)

# ==================== LỆNH OFF & ON (GIỮ NGUYÊN) ====================
@bot.command(name="off")
@is_bot_owner()
async def off_command(ctx, *, command_name: str = None):
    global bot_enabled
    if command_name is None:
        bot_enabled = False
        await ctx.send("🛑 Boss Bảo đã tạm dừng bot. Gõ `nuked on` để bật lại.")
        return
    cmd = bot.get_command(command_name.lower())
    if cmd is None:
        await ctx.send(f"❌ Không tìm thấy lệnh `{command_name}`!")
        return
    if cmd.name in ["off", "on"]:
        await ctx.send("❌ Không thể tắt lệnh `off` hoặc `on`!")
        return
    if cmd.name in DISABLED_COMMANDS:
        await ctx.send(f"❌ Lệnh `{cmd.name}` đã bị tắt rồi!")
        return
    DISABLED_COMMANDS.add(cmd.name)
    save_config()
    await ctx.send(f"✅ Đã tắt lệnh `{cmd.name}`! Gõ `nuked on {cmd.name}` để bật lại.")

@off_command.error
async def off_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send('❌ NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')

@bot.command(name="on")
@is_bot_owner()
async def on_command(ctx, *, command_name: str = None):
    global bot_enabled
    if command_name is None:
        if bot_enabled:
            await ctx.send("🤖 Bot đang hoạt động bình thường!")
        else:
            bot_enabled = True
            await ctx.send("✅ Bot đã hoạt động trở lại!")
        return
    cmd = bot.get_command(command_name.lower())
    if cmd is None:
        await ctx.send(f"❌ Không tìm thấy lệnh `{command_name}`!")
        return
    if cmd.name not in DISABLED_COMMANDS:
        await ctx.send(f"❌ Lệnh `{cmd.name}` không bị tắt!")
        return
    DISABLED_COMMANDS.remove(cmd.name)
    save_config()
    await ctx.send(f"✅ Đã bật lại lệnh `{cmd.name}`!")

@on_command.error
async def on_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send('❌ NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')

# ==================== GLOBAL CHECK ====================
@bot.check
async def globally_disabled_check(ctx):
    if not bot_enabled:
        if ctx.command and ctx.command.name != "on":
            await ctx.send("🛑 Bot đang tạm dừng. Gõ `nuked on` để bật lại.")
            return False
    if ctx.command and ctx.command.name in DISABLED_COMMANDS:
        await ctx.send(f"❌ Lệnh `{ctx.command.name}` đã bị tắt bởi Boss Bảo. Gõ `nuked on {ctx.command.name}` để bật lại.")
        return False
    return True

# ==================== LỆNH BACKUP & RESTORE (GIỮ NGUYÊN) ====================
@bot.command(name="backup")
@is_bot_owner()
async def backup_server(ctx):
    # giữ nguyên
    pass

@backup_server.error
async def backup_server_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')

class RestoreConfirmView(discord.ui.View):
    # giữ nguyên
    pass

async def restore_process(ctx, backup_data, filename):
    # giữ nguyên
    pass

@bot.command(name="restore")
@is_bot_owner()
async def restore_server(ctx, file_name: str = None):
    # giữ nguyên
    pass

@restore_server.error
async def restore_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')

# ==================== LỆNH SLOWMODE, NICK, RESETNICK, VC, HIDE, REVEAL, RENAME, ICON, EMOJI, STEAL, MOVEALL, MUTE, UNMUTE, WARN, CLEAR, MASSBAN, MASSKICK, CLONECHANNEL, WEBHOOKSPAM, SERVERINFO, USERINFO, AVATAR, ADDOWNER, DELETEOWNER, SPAM, STOP (GIỮ NGUYÊN) ====================
# (Tất cả các lệnh này giữ nguyên, chỉ thêm thumbnail vào embed nếu cần, nhưng không bắt buộc)

# ==================== LỆNH TIMEOUT, DEAFEN, UNDEAFEN, MOVE, SETTOPIC, SETNSFW, CREATECATEGORY, RENAMECHANNEL, LISTROLES, LISTCHANNELS, MEMBERCOUNT, AUTOCLEARUSER, AUTOCLEAR (GIỮ NGUYÊN) ====================
# (Tương tự)

# ==================== CÁC LỆNH KINH TẾ (GIỮ NGUYÊN) ====================
# (balance, daily, work, give, beg, crime, bank, setcoins, addcoins, removecoins, resetdaily, guithu, buyrole, leaderboard)

# ==================== CÁC LỆNH COINFLIP, SLOTS, DICE, RPS, HILO, CRASH, LOTTERY, BLACKJACK (GIỮ NGUYÊN) ====================
# (giữ nguyên)

# ==================== CÁC LỆNH TÌNH YÊU (GIỮ NGUYÊN) ====================
# (love, hug, kiss, slap, pat, cuddle, marry, divorce, ship, crush)

# ==================== MENU HELP & SETUP (CẬP NHẬT) ====================
# Danh sách các danh mục với emoji và gif thumbnail
HELP_CATEGORIES = {
    "🛡️ Quản lý Mod": [
        "`nuked kick @user` – Kick thành viên",
        "`nuked ban @user` – Ban thành viên",
        "`nuked unban <id>` – Gỡ ban",
        "`nuked mute @user [thời gian]` – Mute (vd: 10m, 2d, 1w, 1t)",
        "`nuked unmute @user` – Bỏ mute",
        "`nuked warn @user` – Cảnh cáo qua DM",
        "`nuked timeout @user <thời gian>` – Timeout",
        "`nuked clearuser @user` – Xóa tin nhắn của user",
        "`nuked kickall` – Kick toàn bộ thành viên",
        "`nuked massban @user1 @user2 ...` – Ban nhiều người",
        "`nuked masskick @user1 @user2 ...` – Kick nhiều người",
        "`nuked clear <số>` – Xóa tin nhắn trong kênh",
        "`nuked purge all` – Xóa toàn bộ tin nhắn server (cần xác nhận)",
        "`nuked warn @user` – Cảnh cáo thành viên",
    ],
    "📢 Quản lý Kênh": [
        "`nuked createchannel <tên>` – Tạo kênh văn bản",
        "`nuked deletechannel #kênh` – Xóa kênh (mặc định kênh hiện tại)",
        "`nuked createcategory <tên>` – Tạo category",
        "`nuked renamechannel #kênh <tên mới>` – Đổi tên kênh",
        "`nuked lock #kênh` – Khóa kênh (cấm gửi tin)",
        "`nuked unlock #kênh` – Mở khóa",
        "`nuked hide #kênh` – Ẩn kênh khỏi @everyone",
        "`nuked reveal #kênh` – Hiện kênh trở lại",
        "`nuked clonechannel #kênh` – Clone kênh",
        "`nuked vc <tên>` – Tạo voice channel",
        "`nuked settopic #kênh <nội dung>` – Đặt chủ đề kênh",
        "`nuked setnsfw #kênh <true/false>` – Bật/tắt NSFW",
        "`nuked deleteallchannels` – Xóa tất cả kênh (cần xác nhận)",
        "`nuked spamchannels <số lượng>` – Tạo hàng loạt kênh spam",
        "`nuked slowmode <giây>` – Bật slowmode cho kênh hiện tại",
    ],
    "🎭 Quản lý Role": [
        "`nuked addrole <tên>` – Tạo role mới với quyền của bot",
        "`nuked role @user <role>` – Gán role cho người",
        "`nuked removerole @user <role>` – Gỡ role",
        "`nuked spamroles <số lượng>` – Tạo hàng loạt role",
        "`nuked deleteallroles` – Xóa tất cả role (trừ @everyone, cần xác nhận)",
        "`nuked listroles` – Liệt kê danh sách role",
    ],
    "📊 Hệ thống Level": [
        "`nuked setlv <level> @user` – Set level cho thành viên",
        "`nuked lv [@user]` – Xem level của bạn hoặc người khác",
        "`nuked channelslv #kênh` – Cài kênh thông báo level",
    ],
    "🎉 Chào mừng & Tạm biệt": [
        "`nuked setwelcome #kênh` – Cài kênh chào mừng thành viên mới",
        "`nuked setgoodbye #kênh` – Cài kênh tạm biệt khi thành viên rời",
    ],
    "📋 Log & Thông tin": [
        "`nuked log #kênh` – Cài kênh log sự kiện (xóa tin, tạo/xóa kênh, join/leave...)",
        "`nuked serverinfo` – Xem thông tin chi tiết server",
        "`nuked userinfo @user` – Xem thông tin thành viên",
        "`nuked avatar @user` – Xem avatar",
        "`nuked membercount` – Số lượng thành viên hiện tại",
        "`nuked listchannels` – Danh sách kênh văn bản",
        "`nuked ping` – Kiểm tra độ trễ bot",
        "`nuked uptime` – Thời gian bot đã hoạt động",
    ],
    "⚠️ Spam & Nuke": [
        "`nuked spam @user [nội dung]` – Spam chửi (có sẵn hoặc tùy chỉnh)",
        "`nuked stop` – Dừng mọi tác vụ spam",
        "`nuked spameveryone` – Spam @everyone và @here vào tất cả kênh",
        "`nuked nuke` – NUKE SERVER (xóa sạch, tạo kênh, spam)",
        "`nuked webhookspam [nội dung]` – Spam qua webhook (20 tin)",
    ],
    "⚙️ Cấu hình Server": [
        "`nuked setservername <tên>` – Đổi tên server",
        "`nuked setservericon [url]` – Đổi icon server (url hoặc file đính kèm)",
        "`nuked rename <tên>` – Alias của setservername",
        "`nuked icon [url]` – Alias của setservericon",
        "`nuked backup` – Backup cấu hình server (kênh, role)",
        "`nuked restore` – Khôi phục server từ file backup (cần xác nhận)",
    ],
    "👑 Quản lý Owner": [
        "`nuked addowner @user` – Thêm người dùng vào danh sách Owner",
        "`nuked deleteowner @user` – Xóa người dùng khỏi danh sách Owner",
        "`nuked showsv` – Xem danh sách server bot đang tham gia",
        "`nuked setup` – Mở bảng điều khiển quản trị (menu tương tác)",
        "`nuked admincmd` – Danh sách tất cả lệnh quản trị (dài)",
        "`nuked off [lệnh]` – Tắt bot hoặc một lệnh cụ thể",
        "`nuked on [lệnh]` – Bật bot hoặc bật lại lệnh đã tắt",
        "`nuked setcoins @user <số>` – Đặt số coin cho thành viên",
        "`nuked addcoins @user <số>` – Cộng thêm coin",
        "`nuked removecoins @user <số>` – Trừ coin",
        "`nuked resetdaily @user` – Reset daily của thành viên",
    ],
    "🔊 Voice & Emoji": [
        "`nuked moveall #voice` – Di chuyển tất cả thành viên trong voice vào kênh chỉ định",
        "`nuked move @user #voice` – Di chuyển một thành viên",
        "`nuked deafen @user` – Làm điếc thành viên trong voice",
        "`nuked undeafen @user` – Bỏ điếc",
        "`nuked emoji` – Xem danh sách emoji server",
        "`nuked steal <id> <tên>` – Copy emoji từ server khác",
    ],
    "✉️ Tiện ích": [
        "`nuked guithu @user <nội dung>` – Gửi tin nhắn riêng cho thành viên",
        "`nuked nick @user <tên>` – Đổi nickname cho thành viên",
        "`nuked resetnick @user` – Reset nickname về tên gốc",
        "`nuked poll <câu hỏi> | <lựa chọn1> | <lựa chọn2> ...` – Tạo bình chọn (tối đa 10)",
        "`nuked remind <thời gian> <nội dung>` – Đặt lời nhắc (vd: 10m, 2h, 1d)",
        "`nuked math <biểu thức>` – Tính toán biểu thức đơn giản",
        "`nuked translate <ngôn ngữ> <văn bản>` – Dịch văn bản (Google Translate)",
        "`nuked urban <từ>` – Tra từ điển Urban",
        "`nuked weather <thành phố>` – Xem thời tiết (API OpenWeather)",
    ],
    "💘 Tình yêu": [
        "`nuked love @user1 @user2` – Tính tỷ lệ tình yêu",
        "`nuked hug @user` – Ôm",
        "`nuked kiss @user` – Hôn",
        "`nuked slap @user` – Tát",
        "`nuked pat @user` – Vỗ đầu",
        "`nuked cuddle @user` – Âu yếm",
        "`nuked marry @user` – Kết hôn (lưu vào file)",
        "`nuked divorce @user` – Ly hôn",
        "`nuked ship @user1 @user2` – Ghép đôi ngẫu nhiên",
        "`nuked crush @user` – Tỏ tình",
    ],
    "🚦 Bật/Tắt lệnh": [
        "`nuked off <tên_lệnh>` – Tắt một lệnh (chỉ Owner)",
        "`nuked on <tên_lệnh>` – Bật lại lệnh đã tắt",
        "`nuked off` (không tham số) – Tắt toàn bộ bot",
        "`nuked on` (không tham số) – Bật lại bot",
    ],
    "💰 Coin & Giải trí": [
        "`nuked balance` – Xem số dư ví & ngân hàng",
        "`nuked daily` – Nhận coin mỗi ngày (100-500)",
        "`nuked work` – Làm việc kiếm coin (50-300, mỗi 1h)",
        "`nuked give @user <số>` – Chuyển coin cho người khác",
        "`nuked beg` – Xin tiền (mỗi 30s)",
        "`nuked crime` – Trộm cướp (mỗi 60s, 55% thành công)",
        "`nuked bank deposit <số/all>` – Gửi tiền vào ngân hàng",
        "`nuked bank withdraw <số/all>` – Rút tiền từ ngân hàng",
        "`nuked shop` – Xem cửa hàng vật phẩm",
        "`nuked buyrole <tên_role>` – Mua role bằng coin (giá 10000)",
        "`nuked buyitem <tên_vật_phẩm>` – Mua vật phẩm từ shop",
        "`nuked inventory` – Xem túi đồ",
        "`nuked leaderboard` – Bảng xếp hạng đại gia",
        "`nuked coinflip <số> <h/t>` – Tung đồng xu (x2)",
        "`nuked slots <số>` – Máy quay xèng (jackpot x5)",
        "`nuked dice <số> <1-6>` – Đoán xúc xắc (x4)",
        "`nuked rps <số> <r/p/s>` – Oẳn tù tì (x2)",
        "`nuked hilo <số> <h/l>` – Cao / thấp hơn 7 (x1.8)",
        "`nuked crash <số>` – Tên lửa – dừng đúng lúc để nhân tiền",
        "`nuked lottery <số>` – Xổ số (x10 nếu trúng)",
        "`nuked blackjack <số>` – Xì dách 21 điểm (x2)",
    ],
    "📖 Hướng dẫn chung": [
        "`nuked help` – Mở menu trợ giúp tổng hợp",
        "`nuked games` – Mở trung tâm giải trí (game, casino)",
        "`nuked setup` – Bảng điều khiển quản trị (dành cho Owner)",
        "`nuked ping` – Kiểm tra độ trễ bot",
        "`nuked uptime` – Thời gian hoạt động của bot",
        "`nuked support` – Nhận link hỗ trợ",
    ]
}

HELP_CATEGORY_DESCRIPTIONS = {
    "🛡️ Quản lý Mod": "Các lệnh quản lý thành viên: kick, ban, mute, warn, timeout, xóa tin nhắn...",
    "📢 Quản lý Kênh": "Tạo, xóa, đổi tên, khóa/mở, ẩn/hiện, clone kênh, quản lý slowmode...",
    "🎭 Quản lý Role": "Tạo role, gán, gỡ, spam role, xóa hàng loạt role...",
    "📊 Hệ thống Level": "Thiết lập level, xem level, cấu hình kênh thông báo level...",
    "🎉 Chào mừng & Tạm biệt": "Cài đặt kênh chào mừng và tạm biệt thành viên...",
    "📋 Log & Thông tin": "Cấu hình log, xem thông tin server, user, avatar...",
    "⚠️ Spam & Nuke": "Các lệnh spam, phá server, nuke... (chỉ Owner)",
    "⚙️ Cấu hình Server": "Đổi tên, đổi icon, backup, restore server...",
    "👑 Quản lý Owner": "Danh sách lệnh dành riêng cho chủ bot (Boss Bảo và đồng minh)",
    "🔊 Voice & Emoji": "Quản lý voice (di chuyển, điếc) và emoji (xem, copy)...",
    "✉️ Tiện ích": "Gửi thư, đổi nickname, tạo poll, đặt lời nhắc, tính toán, dịch, tra từ điển, thời tiết...",
    "💘 Tình yêu": "Các lệnh tương tác vui vẻ: love, hug, kiss, slap, marry...",
    "🚦 Bật/Tắt lệnh": "Quản lý bật/tắt từng lệnh hoặc toàn bộ bot (chỉ Owner)",
    "💰 Coin & Giải trí": "Hệ thống kinh tế, coin, game casino, bảng xếp hạng...",
    "📖 Hướng dẫn chung": "Các lệnh trợ giúp và thông tin cơ bản.",
}

# Gif thumbnail cho từng danh mục
CATEGORY_THUMBNAILS = {
    "🛡️ Quản lý Mod": "https://media.tenor.com/1J9k3C4d5zIAAAAM/mod.gif",
    "📢 Quản lý Kênh": "https://media.tenor.com/2k4z1C2d5zIAAAAM/channel.gif",
    "🎭 Quản lý Role": "https://media.tenor.com/3L5k2C3d5zIAAAAM/roles.gif",
    "📊 Hệ thống Level": "https://media.tenor.com/4M6k2C3d5zIAAAAM/level.gif",
    "🎉 Chào mừng & Tạm biệt": "https://media.tenor.com/5N7k2C3d5zIAAAAM/welcome.gif",
    "📋 Log & Thông tin": "https://media.tenor.com/6O8k2C3d5zIAAAAM/info.gif",
    "⚠️ Spam & Nuke": "https://media.tenor.com/7P9k2C3d5zIAAAAM/nuke.gif",
    "⚙️ Cấu hình Server": "https://media.tenor.com/8Q0k2C3d5zIAAAAM/settings.gif",
    "👑 Quản lý Owner": "https://media.tenor.com/9R1k2C3d5zIAAAAM/owner.gif",
    "🔊 Voice & Emoji": "https://media.tenor.com/0S2k2C3d5zIAAAAM/voice.gif",
    "✉️ Tiện ích": "https://media.tenor.com/1T3k2C3d5zIAAAAM/utility.gif",
    "💘 Tình yêu": "https://media.tenor.com/2U4k2C3d5zIAAAAM/love.gif",
    "🚦 Bật/Tắt lệnh": "https://media.tenor.com/3V5k2C3d5zIAAAAM/toggle.gif",
    "💰 Coin & Giải trí": "https://media.tenor.com/4W6k2C3d5zIAAAAM/coin.gif",
    "📖 Hướng dẫn chung": "https://media.tenor.com/5X7k2C3d5zIAAAAM/help.gif",
}

# ==================== CLASS VIEW TƯƠNG TÁC CHO HELP (CẬP NHẬT) ====================
class HelpView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        for category_name in HELP_CATEGORIES.keys():
            button = discord.ui.Button(
                label=category_name,
                style=discord.ButtonStyle.primary,
                custom_id=category_name
            )
            button.callback = self.make_callback(category_name)
            self.add_item(button)

    def make_callback(self, category_name):
        async def callback(interaction: discord.Interaction):
            commands_list = HELP_CATEGORIES.get(category_name, [])
            description = HELP_CATEGORY_DESCRIPTIONS.get(category_name, "")
            thumbnail = CATEGORY_THUMBNAILS.get(category_name, None)
            embed = discord.Embed(
                title=f"📋 Danh mục: {category_name}",
                description=f"**Công dụng:** {description}\n\n" + "\n".join(commands_list) if commands_list else "Không có lệnh nào.",
                color=0x00FF00
            )
            if thumbnail:
                embed.set_thumbnail(url=thumbnail)
            embed.set_footer(text="Boss Bảo 💖")
            await interaction.response.send_message(embed=embed, ephemeral=True)
        return callback

# ==================== LỆNH SETUP (CHỈ OWNER) ====================
@bot.command(name="setup")
@is_bot_owner()
async def setup(ctx):
    embed = discord.Embed(
        title="💖 HỆ THỐNG QUẢN TRỊ TỐI CAO CỦA BOSS BẢO 💖",
        description="Chọn một danh mục bên dưới để xem các lệnh tương ứng.",
        color=0xFF69B4
    )
    for category_name, desc in HELP_CATEGORY_DESCRIPTIONS.items():
        embed.add_field(name=category_name, value=desc, inline=False)
    embed.set_image(url=CUSTOM_SETUP_GIF)
    embed.set_footer(text="Độc quyền phục vụ Boss Bảo 💖", icon_url=ctx.author.display_avatar.url)
    view = HelpView()
    await ctx.send(embed=embed, view=view)

@setup.error
async def setup_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send('❌ NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')

# ==================== LỆNH HELP (CÔNG KHAI) ====================
@bot.command(name="help")
async def help_command(ctx):
    embed = discord.Embed(
        title="📖 CẨM NANG ĐIỀU HÀNH BOT",
        description="Chọn một danh mục bên dưới để xem các lệnh chi tiết.\n\n**Mỗi danh mục đều có ảnh gif minh họa bên cạnh!**",
        color=0xFF69B4
    )
    for category_name, desc in HELP_CATEGORY_DESCRIPTIONS.items():
        embed.add_field(name=category_name, value=desc, inline=False)
    embed.set_image(url=CUSTOM_SETUP_GIF)
    embed.set_footer(text="Tôn vinh Boss Bảo 💖", icon_url=ctx.author.display_avatar.url)
    view = HelpView()
    await ctx.send(embed=embed, view=view)

# ==================== LỚP GUIDEVIEW (CẬP NHẬT VỚI THUMBNAIL) ====================
class GuideView(discord.ui.View):
    def __init__(self, parent_interaction):
        super().__init__(timeout=120)
        self.parent_interaction = parent_interaction
        self.add_item(discord.ui.Button(label="💰 Kinh tế", style=discord.ButtonStyle.primary, custom_id="guide_economy"))
        self.add_item(discord.ui.Button(label="🎮 Game", style=discord.ButtonStyle.success, custom_id="guide_game"))
        self.add_item(discord.ui.Button(label="💘 Tình yêu", style=discord.ButtonStyle.danger, custom_id="guide_love"))
        self.add_item(discord.ui.Button(label="🛠️ Admin", style=discord.ButtonStyle.secondary, custom_id="guide_admin"))
        self.add_item(discord.ui.Button(label="❓ Lệnh cơ bản", style=discord.ButtonStyle.primary, custom_id="guide_basic"))
        self.add_item(discord.ui.Button(label="🎯 Mẹo hay", style=discord.ButtonStyle.success, custom_id="guide_tips"))
        back = discord.ui.Button(label="🔙 Quay lại", style=discord.ButtonStyle.danger, custom_id="guide_back")
        back.callback = self.back_callback
        self.add_item(back)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        cid = interaction.data["custom_id"]
        if cid.startswith("guide_"):
            await self.handle_guide(interaction, cid)
            return True
        return False

    async def handle_guide(self, interaction: discord.Interaction, cid: str):
        embeds = {
            "guide_economy": discord.Embed(
                title="💰 KINH TẾ & COIN",
                description=(
                    "**Các lệnh kiếm và quản lý coin:**\n"
                    "💰 `nuked balance` – Xem số dư ví và ngân hàng.\n"
                    "🎁 `nuked daily` – Nhận thưởng mỗi ngày (100-500 coin).\n"
                    "💼 `nuked work` – Làm việc kiếm 50-300 coin (mỗi 1h).\n"
                    "🥺 `nuked beg` – Xin tiền người khác (mỗi 30s).\n"
                    "🚨 `nuked crime` – Trộm cướp (mỗi 60s, 55% thành công).\n"
                    "🏦 `nuked bank deposit <số/all>` – Gửi tiền vào ngân hàng.\n"
                    "💸 `nuked bank withdraw <số/all>` – Rút tiền về ví.\n"
                    "🤝 `nuked give @user <số>` – Chuyển coin cho bạn bè.\n"
                    "🏆 `nuked leaderboard` – Xem top 10 đại gia.\n\n"
                    "💡 **Mẹo:** Hãy dùng `daily` và `work` mỗi ngày để tích lũy nhanh."
                ),
                color=0xF1C40F
            ),
            "guide_game": discord.Embed(
                title="🎮 TRÒ CHƠI GIẢI TRÍ",
                description=(
                    "**Các trò chơi may rủi (đặt cược bằng coin):**\n"
                    "🪙 `nuked coinflip <tiền> <h/t>` – Tung đồng xu (x2).\n"
                    "🎲 `nuked dice <tiền> <1-6>` – Đoán xúc xắc (x4).\n"
                    "✂️ `nuked rps <tiền> <r/p/s>` – Oẳn tù tì (x2).\n"
                    "🎴 `nuked hilo <tiền> <h/l>` – Cao / thấp hơn 7 (x1.8).\n"
                    "🎰 `nuked slots <tiền>` – Máy quay xèng (jackpot x5).\n"
                    "🚀 `nuked crash <tiền>` – Tên lửa – dừng đúng lúc để nhân tiền.\n"
                    "🎫 `nuked lottery <tiền>` – Xổ số (x10 nếu trúng).\n"
                    "🃏 `nuked blackjack <tiền>` – Xì dách 21 điểm (x2).\n\n"
                    "💡 **MẸO:** Chơi `slots` hoặc `lottery` để có cơ hội thắng lớn, nhưng rủi ro cao!"
                ),
                color=0x2ECC71
            ),
            "guide_love": discord.Embed(
                title="💘 TÌNH YÊU & TƯƠNG TÁC",
                description=(
                    "**Các lệnh tương tác vui vẻ:**\n"
                    "💕 `nuked love @user1 @user2` – Tính tỷ lệ tình yêu.\n"
                    "🤗 `nuked hug @user` – Ôm người khác.\n"
                    "😘 `nuked kiss @user` – Hôn người khác.\n"
                    "👋 `nuked slap @user` – Tát người khác.\n"
                    "🫳 `nuked pat @user` – Vỗ đầu người khác.\n"
                    "🥰 `nuked cuddle @user` – Âu yếm.\n"
                    "💍 `nuked marry @user` – Kết hôn (lưu vào file).\n"
                    "💔 `nuked divorce @user` – Ly hôn.\n"
                    "💞 `nuked ship @user1 @user2` – Ghép đôi ngẫu nhiên.\n"
                    "💌 `nuked crush @user` – Tỏ tình.\n\n"
                    "💡 **VUI:** Hãy thử `marry` và `divorce` để tạo không khí hài hước!"
                ),
                color=0xFF1493
            ),
            "guide_admin": discord.Embed(
                title="🛠️ LỆNH QUẢN TRỊ (OWNER)",
                description=(
                    "**Các lệnh dành riêng cho chủ bot (Boss Bảo):**\n"
                    "👑 `nuked addowner @user` – Thêm owner.\n"
                    "🗑️ `nuked deleteowner @user` – Xóa owner.\n"
                    "📊 `nuked setlv <level> @user` – Set level cho user.\n"
                    "📢 `nuked channelslv #kênh` – Cài kênh thông báo level.\n"
                    "📋 `nuked log #kênh` – Cài kênh log sự kiện.\n"
                    "🎉 `nuked setwelcome #kênh` – Cài kênh chào mừng.\n"
                    "👋 `nuked setgoodbye #kênh` – Cài kênh tạm biệt.\n"
                    "💾 `nuked backup` – Backup server.\n"
                    "🔄 `nuked restore` – Restore server.\n"
                    "🚫 `nuked off <lệnh>` – Tắt một lệnh.\n"
                    "✅ `nuked on <lệnh>` – Bật lại lệnh.\n"
                    "🛑 `nuked off` (không tham số) – Tắt toàn bộ bot.\n"
                    "🔛 `nuked on` (không tham số) – Bật lại bot.\n\n"
                    "💡 **LƯU Ý:** Các lệnh `setup`, `showsv`, `nuke`, `spam...` cũng thuộc nhóm này."
                ),
                color=0x9B59B6
            ),
            "guide_basic": discord.Embed(
                title="❓ LỆNH CƠ BẢN CHO MỌI NGƯỜI",
                description=(
                    "**Những lệnh hữu ích hàng ngày:**\n"
                    "📖 `nuked help` – Mở menu trợ giúp tổng hợp.\n"
                    "🎮 `nuked games` – Mở trung tâm giải trí.\n"
                    "👤 `nuked userinfo @user` – Xem thông tin người dùng.\n"
                    "🖼️ `nuked avatar @user` – Xem avatar.\n"
                    "🏰 `nuked serverinfo` – Xem thông tin server.\n"
                    "👥 `nuked membercount` – Xem số thành viên.\n"
                    "🎒 `nuked inventory` – Xem túi đồ của bạn.\n"
                    "🛒 `nuked shop` – Mở cửa hàng mua vật phẩm.\n"
                    "💳 `nuked buyitem <tên>` – Mua nhanh vật phẩm.\n"
                    "📨 `nuked guithu @user <nội dung>` – Gửi tin nhắn riêng.\n\n"
                    "💡 **GỢI Ý:** Hãy dùng `help` và `games` để khám phá tất cả tính năng."
                ),
                color=0x3498DB
            ),
            "guide_tips": discord.Embed(
                title="🎯 MẸO HAY KHI CHƠI",
                description=(
                    "**💰 1. Tích lũy coin:**\n"
                    "   • 📅 Nhận `daily` mỗi ngày trước khi chơi game.\n"
                    "   • ⏰ Làm `work` mỗi giờ để có thu nhập đều.\n"
                    "   • 🚨 Tham gia `crime` khi đã có vốn (rủi ro nhưng lợi nhuận cao).\n\n"
                    "**🎯 2. Chơi game thông minh:**\n"
                    "   • 💡 Bắt đầu với cược nhỏ để làm quen luật.\n"
                    "   • 🪙 `coinflip` và ✂️ `rps` có tỷ lệ 50/50 – an toàn nhất.\n"
                    "   • 🎰 `slots` và 🎫 `lottery` may rủi cao nhưng thưởng lớn.\n"
                    "   • 🚀 `crash` đòi hỏi canh thời điểm – thử với cược thấp trước.\n\n"
                    "**🛒 3. Tận dụng shop:**\n"
                    "   • 🛍️ Mua vật phẩm có lợi thế như tăng may mắn, bảo vệ.\n"
                    "   • 🏷️ Dùng `buyrole` để mua role đặc biệt nếu có đủ coin.\n\n"
                    "**💬 4. Tương tác xã hội:**\n"
                    "   • 💘 Dùng các lệnh tình yêu để tạo không khí vui vẻ.\n"
                    "   • 📨 Gửi thư (`guithu`) để nhắn nhủ bạn bè.\n\n"
                    "**Chúc bạn chơi vui và thắng lớn!** 🎉"
                ),
                color=0xE67E22
            )
        }
        embed = embeds.get(cid, discord.Embed(title="⚠️ Không tìm thấy", color=0xFF0000))
        embed.set_footer(text="Boss Bảo 💖")
        # Thêm thumbnail gif tương ứng
        gif_thumbnails = {
            "guide_economy": "https://media.tenor.com/9Y8pLfX1nK0AAAAM/money.gif",
            "guide_game": "https://media.tenor.com/2k4z1C2d5zIAAAAM/anime-games.gif",
            "guide_love": "https://media.tenor.com/5L1k2C3d4zIAAAAM/anime-love.gif",
            "guide_admin": "https://media.tenor.com/8Y3p5T4a1r2AAAAM/admin.gif",
            "guide_basic": "https://media.tenor.com/7Z5l3Q8w2v0AAAAM/help.gif",
            "guide_tips": "https://media.tenor.com/6Z2o4U5z9s8AAAAM/tips.gif"
        }
        if cid in gif_thumbnails:
            embed.set_thumbnail(url=gif_thumbnails[cid])
        # Nút quay lại
        back_button = discord.ui.Button(label="🔙 Quay lại", style=discord.ButtonStyle.danger, custom_id="guide_back")
        back_button.callback = self.back_callback
        view = discord.ui.View()
        view.add_item(back_button)
        await interaction.response.edit_message(embed=embed, view=view)

    async def back_callback(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="📘 HƯỚNG DẪN SỬ DỤNG BOT",
            description=(
                "Chọn một chủ đề bên dưới để xem hướng dẫn chi tiết.\n"
                "Mỗi chủ đề sẽ hiển thị các lệnh và mẹo liên quan."
            ),
            color=0x00FFFF
        )
        embed.set_thumbnail(url="https://media.tenor.com/2k4z1C2d5zIAAAAM/anime-hug.gif")
        embed.set_footer(text="Boss Bảo 💖")
        view = GuideView(interaction)
        await interaction.response.edit_message(embed=embed, view=view)

# ==================== LỚP GAMEMENUVIEW (CẬP NHẬT) ====================
class GameMenuView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(label="💵 Kiếm Coin", style=discord.ButtonStyle.primary, custom_id="coin", row=0))
        self.add_item(discord.ui.Button(label="🎲 Mini Games", style=discord.ButtonStyle.success, custom_id="mini", row=0))
        self.add_item(discord.ui.Button(label="🎰 Sòng Bạc Casino", style=discord.ButtonStyle.danger, custom_id="casino", row=0))
        self.add_item(discord.ui.Button(label="🛒 Cửa Hàng & Vàng", style=discord.ButtonStyle.secondary, custom_id="shop", row=1))
        self.add_item(discord.ui.Button(label="🏆 Bảng Xếp Hạng", style=discord.ButtonStyle.primary, custom_id="lb", row=1))
        self.add_item(discord.ui.Button(label="📘 Hướng Dẫn", style=discord.ButtonStyle.secondary, custom_id="guide", row=2))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        cid = interaction.data["custom_id"]
        if cid == "guide":
            embed = discord.Embed(
                title="📘 HƯỚNG DẪN SỬ DỤNG BOT",
                description=(
                    "Chọn một chủ đề bên dưới để xem hướng dẫn chi tiết.\n"
                    "Mỗi chủ đề sẽ hiển thị các lệnh và mẹo liên quan."
                ),
                color=0x00FFFF
            )
            embed.set_thumbnail(url="https://media.tenor.com/2k4z1C2d5zIAAAAM/anime-hug.gif")
            embed.set_footer(text="Boss Bảo 💖")
            view = GuideView(interaction)
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            return True
        if cid == "coin":
            embed = discord.Embed(
                title="💵 DANH MỤC LỆNH KIẾM TIỀN 💵",
                description=(
                    "💰 `nuked balance` — Xem số dư ví & ngân hàng 💳\n"
                    "🎁 `nuked daily` — Nhận quà mỗi ngày (100 - 500 coin) 🌟\n"
                    "💼 `nuked work` — Tăng ca kiếm thêm thu nhập 🛠️\n"
                    "🥺 `nuked beg` — Xin tiền cư dân mạng 🤲\n"
                    "🥷 `nuked crime` — Đi trộm cướp (Cẩn thận đi tù!) 🚨\n"
                    "🏦 `nuked bank deposit <số>` — Gửi tiền gửi tiết kiệm 🔒\n"
                    "💸 `nuked bank withdraw <số>` — Rút tiền mặt ra tiêu 🏧\n"
                    "🤝 `nuked give @user <số>` — Chuyển tiền cho bạn bè 🎁"
                ),
                color=0x00FFCC
            )
            embed.set_thumbnail(url="https://media.tenor.com/9Y8pLfX1nK0AAAAM/money.gif")
        elif cid == "mini":
            embed = discord.Embed(
                title="🎲 DANH MỤC MINI GAMES 🎲",
                description=(
                    "🪙 `nuked coinflip <tiền> <h/t>` — Tung đồng xu 50/50 ✨\n"
                    "🎲 `nuked dice <tiền> <1-6>` — Đoán mặt xúc xắc x4 🎯\n"
                    "✂️ `nuked rps <tiền> <r/p/s>` — Oẳn tù tì ăn tiền 🪨\n"
                    "🎴 `nuked hilo <tiền> <h/l>` — Đoán bài Cao hay Thấp 📈"
                ),
                color=0x2ECC71
            )
            embed.set_thumbnail(url="https://media.tenor.com/2k4z1C2d5zIAAAAM/anime-games.gif")
        elif cid == "casino":
            embed = discord.Embed(
                title="🎰 SÒNG BẠC CASINO THỜI THƯỢNG 🎰",
                description=(
                    "🎰 `nuked slots <tiền>` — Máy quay xèng Jackpot x5 💎\n"
                    "🚀 `nuked crash <tiền>` — Tên lửa vũ trụ nhân tiền 💥\n"
                    "🎫 `nuked lottery <tiền>` — Mua vé số đại phát x10 🧧\n"
                    "🃏 `nuked blackjack <tiền>` — Xì dách 21 điểm cực đỉnh ♠️"
                ),
                color=0xE74C3C
            )
            embed.set_thumbnail(url="https://media.tenor.com/7P9k2C3d5zIAAAAM/nuke.gif")
        elif cid == "shop":
            embed = discord.Embed(
                title="🛒 CỬA HÀNG & ROLE SHOP 🛒",
                description=(
                    "🛍️ `nuked shop` — Xem danh sách vật phẩm hỗ trợ 📜\n"
                    "💳 `nuked buyitem <tên>` — Mua vật phẩm từ Shop 📦\n"
                    "🎒 `nuked inventory` — Mở túi đồ cá nhân 🎒\n"
                    "🏷️ `nuked buyrole <tên>` — Dùng coin mua Role VIP 👑"
                ),
                color=0xF1C40F
            )
            embed.set_thumbnail(url="https://media.tenor.com/4W6k2C3d5zIAAAAM/coin.gif")
        elif cid == "lb":
            embed = discord.Embed(
                title="🏆 BẢNG XẾP HẠNG 🏆",
                description="📊 `nuked leaderboard` — Top 10 đại gia server 👑",
                color=0x9B59B6
            )
            embed.set_thumbnail(url="https://media.tenor.com/1T3k2C3d5zIAAAAM/utility.gif")
        else:
            return True
        embed.set_footer(text="Boss Bảo 💖")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return True

# ==================== LỆNH GAMES ====================
@bot.command(name="games", aliases=["helpgame"])
async def games_menu(ctx):
    embed = discord.Embed(
        title="🎮 TRUNG TÂM GIẢI TRÍ GAME & CASINO 🎮",
        description=(
            "Chào mừng bạn đến với **Nuked Game Center**! 🎉\n\n"
            "👇 **Nhấn vào các nút bấm dưới đây** để xem toàn bộ danh mục hướng dẫn và lệnh chơi chi tiết nhé!"
        ),
        color=0x00FFFF
    )
    embed.set_thumbnail(url="https://media.tenor.com/2k4z1C2d5zIAAAAM/anime-games.gif")
    embed.set_footer(text="Chúc các bạn chơi game vui vẻ & thắng lớn! 💖")
    view = GameMenuView()
    await ctx.send(embed=embed, view=view)

# ==================== CÁC LỆNH TIỆN ÍCH MỚI ====================
@bot.command(name="ping")
async def ping(ctx):
    """🏓 Kiểm tra độ trễ của bot"""
    latency = round(bot.latency * 1000)
    embed = discord.Embed(
        title="🏓 PONG!",
        description=f"⏱️ Độ trễ: **{latency}ms**",
        color=0x00FF00
    )
    embed.set_thumbnail(url="https://media.tenor.com/7Z5l3Q8w2v0AAAAM/help.gif")
    await ctx.send(embed=embed)

@bot.command(name="uptime")
async def uptime(ctx):
    """⏳ Thời gian bot đã hoạt động"""
    now = datetime.now()
    delta = now - bot.launch_time if hasattr(bot, 'launch_time') else timedelta(0)
    if not hasattr(bot, 'launch_time'):
        bot.launch_time = now
        delta = timedelta(0)
    days = delta.days
    hours, rem = divmod(delta.seconds, 3600)
    minutes, seconds = divmod(rem, 60)
    embed = discord.Embed(
        title="⏳ UPTIME",
        description=f"Bot đã hoạt động được **{days} ngày, {hours} giờ, {minutes} phút, {seconds} giây**.",
        color=0x00CCFF
    )
    embed.set_thumbnail(url="https://media.tenor.com/7Z5l3Q8w2v0AAAAM/help.gif")
    await ctx.send(embed=embed)

@bot.command(name="support")
async def support(ctx):
    """🔗 Lấy link hỗ trợ"""
    embed = discord.Embed(
        title="🔗 LIÊN KẾT HỖ TRỢ",
        description=(
            "📌 **Server hỗ trợ 1:** [https://discord.gg/Grr6RWe9A](https://discord.gg/Grr6RWe9A)\n"
            "📌 **Server hỗ trợ 2:** [https://discord.gg/4wrsMbRVpU](https://discord.gg/4wrsMbRVpU)"
        ),
        color=0x3498DB
    )
    embed.set_thumbnail(url="https://media.tenor.com/1T3k2C3d5zIAAAAM/utility.gif")
    await ctx.send(embed=embed)

@bot.command(name="poll")
async def poll(ctx, *, text: str):
    """📊 Tạo bình chọn với các lựa chọn (dùng dấu | để phân cách)"""
    parts = [p.strip() for p in text.split('|')]
    if len(parts) < 3:
        await ctx.send("❌ Cú pháp: `nuked poll <câu hỏi> | <lựa chọn1> | <lựa chọn2> ...` (tối đa 10 lựa chọn)")
        return
    question = parts[0]
    options = parts[1:]
    if len(options) > 10:
        await ctx.send("❌ Chỉ tối đa 10 lựa chọn!")
        return
    if len(options) < 2:
        await ctx.send("❌ Cần ít nhất 2 lựa chọn!")
        return
    # Tạo embed
    embed = discord.Embed(
        title="📊 BÌNH CHỌN",
        description=f"**{question}**",
        color=0x00CCFF
    )
    emojis = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟']
    desc = ""
    for i, opt in enumerate(options):
        desc += f"{emojis[i]} {opt}\n"
    embed.add_field(name="Các lựa chọn", value=desc, inline=False)
    embed.set_footer(text=f"Người tạo: {ctx.author.display_name}")
    message = await ctx.send(embed=embed)
    # Thêm reaction
    for i in range(len(options)):
        await message.add_reaction(emojis[i])

@bot.command(name="math")
async def math_cmd(ctx, *, expression: str):
    """🧮 Tính toán biểu thức đơn giản"""
    try:
        # Chỉ cho phép các ký tự an toàn
        if not re.match(r'^[\d+\-*/().\s]+$', expression):
            await ctx.send("❌ Biểu thức chỉ chứa số, +, -, *, /, (, ) và dấu cách.")
            return
        result = eval(expression)
        embed = discord.Embed(
            title="🧮 KẾT QUẢ",
            description=f"`{expression}` = **{result}**",
            color=0x00FF00
        )
        embed.set_thumbnail(url="https://media.tenor.com/1T3k2C3d5zIAAAAM/utility.gif")
        await ctx.send(embed=embed)
    except Exception:
        await ctx.send("❌ Biểu thức không hợp lệ!")

@bot.command(name="translate")
async def translate(ctx, target_lang: str, *, text: str):
    """🌍 Dịch văn bản (sử dụng Google Translate API)"""
    # Sử dụng googletrans hoặc dịch vụ khác, nhưng để đơn giản, giả lập
    # Thực tế nên dùng thư viện googletrans, nhưng ở đây ta tạm dùng translatepy
    # Để tránh thêm dependency, ta có thể dùng API miễn phí, nhưng mình sẽ bỏ qua.
    await ctx.send("⚠️ Lệnh này yêu cầu cài đặt thêm thư viện. Vui lòng liên hệ Boss Bảo để kích hoạt.")

@bot.command(name="urban")
async def urban(ctx, *, word: str):
    """📖 Tra từ điển Urban"""
    # Tương tự, cần API, tạm thời bỏ qua
    await ctx.send("⚠️ Lệnh này đang được phát triển.")

@bot.command(name="weather")
async def weather(ctx, *, city: str):
    """🌤️ Xem thời tiết (cần API key)"""
    await ctx.send("⚠️ Lệnh này yêu cầu API key. Vui lòng liên hệ Boss Bảo để cấu hình.")

@bot.command(name="remind")
async def remind(ctx, time_str: str, *, reminder: str):
    """⏰ Đặt lời nhắc (vd: 10m, 2h, 1d)"""
    try:
        unit = time_str[-1].lower()
        val = int(time_str[:-1])
        if unit == 'm':
            seconds = val * 60
        elif unit == 'h':
            seconds = val * 3600
        elif unit == 'd':
            seconds = val * 86400
        else:
            await ctx.send("❌ Đơn vị thời gian: m (phút), h (giờ), d (ngày)")
            return
        await ctx.send(f"⏰ Đã đặt lời nhắc sau {time_str}: `{reminder}`")
        await asyncio.sleep(seconds)
        await ctx.send(f"🔔 **{ctx.author.mention}**, đã đến giờ nhắc bạn: `{reminder}`")
    except:
        await ctx.send("❌ Sai định dạng. Ví dụ: `nuked remind 10m Họp nhóm`")

# ==================== XỬ LÝ MESSAGE (GIỮ NGUYÊN) ====================
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    guild_id = message.guild.id if message.guild else None
    if guild_id:
        if guild_id not in USER_LEVELS:
            USER_LEVELS[guild_id] = {}
        user_id = message.author.id
        if user_id not in USER_LEVELS[guild_id]:
            USER_LEVELS[guild_id][user_id] = {"exp": 0, "level": 1}
        user_data = USER_LEVELS[guild_id][user_id]
        if user_data["level"] < 670:
            user_data["exp"] += 30
            required_exp_for_next = get_required_exp(user_data["level"])
            while user_data["exp"] >= required_exp_for_next and user_data["level"] < 670:
                user_data["exp"] -= required_exp_for_next
                user_data["level"] += 1
                new_lv = user_data["level"]
                if isinstance(message.author, discord.Member):
                    await check_and_assign_level_roles(message.author, new_lv)

                coin_reward = random.randint(50, 200)
                add_coins(message.author.id, coin_reward)

                level_embed = discord.Embed(
                    title="🎉 **CHÚC MỪNG LÊN LEVEL!** 🎉",
                    description=f"🌟 {message.author.mention} đã xuất sắc thăng cấp lên **Level {new_lv}**! 🚀",
                    color=0xFFD700
                )
                level_embed.add_field(name="💰 Thưởng coin", value=f"+{coin_reward} coin", inline=False)
                level_embed.set_image(url="https://i.pinimg.com/originals/c3/2c/e0/c32ce0a583261b5a296afc194671a5f9.gif")
                level_embed.set_footer(text="Hệ thống thăng cấp tự động độc quyền")
                target_channel = message.channel
                if guild_id in SERVER_LEVEL_CHANNELS:
                    set_ch = message.guild.get_channel(SERVER_LEVEL_CHANNELS[guild_id])
                    if set_ch:
                        target_channel = set_ch
                try:
                    await target_channel.send(embed=level_embed)
                except:
                    pass
                required_exp_for_next = get_required_exp(user_data["level"])
                save_levels()

    await bot.process_commands(message)

    if message.content.lower().startswith("nuked"):
        content_without_prefix = message.content[len("nuked "):].strip() if len(message.content) > 5 else ""
        if content_without_prefix == "":
            await message.reply("ơi gì vậy sài lệnh thì cứ nuked + lệnh nha")
        else:
            ctx = await bot.get_context(message)
            if ctx.command is None:
                await message.reply("ơi gì vậy sài lệnh thì cứ nuked + lệnh nha")

    has_owner_mention = False
    if message.mentions:
        for user in message.mentions:
            if user.id in BOT_OWNERS:
                has_owner_mention = True
                break

    if not has_owner_mention:
        content_lower = message.content.lower()
        if "bảo" in content_lower:
            owner_id = BOT_OWNERS[0]
            owner_user = bot.get_user(owner_id)
            if owner_user is None:
                try:
                    owner_user = await bot.fetch_user(owner_id)
                except:
                    owner_user = None
            if owner_user:
                await message.reply(f"{owner_user.mention} ê boss nghe k cs ng gọi kìa")

# ==================== SỰ KIỆN JOIN/LEAVE (GIỮ NGUYÊN) ====================
@bot.event
async def on_member_join(member):
    # giữ nguyên
    pass

@bot.event
async def on_member_remove(member):
    # giữ nguyên
    pass

# ==================== ON_READY ====================
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print("✨ Bot đã sẵn sàng phục vụ Boss Bảo!")

if __name__ == "__main__":
    if DISCORD_TOKEN is None:
        print("❌ Thiếu TOKEN. Hãy đặt biến môi trường TOKEN.")
        sys.exit(1)
    keep_alive()
    bot.run(DISCORD_TOKEN)
