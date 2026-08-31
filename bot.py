from pathlib import Path

code = r'''import asyncio
import json
import os
import random
from datetime import datetime, timedelta, timezone

import discord
from discord.ext import commands
from discord.ui import Button, Select, View

# ============================================================
# 🌟 NUKED BOT — ULTIMATE SAFE EDITION
# ============================================================
# Prefix: nuked
#
# Điểm nổi bật:
# - Menu Help tương tác bằng Select + Buttons.
# - GIF nằm ở thumbnail bên PHẢI của Embed.
# - Chia lệnh theo danh mục, emoji + mô tả rõ ràng.
# - Có riêng danh mục OWNER.
# - Level / XP / Coin lưu JSON.
# - Welcome / Goodbye / Log.
# - Moderation theo từng đối tượng.
# - Backup cấu trúc server.
# - Các lệnh phá hoại vẫn được HIỂN THỊ để giữ tương thích menu,
#   nhưng bị khóa thực thi an toàn.
#
# Cài:
#   pip install -U discord.py
#
# Token:
#   Windows CMD:
#       set TOKEN=TOKEN_CUA_BAN
#       python bot.py
#
# Railway:
#   Variables -> TOKEN = token bot
# ============================================================

TOKEN = os.getenv("TOKEN")
PREFIX = "nuked "

# 👑 Thay bằng ID Owner thật của bạn nếu cần.
BOT_OWNERS = {
    1540585511842881616,
    1542453882263707759,
    1502969774202814625,
}

CONFIG_FILE = "config.json"
LEVEL_FILE = "levels.json"
COIN_FILE = "coins.json"
BACKUP_DIR = "backups"

MAX_LEVEL = 670
XP_PER_MESSAGE = 10
XP_COOLDOWN_SECONDS = 30

# GIF dùng thumbnail => hiển thị bên phải embed.
MENU_GIF = "https://media.tenor.com/2k4z1C2d5zIAAAAM/anime-hug.gif"
LEVEL_GIF = "https://i.pinimg.com/originals/c3/2c/e0/c32ce0a583261b5a296afc194671a5f9.gif"
WELCOME_GIF = "https://i.pinimg.com/originals/54/19/c9/5419c9ce3ffade43b2837daa2c96b1d9.gif"
GOODBYE_GIF = "https://i.pinimg.com/originals/16/d5/83/16d583a3fd6d356e5a1d5e57b318474c.gif"

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(
    command_prefix=PREFIX,
    intents=intents,
    help_command=None,
    case_insensitive=True,
)

# ============================================================
# 💾 DATA
# ============================================================

SERVER_LOG_CHANNELS = {}
WELCOME_CHANNELS = {}
GOODBYE_CHANNELS = {}
SERVER_LEVEL_CHANNELS = {}
DISABLED_COMMANDS = set()

USER_LEVELS = {}
USER_COINS = {}

XP_COOLDOWNS = {}
COMMAND_COOLDOWNS = {}


def read_json(filename, default):
    try:
        with open(filename, "r", encoding="utf-8") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return default


def write_json(filename, data):
    temp = f"{filename}.tmp"
    with open(temp, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)
    os.replace(temp, filename)


def load_all_data():
    global SERVER_LOG_CHANNELS
    global WELCOME_CHANNELS
    global GOODBYE_CHANNELS
    global SERVER_LEVEL_CHANNELS
    global DISABLED_COMMANDS
    global BOT_OWNERS
    global USER_LEVELS
    global USER_COINS

    config = read_json(CONFIG_FILE, {})

    SERVER_LOG_CHANNELS = config.get("log_channels", {})
    WELCOME_CHANNELS = config.get("welcome_channels", {})
    GOODBYE_CHANNELS = config.get("goodbye_channels", {})
    SERVER_LEVEL_CHANNELS = config.get("level_channels", {})
    DISABLED_COMMANDS = set(config.get("disabled_commands", []))

    saved_owners = config.get("owners")
    if isinstance(saved_owners, list) and saved_owners:
        try:
            BOT_OWNERS = {int(x) for x in saved_owners}
        except ValueError:
            pass

    USER_LEVELS = read_json(LEVEL_FILE, {})
    USER_COINS = read_json(COIN_FILE, {})


def save_config():
    write_json(
        CONFIG_FILE,
        {
            "log_channels": SERVER_LOG_CHANNELS,
            "welcome_channels": WELCOME_CHANNELS,
            "goodbye_channels": GOODBYE_CHANNELS,
            "level_channels": SERVER_LEVEL_CHANNELS,
            "owners": sorted(BOT_OWNERS),
            "disabled_commands": sorted(DISABLED_COMMANDS),
        },
    )


def save_levels():
    write_json(LEVEL_FILE, USER_LEVELS)


def save_coins():
    write_json(COIN_FILE, USER_COINS)


load_all_data()


# ============================================================
# 🎨 EMBED HELPERS
# ============================================================

def make_embed(
    title,
    description="",
    color=discord.Color.blurple(),
    thumbnail=MENU_GIF,
):
    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=datetime.now(timezone.utc),
    )
    if thumbnail:
        embed.set_thumbnail(url=thumbnail)

    embed.set_footer(
        text="Nuked Bot • Ultimate Safe Edition • Tối ưu trải nghiệm"
    )
    return embed


def success(title, description):
    return make_embed(
        f"✅ {title}",
        description,
        discord.Color.green(),
    )


def fail(description):
    return make_embed(
        "❌ Không thể thực hiện",
        description,
        discord.Color.red(),
    )


def owner_embed(title, description):
    return make_embed(
        f"👑 {title}",
        description,
        discord.Color.gold(),
    )


# ============================================================
# 🧰 GENERAL HELPERS
# ============================================================

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


def get_level_data(guild_id, user_id):
    guild_key = str(guild_id)
    user_key = str(user_id)

    guild_data = USER_LEVELS.setdefault(guild_key, {})
    data = guild_data.setdefault(
        user_key,
        {
            "exp": 0,
            "level": 1,
        },
    )

    data["exp"] = int(data.get("exp", 0))
    data["level"] = int(data.get("level", 1))

    return data


def get_coin_data(user_id):
    key = str(user_id)

    return USER_COINS.setdefault(
        key,
        {
            "balance": 0,
            "last_daily": 0,
            "last_work": 0,
        },
    )


def get_balance(user_id):
    return int(get_coin_data(user_id).get("balance", 0))


def add_coins(user_id, amount):
    data = get_coin_data(user_id)
    data["balance"] = max(0, get_balance(user_id) + int(amount))
    save_coins()


def required_exp(level):
    return max(100, level * 100)


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
    }

    return units.get(unit)


async def send_log(guild, embed):
    channel_id = SERVER_LOG_CHANNELS.get(str(guild.id))

    if not channel_id:
        return

    channel = guild.get_channel(int(channel_id))

    if channel is None:
        return

    try:
        await channel.send(embed=embed)
    except (discord.Forbidden, discord.HTTPException):
        pass


async def require_enabled(ctx):
    if command_disabled(ctx.command.qualified_name):
        await ctx.send(
            embed=fail(
                f"🔒 Lệnh `{ctx.command.qualified_name}` hiện đang bị Owner tắt."
            )
        )
        return False
    return True


def hierarchy_error(target, author):
    if target == author:
        return "Bạn không thể áp dụng thao tác này lên chính mình."

    if target.top_role >= author.top_role:
        return "Role cao nhất của mục tiêu phải thấp hơn role cao nhất của bạn."

    if target.top_role >= target.guild.me.top_role:
        return "Bot không có role đủ cao để thao tác với thành viên này."

    return None


# ============================================================
# 🧭 HELP MENU DATA
# ============================================================

HELP_CATEGORIES = {
    "🏠 Cơ bản": {
        "description": "Những lệnh dùng hằng ngày để khám phá server và bot.",
        "commands": [
            ("📖 nuked help", "Mở menu trợ giúp tương tác."),
            ("🎮 nuked games", "Mở trung tâm trò chơi an toàn."),
            ("👤 nuked userinfo [@user]", "Xem thông tin thành viên."),
            ("🖼️ nuked avatar [@user]", "Xem avatar."),
            ("🏰 nuked serverinfo", "Xem thông tin server."),
            ("👥 nuked membercount", "Xem số thành viên."),
            ("📊 nuked botinfo", "Xem trạng thái bot."),
        ],
    },
    "📊 Level": {
        "description": "Hệ thống EXP tự động, lưu dữ liệu và thông báo khi lên cấp.",
        "commands": [
            ("⭐ nuked lv [@user]", "Xem level và EXP."),
            ("📈 Tự động EXP", "Nhắn tin để tích EXP."),
            ("🏅 Level role", "Tự động nhận role ở mốc level."),
        ],
    },
    "💰 Coin": {
        "description": "Hệ thống coin giải trí, không có cá cược bằng tiền thật.",
        "commands": [
            ("🎁 nuked daily", "Nhận coin mỗi ngày."),
            ("💼 nuked work", "Làm việc để nhận coin."),
            ("🤲 nuked beg", "Nhận một khoản coin nhỏ."),
            ("💰 nuked balance [@user]", "Xem số dư."),
            ("💸 nuked give @user <số>", "Tặng coin."),
            ("🏆 nuked leaderboard", "Xem bảng xếp hạng coin."),
        ],
    },
    "🛡️ Kiểm duyệt": {
        "description": "Moderation theo từng thành viên hoặc từng tin nhắn.",
        "commands": [
            ("⚠️ nuked warn @user [lý do]", "Cảnh cáo một thành viên."),
            ("👢 nuked kick @user [lý do]", "Kick một thành viên."),
            ("🔨 nuked ban @user [lý do]", "Ban một thành viên."),
            ("♻️ nuked unban <user_id>", "Gỡ ban."),
            ("⏳ nuked timeout @user <10m|2h|1d>", "Timeout."),
            ("🔇 nuked mute @user [10m]", "Mute theo thời gian."),
            ("🔊 nuked unmute @user", "Gỡ mute."),
            ("🧹 nuked clear <1-100>", "Xóa tin nhắn trong kênh hiện tại."),
        ],
    },
    "📢 Kênh & Role": {
        "description": "Quản lý từng kênh/role cụ thể.",
        "commands": [
            ("🆕 nuked createchannel <tên>", "Tạo một text channel."),
            ("🗑️ nuked deletechannel [#kênh]", "Xóa một kênh cụ thể."),
            ("✏️ nuked renamechannel #kênh <tên>", "Đổi tên kênh."),
            ("📝 nuked settopic #kênh <nội dung>", "Đặt topic."),
            ("🐢 nuked slowmode <giây>", "Cài slowmode."),
            ("🔒 nuked lock [#kênh]", "Khóa gửi tin."),
            ("🔓 nuked unlock [#kênh]", "Mở khóa gửi tin."),
            ("🎭 nuked role @user <role>", "Gán role."),
            ("🎭 nuked removerole @user <role>", "Gỡ role."),
            ("📋 nuked listroles", "Liệt kê role."),
            ("📚 nuked listchannels", "Liệt kê channel."),
        ],
    },
    "🎉 Chào mừng": {
        "description": "Tự động chào thành viên mới, goodbye và log.",
        "commands": [
            ("🎉 nuked setwelcome #kênh", "Đặt kênh welcome."),
            ("👋 nuked setgoodbye #kênh", "Đặt kênh goodbye."),
            ("📋 nuked log #kênh", "Đặt kênh log."),
        ],
    },
    "🔊 Voice": {
        "description": "Điều khiển voice theo từng thành viên.",
        "commands": [
            ("🚪 nuked move @user #voice", "Di chuyển một thành viên."),
            ("🔇 nuked deafen @user", "Deafen một thành viên."),
            ("🔊 nuked undeafen @user", "Bỏ deafen."),
            ("🎙️ nuked vc <tên>", "Tạo voice channel."),
        ],
    },
    "🧰 Tiện ích": {
        "description": "Các công cụ phụ trợ.",
        "commands": [
            ("📨 nuked guithu @user <nội dung>", "Gửi DM thông qua bot."),
            ("✏️ nuked nick @user <tên>", "Đổi nickname."),
            ("🔄 nuked resetnick @user", "Reset nickname."),
        ],
    },
    "💾 Backup": {
        "description": "Backup cấu trúc server và phục hồi phần còn thiếu.",
        "commands": [
            ("💾 nuked backup", "Lưu cấu trúc server ra JSON."),
            ("♻️ nuked restore", "Tạo lại phần cấu trúc còn thiếu."),
        ],
    },
    "👑 Owner": {
        "description": "Chỉ BOT_OWNERS được sử dụng.",
        "commands": [
            ("👑 nuked owner", "Xem danh sách Owner."),
            ("➕ nuked addowner @user", "Thêm Owner."),
            ("➖ nuked deleteowner @user", "Xóa Owner."),
            ("🎯 nuked setlv <level> @user", "Đặt level."),
            ("💰 nuked setcoins @user <số>", "Đặt coin."),
            ("➕ nuked addcoins @user <số>", "Cộng coin."),
            ("➖ nuked removecoins @user <số>", "Trừ coin."),
            ("🚫 nuked off <lệnh>", "Tắt một lệnh."),
            ("✅ nuked on <lệnh>", "Bật lại một lệnh."),
            ("📋 nuked disabled", "Xem lệnh đang tắt."),
            ("🔄 nuked reload", "Tải lại JSON config."),
        ],
    },
    "💣 Lệnh nguy hiểm": {
        "description": (
            "Các tên lệnh phá hoại được giữ trong menu để tham chiếu/tương thích, "
            "nhưng KHÔNG có chức năng phá server."
        ),
        "commands": [
            ("💣 nuked nuke", "🔒 Đã khóa thực thi phá hoại."),
            ("💥 nuked massban", "🔒 Đã khóa ban hàng loạt."),
            ("💥 nuked masskick", "🔒 Đã khóa kick hàng loạt."),
            ("🧨 nuked spam", "🔒 Đã khóa spam hàng loạt."),
            ("🧨 nuked webhookspam", "🔒 Đã khóa webhook spam."),
            ("🗑️ nuked deleteall", "🔒 Đã khóa xóa hàng loạt."),
        ],
    },
}


def help_home_embed():
    lines = [
        "✨ **Chào mừng đến với Nuked Bot**",
        "",
        "Một trung tâm điều khiển Discord tập trung vào **giao diện đẹp + dễ dùng + an toàn**.",
        "",
        "📌 **Prefix:** `nuked `",
        "🧭 Chọn danh mục bên dưới để xem cú pháp.",
        "🎞️ GIF được đặt ở thumbnail bên phải.",
        "",
        "━━━━━━━━━━━━━━━━━━━━",
        "💡 **Mẹo:** Bạn có thể dùng `nuked help` bất cứ lúc nào.",
    ]

    return make_embed(
        "🌌 NUKED BOT • CONTROL CENTER",
        "\n".join(lines),
        discord.Color.from_rgb(88, 101, 242),
        MENU_GIF,
    )


def category_embed(category):
    data = HELP_CATEGORIES[category]

    embed = make_embed(
        f"{category} • Danh mục lệnh",
        data["description"],
        discord.Color.blurple(),
        MENU_GIF,
    )

    for command_name, description in data["commands"]:
        embed.add_field(
            name=command_name,
            value=f"> {description}",
            inline=False,
        )

    return embed


class HelpSelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label=name,
                value=name,
                description=data["description"][:100],
                emoji=name.split()[0],
            )
            for name, data in HELP_CATEGORIES.items()
        ]

        super().__init__(
            placeholder="🧭 Chọn một danh mục lệnh...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="nuked_help_select",
        )

    async def callback(self, interaction):
        category = self.values[0]

        await interaction.response.edit_message(
            embed=category_embed(category),
            view=HelpView(),
        )


class HomeButton(Button):
    def __init__(self):
        super().__init__(
            label="Trang chủ",
            emoji="🏠",
            style=discord.ButtonStyle.primary,
            custom_id="nuked_help_home",
        )

    async def callback(self, interaction):
        await interaction.response.edit_message(
            embed=help_home_embed(),
            view=HelpView(),
        )


class OwnerButton(Button):
    def __init__(self):
        super().__init__(
            label="Owner",
            emoji="👑",
            style=discord.ButtonStyle.success,
            custom_id="nuked_help_owner",
        )

    async def callback(self, interaction):
        if not is_owner_id(interaction.user.id):
            await interaction.response.send_message(
                embed=fail("🔒 Khu vực này chỉ dành cho Owner bot."),
                ephemeral=True,
            )
            return

        await interaction.response.edit_message(
            embed=category_embed("👑 Owner"),
            view=HelpView(),
        )


class HelpView(View):
    def __init__(self):
        super().__init__(timeout=300)

        self.add_item(HelpSelect())
        self.add_item(HomeButton())
        self.add_item(OwnerButton())


# ============================================================
# 🚀 BOT EVENTS
# ============================================================

@bot.event
async def on_ready():
    print("==============================================")
    print(f"🤖 Đăng nhập: {bot.user}")
    print(f"🆔 ID: {bot.user.id}")
    print(f"🏰 Servers: {len(bot.guilds)}")
    print(f"👑 Owners: {len(BOT_OWNERS)}")
    print("🌌 Nuked Bot đã sẵn sàng!")
    print("==============================================")

    try:
        await bot.change_presence(
            status=discord.Status.online,
            activity=discord.Game(name="nuked help • Control Center"),
        )
    except discord.HTTPException:
        pass


@bot.event
async def on_member_join(member):
    channel_id = WELCOME_CHANNELS.get(str(member.guild.id))

    if not channel_id:
        return

    channel = member.guild.get_channel(int(channel_id))

    if channel is None:
        return

    embed = make_embed(
        "🎉 Thành viên mới!",
        (
            f"Chào mừng {member.mention} đến với **{member.guild.name}**!\n\n"
            "💖 Chúc bạn có khoảng thời gian vui vẻ tại server."
        ),
        discord.Color.green(),
        WELCOME_GIF,
    )

    try:
        await channel.send(embed=embed)
    except discord.HTTPException:
        pass


@bot.event
async def on_member_remove(member):
    channel_id = GOODBYE_CHANNELS.get(str(member.guild.id))

    if not channel_id:
        return

    channel = member.guild.get_channel(int(channel_id))

    if channel is None:
        return

    embed = make_embed(
        "👋 Thành viên rời server",
        f"**{member}** đã rời khỏi **{member.guild.name}**.",
        discord.Color.orange(),
        GOODBYE_GIF,
    )

    try:
        await channel.send(embed=embed)
    except discord.HTTPException:
        pass


@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if message.guild:
        key = (message.guild.id, message.author.id)
        now = datetime.now(timezone.utc)

        last = XP_COOLDOWNS.get(key)

        if (
            last is None
            or (now - last).total_seconds() >= XP_COOLDOWN_SECONDS
        ):
            XP_COOLDOWNS[key] = now

            data = get_level_data(
                message.guild.id,
                message.author.id,
            )

            if data["level"] < MAX_LEVEL:
                old_level = data["level"]
                data["exp"] += XP_PER_MESSAGE

                while (
                    data["level"] < MAX_LEVEL
                    and data["exp"] >= required_exp(data["level"])
                ):
                    data["exp"] -= required_exp(data["level"])
                    data["level"] += 1

                save_levels()

                if data["level"] > old_level:
                    channel_id = SERVER_LEVEL_CHANNELS.get(
                        str(message.guild.id)
                    )
                    channel = (
                        message.guild.get_channel(int(channel_id))
                        if channel_id
                        else message.channel
                    )

                    if channel:
                        embed = make_embed(
                            "🎉 LEVEL UP!",
                            (
                                f"🎊 {message.author.mention} đã đạt "
                                f"**Level {data['level']}**!\n\n"
                                f"⭐ EXP hiện tại: `{data['exp']}`"
                            ),
                            discord.Color.gold(),
                            LEVEL_GIF,
                        )

                        try:
                            await channel.send(embed=embed)
                        except discord.HTTPException:
                            pass

    await bot.process_commands(message)


# ============================================================
# 📖 HELP
# ============================================================

@bot.command(name="help")
async def help_command(ctx):
    if not await require_enabled(ctx):
        return

    await ctx.send(
        embed=help_home_embed(),
        view=HelpView(),
    )


# ============================================================
# 🏠 BASIC COMMANDS
# ============================================================

@bot.command(name="botinfo")
async def botinfo(ctx):
    if not await require_enabled(ctx):
        return

    embed = make_embed(
        "🤖 Thông tin Nuked Bot",
        "Hệ thống quản lý Discord với giao diện tương tác.",
        discord.Color.blurple(),
        MENU_GIF,
    )

    embed.add_field(name="🏰 Servers", value=f"`{len(bot.guilds)}`")
    embed.add_field(name="👑 Owners", value=f"`{len(BOT_OWNERS)}`")
    embed.add_field(name="⚡ Prefix", value="`nuked `")
    embed.add_field(name="🛡️ Chế độ", value="`Safe Edition`")
    embed.add_field(
        name="🎨 UI",
        value="`Select + Button + Embed`",
        inline=False,
    )

    await ctx.send(embed=embed)


@bot.command(name="userinfo")
async def userinfo(ctx, member: discord.Member = None):
    if not await require_enabled(ctx):
        return

    member = member or ctx.author

    embed = make_embed(
        f"👤 {member}",
        f"Thông tin chi tiết của {member.mention}.",
        discord.Color.blurple(),
        str(member.display_avatar.url),
    )

    embed.add_field(name="🆔 ID", value=f"`{member.id}`")
    embed.add_field(name="🏷️ Nickname", value=f"`{member.display_name}`")
    embed.add_field(name="🤖 Bot", value="Có" if member.bot else "Không")
    embed.add_field(
        name="📅 Tham gia",
        value=discord.utils.format_dt(member.joined_at, "R")
        if member.joined_at
        else "Không rõ",
    )
    embed.add_field(
        name="🎭 Role cao nhất",
        value=member.top_role.mention,
    )

    await ctx.send(embed=embed)


@bot.command(name="avatar")
async def avatar(ctx, member: discord.Member = None):
    if not await require_enabled(ctx):
        return

    member = member or ctx.author

    embed = make_embed(
        f"🖼️ Avatar của {member}",
        f"[Mở ảnh gốc]({member.display_avatar.url})",
        discord.Color.blurple(),
        str(member.display_avatar.url),
    )

    await ctx.send(embed=embed)


@bot.command(name="serverinfo")
async def serverinfo(ctx):
    if not await require_enabled(ctx):
        return

    guild = ctx.guild

    embed = make_embed(
        f"🏰 {guild.name}",
        "Thông tin máy chủ.",
        discord.Color.blurple(),
        str(guild.icon.url) if guild.icon else MENU_GIF,
    )

    embed.add_field(name="🆔 ID", value=f"`{guild.id}`")
    embed.add_field(name="👥 Thành viên", value=f"`{guild.member_count}`")
    embed.add_field(name="📚 Kênh", value=f"`{len(guild.channels)}`")
    embed.add_field(name="🎭 Role", value=f"`{len(guild.roles)}`")
    embed.add_field(
        name="👑 Owner",
        value=str(guild.owner) if guild.owner else "Không rõ",
    )

    await ctx.send(embed=embed)


@bot.command(name="membercount")
async def membercount(ctx):
    if not await require_enabled(ctx):
        return

    await ctx.send(
        embed=make_embed(
            "👥 Thành viên",
            f"Server hiện có **{ctx.guild.member_count}** thành viên.",
            discord.Color.blurple(),
        )
    )


# ============================================================
# 📊 LEVEL
# ============================================================

@bot.command(name="lv", aliases=["level"])
async def level_command(ctx, member: discord.Member = None):
    if not await require_enabled(ctx):
        return

    member = member or ctx.author

    data = get_level_data(ctx.guild.id, member.id)
    need = required_exp(data["level"])

    embed = make_embed(
        f"⭐ Level của {member.display_name}",
        (
            f"🏅 **Level:** `{data['level']}/{MAX_LEVEL}`\n"
            f"✨ **EXP:** `{data['exp']}/{need}`\n\n"
            "💡 Nhắn tin hợp lệ để tiếp tục nhận EXP."
        ),
        discord.Color.gold(),
        str(member.display_avatar.url),
    )

    await ctx.send(embed=embed)


# ============================================================
# 💰 COIN
# ============================================================

@bot.command(name="balance", aliases=["bal"])
async def balance(ctx, member: discord.Member = None):
    if not await require_enabled(ctx):
        return

    member = member or ctx.author

    await ctx.send(
        embed=make_embed(
            "💰 Số dư",
            f"{member.mention} đang có **{get_balance(member.id):,} coin**.",
            discord.Color.gold(),
            str(member.display_avatar.url),
        )
    )


@bot.command(name="daily")
async def daily(ctx):
    if not await require_enabled(ctx):
        return

    data = get_coin_data(ctx.author.id)
    now = int(datetime.now(timezone.utc).timestamp())

    if now - int(data.get("last_daily", 0)) < 86400:
        remaining = 86400 - (
            now - int(data.get("last_daily", 0))
        )

        hours = remaining // 3600
        minutes = (remaining % 3600) // 60

        await ctx.send(
            embed=fail(
                f"⏳ Bạn đã nhận daily rồi.\n"
                f"Thử lại sau khoảng **{hours}h {minutes}m**."
            )
        )
        return

    amount = random.randint(100, 300)

    data["last_daily"] = now
    data["balance"] = get_balance(ctx.author.id) + amount
    save_coins()

    await ctx.send(
        embed=success(
            "Daily",
            f"🎁 Bạn nhận được **{amount:,} coin** hôm nay!",
        )
    )


@bot.command(name="work")
async def work(ctx):
    if not await require_enabled(ctx):
        return

    data = get_coin_data(ctx.author.id)
    now = int(datetime.now(timezone.utc).timestamp())

    if now - int(data.get("last_work", 0)) < 3600:
        remaining = 3600 - (
            now - int(data.get("last_work", 0))
        )

        minutes = remaining // 60

        await ctx.send(
            embed=fail(
                f"⏳ Bạn đang nghỉ.\nThử lại sau khoảng **{minutes} phút**."
            )
        )
        return

    jobs = [
        "lập trình viên",
        "designer",
        "người giao hàng",
        "thợ xây",
        "nhân viên quán cà phê",
    ]

    job = random.choice(jobs)
    amount = random.randint(80, 220)

    data["last_work"] = now
    data["balance"] = get_balance(ctx.author.id) + amount
    save_coins()

    await ctx.send(
        embed=success(
            "Work",
            f"💼 Bạn làm **{job}** và kiếm được **{amount:,} coin**!",
        )
    )


@bot.command(name="beg")
async def beg(ctx):
    if not await require_enabled(ctx):
        return

    amount = random.randint(10, 80)
    add_coins(ctx.author.id, amount)

    await ctx.send(
        embed=success(
            "Beg",
            f"🤲 Một người tốt bụng cho bạn **{amount:,} coin**.",
        )
    )


@bot.command(name="give")
async def give(ctx, member: discord.Member, amount: int):
    if not await require_enabled(ctx):
        return

    if member.bot:
        await ctx.send(embed=fail("🤖 Không thể chuyển coin cho bot."))
        return

    if member == ctx.author:
        await ctx.send(embed=fail("😅 Không thể tự chuyển coin cho chính mình."))
        return

    if amount <= 0:
        await ctx.send(embed=fail("Số coin phải lớn hơn 0."))
        return

    if get_balance(ctx.author.id) < amount:
        await ctx.send(embed=fail("💸 Bạn không đủ coin."))
        return

    add_coins(ctx.author.id, -amount)
    add_coins(member.id, amount)

    await ctx.send(
        embed=success(
            "Chuyển coin",
            f"💸 {ctx.author.mention} → {member.mention}: **{amount:,} coin**.",
        )
    )


@bot.command(name="leaderboard", aliases=["lb"])
async def leaderboard(ctx):
    if not await require_enabled(ctx):
        return

    rows = sorted(
        USER_COINS.items(),
        key=lambda item: int(item[1].get("balance", 0)),
        reverse=True,
    )

    lines = []

    for index, (user_id, data) in enumerate(rows[:10], start=1):
        user = bot.get_user(int(user_id))
        name = user.display_name if user else f"User {user_id}"
        lines.append(
            f"**{index}.** {name} — `{int(data.get('balance', 0)):,}` coin"
        )

    if not lines:
        lines.append("Chưa có dữ liệu.")

    await ctx.send(
        embed=make_embed(
            "🏆 Coin Leaderboard",
            "\n".join(lines),
            discord.Color.gold(),
        )
    )


# ============================================================
# 🛡️ MODERATION
# ============================================================

@bot.command(name="warn")
@commands.has_guild_permissions(manage_messages=True)
async def warn(ctx, member: discord.Member, *, reason="Không có lý do"):
    if not await require_enabled(ctx):
        return

    error = hierarchy_error(member, ctx.author)

    if error:
        await ctx.send(embed=fail(error))
        return

    embed = make_embed(
        "⚠️ Cảnh cáo",
        (
            f"{member.mention} đã nhận một cảnh cáo.\n"
            f"📝 **Lý do:** {reason}\n"
            f"👮 **Bởi:** {ctx.author.mention}"
        ),
        discord.Color.orange(),
        str(member.display_avatar.url),
    )

    await ctx.send(embed=embed)

    await send_log(
        ctx.guild,
        make_embed(
            "⚠️ Moderation Log",
            f"{ctx.author} warn {member} — {reason}",
            discord.Color.orange(),
        ),
    )


@bot.command(name="kick")
@commands.has_guild_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason="Không có lý do"):
    if not await require_enabled(ctx):
        return

    error = hierarchy_error(member, ctx.author)

    if error:
        await ctx.send(embed=fail(error))
        return

    try:
        await member.kick(reason=reason)
    except discord.Forbidden:
        await ctx.send(embed=fail("Bot không có quyền kick thành viên này."))
        return

    await ctx.send(
        embed=success(
            "Kick thành công",
            f"👢 **{member}** đã bị kick.\n📝 {reason}",
        )
    )


@bot.command(name="ban")
@commands.has_guild_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason="Không có lý do"):
    if not await require_enabled(ctx):
        return

    error = hierarchy_error(member, ctx.author)

    if error:
        await ctx.send(embed=fail(error))
        return

    try:
        await member.ban(reason=reason, delete_message_days=0)
    except discord.Forbidden:
        await ctx.send(embed=fail("Bot không có quyền ban thành viên này."))
        return

    await ctx.send(
        embed=success(
            "Ban thành công",
            f"🔨 **{member}** đã bị ban.\n📝 {reason}",
        )
    )


@bot.command(name="unban")
@commands.has_guild_permissions(ban_members=True)
async def unban(ctx, user_id: int):
    if not await require_enabled(ctx):
        return

    try:
        user = await bot.fetch_user(user_id)
        await ctx.guild.unban(user)
    except discord.NotFound:
        await ctx.send(embed=fail("Không tìm thấy user hoặc user chưa bị ban."))
        return
    except discord.Forbidden:
        await ctx.send(embed=fail("Bot không có quyền unban."))
        return

    await ctx.send(
        embed=success(
            "Unban thành công",
            f"♻️ Đã gỡ ban cho **{user}**.",
        )
    )


@bot.command(name="timeout")
@commands.has_guild_permissions(moderate_members=True)
async def timeout_member(
    ctx,
    member: discord.Member,
    duration: str,
    *,
    reason="Không có lý do",
):
    if not await require_enabled(ctx):
        return

    error = hierarchy_error(member, ctx.author)

    if error:
        await ctx.send(embed=fail(error))
        return

    delta = parse_duration(duration)

    if delta is None:
        await ctx.send(
            embed=fail(
                "⏳ Thời gian không hợp lệ. Ví dụ: `10m`, `2h`, `1d`."
            )
        )
        return

    if delta > timedelta(days=28):
        await ctx.send(embed=fail("⏳ Timeout tối đa là 28 ngày."))
        return

    try:
        await member.timeout(delta, reason=reason)
    except discord.Forbidden:
        await ctx.send(embed=fail("Bot không có quyền timeout."))
        return

    await ctx.send(
        embed=success(
            "Timeout",
            f"⏳ {member.mention} bị timeout **{duration}**.\n📝 {reason}",
        )
    )


@bot.command(name="mute")
@commands.has_guild_permissions(moderate_members=True)
async def mute(ctx, member: discord.Member, duration: str = "10m"):
    if not await require_enabled(ctx):
        return

    error = hierarchy_error(member, ctx.author)

    if error:
        await ctx.send(embed=fail(error))
        return

    delta = parse_duration(duration) or timedelta(minutes=10)

    if delta > timedelta(days=28):
        await ctx.send(embed=fail("⏳ Thời gian mute tối đa là 28 ngày."))
        return

    try:
        await member.timeout(delta, reason=f"Mute bởi {ctx.author}")
    except discord.Forbidden:
        await ctx.send(embed=fail("Bot không có quyền mute."))
        return

    await ctx.send(
        embed=success(
            "Mute",
            f"🔇 {member.mention} đã bị mute trong **{duration}**.",
        )
    )


@bot.command(name="unmute")
@commands.has_guild_permissions(moderate_members=True)
async def unmute(ctx, member: discord.Member):
    if not await require_enabled(ctx):
        return

    try:
        await member.timeout(None, reason=f"Unmute bởi {ctx.author}")
    except discord.Forbidden:
        await ctx.send(embed=fail("Bot không có quyền unmute."))
        return

    await ctx.send(
        embed=success(
            "Unmute",
            f"🔊 {member.mention} đã được unmute.",
        )
    )


@bot.command(name="clear", aliases=["purge"])
@commands.has_guild_permissions(manage_messages=True)
async def clear(ctx, amount: int):
    if not await require_enabled(ctx):
        return

    if amount < 1 or amount > 100:
        await ctx.send(embed=fail("Số lượng phải từ 1 đến 100."))
        return

    try:
        deleted = await ctx.channel.purge(limit=amount + 1)
    except discord.Forbidden:
        await ctx.send(embed=fail("Bot không có quyền quản lý tin nhắn."))
        return

    msg = await ctx.send(
        embed=success(
            "Dọn tin nhắn",
            f"🧹 Đã xóa khoảng **{max(0, len(deleted) - 1)}** tin nhắn.",
        )
    )

    await asyncio.sleep(5)

    try:
        await msg.delete()
    except discord.HTTPException:
        pass


# ============================================================
# 📢 CHANNEL / ROLE
# ============================================================

@bot.command(name="createchannel")
@commands.has_guild_permissions(manage_channels=True)
async def createchannel(ctx, *, name: str):
    if not await require_enabled(ctx):
        return

    name = name.strip()[:100]

    if not name:
        await ctx.send(embed=fail("Tên kênh không hợp lệ."))
        return

    try:
        channel = await ctx.guild.create_text_channel(
            name=name,
            reason=f"Tạo bởi {ctx.author}",
        )
    except discord.Forbidden:
        await ctx.send(embed=fail("Bot không có quyền tạo kênh."))
        return

    await ctx.send(
        embed=success(
            "Tạo kênh",
            f"🆕 Đã tạo {channel.mention}.",
        )
    )


@bot.command(name="deletechannel")
@commands.has_guild_permissions(manage_channels=True)
async def deletechannel(ctx, channel: discord.TextChannel = None):
    if not await require_enabled(ctx):
        return

    channel = channel or ctx.channel

    try:
        await channel.delete(reason=f"Xóa bởi {ctx.author}")
    except discord.Forbidden:
        await ctx.send(embed=fail("Bot không có quyền xóa kênh."))
        return


@bot.command(name="renamechannel")
@commands.has_guild_permissions(manage_channels=True)
async def renamechannel(
    ctx,
    channel: discord.TextChannel,
    *,
    name: str,
):
    if not await require_enabled(ctx):
        return

    try:
        await channel.edit(
            name=name[:100],
            reason=f"Đổi tên bởi {ctx.author}",
        )
    except discord.Forbidden:
        await ctx.send(embed=fail("Bot không có quyền đổi tên kênh."))
        return

    await ctx.send(
        embed=success(
            "Đổi tên kênh",
            f"✏️ Đã đổi thành **{channel.name}**.",
        )
    )


@bot.command(name="settopic")
@commands.has_guild_permissions(manage_channels=True)
async def settopic(
    ctx,
    channel: discord.TextChannel,
    *,
    topic: str,
):
    if not await require_enabled(ctx):
        return

    try:
        await channel.edit(
            topic=topic[:1024],
            reason=f"Đặt topic bởi {ctx.author}",
        )
    except discord.Forbidden:
        await ctx.send(embed=fail("Bot không có quyền sửa topic."))
        return

    await ctx.send(embed=success("Topic", "📝 Đã cập nhật topic."))


@bot.command(name="slowmode")
@commands.has_guild_permissions(manage_channels=True)
async def slowmode(ctx, seconds: int):
    if not await require_enabled(ctx):
        return

    if seconds < 0 or seconds > 21600:
        await ctx.send(
            embed=fail("Slowmode phải từ 0 đến 21600 giây.")
        )
        return

    try:
        await ctx.channel.edit(
            slowmode_delay=seconds,
            reason=f"Slowmode bởi {ctx.author}",
        )
    except discord.Forbidden:
        await ctx.send(embed=fail("Bot không có quyền sửa slowmode."))
        return

    await ctx.send(
        embed=success(
            "Slowmode",
            f"🐢 Đã đặt slowmode: **{seconds}s**.",
        )
    )


async def set_channel_lock(channel, guild, locked):
    everyone = guild.default_role

    overwrite = channel.overwrites_for(everyone)
    overwrite.send_messages = not locked

    await channel.set_permissions(
        everyone,
        overwrite=overwrite,
        reason="Nuked Bot channel lock",
    )


@bot.command(name="lock")
@commands.has_guild_permissions(manage_channels=True)
async def lock(ctx, channel: discord.TextChannel = None):
    if not await require_enabled(ctx):
        return

    channel = channel or ctx.channel

    try:
        await set_channel_lock(channel, ctx.guild, True)
    except discord.Forbidden:
        await ctx.send(embed=fail("Bot không có quyền khóa kênh."))
        return

    await ctx.send(
        embed=success(
            "Khóa kênh",
            f"🔒 {channel.mention} đã được khóa gửi tin.",
        )
    )


@bot.command(name="unlock")
@commands.has_guild_permissions(manage_channels=True)
async def unlock(ctx, channel: discord.TextChannel = None):
    if not await require_enabled(ctx):
        return

    channel = channel or ctx.channel

    try:
        await set_channel_lock(channel, ctx.guild, False)
    except discord.Forbidden:
        await ctx.send(embed=fail("Bot không có quyền mở khóa kênh."))
        return

    await ctx.send(
        embed=success(
            "Mở khóa",
            f"🔓 {channel.mention} đã được mở khóa.",
        )
    )


@bot.command(name="role")
@commands.has_guild_permissions(manage_roles=True)
async def role_command(
    ctx,
    member: discord.Member,
    *,
    role_name: str,
):
    if not await require_enabled(ctx):
        return

    role = discord.utils.find(
        lambda r: r.name.lower() == role_name.lower(),
        ctx.guild.roles,
    )

    if role is None:
        await ctx.send(embed=fail("Không tìm thấy role."))
        return

    if role >= ctx.guild.me.top_role:
        await ctx.send(embed=fail("Role này cao hơn role bot."))
        return

    try:
        await member.add_roles(
            role,
            reason=f"Gán role bởi {ctx.author}",
        )
    except discord.Forbidden:
        await ctx.send(embed=fail("Bot không thể gán role này."))
        return

    await ctx.send(
        embed=success(
            "Gán role",
            f"🎭 Đã gán **{role.name}** cho {member.mention}.",
        )
    )


@bot.command(name="removerole")
@commands.has_guild_permissions(manage_roles=True)
async def removerole(
    ctx,
    member: discord.Member,
    *,
    role_name: str,
):
    if not await require_enabled(ctx):
        return

    role = discord.utils.find(
        lambda r: r.name.lower() == role_name.lower(),
        ctx.guild.roles,
    )

    if role is None:
        await ctx.send(embed=fail("Không tìm thấy role."))
        return

    try:
        await member.remove_roles(
            role,
            reason=f"Gỡ role bởi {ctx.author}",
        )
    except discord.Forbidden:
        await ctx.send(embed=fail("Bot không thể gỡ role này."))
        return

    await ctx.send(
        embed=success(
            "Gỡ role",
            f"🎭 Đã gỡ **{role.name}** khỏi {member.mention}.",
        )
    )


@bot.command(name="listroles")
async def listroles(ctx):
    if not await require_enabled(ctx):
        return

    roles = [
        f"`{role.id}` • {role.name}"
        for role in reversed(ctx.guild.roles)
        if role.name != "@everyone"
    ]

    text = "\n".join(roles[:50]) or "Không có role."

    await ctx.send(
        embed=make_embed(
            "🎭 Danh sách role",
            text,
            discord.Color.blurple(),
        )
    )


@bot.command(name="listchannels")
async def listchannels(ctx):
    if not await require_enabled(ctx):
        return

    text_channels = [
        f"💬 {channel.mention}"
        for channel in ctx.guild.text_channels
    ]

    voice_channels = [
        f"🔊 **{channel.name}**"
        for channel in ctx.guild.voice_channels
    ]

    description = (
        "**💬 Text**\n"
        + ("\n".join(text_channels[:50]) or "Không có")
        + "\n\n**🔊 Voice**\n"
        + ("\n".join(voice_channels[:30]) or "Không có")
    )

    await ctx.send(
        embed=make_embed(
            "📚 Danh sách kênh",
            description,
            discord.Color.blurple(),
        )
    )


# ============================================================
# 🎉 WELCOME / LOG
# ============================================================

@bot.command(name="setwelcome")
@commands.has_guild_permissions(manage_guild=True)
async def setwelcome(ctx, channel: discord.TextChannel):
    if not await require_enabled(ctx):
        return

    WELCOME_CHANNELS[str(ctx.guild.id)] = channel.id
    save_config()

    await ctx.send(
        embed=success(
            "Welcome",
            f"🎉 Kênh welcome: {channel.mention}",
        )
    )


@bot.command(name="setgoodbye")
@commands.has_guild_permissions(manage_guild=True)
async def setgoodbye(ctx, channel: discord.TextChannel):
    if not await require_enabled(ctx):
        return

    GOODBYE_CHANNELS[str(ctx.guild.id)] = channel.id
    save_config()

    await ctx.send(
        embed=success(
            "Goodbye",
            f"👋 Kênh goodbye: {channel.mention}",
        )
    )


@bot.command(name="log")
@commands.has_guild_permissions(manage_guild=True)
async def log_channel(ctx, channel: discord.TextChannel):
    if not await require_enabled(ctx):
        return

    SERVER_LOG_CHANNELS[str(ctx.guild.id)] = channel.id
    save_config()

    await ctx.send(
        embed=success(
            "Log",
            f"📋 Kênh log: {channel.mention}",
        )
    )


# ============================================================
# 🔊 VOICE
# ============================================================

@bot.command(name="move")
@commands.has_guild_permissions(move_members=True)
async def move_member(
    ctx,
    member: discord.Member,
    channel: discord.VoiceChannel,
):
    if not await require_enabled(ctx):
        return

    if member.voice is None:
        await ctx.send(embed=fail("Thành viên không ở voice."))
        return

    try:
        await member.move_to(
            channel,
            reason=f"Move bởi {ctx.author}",
        )
    except discord.Forbidden:
        await ctx.send(embed=fail("Bot không có quyền move."))
        return

    await ctx.send(
        embed=success(
            "Move",
            f"🚪 Đã chuyển {member.mention} → **{channel.name}**.",
        )
    )


@bot.command(name="deafen")
@commands.has_guild_permissions(deafen_members=True)
async def deafen(ctx, member: discord.Member):
    if not await require_enabled(ctx):
        return

    if member.voice is None:
        await ctx.send(embed=fail("Thành viên không ở voice."))
        return

    try:
        await member.edit(deafen=True)
    except discord.Forbidden:
        await ctx.send(embed=fail("Bot không có quyền deafen."))
        return

    await ctx.send(embed=success("Deafen", f"🔇 {member.mention} đã bị deafen."))


@bot.command(name="undeafen")
@commands.has_guild_permissions(deafen_members=True)
async def undeafen(ctx, member: discord.Member):
    if not await require_enabled(ctx):
        return

    try:
        await member.edit(deafen=False)
    except discord.Forbidden:
        await ctx.send(embed=fail("Bot không có quyền undeafen."))
        return

    await ctx.send(
        embed=success(
            "Undeafen",
            f"🔊 {member.mention} đã được undeafen.",
        )
    )


@bot.command(name="vc")
@commands.has_guild_permissions(manage_channels=True)
async def vc(ctx, *, name: str):
    if not await require_enabled(ctx):
        return

    try:
        channel = await ctx.guild.create_voice_channel(
            name=name[:100],
            reason=f"Tạo voice bởi {ctx.author}",
        )
    except discord.Forbidden:
        await ctx.send(embed=fail("Bot không có quyền tạo voice."))
        return

    await ctx.send(
        embed=success(
            "Tạo voice",
            f"🎙️ Đã tạo **{channel.name}**.",
        )
    )


# ============================================================
# 🧰 UTILITIES
# ============================================================

@bot.command(name="nick")
@commands.has_guild_permissions(manage_nicknames=True)
async def nick(ctx, member: discord.Member, *, nickname: str):
    if not await require_enabled(ctx):
        return

    error = hierarchy_error(member, ctx.author)

    if error:
        await ctx.send(embed=fail(error))
        return

    try:
        await member.edit(
            nick=nickname[:32],
            reason=f"Đổi nickname bởi {ctx.author}",
        )
    except discord.Forbidden:
        await ctx.send(embed=fail("Bot không thể đổi nickname."))
        return

    await ctx.send(
        embed=success(
            "Nickname",
            f"✏️ Đã đổi nickname của {member.mention}.",
        )
    )


@bot.command(name="resetnick")
@commands.has_guild_permissions(manage_nicknames=True)
async def resetnick(ctx, member: discord.Member):
    if not await require_enabled(ctx):
        return

    try:
        await member.edit(
            nick=None,
            reason=f"Reset nickname bởi {ctx.author}",
        )
    except discord.Forbidden:
        await ctx.send(embed=fail("Bot không thể reset nickname."))
        return

    await ctx.send(
        embed=success(
            "Reset nickname",
            f"🔄 Đã reset nickname của {member.mention}.",
        )
    )


@bot.command(name="guithu")
async def guithu(ctx, member: discord.Member, *, content: str):
    if not await require_enabled(ctx):
        return

    if len(content) > 1900:
        await ctx.send(embed=fail("Tin nhắn quá dài."))
        return

    try:
        await member.send(
            embed=make_embed(
                "📨 Tin nhắn từ server",
                content,
                discord.Color.blurple(),
                str(ctx.author.display_avatar.url),
            )
        )
    except discord.Forbidden:
        await ctx.send(embed=fail("Không thể gửi DM cho thành viên này."))
        return

    await ctx.send(
        embed=success(
            "Đã gửi tin",
            f"📨 Đã gửi DM cho {member.mention}.",
        )
    )


# ============================================================
# 💾 BACKUP / RESTORE
# ============================================================

def backup_path(guild_id):
    os.makedirs(BACKUP_DIR, exist_ok=True)
    return os.path.join(
        BACKUP_DIR,
        f"{guild_id}.json",
    )


@bot.command(name="backup")
@commands.has_guild_permissions(manage_guild=True)
async def backup(ctx):
    if not await require_enabled(ctx):
        return

    guild = ctx.guild

    data = {
        "guild_id": guild.id,
        "guild_name": guild.name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "roles": [
            {
                "name": role.name,
                "color": role.color.value,
                "hoist": role.hoist,
                "mentionable": role.mentionable,
            }
            for role in guild.roles
            if role.name != "@everyone"
        ],
        "categories": [
            {
                "name": category.name,
                "position": category.position,
            }
            for category in guild.categories
        ],
        "channels": [
            {
                "name": channel.name,
                "type": str(channel.type),
                "category": channel.category.name
                if channel.category
                else None,
                "topic": getattr(channel, "topic", None),
                "position": channel.position,
            }
            for channel in guild.channels
            if not isinstance(channel, discord.CategoryChannel)
        ],
    }

    path = backup_path(guild.id)
    write_json(path, data)

    await ctx.send(
        embed=success(
            "Backup hoàn tất",
            (
                f"💾 Đã lưu cấu trúc server.\n"
                f"📁 `{path}`\n"
                "🛡️ Backup không chứa token/password."
            ),
        )
    )


@bot.command(name="restore")
@commands.has_guild_permissions(manage_guild=True)
async def restore(ctx):
    if not await require_enabled(ctx):
        return

    path = backup_path(ctx.guild.id)

    if not os.path.exists(path):
        await ctx.send(
            embed=fail(
                "Không tìm thấy backup cho server này. "
                "Hãy chạy `nuked backup` trước."
            )
        )
        return

    data = read_json(path, {})

    existing_categories = {
        category.name.lower()
        for category in ctx.guild.categories
    }

    existing_channels = {
        channel.name.lower()
        for channel in ctx.guild.channels
    }

    created_categories = 0
    created_channels = 0

    # Restore chỉ tạo phần còn thiếu.
    # Không xóa channel/role hiện tại.
    for category_data in data.get("categories", []):
        name = str(category_data.get("name", "")).strip()

        if not name:
            continue

        if name.lower() in existing_categories:
            continue

        try:
            await ctx.guild.create_category(
                name=name[:100],
                reason=f"Restore bởi {ctx.author}",
            )
            created_categories += 1
        except discord.Forbidden:
            break

    categories_by_name = {
        category.name.lower(): category
        for category in ctx.guild.categories
    }

    for channel_data in data.get("channels", []):
        name = str(channel_data.get("name", "")).strip()

        if not name or name.lower() in existing_channels:
            continue

        category_name = channel_data.get("category")
        category = (
            categories_by_name.get(str(category_name).lower())
            if category_name
            else None
        )

        channel_type = channel_data.get("type", "text")

        try:
            if channel_type == "voice":
                await ctx.guild.create_voice_channel(
                    name=name[:100],
                    category=category,
                    reason=f"Restore bởi {ctx.author}",
                )
            else:
                await ctx.guild.create_text_channel(
                    name=name[:100],
                    topic=channel_data.get("topic"),
                    category=category,
                    reason=f"Restore bởi {ctx.author}",
                )

            created_channels += 1
        except discord.Forbidden:
            break

    await ctx.send(
        embed=success(
            "Restore hoàn tất",
            (
                f"♻️ Category tạo mới: **{created_categories}**\n"
                f"📚 Channel tạo mới: **{created_channels}**\n\n"
                "🛡️ Chế độ restore an toàn: **không xóa dữ liệu hiện có**."
            ),
        )
    )


# ============================================================
# 👑 OWNER
# ============================================================

@bot.command(name="owner")
@owner_only()
async def owner(ctx):
    owners = "\n".join(
        f"👑 <@{owner_id}> — `{owner_id}`"
        for owner_id in sorted(BOT_OWNERS)
    )

    await ctx.send(
        embed=owner_embed(
            "Khu vực Owner",
            (
                "**Quyền Owner bot:**\n"
                "• Quản lý Owner\n"
                "• Quản lý level/coin\n"
                "• Bật/tắt lệnh\n"
                "• Reload config\n\n"
                "**Danh sách Owner:**\n"
                f"{owners}"
            ),
        )
    )


@bot.command(name="addowner")
@owner_only()
async def addowner(ctx, member: discord.Member):
    if member.id in BOT_OWNERS:
        await ctx.send(embed=fail("Người này đã là Owner."))
        return

    BOT_OWNERS.add(member.id)
    save_config()

    await ctx.send(
        embed=owner_embed(
            "Thêm Owner",
            f"➕ Đã thêm {member.mention} vào Owner bot.",
        )
    )


@bot.command(name="deleteowner")
@owner_only()
async def deleteowner(ctx, member: discord.Member):
    if member.id not in BOT_OWNERS:
        await ctx.send(embed=fail("Người này không phải Owner."))
        return

    if len(BOT_OWNERS) <= 1:
        await ctx.send(
            embed=fail("Không thể xóa Owner cuối cùng.")
        )
        return

    BOT_OWNERS.remove(member.id)
    save_config()

    await ctx.send(
        embed=owner_embed(
            "Xóa Owner",
            f"➖ Đã xóa {member.mention} khỏi Owner bot.",
        )
    )


@bot.command(name="setlv")
@owner_only()
async def setlv(ctx, level: int, member: discord.Member):
    if level < 1 or level > MAX_LEVEL:
        await ctx.send(
            embed=fail(f"Level phải từ 1 đến {MAX_LEVEL}.")
        )
        return

    data = get_level_data(ctx.guild.id, member.id)
    data["level"] = level
    data["exp"] = 0
    save_levels()

    await ctx.send(
        embed=owner_embed(
            "Set Level",
            f"🎯 {member.mention} → **Level {level}**.",
        )
    )


@bot.command(name="setcoins")
@owner_only()
async def setcoins(ctx, member: discord.Member, amount: int):
    if amount < 0:
        await ctx.send(embed=fail("Coin không thể âm."))
        return

    data = get_coin_data(member.id)
    data["balance"] = amount
    save_coins()

    await ctx.send(
        embed=owner_embed(
            "Set Coin",
            f"💰 {member.mention} → **{amount:,} coin**.",
        )
    )


@bot.command(name="addcoins")
@owner_only()
async def addcoins(ctx, member: discord.Member, amount: int):
    if amount <= 0:
        await ctx.send(embed=fail("Số coin phải lớn hơn 0."))
        return

    add_coins(member.id, amount)

    await ctx.send(
        embed=owner_embed(
            "Add Coin",
            f"➕ {member.mention} + **{amount:,} coin**.",
        )
    )


@bot.command(name="removecoins")
@owner_only()
async def removecoins(ctx, member: discord.Member, amount: int):
    if amount <= 0:
        await ctx.send(embed=fail("Số coin phải lớn hơn 0."))
        return

    add_coins(member.id, -amount)

    await ctx.send(
        embed=owner_embed(
            "Remove Coin",
            f"➖ {member.mention} - **{amount:,} coin**.",
        )
    )


@bot.command(name="off")
@owner_only()
async def off(ctx, command_name: str):
    command_name = command_name.lower().replace(PREFIX.strip().lower(), "")

    # Không cho tắt help để Owner luôn có menu.
    if command_name == "help":
        await ctx.send(embed=fail("Không thể tắt lệnh help."))
        return

    if bot.get_command(command_name) is None:
        await ctx.send(embed=fail("Không tìm thấy lệnh này."))
        return

    DISABLED_COMMANDS.add(command_name)
    save_config()

    await ctx.send(
        embed=owner_embed(
            "Tắt lệnh",
            f"🚫 Đã tắt `{command_name}`.",
        )
    )


@bot.command(name="on")
@owner_only()
async def on_command(ctx, command_name: str):
    command_name = command_name.lower().replace(PREFIX.strip().lower(), "")

    DISABLED_COMMANDS.discard(command_name)
    save_config()

    await ctx.send(
        embed=owner_embed(
            "Bật lệnh",
            f"✅ Đã bật `{command_name}`.",
        )
    )


@bot.command(name="disabled")
@owner_only()
async def disabled(ctx):
    if not DISABLED_COMMANDS:
        text = "✨ Không có lệnh nào đang bị tắt."
    else:
        text = "\n".join(
            f"🚫 `{name}`"
            for name in sorted(DISABLED_COMMANDS)
        )

    await ctx.send(
        embed=owner_embed(
            "Lệnh đang tắt",
            text,
        )
    )


@bot.command(name="reload")
@owner_only()
async def reload_config(ctx):
    load_all_data()

    await ctx.send(
        embed=owner_embed(
            "Reload",
            "🔄 Đã tải lại `config.json`, `levels.json`, `coins.json`.",
        )
    )


# ============================================================
# 💣 DANGEROUS COMMAND NAMES — LOCKED
# ============================================================
# Giữ tên lệnh để menu/tài liệu không bị thiếu.
# Không thực hiện hành vi phá hoại hàng loạt.

LOCKED_DANGEROUS_COMMANDS = [
    "nuke",
    "massban",
    "masskick",
    "spam",
    "webhookspam",
    "deleteall",
]


def register_locked_command(command_name):
    async def locked(ctx, *args, **kwargs):
        await ctx.send(
            embed=make_embed(
                "🔒 Tính năng đã khóa",
                (
                    f"Lệnh `{PREFIX}{command_name}` vẫn tồn tại trong menu "
                    "để tham chiếu, nhưng chức năng phá hoại hàng loạt "
                    "đã bị vô hiệu hóa trong Safe Edition.\n\n"
                    "🛡️ Bot không thực hiện xóa hàng loạt, kick/ban hàng loạt "
                    "hoặc spam."
                ),
                discord.Color.red(),
            )
        )

    locked.__name__ = command_name
    bot.command(name=command_name)(locked)


for _locked_name in LOCKED_DANGEROUS_COMMANDS:
    register_locked_command(_locked_name)


# ============================================================
# 🎮 GAMES
# ============================================================

@bot.command(name="games")
async def games(ctx):
    if not await require_enabled(ctx):
        return

    embed = make_embed(
        "🎮 Game Center",
        "Một vài trò chơi đơn giản ngay trong Discord.",
        discord.Color.blurple(),
    )

    embed.add_field(
        name="🎲 nuked roll",
        value="Tung xúc xắc 1–100.",
        inline=False,
    )
    embed.add_field(
        name="🪙 nuked coinflip",
        value="Tung đồng xu.",
        inline=False,
    )

    await ctx.send(embed=embed)


@bot.command(name="roll")
async def roll(ctx):
    if not await require_enabled(ctx):
        return

    number = random.randint(1, 100)

    await ctx.send(
        embed=make_embed(
            "🎲 Roll",
            f"Bạn tung được **{number}**!",
            discord.Color.blurple(),
        )
    )


@bot.command(name="coinflip")
async def coinflip(ctx):
    if not await require_enabled(ctx):
        return

    result = random.choice(["🪙 MẶT NGỬA", "🪙 MẶT SẤP"])

    await ctx.send(
        embed=make_embed(
            "🪙 Coinflip",
            f"Kết quả: **{result}**",
            discord.Color.gold(),
        )
    )


# ============================================================
# ❗ ERROR HANDLER
# ============================================================

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return

    if isinstance(error, commands.CheckFailure):
        await ctx.send(
            embed=fail(
                "🔒 Bạn không có quyền sử dụng lệnh này."
            )
        )
        return

    if isinstance(error, commands.MissingPermissions):
        await ctx.send(
            embed=fail(
                "🛡️ Bạn không có quyền Discord cần thiết cho lệnh này."
            )
        )
        return

    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(
            embed=fail(
                f"Thiếu tham số: `{error.param.name}`.\n"
                f"💡 Dùng `nuked help` để xem cú pháp."
            )
        )
        return

    if isinstance(error, commands.BadArgument):
        await ctx.send(
            embed=fail(
                "Không đọc được tham số. Hãy kiểm tra mention, ID hoặc số."
            )
        )
        return

    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(
            embed=fail(
                f"⏳ Hãy chờ **{error.retry_after:.1f}s** rồi thử lại."
            )
        )
        return

    if isinstance(error, discord.Forbidden):
        await ctx.send(
            embed=fail(
                "Discord từ chối thao tác. Hãy kiểm tra quyền và role của bot."
            )
        )
        return

    print(
        f"[ERROR] {ctx.command}: "
        f"{type(error).__name__}: {error}"
    )

    await ctx.send(
        embed=fail(
            "Đã xảy ra lỗi không xác định. "
            "Hãy kiểm tra console để xem chi tiết."
        )
    )


# ============================================================
# ▶️ START
# ============================================================

if not TOKEN:
    raise RuntimeError(
        "❌ Chưa có TOKEN. "
        "Hãy đặt biến môi trường TOKEN trước khi chạy bot."
    )

bot.run(TOKEN)
'''

path = Path("/mnt/data/nuked_bot_ultimate_safe.py")
path.write_text(code, encoding="utf-8")

print(f"Đã tạo file: {path}")
print(f"Số dòng: {len(code.splitlines())}")
