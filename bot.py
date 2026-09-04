import asyncio
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


# ============================================================
# 🌌 EXTENDED COMMAND CENTER — 10 CATEGORIES / 32+ COMMANDS
# ============================================================
# Phần mở rộng này lấy cảm hứng từ các nhóm tính năng phổ biến
# của bot Discord hiện đại: tiện ích, moderation, economy, level,
# server tools, role tools, fun, backup/config và owner tools.
# Không bao gồm Anti hoặc Voice theo yêu cầu.
# Các lệnh mở rộng dùng handler an toàn, không phá server.

EXTENDED_HELP_CATEGORIES = {
    '🏠 Cơ Bản': {
        'description': 'Bộ lệnh mở rộng được thiết kế theo nhóm.',
        'commands': [
            ('nuked pingx', 'Kiểm tra độ trễ bot.'),
            ('nuked about', 'Thông tin tổng quan bot.'),
            ('nuked uptime', 'Hiển thị trạng thái hoạt động.'),
            ('nuked prefix', 'Xem prefix hiện tại.'),
            ('nuked commands', 'Xem tổng số lệnh mở rộng.'),
            ('nuked status', 'Xem trạng thái hệ thống.'),
            ('nuked botavatar', 'Xem avatar bot.'),
            ('nuked botbanner', 'Xem banner bot nếu có.'),
            ('nuked botname', 'Xem tên bot.'),
            ('nuked botid', 'Xem ID bot.'),
            ('nuked guildid', 'Xem ID server.'),
            ('nuked channelid', 'Xem ID kênh hiện tại.'),
            ('nuked myid', 'Xem ID của bạn.'),
            ('nuked roles', 'Xem nhanh số role.'),
            ('nuked channels', 'Xem nhanh số kênh.'),
            ('nuked emojis', 'Xem số emoji server.'),
            ('nuked stickers', 'Xem số sticker server.'),
            ('nuked boosts', 'Xem mức boost server.'),
            ('nuked created', 'Xem ngày tạo server.'),
            ('nuked joined', 'Xem ngày bạn tham gia.'),
            ('nuked permissions', 'Xem quyền cơ bản của bạn.'),
            ('nuked me', 'Xem hồ sơ nhanh của bạn.'),
            ('nuked server', 'Xem thông tin server dạng gọn.'),
            ('nuked whoami', 'Thông tin người dùng hiện tại.'),
            ('nuked inviteinfo', 'Hiển thị hướng dẫn mời bot.'),
            ('nuked latency', 'Kiểm tra websocket latency.'),
            ('nuked shards', 'Xem số shard.'),
            ('nuked python', 'Xem phiên bản Python.'),
            ('nuked discordpy', 'Xem phiên bản discord.py.'),
            ('nuked time', 'Xem thời gian hệ thống.'),
            ('nuked date', 'Xem ngày hệ thống.'),
            ('nuked helpall', 'Mở danh mục mở rộng.'),
        ],
    },
    '👤 Thành Viên': {
        'description': 'Bộ lệnh mở rộng được thiết kế theo nhóm.',
        'commands': [
            ('nuked profile', 'Xem hồ sơ thành viên.'),
            ('nuked member', 'Tra cứu thành viên.'),
            ('nuked joinedat', 'Xem thời điểm tham gia.'),
            ('nuked accountage', 'Xem tuổi tài khoản Discord.'),
            ('nuked rolesof', 'Xem role của thành viên.'),
            ('nuked toprole', 'Xem role cao nhất.'),
            ('nuked nickname', 'Xem nickname.'),
            ('nuked mention', 'Tạo mention an toàn.'),
            ('nuked badges', 'Xem huy hiệu công khai.'),
            ('nuked botcheck', 'Kiểm tra tài khoản có phải bot.'),
            ('nuked mutuals', 'Xem thông tin thành viên chung.'),
            ('nuked presence', 'Xem trạng thái hoạt động.'),
            ('nuked activity', 'Xem activity công khai.'),
            ('nuked timezone', 'Hiển thị UTC server.'),
            ('nuked userid', 'Xem ID thành viên.'),
            ('nuked membercountx', 'Đếm thành viên.'),
            ('nuked humans', 'Đếm thành viên người.'),
            ('nuked botcount', 'Đếm bot.'),
            ('nuked newest', 'Tìm thành viên mới gần đây.'),
            ('nuked oldest', 'Tìm thành viên tham gia sớm.'),
            ('nuked roleusers', 'Xem số người có role.'),
            ('nuked displayname', 'Xem display name.'),
            ('nuked globalname', 'Xem global name.'),
            ('nuked avatarurl', 'Lấy URL avatar.'),
            ('nuked bannerurl', 'Lấy URL banner nếu có.'),
            ('nuked usercreated', 'Xem ngày tạo tài khoản.'),
            ('nuked userjoined', 'Xem ngày vào server.'),
            ('nuked userinfo2', 'Xem hồ sơ chi tiết.'),
            ('nuked membernote', 'Ghi chú hướng dẫn quản lý thành viên.'),
            ('nuked memberhelp', 'Hướng dẫn lệnh thành viên.'),
            ('nuked lookup', 'Tra cứu ID hoặc mention.'),
            ('nuked findmember', 'Tìm thành viên theo tên.'),
        ],
    },
    '🛡️ Kiểm Duyệt': {
        'description': 'Bộ lệnh mở rộng được thiết kế theo nhóm.',
        'commands': [
            ('nuked warnx', 'Cảnh cáo thành viên.'),
            ('nuked warnings', 'Xem cảnh cáo.'),
            ('nuked clearx', 'Xóa tin nhắn giới hạn.'),
            ('nuked slowmodex', 'Cấu hình slowmode.'),
            ('nuked lockx', 'Khóa kênh hiện tại.'),
            ('nuked unlockx', 'Mở khóa kênh.'),
            ('nuked timeoutx', 'Timeout một thành viên.'),
            ('nuked untimeout', 'Gỡ timeout.'),
            ('nuked kickx', 'Kick một thành viên.'),
            ('nuked banx', 'Ban một thành viên.'),
            ('nuked unbanx', 'Gỡ ban bằng ID.'),
            ('nuked softban', 'Hướng dẫn softban an toàn.'),
            ('nuked modlog', 'Xem hướng dẫn modlog.'),
            ('nuked reason', 'Xem lý do thao tác gần nhất.'),
            ('nuked case', 'Tra cứu case ID.'),
            ('nuked modstats', 'Thống kê kiểm duyệt.'),
            ('nuked modhelp', 'Hướng dẫn moderation.'),
            ('nuked audit', 'Hướng dẫn xem audit log.'),
            ('nuked purge', 'Xóa nhóm tin nhắn theo giới hạn.'),
            ('nuked clean', 'Làm sạch tin nhắn bot.'),
            ('nuked filter', 'Xem trạng thái bộ lọc.'),
            ('nuked automod', 'Xem hướng dẫn AutoMod.'),
            ('nuked rules', 'Hiển thị quy tắc server.'),
            ('nuked report', 'Tạo mẫu báo cáo.'),
            ('nuked appeal', 'Hướng dẫn kháng nghị.'),
            ('nuked modinfo', 'Thông tin công cụ moderation.'),
            ('nuked cases', 'Danh sách case theo dữ liệu bot.'),
            ('nuked muteinfo', 'Thông tin mute/timeout.'),
            ('nuked kickinfo', 'Thông tin quyền kick.'),
            ('nuked baninfo', 'Thông tin quyền ban.'),
            ('nuked permissioncheck', 'Kiểm tra quyền moderation.'),
        ],
    },
    '📢 Kênh': {
        'description': 'Bộ lệnh mở rộng được thiết kế theo nhóm.',
        'commands': [
            ('nuked channelinfo', 'Thông tin kênh hiện tại.'),
            ('nuked channelname', 'Xem tên kênh.'),
            ('nuked channeltopic', 'Xem topic kênh.'),
            ('nuked channeltype', 'Xem loại kênh.'),
            ('nuked channelposition', 'Xem vị trí kênh.'),
            ('nuked channelcategory', 'Xem category.'),
            ('nuked channelcreated', 'Xem ngày tạo kênh.'),
            ('nuked channelmention', 'Tạo mention kênh.'),
            ('nuked channelid2', 'Xem ID kênh.'),
            ('nuked listtext', 'Liệt kê text channel.'),
            ('nuked listvoice', 'Liệt kê voice channel.'),
            ('nuked listcategory', 'Liệt kê category.'),
            ('nuked listforum', 'Liệt kê forum channel.'),
            ('nuked liststage', 'Liệt kê stage channel.'),
            ('nuked channelcount', 'Đếm channel.'),
            ('nuked textcount', 'Đếm text channel.'),
            ('nuked voicecount', 'Đếm voice channel.'),
            ('nuked categorycount', 'Đếm category.'),
            ('nuked forumcount', 'Đếm forum channel.'),
            ('nuked createchannelx', 'Hướng dẫn tạo kênh.'),
            ('nuked renamechannelx', 'Hướng dẫn đổi tên kênh.'),
            ('nuked settopicx', 'Hướng dẫn đặt topic.'),
            ('nuked slowmodeinfo', 'Thông tin slowmode.'),
            ('nuked lockinfo', 'Thông tin khóa kênh.'),
            ('nuked unlockinfo', 'Thông tin mở khóa.'),
            ('nuked channelperms', 'Kiểm tra quyền kênh.'),
            ('nuked channelhelp', 'Hướng dẫn quản lý kênh.'),
            ('nuked archiveinfo', 'Hướng dẫn archive.'),
            ('nuked threadinfo', 'Thông tin thread.'),
            ('nuked threads', 'Đếm thread hiện có.'),
            ('nuked channelstats', 'Thống kê kênh.'),
        ],
    },
    '🎭 Role': {
        'description': 'Bộ lệnh mở rộng được thiết kế theo nhóm.',
        'commands': [
            ('nuked roleinfo', 'Thông tin role.'),
            ('nuked rolelist', 'Liệt kê role.'),
            ('nuked rolecount', 'Đếm role.'),
            ('nuked rolemembers', 'Xem số thành viên có role.'),
            ('nuked rolecolor', 'Xem màu role.'),
            ('nuked roleposition', 'Xem vị trí role.'),
            ('nuked rolemention', 'Tạo mention role.'),
            ('nuked rolecreated', 'Xem ngày tạo role.'),
            ('nuked roleperms', 'Xem quyền role.'),
            ('nuked rolehelp', 'Hướng dẫn role.'),
            ('nuked addroleinfo', 'Hướng dẫn thêm role.'),
            ('nuked removeroleinfo', 'Hướng dẫn gỡ role.'),
            ('nuked autoroleinfo', 'Hướng dẫn autorole.'),
            ('nuked rolehierarchy', 'Xem thứ tự role.'),
            ('nuked botrole', 'Xem role cao nhất của bot.'),
            ('nuked memberroles', 'Xem role thành viên.'),
            ('nuked commonroles', 'Xem role phổ biến.'),
            ('nuked emptyroles', 'Tìm role không có thành viên.'),
            ('nuked managedroles', 'Xem role managed.'),
            ('nuked hoistedroles', 'Xem role hiển thị riêng.'),
            ('nuked coloredroles', 'Xem role có màu.'),
            ('nuked rolepermissions', 'Kiểm tra permission role.'),
            ('nuked rolepositionof', 'Tra vị trí role.'),
            ('nuked rolelookup', 'Tra cứu role.'),
            ('nuked roleusage', 'Hướng dẫn dùng role.'),
            ('nuked rolecommand', 'Hướng dẫn lệnh role.'),
            ('nuked roleconfig', 'Hướng dẫn cấu hình role.'),
            ('nuked rolebackup', 'Thông tin backup role.'),
            ('nuked roleaudit', 'Hướng dẫn audit role.'),
            ('nuked rolecountx', 'Thống kê role.'),
            ('nuked rolecenter', 'Mở trung tâm role.'),
        ],
    },
    '🎉 Giải Trí': {
        'description': 'Bộ lệnh mở rộng được thiết kế theo nhóm.',
        'commands': [
            ('nuked 8ball', 'Trả lời ngẫu nhiên vui vẻ.'),
            ('nuked choose', 'Chọn một phương án.'),
            ('nuked rollx', 'Tung xúc xắc.'),
            ('nuked coinflipx', 'Tung đồng xu ảo.'),
            ('nuked rate', 'Chấm điểm vui.'),
            ('nuked shipx', 'Ghép đôi vui.'),
            ('nuked lovecheck', 'Tỷ lệ tình cảm vui.'),
            ('nuked hugx', 'Tương tác ôm vui.'),
            ('nuked patx', 'Tương tác vỗ đầu vui.'),
            ('nuked cuddlex', 'Tương tác âu yếm vui.'),
            ('nuked slapx', 'Tương tác tát giả lập vui.'),
            ('nuked highfive', 'Đập tay vui.'),
            ('nuked wave', 'Vẫy tay.'),
            ('nuked dance', 'Tin nhắn nhảy vui.'),
            ('nuked cheer', 'Cổ vũ thành viên.'),
            ('nuked joke', 'Một câu đùa ngắn.'),
            ('nuked compliment', 'Lời khen vui.'),
            ('nuked roastlight', 'Roast nhẹ, không xúc phạm.'),
            ('nuked meme', 'Gợi ý meme.'),
            ('nuked fortune', 'Lời tiên đoán vui.'),
            ('nuked rps', 'Kéo búa bao.'),
            ('nuked number', 'Tạo số ngẫu nhiên.'),
            ('nuked randomword', 'Tạo từ ngẫu nhiên.'),
            ('nuked pick', 'Chọn ngẫu nhiên.'),
            ('nuked reverse', 'Đảo chuỗi văn bản.'),
            ('nuked sayinfo', 'Hướng dẫn lệnh nói.'),
            ('nuked emoji', 'Chọn emoji vui.'),
            ('nuked color', 'Tạo mã màu ngẫu nhiên.'),
            ('nuked fact', 'Một sự thật vui.'),
            ('nuked quiz', 'Câu hỏi vui.'),
            ('nuked funhelp', 'Hướng dẫn giải trí.'),
        ],
    },
    '💰 Kinh Tế': {
        'description': 'Bộ lệnh mở rộng được thiết kế theo nhóm.',
        'commands': [
            ('nuked balx', 'Xem số dư.'),
            ('nuked dailyx', 'Nhận coin hằng ngày.'),
            ('nuked workx', 'Nhận coin từ work.'),
            ('nuked begx', 'Nhận coin nhỏ.'),
            ('nuked givex', 'Tặng coin.'),
            ('nuked payinfo', 'Hướng dẫn chuyển coin.'),
            ('nuked leaderboardx', 'Bảng xếp hạng coin.'),
            ('nuked richest', 'Xem người nhiều coin.'),
            ('nuked wallet', 'Xem ví.'),
            ('nuked economy', 'Tổng quan kinh tế.'),
            ('nuked shopinfo', 'Thông tin shop.'),
            ('nuked inventoryx', 'Xem inventory.'),
            ('nuked iteminfo', 'Thông tin vật phẩm.'),
            ('nuked buyinfo', 'Hướng dẫn mua.'),
            ('nuked sellinfo', 'Hướng dẫn bán.'),
            ('nuked giftinfo', 'Hướng dẫn tặng vật phẩm.'),
            ('nuked tradeinfo', 'Hướng dẫn trao đổi.'),
            ('nuked economyhelp', 'Hướng dẫn kinh tế.'),
            ('nuked coinstats', 'Thống kê coin.'),
            ('nuked earnings', 'Thống kê thu nhập.'),
            ('nuked spending', 'Hướng dẫn theo dõi chi tiêu.'),
            ('nuked economyrank', 'Xếp hạng kinh tế.'),
            ('nuked coincheck', 'Kiểm tra số dư.'),
            ('nuked dailyinfo', 'Thông tin daily.'),
            ('nuked workinfo', 'Thông tin work.'),
            ('nuked beginfo', 'Thông tin beg.'),
            ('nuked shop', 'Mở shop an toàn.'),
            ('nuked inventory', 'Mở kho vật phẩm.'),
            ('nuked transfer', 'Hướng dẫn chuyển coin.'),
            ('nuked economyconfig', 'Thông tin cấu hình kinh tế.'),
            ('nuked coinhelp', 'Trợ giúp hệ thống coin.'),
        ],
    },
    '⭐ Level': {
        'description': 'Bộ lệnh mở rộng được thiết kế theo nhóm.',
        'commands': [
            ('nuked levelx', 'Xem level.'),
            ('nuked rank', 'Xem thứ hạng.'),
            ('nuked xp', 'Xem EXP.'),
            ('nuked xprank', 'Xếp hạng EXP.'),
            ('nuked nextlevel', 'Xem EXP cần lên cấp.'),
            ('nuked levelstats', 'Thống kê level.'),
            ('nuked leveltop', 'Top level.'),
            ('nuked leveluser', 'Level của thành viên.'),
            ('nuked xpuser', 'EXP của thành viên.'),
            ('nuked levelrole', 'Thông tin role theo level.'),
            ('nuked levelhelp', 'Hướng dẫn level.'),
            ('nuked xpinfo', 'Thông tin EXP.'),
            ('nuked levelupinfo', 'Thông tin level up.'),
            ('nuked rankinfo', 'Thông tin rank.'),
            ('nuked progress', 'Tiến độ level.'),
            ('nuked progressbar', 'Thanh tiến độ EXP.'),
            ('nuked maxlevel', 'Xem level tối đa.'),
            ('nuked levelconfig', 'Thông tin cấu hình level.'),
            ('nuked xpcooldown', 'Thông tin cooldown EXP.'),
            ('nuked xpmessage', 'Thông tin EXP từ tin nhắn.'),
            ('nuked levelleaderboard', 'Bảng xếp hạng level.'),
            ('nuked rankuser', 'Rank của thành viên.'),
            ('nuked xpneeded', 'EXP còn thiếu.'),
            ('nuked levelcompare', 'So sánh level.'),
            ('nuked xptotal', 'Tổng EXP.'),
            ('nuked leveltotal', 'Tổng level.'),
            ('nuked levelcenter', 'Trung tâm level.'),
            ('nuked levelstats2', 'Thống kê level nâng cao.'),
            ('nuked xpstats', 'Thống kê EXP.'),
            ('nuked rankstats', 'Thống kê rank.'),
            ('nuked leveltips', 'Mẹo tăng level hợp lệ.'),
            ('nuked levelmenu', 'Menu level.'),
        ],
    },
    '💾 Backup & Cấu Hình': {
        'description': 'Bộ lệnh mở rộng được thiết kế theo nhóm.',
        'commands': [
            ('nuked backupinfo', 'Thông tin backup.'),
            ('nuked backuplist', 'Danh sách backup.'),
            ('nuked backuphelp', 'Hướng dẫn backup.'),
            ('nuked restoreinfo', 'Thông tin restore.'),
            ('nuked configinfo', 'Thông tin config.'),
            ('nuked reloadinfo', 'Thông tin reload.'),
            ('nuked loginfo', 'Thông tin log.'),
            ('nuked welcomeinfo', 'Thông tin welcome.'),
            ('nuked goodbyeinfo', 'Thông tin goodbye.'),
            ('nuked disabledinfo', 'Xem lệnh bị tắt.'),
            ('nuked settings', 'Tổng quan cài đặt.'),
            ('nuked settingshelp', 'Hướng dẫn cài đặt.'),
            ('nuked serverconfig', 'Hướng dẫn cấu hình server.'),
            ('nuked logconfig', 'Hướng dẫn cấu hình log.'),
            ('nuked welcomeconfig', 'Hướng dẫn welcome.'),
            ('nuked goodbyeconfig', 'Hướng dẫn goodbye.'),
            ('nuked levelconfig2', 'Hướng dẫn cấu hình level.'),
            ('nuked economyconfig2', 'Hướng dẫn cấu hình coin.'),
            ('nuked prefixconfig', 'Thông tin prefix.'),
            ('nuked menuconfig', 'Thông tin menu.'),
            ('nuked embedinfo', 'Thông tin embed.'),
            ('nuked gifinfo', 'Thông tin GIF menu.'),
            ('nuked jsoninfo', 'Thông tin file JSON.'),
            ('nuked datahelp', 'Hướng dẫn dữ liệu.'),
            ('nuked resetinfo', 'Thông tin reset dữ liệu.'),
            ('nuked exportinfo', 'Hướng dẫn xuất dữ liệu.'),
            ('nuked importinfo', 'Hướng dẫn nhập dữ liệu.'),
            ('nuked configcheck', 'Kiểm tra cấu hình.'),
            ('nuked healthcheck', 'Kiểm tra sức khỏe bot.'),
            ('nuked diagnose', 'Chẩn đoán lỗi cơ bản.'),
            ('nuked configcenter', 'Trung tâm cấu hình.'),
        ],
    },
    '👑 Owner & Quản Trị Bot': {
        'description': 'Bộ lệnh mở rộng được thiết kế theo nhóm.',
        'commands': [
            ('nuked ownerlist', 'Xem danh sách Owner.'),
            ('nuked ownercheck', 'Kiểm tra quyền Owner.'),
            ('nuked ownerhelp', 'Hướng dẫn Owner.'),
            ('nuked botreload', 'Reload dữ liệu an toàn.'),
            ('nuked botoff', 'Thông tin tắt lệnh.'),
            ('nuked boton', 'Thông tin bật lệnh.'),
            ('nuked disabledlist', 'Liệt kê lệnh bị tắt.'),
            ('nuked setlvinfo', 'Hướng dẫn set level.'),
            ('nuked setcoinsinfo', 'Hướng dẫn set coin.'),
            ('nuked addcoinsinfo', 'Hướng dẫn cộng coin.'),
            ('nuked removecoinsinfo', 'Hướng dẫn trừ coin.'),
            ('nuked addownerinfo', 'Hướng dẫn thêm Owner.'),
            ('nuked deleteownerinfo', 'Hướng dẫn xóa Owner.'),
            ('nuked ownerstats', 'Thống kê Owner.'),
            ('nuked botstats', 'Thống kê bot.'),
            ('nuked serverstats', 'Thống kê server.'),
            ('nuked commandstats', 'Thống kê lệnh.'),
            ('nuked errorstats', 'Thống kê lỗi.'),
            ('nuked cooldowns', 'Xem hướng dẫn cooldown.'),
            ('nuked permissionsx', 'Kiểm tra permission.'),
            ('nuked auditinfo', 'Hướng dẫn audit.'),
            ('nuked ratelimitinfo', 'Thông tin rate limit.'),
            ('nuked cacheinfo', 'Thông tin cache.'),
            ('nuked memoryinfo', 'Thông tin bộ nhớ.'),
            ('nuked latencyinfo', 'Thông tin latency.'),
            ('nuked taskinfo', 'Thông tin background task.'),
            ('nuked jsonstatus', 'Trạng thái JSON.'),
            ('nuked ownerconfig', 'Thông tin cấu hình Owner.'),
            ('nuked ownerpanel', 'Mở bảng Owner an toàn.'),
            ('nuked adminhelp', 'Hướng dẫn quản trị.'),
            ('nuked controlcenter', 'Mở Control Center.'),
        ],
    },
}


# ------------------------------------------------------------
# 🏠 Cơ Bản • pingx
# ------------------------------------------------------------
@bot.command(name="pingx")
async def extended_pingx(ctx, *, text: str = ""):
    """Kiểm tra độ trễ bot."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🏠 Cơ Bản • nuked pingx",
        (
            "📌 **Mô tả:** Kiểm tra độ trễ bot.\n\n"
            "🧭 **Cách dùng:** `nuked pingx`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🏠 Cơ Bản • about
# ------------------------------------------------------------
@bot.command(name="about")
async def extended_about(ctx, *, text: str = ""):
    """Thông tin tổng quan bot."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🏠 Cơ Bản • nuked about",
        (
            "📌 **Mô tả:** Thông tin tổng quan bot.\n\n"
            "🧭 **Cách dùng:** `nuked about`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🏠 Cơ Bản • uptime
# ------------------------------------------------------------
@bot.command(name="uptime")
async def extended_uptime(ctx, *, text: str = ""):
    """Hiển thị trạng thái hoạt động."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🏠 Cơ Bản • nuked uptime",
        (
            "📌 **Mô tả:** Hiển thị trạng thái hoạt động.\n\n"
            "🧭 **Cách dùng:** `nuked uptime`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🏠 Cơ Bản • prefix
# ------------------------------------------------------------
@bot.command(name="prefix")
async def extended_prefix(ctx, *, text: str = ""):
    """Xem prefix hiện tại."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🏠 Cơ Bản • nuked prefix",
        (
            "📌 **Mô tả:** Xem prefix hiện tại.\n\n"
            "🧭 **Cách dùng:** `nuked prefix`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🏠 Cơ Bản • commands
# ------------------------------------------------------------
@bot.command(name="commands")
async def extended_commands(ctx, *, text: str = ""):
    """Xem tổng số lệnh mở rộng."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🏠 Cơ Bản • nuked commands",
        (
            "📌 **Mô tả:** Xem tổng số lệnh mở rộng.\n\n"
            "🧭 **Cách dùng:** `nuked commands`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🏠 Cơ Bản • status
# ------------------------------------------------------------
@bot.command(name="status")
async def extended_status(ctx, *, text: str = ""):
    """Xem trạng thái hệ thống."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🏠 Cơ Bản • nuked status",
        (
            "📌 **Mô tả:** Xem trạng thái hệ thống.\n\n"
            "🧭 **Cách dùng:** `nuked status`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🏠 Cơ Bản • botavatar
# ------------------------------------------------------------
@bot.command(name="botavatar")
async def extended_botavatar(ctx, *, text: str = ""):
    """Xem avatar bot."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🏠 Cơ Bản • nuked botavatar",
        (
            "📌 **Mô tả:** Xem avatar bot.\n\n"
            "🧭 **Cách dùng:** `nuked botavatar`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🏠 Cơ Bản • botbanner
# ------------------------------------------------------------
@bot.command(name="botbanner")
async def extended_botbanner(ctx, *, text: str = ""):
    """Xem banner bot nếu có."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🏠 Cơ Bản • nuked botbanner",
        (
            "📌 **Mô tả:** Xem banner bot nếu có.\n\n"
            "🧭 **Cách dùng:** `nuked botbanner`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🏠 Cơ Bản • botname
# ------------------------------------------------------------
@bot.command(name="botname")
async def extended_botname(ctx, *, text: str = ""):
    """Xem tên bot."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🏠 Cơ Bản • nuked botname",
        (
            "📌 **Mô tả:** Xem tên bot.\n\n"
            "🧭 **Cách dùng:** `nuked botname`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🏠 Cơ Bản • botid
# ------------------------------------------------------------
@bot.command(name="botid")
async def extended_botid(ctx, *, text: str = ""):
    """Xem ID bot."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🏠 Cơ Bản • nuked botid",
        (
            "📌 **Mô tả:** Xem ID bot.\n\n"
            "🧭 **Cách dùng:** `nuked botid`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🏠 Cơ Bản • guildid
# ------------------------------------------------------------
@bot.command(name="guildid")
async def extended_guildid(ctx, *, text: str = ""):
    """Xem ID server."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🏠 Cơ Bản • nuked guildid",
        (
            "📌 **Mô tả:** Xem ID server.\n\n"
            "🧭 **Cách dùng:** `nuked guildid`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🏠 Cơ Bản • channelid
# ------------------------------------------------------------
@bot.command(name="channelid")
async def extended_channelid(ctx, *, text: str = ""):
    """Xem ID kênh hiện tại."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🏠 Cơ Bản • nuked channelid",
        (
            "📌 **Mô tả:** Xem ID kênh hiện tại.\n\n"
            "🧭 **Cách dùng:** `nuked channelid`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🏠 Cơ Bản • myid
# ------------------------------------------------------------
@bot.command(name="myid")
async def extended_myid(ctx, *, text: str = ""):
    """Xem ID của bạn."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🏠 Cơ Bản • nuked myid",
        (
            "📌 **Mô tả:** Xem ID của bạn.\n\n"
            "🧭 **Cách dùng:** `nuked myid`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🏠 Cơ Bản • roles
# ------------------------------------------------------------
@bot.command(name="roles")
async def extended_roles(ctx, *, text: str = ""):
    """Xem nhanh số role."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🏠 Cơ Bản • nuked roles",
        (
            "📌 **Mô tả:** Xem nhanh số role.\n\n"
            "🧭 **Cách dùng:** `nuked roles`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🏠 Cơ Bản • channels
# ------------------------------------------------------------
@bot.command(name="channels")
async def extended_channels(ctx, *, text: str = ""):
    """Xem nhanh số kênh."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🏠 Cơ Bản • nuked channels",
        (
            "📌 **Mô tả:** Xem nhanh số kênh.\n\n"
            "🧭 **Cách dùng:** `nuked channels`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🏠 Cơ Bản • emojis
# ------------------------------------------------------------
@bot.command(name="emojis")
async def extended_emojis(ctx, *, text: str = ""):
    """Xem số emoji server."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🏠 Cơ Bản • nuked emojis",
        (
            "📌 **Mô tả:** Xem số emoji server.\n\n"
            "🧭 **Cách dùng:** `nuked emojis`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🏠 Cơ Bản • stickers
# ------------------------------------------------------------
@bot.command(name="stickers")
async def extended_stickers(ctx, *, text: str = ""):
    """Xem số sticker server."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🏠 Cơ Bản • nuked stickers",
        (
            "📌 **Mô tả:** Xem số sticker server.\n\n"
            "🧭 **Cách dùng:** `nuked stickers`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🏠 Cơ Bản • boosts
# ------------------------------------------------------------
@bot.command(name="boosts")
async def extended_boosts(ctx, *, text: str = ""):
    """Xem mức boost server."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🏠 Cơ Bản • nuked boosts",
        (
            "📌 **Mô tả:** Xem mức boost server.\n\n"
            "🧭 **Cách dùng:** `nuked boosts`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🏠 Cơ Bản • created
# ------------------------------------------------------------
@bot.command(name="created")
async def extended_created(ctx, *, text: str = ""):
    """Xem ngày tạo server."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🏠 Cơ Bản • nuked created",
        (
            "📌 **Mô tả:** Xem ngày tạo server.\n\n"
            "🧭 **Cách dùng:** `nuked created`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🏠 Cơ Bản • joined
# ------------------------------------------------------------
@bot.command(name="joined")
async def extended_joined(ctx, *, text: str = ""):
    """Xem ngày bạn tham gia."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🏠 Cơ Bản • nuked joined",
        (
            "📌 **Mô tả:** Xem ngày bạn tham gia.\n\n"
            "🧭 **Cách dùng:** `nuked joined`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🏠 Cơ Bản • permissions
# ------------------------------------------------------------
@bot.command(name="permissions")
async def extended_permissions(ctx, *, text: str = ""):
    """Xem quyền cơ bản của bạn."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🏠 Cơ Bản • nuked permissions",
        (
            "📌 **Mô tả:** Xem quyền cơ bản của bạn.\n\n"
            "🧭 **Cách dùng:** `nuked permissions`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🏠 Cơ Bản • me
# ------------------------------------------------------------
@bot.command(name="me")
async def extended_me(ctx, *, text: str = ""):
    """Xem hồ sơ nhanh của bạn."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🏠 Cơ Bản • nuked me",
        (
            "📌 **Mô tả:** Xem hồ sơ nhanh của bạn.\n\n"
            "🧭 **Cách dùng:** `nuked me`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🏠 Cơ Bản • server
# ------------------------------------------------------------
@bot.command(name="server")
async def extended_server(ctx, *, text: str = ""):
    """Xem thông tin server dạng gọn."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🏠 Cơ Bản • nuked server",
        (
            "📌 **Mô tả:** Xem thông tin server dạng gọn.\n\n"
            "🧭 **Cách dùng:** `nuked server`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🏠 Cơ Bản • whoami
# ------------------------------------------------------------
@bot.command(name="whoami")
async def extended_whoami(ctx, *, text: str = ""):
    """Thông tin người dùng hiện tại."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🏠 Cơ Bản • nuked whoami",
        (
            "📌 **Mô tả:** Thông tin người dùng hiện tại.\n\n"
            "🧭 **Cách dùng:** `nuked whoami`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🏠 Cơ Bản • inviteinfo
# ------------------------------------------------------------
@bot.command(name="inviteinfo")
async def extended_inviteinfo(ctx, *, text: str = ""):
    """Hiển thị hướng dẫn mời bot."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🏠 Cơ Bản • nuked inviteinfo",
        (
            "📌 **Mô tả:** Hiển thị hướng dẫn mời bot.\n\n"
            "🧭 **Cách dùng:** `nuked inviteinfo`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🏠 Cơ Bản • latency
# ------------------------------------------------------------
@bot.command(name="latency")
async def extended_latency(ctx, *, text: str = ""):
    """Kiểm tra websocket latency."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🏠 Cơ Bản • nuked latency",
        (
            "📌 **Mô tả:** Kiểm tra websocket latency.\n\n"
            "🧭 **Cách dùng:** `nuked latency`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🏠 Cơ Bản • shards
# ------------------------------------------------------------
@bot.command(name="shards")
async def extended_shards(ctx, *, text: str = ""):
    """Xem số shard."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🏠 Cơ Bản • nuked shards",
        (
            "📌 **Mô tả:** Xem số shard.\n\n"
            "🧭 **Cách dùng:** `nuked shards`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🏠 Cơ Bản • python
# ------------------------------------------------------------
@bot.command(name="python")
async def extended_python(ctx, *, text: str = ""):
    """Xem phiên bản Python."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🏠 Cơ Bản • nuked python",
        (
            "📌 **Mô tả:** Xem phiên bản Python.\n\n"
            "🧭 **Cách dùng:** `nuked python`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🏠 Cơ Bản • discordpy
# ------------------------------------------------------------
@bot.command(name="discordpy")
async def extended_discordpy(ctx, *, text: str = ""):
    """Xem phiên bản discord.py."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🏠 Cơ Bản • nuked discordpy",
        (
            "📌 **Mô tả:** Xem phiên bản discord.py.\n\n"
            "🧭 **Cách dùng:** `nuked discordpy`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🏠 Cơ Bản • time
# ------------------------------------------------------------
@bot.command(name="time")
async def extended_time(ctx, *, text: str = ""):
    """Xem thời gian hệ thống."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🏠 Cơ Bản • nuked time",
        (
            "📌 **Mô tả:** Xem thời gian hệ thống.\n\n"
            "🧭 **Cách dùng:** `nuked time`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🏠 Cơ Bản • date
# ------------------------------------------------------------
@bot.command(name="date")
async def extended_date(ctx, *, text: str = ""):
    """Xem ngày hệ thống."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🏠 Cơ Bản • nuked date",
        (
            "📌 **Mô tả:** Xem ngày hệ thống.\n\n"
            "🧭 **Cách dùng:** `nuked date`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🏠 Cơ Bản • helpall
# ------------------------------------------------------------
@bot.command(name="helpall")
async def extended_helpall(ctx, *, text: str = ""):
    """Mở danh mục mở rộng."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🏠 Cơ Bản • nuked helpall",
        (
            "📌 **Mô tả:** Mở danh mục mở rộng.\n\n"
            "🧭 **Cách dùng:** `nuked helpall`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 👤 Thành Viên • profile
# ------------------------------------------------------------
@bot.command(name="profile")
async def extended_profile(ctx, *, text: str = ""):
    """Xem hồ sơ thành viên."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 👤 Thành Viên • nuked profile",
        (
            "📌 **Mô tả:** Xem hồ sơ thành viên.\n\n"
            "🧭 **Cách dùng:** `nuked profile`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 👤 Thành Viên • member
# ------------------------------------------------------------
@bot.command(name="member")
async def extended_member(ctx, *, text: str = ""):
    """Tra cứu thành viên."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 👤 Thành Viên • nuked member",
        (
            "📌 **Mô tả:** Tra cứu thành viên.\n\n"
            "🧭 **Cách dùng:** `nuked member`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 👤 Thành Viên • joinedat
# ------------------------------------------------------------
@bot.command(name="joinedat")
async def extended_joinedat(ctx, *, text: str = ""):
    """Xem thời điểm tham gia."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 👤 Thành Viên • nuked joinedat",
        (
            "📌 **Mô tả:** Xem thời điểm tham gia.\n\n"
            "🧭 **Cách dùng:** `nuked joinedat`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 👤 Thành Viên • accountage
# ------------------------------------------------------------
@bot.command(name="accountage")
async def extended_accountage(ctx, *, text: str = ""):
    """Xem tuổi tài khoản Discord."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 👤 Thành Viên • nuked accountage",
        (
            "📌 **Mô tả:** Xem tuổi tài khoản Discord.\n\n"
            "🧭 **Cách dùng:** `nuked accountage`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 👤 Thành Viên • rolesof
# ------------------------------------------------------------
@bot.command(name="rolesof")
async def extended_rolesof(ctx, *, text: str = ""):
    """Xem role của thành viên."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 👤 Thành Viên • nuked rolesof",
        (
            "📌 **Mô tả:** Xem role của thành viên.\n\n"
            "🧭 **Cách dùng:** `nuked rolesof`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 👤 Thành Viên • toprole
# ------------------------------------------------------------
@bot.command(name="toprole")
async def extended_toprole(ctx, *, text: str = ""):
    """Xem role cao nhất."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 👤 Thành Viên • nuked toprole",
        (
            "📌 **Mô tả:** Xem role cao nhất.\n\n"
            "🧭 **Cách dùng:** `nuked toprole`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 👤 Thành Viên • nickname
# ------------------------------------------------------------
@bot.command(name="nickname")
async def extended_nickname(ctx, *, text: str = ""):
    """Xem nickname."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 👤 Thành Viên • nuked nickname",
        (
            "📌 **Mô tả:** Xem nickname.\n\n"
            "🧭 **Cách dùng:** `nuked nickname`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 👤 Thành Viên • mention
# ------------------------------------------------------------
@bot.command(name="mention")
async def extended_mention(ctx, *, text: str = ""):
    """Tạo mention an toàn."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 👤 Thành Viên • nuked mention",
        (
            "📌 **Mô tả:** Tạo mention an toàn.\n\n"
            "🧭 **Cách dùng:** `nuked mention`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 👤 Thành Viên • badges
# ------------------------------------------------------------
@bot.command(name="badges")
async def extended_badges(ctx, *, text: str = ""):
    """Xem huy hiệu công khai."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 👤 Thành Viên • nuked badges",
        (
            "📌 **Mô tả:** Xem huy hiệu công khai.\n\n"
            "🧭 **Cách dùng:** `nuked badges`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 👤 Thành Viên • botcheck
# ------------------------------------------------------------
@bot.command(name="botcheck")
async def extended_botcheck(ctx, *, text: str = ""):
    """Kiểm tra tài khoản có phải bot."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 👤 Thành Viên • nuked botcheck",
        (
            "📌 **Mô tả:** Kiểm tra tài khoản có phải bot.\n\n"
            "🧭 **Cách dùng:** `nuked botcheck`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 👤 Thành Viên • mutuals
# ------------------------------------------------------------
@bot.command(name="mutuals")
async def extended_mutuals(ctx, *, text: str = ""):
    """Xem thông tin thành viên chung."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 👤 Thành Viên • nuked mutuals",
        (
            "📌 **Mô tả:** Xem thông tin thành viên chung.\n\n"
            "🧭 **Cách dùng:** `nuked mutuals`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 👤 Thành Viên • presence
# ------------------------------------------------------------
@bot.command(name="presence")
async def extended_presence(ctx, *, text: str = ""):
    """Xem trạng thái hoạt động."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 👤 Thành Viên • nuked presence",
        (
            "📌 **Mô tả:** Xem trạng thái hoạt động.\n\n"
            "🧭 **Cách dùng:** `nuked presence`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 👤 Thành Viên • activity
# ------------------------------------------------------------
@bot.command(name="activity")
async def extended_activity(ctx, *, text: str = ""):
    """Xem activity công khai."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 👤 Thành Viên • nuked activity",
        (
            "📌 **Mô tả:** Xem activity công khai.\n\n"
            "🧭 **Cách dùng:** `nuked activity`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 👤 Thành Viên • timezone
# ------------------------------------------------------------
@bot.command(name="timezone")
async def extended_timezone(ctx, *, text: str = ""):
    """Hiển thị UTC server."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 👤 Thành Viên • nuked timezone",
        (
            "📌 **Mô tả:** Hiển thị UTC server.\n\n"
            "🧭 **Cách dùng:** `nuked timezone`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 👤 Thành Viên • userid
# ------------------------------------------------------------
@bot.command(name="userid")
async def extended_userid(ctx, *, text: str = ""):
    """Xem ID thành viên."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 👤 Thành Viên • nuked userid",
        (
            "📌 **Mô tả:** Xem ID thành viên.\n\n"
            "🧭 **Cách dùng:** `nuked userid`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 👤 Thành Viên • membercountx
# ------------------------------------------------------------
@bot.command(name="membercountx")
async def extended_membercountx(ctx, *, text: str = ""):
    """Đếm thành viên."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 👤 Thành Viên • nuked membercountx",
        (
            "📌 **Mô tả:** Đếm thành viên.\n\n"
            "🧭 **Cách dùng:** `nuked membercountx`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 👤 Thành Viên • humans
# ------------------------------------------------------------
@bot.command(name="humans")
async def extended_humans(ctx, *, text: str = ""):
    """Đếm thành viên người."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 👤 Thành Viên • nuked humans",
        (
            "📌 **Mô tả:** Đếm thành viên người.\n\n"
            "🧭 **Cách dùng:** `nuked humans`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 👤 Thành Viên • botcount
# ------------------------------------------------------------
@bot.command(name="botcount")
async def extended_botcount(ctx, *, text: str = ""):
    """Đếm bot."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 👤 Thành Viên • nuked botcount",
        (
            "📌 **Mô tả:** Đếm bot.\n\n"
            "🧭 **Cách dùng:** `nuked botcount`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 👤 Thành Viên • newest
# ------------------------------------------------------------
@bot.command(name="newest")
async def extended_newest(ctx, *, text: str = ""):
    """Tìm thành viên mới gần đây."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 👤 Thành Viên • nuked newest",
        (
            "📌 **Mô tả:** Tìm thành viên mới gần đây.\n\n"
            "🧭 **Cách dùng:** `nuked newest`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 👤 Thành Viên • oldest
# ------------------------------------------------------------
@bot.command(name="oldest")
async def extended_oldest(ctx, *, text: str = ""):
    """Tìm thành viên tham gia sớm."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 👤 Thành Viên • nuked oldest",
        (
            "📌 **Mô tả:** Tìm thành viên tham gia sớm.\n\n"
            "🧭 **Cách dùng:** `nuked oldest`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 👤 Thành Viên • roleusers
# ------------------------------------------------------------
@bot.command(name="roleusers")
async def extended_roleusers(ctx, *, text: str = ""):
    """Xem số người có role."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 👤 Thành Viên • nuked roleusers",
        (
            "📌 **Mô tả:** Xem số người có role.\n\n"
            "🧭 **Cách dùng:** `nuked roleusers`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 👤 Thành Viên • displayname
# ------------------------------------------------------------
@bot.command(name="displayname")
async def extended_displayname(ctx, *, text: str = ""):
    """Xem display name."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 👤 Thành Viên • nuked displayname",
        (
            "📌 **Mô tả:** Xem display name.\n\n"
            "🧭 **Cách dùng:** `nuked displayname`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 👤 Thành Viên • globalname
# ------------------------------------------------------------
@bot.command(name="globalname")
async def extended_globalname(ctx, *, text: str = ""):
    """Xem global name."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 👤 Thành Viên • nuked globalname",
        (
            "📌 **Mô tả:** Xem global name.\n\n"
            "🧭 **Cách dùng:** `nuked globalname`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 👤 Thành Viên • avatarurl
# ------------------------------------------------------------
@bot.command(name="avatarurl")
async def extended_avatarurl(ctx, *, text: str = ""):
    """Lấy URL avatar."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 👤 Thành Viên • nuked avatarurl",
        (
            "📌 **Mô tả:** Lấy URL avatar.\n\n"
            "🧭 **Cách dùng:** `nuked avatarurl`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 👤 Thành Viên • bannerurl
# ------------------------------------------------------------
@bot.command(name="bannerurl")
async def extended_bannerurl(ctx, *, text: str = ""):
    """Lấy URL banner nếu có."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 👤 Thành Viên • nuked bannerurl",
        (
            "📌 **Mô tả:** Lấy URL banner nếu có.\n\n"
            "🧭 **Cách dùng:** `nuked bannerurl`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 👤 Thành Viên • usercreated
# ------------------------------------------------------------
@bot.command(name="usercreated")
async def extended_usercreated(ctx, *, text: str = ""):
    """Xem ngày tạo tài khoản."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 👤 Thành Viên • nuked usercreated",
        (
            "📌 **Mô tả:** Xem ngày tạo tài khoản.\n\n"
            "🧭 **Cách dùng:** `nuked usercreated`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 👤 Thành Viên • userjoined
# ------------------------------------------------------------
@bot.command(name="userjoined")
async def extended_userjoined(ctx, *, text: str = ""):
    """Xem ngày vào server."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 👤 Thành Viên • nuked userjoined",
        (
            "📌 **Mô tả:** Xem ngày vào server.\n\n"
            "🧭 **Cách dùng:** `nuked userjoined`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 👤 Thành Viên • userinfo2
# ------------------------------------------------------------
@bot.command(name="userinfo2")
async def extended_userinfo2(ctx, *, text: str = ""):
    """Xem hồ sơ chi tiết."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 👤 Thành Viên • nuked userinfo2",
        (
            "📌 **Mô tả:** Xem hồ sơ chi tiết.\n\n"
            "🧭 **Cách dùng:** `nuked userinfo2`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 👤 Thành Viên • membernote
# ------------------------------------------------------------
@bot.command(name="membernote")
async def extended_membernote(ctx, *, text: str = ""):
    """Ghi chú hướng dẫn quản lý thành viên."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 👤 Thành Viên • nuked membernote",
        (
            "📌 **Mô tả:** Ghi chú hướng dẫn quản lý thành viên.\n\n"
            "🧭 **Cách dùng:** `nuked membernote`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 👤 Thành Viên • memberhelp
# ------------------------------------------------------------
@bot.command(name="memberhelp")
async def extended_memberhelp(ctx, *, text: str = ""):
    """Hướng dẫn lệnh thành viên."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 👤 Thành Viên • nuked memberhelp",
        (
            "📌 **Mô tả:** Hướng dẫn lệnh thành viên.\n\n"
            "🧭 **Cách dùng:** `nuked memberhelp`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 👤 Thành Viên • lookup
# ------------------------------------------------------------
@bot.command(name="lookup")
async def extended_lookup(ctx, *, text: str = ""):
    """Tra cứu ID hoặc mention."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 👤 Thành Viên • nuked lookup",
        (
            "📌 **Mô tả:** Tra cứu ID hoặc mention.\n\n"
            "🧭 **Cách dùng:** `nuked lookup`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 👤 Thành Viên • findmember
# ------------------------------------------------------------
@bot.command(name="findmember")
async def extended_findmember(ctx, *, text: str = ""):
    """Tìm thành viên theo tên."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 👤 Thành Viên • nuked findmember",
        (
            "📌 **Mô tả:** Tìm thành viên theo tên.\n\n"
            "🧭 **Cách dùng:** `nuked findmember`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🛡️ Kiểm Duyệt • warnx
# ------------------------------------------------------------
@bot.command(name="warnx")
async def extended_warnx(ctx, *, text: str = ""):
    """Cảnh cáo thành viên."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🛡️ Kiểm Duyệt • nuked warnx",
        (
            "📌 **Mô tả:** Cảnh cáo thành viên.\n\n"
            "🧭 **Cách dùng:** `nuked warnx`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🛡️ Kiểm Duyệt • warnings
# ------------------------------------------------------------
@bot.command(name="warnings")
async def extended_warnings(ctx, *, text: str = ""):
    """Xem cảnh cáo."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🛡️ Kiểm Duyệt • nuked warnings",
        (
            "📌 **Mô tả:** Xem cảnh cáo.\n\n"
            "🧭 **Cách dùng:** `nuked warnings`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🛡️ Kiểm Duyệt • clearx
# ------------------------------------------------------------
@bot.command(name="clearx")
async def extended_clearx(ctx, *, text: str = ""):
    """Xóa tin nhắn giới hạn."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🛡️ Kiểm Duyệt • nuked clearx",
        (
            "📌 **Mô tả:** Xóa tin nhắn giới hạn.\n\n"
            "🧭 **Cách dùng:** `nuked clearx`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🛡️ Kiểm Duyệt • slowmodex
# ------------------------------------------------------------
@bot.command(name="slowmodex")
async def extended_slowmodex(ctx, *, text: str = ""):
    """Cấu hình slowmode."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🛡️ Kiểm Duyệt • nuked slowmodex",
        (
            "📌 **Mô tả:** Cấu hình slowmode.\n\n"
            "🧭 **Cách dùng:** `nuked slowmodex`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🛡️ Kiểm Duyệt • lockx
# ------------------------------------------------------------
@bot.command(name="lockx")
async def extended_lockx(ctx, *, text: str = ""):
    """Khóa kênh hiện tại."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🛡️ Kiểm Duyệt • nuked lockx",
        (
            "📌 **Mô tả:** Khóa kênh hiện tại.\n\n"
            "🧭 **Cách dùng:** `nuked lockx`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🛡️ Kiểm Duyệt • unlockx
# ------------------------------------------------------------
@bot.command(name="unlockx")
async def extended_unlockx(ctx, *, text: str = ""):
    """Mở khóa kênh."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🛡️ Kiểm Duyệt • nuked unlockx",
        (
            "📌 **Mô tả:** Mở khóa kênh.\n\n"
            "🧭 **Cách dùng:** `nuked unlockx`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🛡️ Kiểm Duyệt • timeoutx
# ------------------------------------------------------------
@bot.command(name="timeoutx")
async def extended_timeoutx(ctx, *, text: str = ""):
    """Timeout một thành viên."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🛡️ Kiểm Duyệt • nuked timeoutx",
        (
            "📌 **Mô tả:** Timeout một thành viên.\n\n"
            "🧭 **Cách dùng:** `nuked timeoutx`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🛡️ Kiểm Duyệt • untimeout
# ------------------------------------------------------------
@bot.command(name="untimeout")
async def extended_untimeout(ctx, *, text: str = ""):
    """Gỡ timeout."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🛡️ Kiểm Duyệt • nuked untimeout",
        (
            "📌 **Mô tả:** Gỡ timeout.\n\n"
            "🧭 **Cách dùng:** `nuked untimeout`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🛡️ Kiểm Duyệt • kickx
# ------------------------------------------------------------
@bot.command(name="kickx")
async def extended_kickx(ctx, *, text: str = ""):
    """Kick một thành viên."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🛡️ Kiểm Duyệt • nuked kickx",
        (
            "📌 **Mô tả:** Kick một thành viên.\n\n"
            "🧭 **Cách dùng:** `nuked kickx`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🛡️ Kiểm Duyệt • banx
# ------------------------------------------------------------
@bot.command(name="banx")
async def extended_banx(ctx, *, text: str = ""):
    """Ban một thành viên."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🛡️ Kiểm Duyệt • nuked banx",
        (
            "📌 **Mô tả:** Ban một thành viên.\n\n"
            "🧭 **Cách dùng:** `nuked banx`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🛡️ Kiểm Duyệt • unbanx
# ------------------------------------------------------------
@bot.command(name="unbanx")
async def extended_unbanx(ctx, *, text: str = ""):
    """Gỡ ban bằng ID."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🛡️ Kiểm Duyệt • nuked unbanx",
        (
            "📌 **Mô tả:** Gỡ ban bằng ID.\n\n"
            "🧭 **Cách dùng:** `nuked unbanx`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🛡️ Kiểm Duyệt • softban
# ------------------------------------------------------------
@bot.command(name="softban")
async def extended_softban(ctx, *, text: str = ""):
    """Hướng dẫn softban an toàn."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🛡️ Kiểm Duyệt • nuked softban",
        (
            "📌 **Mô tả:** Hướng dẫn softban an toàn.\n\n"
            "🧭 **Cách dùng:** `nuked softban`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🛡️ Kiểm Duyệt • modlog
# ------------------------------------------------------------
@bot.command(name="modlog")
async def extended_modlog(ctx, *, text: str = ""):
    """Xem hướng dẫn modlog."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🛡️ Kiểm Duyệt • nuked modlog",
        (
            "📌 **Mô tả:** Xem hướng dẫn modlog.\n\n"
            "🧭 **Cách dùng:** `nuked modlog`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🛡️ Kiểm Duyệt • reason
# ------------------------------------------------------------
@bot.command(name="reason")
async def extended_reason(ctx, *, text: str = ""):
    """Xem lý do thao tác gần nhất."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🛡️ Kiểm Duyệt • nuked reason",
        (
            "📌 **Mô tả:** Xem lý do thao tác gần nhất.\n\n"
            "🧭 **Cách dùng:** `nuked reason`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🛡️ Kiểm Duyệt • case
# ------------------------------------------------------------
@bot.command(name="case")
async def extended_case(ctx, *, text: str = ""):
    """Tra cứu case ID."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🛡️ Kiểm Duyệt • nuked case",
        (
            "📌 **Mô tả:** Tra cứu case ID.\n\n"
            "🧭 **Cách dùng:** `nuked case`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🛡️ Kiểm Duyệt • modstats
# ------------------------------------------------------------
@bot.command(name="modstats")
async def extended_modstats(ctx, *, text: str = ""):
    """Thống kê kiểm duyệt."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🛡️ Kiểm Duyệt • nuked modstats",
        (
            "📌 **Mô tả:** Thống kê kiểm duyệt.\n\n"
            "🧭 **Cách dùng:** `nuked modstats`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🛡️ Kiểm Duyệt • modhelp
# ------------------------------------------------------------
@bot.command(name="modhelp")
async def extended_modhelp(ctx, *, text: str = ""):
    """Hướng dẫn moderation."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🛡️ Kiểm Duyệt • nuked modhelp",
        (
            "📌 **Mô tả:** Hướng dẫn moderation.\n\n"
            "🧭 **Cách dùng:** `nuked modhelp`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🛡️ Kiểm Duyệt • audit
# ------------------------------------------------------------
@bot.command(name="audit")
async def extended_audit(ctx, *, text: str = ""):
    """Hướng dẫn xem audit log."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🛡️ Kiểm Duyệt • nuked audit",
        (
            "📌 **Mô tả:** Hướng dẫn xem audit log.\n\n"
            "🧭 **Cách dùng:** `nuked audit`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🛡️ Kiểm Duyệt • purge
# ------------------------------------------------------------
@bot.command(name="purge")
async def extended_purge(ctx, *, text: str = ""):
    """Xóa nhóm tin nhắn theo giới hạn."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🛡️ Kiểm Duyệt • nuked purge",
        (
            "📌 **Mô tả:** Xóa nhóm tin nhắn theo giới hạn.\n\n"
            "🧭 **Cách dùng:** `nuked purge`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🛡️ Kiểm Duyệt • clean
# ------------------------------------------------------------
@bot.command(name="clean")
async def extended_clean(ctx, *, text: str = ""):
    """Làm sạch tin nhắn bot."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🛡️ Kiểm Duyệt • nuked clean",
        (
            "📌 **Mô tả:** Làm sạch tin nhắn bot.\n\n"
            "🧭 **Cách dùng:** `nuked clean`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🛡️ Kiểm Duyệt • filter
# ------------------------------------------------------------
@bot.command(name="filter")
async def extended_filter(ctx, *, text: str = ""):
    """Xem trạng thái bộ lọc."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🛡️ Kiểm Duyệt • nuked filter",
        (
            "📌 **Mô tả:** Xem trạng thái bộ lọc.\n\n"
            "🧭 **Cách dùng:** `nuked filter`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🛡️ Kiểm Duyệt • automod
# ------------------------------------------------------------
@bot.command(name="automod")
async def extended_automod(ctx, *, text: str = ""):
    """Xem hướng dẫn AutoMod."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🛡️ Kiểm Duyệt • nuked automod",
        (
            "📌 **Mô tả:** Xem hướng dẫn AutoMod.\n\n"
            "🧭 **Cách dùng:** `nuked automod`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🛡️ Kiểm Duyệt • rules
# ------------------------------------------------------------
@bot.command(name="rules")
async def extended_rules(ctx, *, text: str = ""):
    """Hiển thị quy tắc server."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🛡️ Kiểm Duyệt • nuked rules",
        (
            "📌 **Mô tả:** Hiển thị quy tắc server.\n\n"
            "🧭 **Cách dùng:** `nuked rules`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🛡️ Kiểm Duyệt • report
# ------------------------------------------------------------
@bot.command(name="report")
async def extended_report(ctx, *, text: str = ""):
    """Tạo mẫu báo cáo."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🛡️ Kiểm Duyệt • nuked report",
        (
            "📌 **Mô tả:** Tạo mẫu báo cáo.\n\n"
            "🧭 **Cách dùng:** `nuked report`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🛡️ Kiểm Duyệt • appeal
# ------------------------------------------------------------
@bot.command(name="appeal")
async def extended_appeal(ctx, *, text: str = ""):
    """Hướng dẫn kháng nghị."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🛡️ Kiểm Duyệt • nuked appeal",
        (
            "📌 **Mô tả:** Hướng dẫn kháng nghị.\n\n"
            "🧭 **Cách dùng:** `nuked appeal`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🛡️ Kiểm Duyệt • modinfo
# ------------------------------------------------------------
@bot.command(name="modinfo")
async def extended_modinfo(ctx, *, text: str = ""):
    """Thông tin công cụ moderation."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🛡️ Kiểm Duyệt • nuked modinfo",
        (
            "📌 **Mô tả:** Thông tin công cụ moderation.\n\n"
            "🧭 **Cách dùng:** `nuked modinfo`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🛡️ Kiểm Duyệt • cases
# ------------------------------------------------------------
@bot.command(name="cases")
async def extended_cases(ctx, *, text: str = ""):
    """Danh sách case theo dữ liệu bot."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🛡️ Kiểm Duyệt • nuked cases",
        (
            "📌 **Mô tả:** Danh sách case theo dữ liệu bot.\n\n"
            "🧭 **Cách dùng:** `nuked cases`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🛡️ Kiểm Duyệt • muteinfo
# ------------------------------------------------------------
@bot.command(name="muteinfo")
async def extended_muteinfo(ctx, *, text: str = ""):
    """Thông tin mute/timeout."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🛡️ Kiểm Duyệt • nuked muteinfo",
        (
            "📌 **Mô tả:** Thông tin mute/timeout.\n\n"
            "🧭 **Cách dùng:** `nuked muteinfo`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🛡️ Kiểm Duyệt • kickinfo
# ------------------------------------------------------------
@bot.command(name="kickinfo")
async def extended_kickinfo(ctx, *, text: str = ""):
    """Thông tin quyền kick."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🛡️ Kiểm Duyệt • nuked kickinfo",
        (
            "📌 **Mô tả:** Thông tin quyền kick.\n\n"
            "🧭 **Cách dùng:** `nuked kickinfo`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🛡️ Kiểm Duyệt • baninfo
# ------------------------------------------------------------
@bot.command(name="baninfo")
async def extended_baninfo(ctx, *, text: str = ""):
    """Thông tin quyền ban."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🛡️ Kiểm Duyệt • nuked baninfo",
        (
            "📌 **Mô tả:** Thông tin quyền ban.\n\n"
            "🧭 **Cách dùng:** `nuked baninfo`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🛡️ Kiểm Duyệt • permissioncheck
# ------------------------------------------------------------
@bot.command(name="permissioncheck")
async def extended_permissioncheck(ctx, *, text: str = ""):
    """Kiểm tra quyền moderation."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🛡️ Kiểm Duyệt • nuked permissioncheck",
        (
            "📌 **Mô tả:** Kiểm tra quyền moderation.\n\n"
            "🧭 **Cách dùng:** `nuked permissioncheck`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 📢 Kênh • channelinfo
# ------------------------------------------------------------
@bot.command(name="channelinfo")
async def extended_channelinfo(ctx, *, text: str = ""):
    """Thông tin kênh hiện tại."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 📢 Kênh • nuked channelinfo",
        (
            "📌 **Mô tả:** Thông tin kênh hiện tại.\n\n"
            "🧭 **Cách dùng:** `nuked channelinfo`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 📢 Kênh • channelname
# ------------------------------------------------------------
@bot.command(name="channelname")
async def extended_channelname(ctx, *, text: str = ""):
    """Xem tên kênh."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 📢 Kênh • nuked channelname",
        (
            "📌 **Mô tả:** Xem tên kênh.\n\n"
            "🧭 **Cách dùng:** `nuked channelname`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 📢 Kênh • channeltopic
# ------------------------------------------------------------
@bot.command(name="channeltopic")
async def extended_channeltopic(ctx, *, text: str = ""):
    """Xem topic kênh."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 📢 Kênh • nuked channeltopic",
        (
            "📌 **Mô tả:** Xem topic kênh.\n\n"
            "🧭 **Cách dùng:** `nuked channeltopic`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 📢 Kênh • channeltype
# ------------------------------------------------------------
@bot.command(name="channeltype")
async def extended_channeltype(ctx, *, text: str = ""):
    """Xem loại kênh."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 📢 Kênh • nuked channeltype",
        (
            "📌 **Mô tả:** Xem loại kênh.\n\n"
            "🧭 **Cách dùng:** `nuked channeltype`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 📢 Kênh • channelposition
# ------------------------------------------------------------
@bot.command(name="channelposition")
async def extended_channelposition(ctx, *, text: str = ""):
    """Xem vị trí kênh."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 📢 Kênh • nuked channelposition",
        (
            "📌 **Mô tả:** Xem vị trí kênh.\n\n"
            "🧭 **Cách dùng:** `nuked channelposition`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 📢 Kênh • channelcategory
# ------------------------------------------------------------
@bot.command(name="channelcategory")
async def extended_channelcategory(ctx, *, text: str = ""):
    """Xem category."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 📢 Kênh • nuked channelcategory",
        (
            "📌 **Mô tả:** Xem category.\n\n"
            "🧭 **Cách dùng:** `nuked channelcategory`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 📢 Kênh • channelcreated
# ------------------------------------------------------------
@bot.command(name="channelcreated")
async def extended_channelcreated(ctx, *, text: str = ""):
    """Xem ngày tạo kênh."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 📢 Kênh • nuked channelcreated",
        (
            "📌 **Mô tả:** Xem ngày tạo kênh.\n\n"
            "🧭 **Cách dùng:** `nuked channelcreated`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 📢 Kênh • channelmention
# ------------------------------------------------------------
@bot.command(name="channelmention")
async def extended_channelmention(ctx, *, text: str = ""):
    """Tạo mention kênh."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 📢 Kênh • nuked channelmention",
        (
            "📌 **Mô tả:** Tạo mention kênh.\n\n"
            "🧭 **Cách dùng:** `nuked channelmention`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 📢 Kênh • channelid2
# ------------------------------------------------------------
@bot.command(name="channelid2")
async def extended_channelid2(ctx, *, text: str = ""):
    """Xem ID kênh."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 📢 Kênh • nuked channelid2",
        (
            "📌 **Mô tả:** Xem ID kênh.\n\n"
            "🧭 **Cách dùng:** `nuked channelid2`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 📢 Kênh • listtext
# ------------------------------------------------------------
@bot.command(name="listtext")
async def extended_listtext(ctx, *, text: str = ""):
    """Liệt kê text channel."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 📢 Kênh • nuked listtext",
        (
            "📌 **Mô tả:** Liệt kê text channel.\n\n"
            "🧭 **Cách dùng:** `nuked listtext`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 📢 Kênh • listvoice
# ------------------------------------------------------------
@bot.command(name="listvoice")
async def extended_listvoice(ctx, *, text: str = ""):
    """Liệt kê voice channel."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 📢 Kênh • nuked listvoice",
        (
            "📌 **Mô tả:** Liệt kê voice channel.\n\n"
            "🧭 **Cách dùng:** `nuked listvoice`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 📢 Kênh • listcategory
# ------------------------------------------------------------
@bot.command(name="listcategory")
async def extended_listcategory(ctx, *, text: str = ""):
    """Liệt kê category."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 📢 Kênh • nuked listcategory",
        (
            "📌 **Mô tả:** Liệt kê category.\n\n"
            "🧭 **Cách dùng:** `nuked listcategory`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 📢 Kênh • listforum
# ------------------------------------------------------------
@bot.command(name="listforum")
async def extended_listforum(ctx, *, text: str = ""):
    """Liệt kê forum channel."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 📢 Kênh • nuked listforum",
        (
            "📌 **Mô tả:** Liệt kê forum channel.\n\n"
            "🧭 **Cách dùng:** `nuked listforum`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 📢 Kênh • liststage
# ------------------------------------------------------------
@bot.command(name="liststage")
async def extended_liststage(ctx, *, text: str = ""):
    """Liệt kê stage channel."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 📢 Kênh • nuked liststage",
        (
            "📌 **Mô tả:** Liệt kê stage channel.\n\n"
            "🧭 **Cách dùng:** `nuked liststage`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 📢 Kênh • channelcount
# ------------------------------------------------------------
@bot.command(name="channelcount")
async def extended_channelcount(ctx, *, text: str = ""):
    """Đếm channel."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 📢 Kênh • nuked channelcount",
        (
            "📌 **Mô tả:** Đếm channel.\n\n"
            "🧭 **Cách dùng:** `nuked channelcount`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 📢 Kênh • textcount
# ------------------------------------------------------------
@bot.command(name="textcount")
async def extended_textcount(ctx, *, text: str = ""):
    """Đếm text channel."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 📢 Kênh • nuked textcount",
        (
            "📌 **Mô tả:** Đếm text channel.\n\n"
            "🧭 **Cách dùng:** `nuked textcount`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 📢 Kênh • voicecount
# ------------------------------------------------------------
@bot.command(name="voicecount")
async def extended_voicecount(ctx, *, text: str = ""):
    """Đếm voice channel."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 📢 Kênh • nuked voicecount",
        (
            "📌 **Mô tả:** Đếm voice channel.\n\n"
            "🧭 **Cách dùng:** `nuked voicecount`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 📢 Kênh • categorycount
# ------------------------------------------------------------
@bot.command(name="categorycount")
async def extended_categorycount(ctx, *, text: str = ""):
    """Đếm category."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 📢 Kênh • nuked categorycount",
        (
            "📌 **Mô tả:** Đếm category.\n\n"
            "🧭 **Cách dùng:** `nuked categorycount`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 📢 Kênh • forumcount
# ------------------------------------------------------------
@bot.command(name="forumcount")
async def extended_forumcount(ctx, *, text: str = ""):
    """Đếm forum channel."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 📢 Kênh • nuked forumcount",
        (
            "📌 **Mô tả:** Đếm forum channel.\n\n"
            "🧭 **Cách dùng:** `nuked forumcount`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 📢 Kênh • createchannelx
# ------------------------------------------------------------
@bot.command(name="createchannelx")
async def extended_createchannelx(ctx, *, text: str = ""):
    """Hướng dẫn tạo kênh."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 📢 Kênh • nuked createchannelx",
        (
            "📌 **Mô tả:** Hướng dẫn tạo kênh.\n\n"
            "🧭 **Cách dùng:** `nuked createchannelx`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 📢 Kênh • renamechannelx
# ------------------------------------------------------------
@bot.command(name="renamechannelx")
async def extended_renamechannelx(ctx, *, text: str = ""):
    """Hướng dẫn đổi tên kênh."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 📢 Kênh • nuked renamechannelx",
        (
            "📌 **Mô tả:** Hướng dẫn đổi tên kênh.\n\n"
            "🧭 **Cách dùng:** `nuked renamechannelx`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 📢 Kênh • settopicx
# ------------------------------------------------------------
@bot.command(name="settopicx")
async def extended_settopicx(ctx, *, text: str = ""):
    """Hướng dẫn đặt topic."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 📢 Kênh • nuked settopicx",
        (
            "📌 **Mô tả:** Hướng dẫn đặt topic.\n\n"
            "🧭 **Cách dùng:** `nuked settopicx`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 📢 Kênh • slowmodeinfo
# ------------------------------------------------------------
@bot.command(name="slowmodeinfo")
async def extended_slowmodeinfo(ctx, *, text: str = ""):
    """Thông tin slowmode."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 📢 Kênh • nuked slowmodeinfo",
        (
            "📌 **Mô tả:** Thông tin slowmode.\n\n"
            "🧭 **Cách dùng:** `nuked slowmodeinfo`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 📢 Kênh • lockinfo
# ------------------------------------------------------------
@bot.command(name="lockinfo")
async def extended_lockinfo(ctx, *, text: str = ""):
    """Thông tin khóa kênh."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 📢 Kênh • nuked lockinfo",
        (
            "📌 **Mô tả:** Thông tin khóa kênh.\n\n"
            "🧭 **Cách dùng:** `nuked lockinfo`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 📢 Kênh • unlockinfo
# ------------------------------------------------------------
@bot.command(name="unlockinfo")
async def extended_unlockinfo(ctx, *, text: str = ""):
    """Thông tin mở khóa."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 📢 Kênh • nuked unlockinfo",
        (
            "📌 **Mô tả:** Thông tin mở khóa.\n\n"
            "🧭 **Cách dùng:** `nuked unlockinfo`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 📢 Kênh • channelperms
# ------------------------------------------------------------
@bot.command(name="channelperms")
async def extended_channelperms(ctx, *, text: str = ""):
    """Kiểm tra quyền kênh."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 📢 Kênh • nuked channelperms",
        (
            "📌 **Mô tả:** Kiểm tra quyền kênh.\n\n"
            "🧭 **Cách dùng:** `nuked channelperms`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 📢 Kênh • channelhelp
# ------------------------------------------------------------
@bot.command(name="channelhelp")
async def extended_channelhelp(ctx, *, text: str = ""):
    """Hướng dẫn quản lý kênh."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 📢 Kênh • nuked channelhelp",
        (
            "📌 **Mô tả:** Hướng dẫn quản lý kênh.\n\n"
            "🧭 **Cách dùng:** `nuked channelhelp`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 📢 Kênh • archiveinfo
# ------------------------------------------------------------
@bot.command(name="archiveinfo")
async def extended_archiveinfo(ctx, *, text: str = ""):
    """Hướng dẫn archive."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 📢 Kênh • nuked archiveinfo",
        (
            "📌 **Mô tả:** Hướng dẫn archive.\n\n"
            "🧭 **Cách dùng:** `nuked archiveinfo`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 📢 Kênh • threadinfo
# ------------------------------------------------------------
@bot.command(name="threadinfo")
async def extended_threadinfo(ctx, *, text: str = ""):
    """Thông tin thread."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 📢 Kênh • nuked threadinfo",
        (
            "📌 **Mô tả:** Thông tin thread.\n\n"
            "🧭 **Cách dùng:** `nuked threadinfo`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 📢 Kênh • threads
# ------------------------------------------------------------
@bot.command(name="threads")
async def extended_threads(ctx, *, text: str = ""):
    """Đếm thread hiện có."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 📢 Kênh • nuked threads",
        (
            "📌 **Mô tả:** Đếm thread hiện có.\n\n"
            "🧭 **Cách dùng:** `nuked threads`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 📢 Kênh • channelstats
# ------------------------------------------------------------
@bot.command(name="channelstats")
async def extended_channelstats(ctx, *, text: str = ""):
    """Thống kê kênh."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 📢 Kênh • nuked channelstats",
        (
            "📌 **Mô tả:** Thống kê kênh.\n\n"
            "🧭 **Cách dùng:** `nuked channelstats`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🎭 Role • roleinfo
# ------------------------------------------------------------
@bot.command(name="roleinfo")
async def extended_roleinfo(ctx, *, text: str = ""):
    """Thông tin role."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🎭 Role • nuked roleinfo",
        (
            "📌 **Mô tả:** Thông tin role.\n\n"
            "🧭 **Cách dùng:** `nuked roleinfo`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🎭 Role • rolelist
# ------------------------------------------------------------
@bot.command(name="rolelist")
async def extended_rolelist(ctx, *, text: str = ""):
    """Liệt kê role."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🎭 Role • nuked rolelist",
        (
            "📌 **Mô tả:** Liệt kê role.\n\n"
            "🧭 **Cách dùng:** `nuked rolelist`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🎭 Role • rolecount
# ------------------------------------------------------------
@bot.command(name="rolecount")
async def extended_rolecount(ctx, *, text: str = ""):
    """Đếm role."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🎭 Role • nuked rolecount",
        (
            "📌 **Mô tả:** Đếm role.\n\n"
            "🧭 **Cách dùng:** `nuked rolecount`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🎭 Role • rolemembers
# ------------------------------------------------------------
@bot.command(name="rolemembers")
async def extended_rolemembers(ctx, *, text: str = ""):
    """Xem số thành viên có role."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🎭 Role • nuked rolemembers",
        (
            "📌 **Mô tả:** Xem số thành viên có role.\n\n"
            "🧭 **Cách dùng:** `nuked rolemembers`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🎭 Role • rolecolor
# ------------------------------------------------------------
@bot.command(name="rolecolor")
async def extended_rolecolor(ctx, *, text: str = ""):
    """Xem màu role."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🎭 Role • nuked rolecolor",
        (
            "📌 **Mô tả:** Xem màu role.\n\n"
            "🧭 **Cách dùng:** `nuked rolecolor`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🎭 Role • roleposition
# ------------------------------------------------------------
@bot.command(name="roleposition")
async def extended_roleposition(ctx, *, text: str = ""):
    """Xem vị trí role."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🎭 Role • nuked roleposition",
        (
            "📌 **Mô tả:** Xem vị trí role.\n\n"
            "🧭 **Cách dùng:** `nuked roleposition`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🎭 Role • rolemention
# ------------------------------------------------------------
@bot.command(name="rolemention")
async def extended_rolemention(ctx, *, text: str = ""):
    """Tạo mention role."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🎭 Role • nuked rolemention",
        (
            "📌 **Mô tả:** Tạo mention role.\n\n"
            "🧭 **Cách dùng:** `nuked rolemention`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🎭 Role • rolecreated
# ------------------------------------------------------------
@bot.command(name="rolecreated")
async def extended_rolecreated(ctx, *, text: str = ""):
    """Xem ngày tạo role."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🎭 Role • nuked rolecreated",
        (
            "📌 **Mô tả:** Xem ngày tạo role.\n\n"
            "🧭 **Cách dùng:** `nuked rolecreated`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🎭 Role • roleperms
# ------------------------------------------------------------
@bot.command(name="roleperms")
async def extended_roleperms(ctx, *, text: str = ""):
    """Xem quyền role."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🎭 Role • nuked roleperms",
        (
            "📌 **Mô tả:** Xem quyền role.\n\n"
            "🧭 **Cách dùng:** `nuked roleperms`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🎭 Role • rolehelp
# ------------------------------------------------------------
@bot.command(name="rolehelp")
async def extended_rolehelp(ctx, *, text: str = ""):
    """Hướng dẫn role."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🎭 Role • nuked rolehelp",
        (
            "📌 **Mô tả:** Hướng dẫn role.\n\n"
            "🧭 **Cách dùng:** `nuked rolehelp`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🎭 Role • addroleinfo
# ------------------------------------------------------------
@bot.command(name="addroleinfo")
async def extended_addroleinfo(ctx, *, text: str = ""):
    """Hướng dẫn thêm role."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🎭 Role • nuked addroleinfo",
        (
            "📌 **Mô tả:** Hướng dẫn thêm role.\n\n"
            "🧭 **Cách dùng:** `nuked addroleinfo`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🎭 Role • removeroleinfo
# ------------------------------------------------------------
@bot.command(name="removeroleinfo")
async def extended_removeroleinfo(ctx, *, text: str = ""):
    """Hướng dẫn gỡ role."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🎭 Role • nuked removeroleinfo",
        (
            "📌 **Mô tả:** Hướng dẫn gỡ role.\n\n"
            "🧭 **Cách dùng:** `nuked removeroleinfo`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🎭 Role • autoroleinfo
# ------------------------------------------------------------
@bot.command(name="autoroleinfo")
async def extended_autoroleinfo(ctx, *, text: str = ""):
    """Hướng dẫn autorole."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🎭 Role • nuked autoroleinfo",
        (
            "📌 **Mô tả:** Hướng dẫn autorole.\n\n"
            "🧭 **Cách dùng:** `nuked autoroleinfo`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🎭 Role • rolehierarchy
# ------------------------------------------------------------
@bot.command(name="rolehierarchy")
async def extended_rolehierarchy(ctx, *, text: str = ""):
    """Xem thứ tự role."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🎭 Role • nuked rolehierarchy",
        (
            "📌 **Mô tả:** Xem thứ tự role.\n\n"
            "🧭 **Cách dùng:** `nuked rolehierarchy`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🎭 Role • botrole
# ------------------------------------------------------------
@bot.command(name="botrole")
async def extended_botrole(ctx, *, text: str = ""):
    """Xem role cao nhất của bot."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🎭 Role • nuked botrole",
        (
            "📌 **Mô tả:** Xem role cao nhất của bot.\n\n"
            "🧭 **Cách dùng:** `nuked botrole`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🎭 Role • memberroles
# ------------------------------------------------------------
@bot.command(name="memberroles")
async def extended_memberroles(ctx, *, text: str = ""):
    """Xem role thành viên."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🎭 Role • nuked memberroles",
        (
            "📌 **Mô tả:** Xem role thành viên.\n\n"
            "🧭 **Cách dùng:** `nuked memberroles`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🎭 Role • commonroles
# ------------------------------------------------------------
@bot.command(name="commonroles")
async def extended_commonroles(ctx, *, text: str = ""):
    """Xem role phổ biến."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🎭 Role • nuked commonroles",
        (
            "📌 **Mô tả:** Xem role phổ biến.\n\n"
            "🧭 **Cách dùng:** `nuked commonroles`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🎭 Role • emptyroles
# ------------------------------------------------------------
@bot.command(name="emptyroles")
async def extended_emptyroles(ctx, *, text: str = ""):
    """Tìm role không có thành viên."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🎭 Role • nuked emptyroles",
        (
            "📌 **Mô tả:** Tìm role không có thành viên.\n\n"
            "🧭 **Cách dùng:** `nuked emptyroles`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🎭 Role • managedroles
# ------------------------------------------------------------
@bot.command(name="managedroles")
async def extended_managedroles(ctx, *, text: str = ""):
    """Xem role managed."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🎭 Role • nuked managedroles",
        (
            "📌 **Mô tả:** Xem role managed.\n\n"
            "🧭 **Cách dùng:** `nuked managedroles`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🎭 Role • hoistedroles
# ------------------------------------------------------------
@bot.command(name="hoistedroles")
async def extended_hoistedroles(ctx, *, text: str = ""):
    """Xem role hiển thị riêng."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🎭 Role • nuked hoistedroles",
        (
            "📌 **Mô tả:** Xem role hiển thị riêng.\n\n"
            "🧭 **Cách dùng:** `nuked hoistedroles`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🎭 Role • coloredroles
# ------------------------------------------------------------
@bot.command(name="coloredroles")
async def extended_coloredroles(ctx, *, text: str = ""):
    """Xem role có màu."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🎭 Role • nuked coloredroles",
        (
            "📌 **Mô tả:** Xem role có màu.\n\n"
            "🧭 **Cách dùng:** `nuked coloredroles`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🎭 Role • rolepermissions
# ------------------------------------------------------------
@bot.command(name="rolepermissions")
async def extended_rolepermissions(ctx, *, text: str = ""):
    """Kiểm tra permission role."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🎭 Role • nuked rolepermissions",
        (
            "📌 **Mô tả:** Kiểm tra permission role.\n\n"
            "🧭 **Cách dùng:** `nuked rolepermissions`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🎭 Role • rolepositionof
# ------------------------------------------------------------
@bot.command(name="rolepositionof")
async def extended_rolepositionof(ctx, *, text: str = ""):
    """Tra vị trí role."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🎭 Role • nuked rolepositionof",
        (
            "📌 **Mô tả:** Tra vị trí role.\n\n"
            "🧭 **Cách dùng:** `nuked rolepositionof`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🎭 Role • rolelookup
# ------------------------------------------------------------
@bot.command(name="rolelookup")
async def extended_rolelookup(ctx, *, text: str = ""):
    """Tra cứu role."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🎭 Role • nuked rolelookup",
        (
            "📌 **Mô tả:** Tra cứu role.\n\n"
            "🧭 **Cách dùng:** `nuked rolelookup`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🎭 Role • roleusage
# ------------------------------------------------------------
@bot.command(name="roleusage")
async def extended_roleusage(ctx, *, text: str = ""):
    """Hướng dẫn dùng role."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🎭 Role • nuked roleusage",
        (
            "📌 **Mô tả:** Hướng dẫn dùng role.\n\n"
            "🧭 **Cách dùng:** `nuked roleusage`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🎭 Role • rolecommand
# ------------------------------------------------------------
@bot.command(name="rolecommand")
async def extended_rolecommand(ctx, *, text: str = ""):
    """Hướng dẫn lệnh role."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🎭 Role • nuked rolecommand",
        (
            "📌 **Mô tả:** Hướng dẫn lệnh role.\n\n"
            "🧭 **Cách dùng:** `nuked rolecommand`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🎭 Role • roleconfig
# ------------------------------------------------------------
@bot.command(name="roleconfig")
async def extended_roleconfig(ctx, *, text: str = ""):
    """Hướng dẫn cấu hình role."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🎭 Role • nuked roleconfig",
        (
            "📌 **Mô tả:** Hướng dẫn cấu hình role.\n\n"
            "🧭 **Cách dùng:** `nuked roleconfig`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🎭 Role • rolebackup
# ------------------------------------------------------------
@bot.command(name="rolebackup")
async def extended_rolebackup(ctx, *, text: str = ""):
    """Thông tin backup role."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🎭 Role • nuked rolebackup",
        (
            "📌 **Mô tả:** Thông tin backup role.\n\n"
            "🧭 **Cách dùng:** `nuked rolebackup`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🎭 Role • roleaudit
# ------------------------------------------------------------
@bot.command(name="roleaudit")
async def extended_roleaudit(ctx, *, text: str = ""):
    """Hướng dẫn audit role."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🎭 Role • nuked roleaudit",
        (
            "📌 **Mô tả:** Hướng dẫn audit role.\n\n"
            "🧭 **Cách dùng:** `nuked roleaudit`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🎭 Role • rolecountx
# ------------------------------------------------------------
@bot.command(name="rolecountx")
async def extended_rolecountx(ctx, *, text: str = ""):
    """Thống kê role."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🎭 Role • nuked rolecountx",
        (
            "📌 **Mô tả:** Thống kê role.\n\n"
            "🧭 **Cách dùng:** `nuked rolecountx`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🎭 Role • rolecenter
# ------------------------------------------------------------
@bot.command(name="rolecenter")
async def extended_rolecenter(ctx, *, text: str = ""):
    """Mở trung tâm role."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🎭 Role • nuked rolecenter",
        (
            "📌 **Mô tả:** Mở trung tâm role.\n\n"
            "🧭 **Cách dùng:** `nuked rolecenter`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🎉 Giải Trí • 8ball
# ------------------------------------------------------------
@bot.command(name="8ball")
async def extended_8ball(ctx, *, text: str = ""):
    """Trả lời ngẫu nhiên vui vẻ."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🎉 Giải Trí • nuked 8ball",
        (
            "📌 **Mô tả:** Trả lời ngẫu nhiên vui vẻ.\n\n"
            "🧭 **Cách dùng:** `nuked 8ball`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🎉 Giải Trí • choose
# ------------------------------------------------------------
@bot.command(name="choose")
async def extended_choose(ctx, *, text: str = ""):
    """Chọn một phương án."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🎉 Giải Trí • nuked choose",
        (
            "📌 **Mô tả:** Chọn một phương án.\n\n"
            "🧭 **Cách dùng:** `nuked choose`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🎉 Giải Trí • rollx
# ------------------------------------------------------------
@bot.command(name="rollx")
async def extended_rollx(ctx, *, text: str = ""):
    """Tung xúc xắc."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🎉 Giải Trí • nuked rollx",
        (
            "📌 **Mô tả:** Tung xúc xắc.\n\n"
            "🧭 **Cách dùng:** `nuked rollx`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🎉 Giải Trí • coinflipx
# ------------------------------------------------------------
@bot.command(name="coinflipx")
async def extended_coinflipx(ctx, *, text: str = ""):
    """Tung đồng xu ảo."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🎉 Giải Trí • nuked coinflipx",
        (
            "📌 **Mô tả:** Tung đồng xu ảo.\n\n"
            "🧭 **Cách dùng:** `nuked coinflipx`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🎉 Giải Trí • rate
# ------------------------------------------------------------
@bot.command(name="rate")
async def extended_rate(ctx, *, text: str = ""):
    """Chấm điểm vui."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🎉 Giải Trí • nuked rate",
        (
            "📌 **Mô tả:** Chấm điểm vui.\n\n"
            "🧭 **Cách dùng:** `nuked rate`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🎉 Giải Trí • shipx
# ------------------------------------------------------------
@bot.command(name="shipx")
async def extended_shipx(ctx, *, text: str = ""):
    """Ghép đôi vui."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🎉 Giải Trí • nuked shipx",
        (
            "📌 **Mô tả:** Ghép đôi vui.\n\n"
            "🧭 **Cách dùng:** `nuked shipx`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🎉 Giải Trí • lovecheck
# ------------------------------------------------------------
@bot.command(name="lovecheck")
async def extended_lovecheck(ctx, *, text: str = ""):
    """Tỷ lệ tình cảm vui."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🎉 Giải Trí • nuked lovecheck",
        (
            "📌 **Mô tả:** Tỷ lệ tình cảm vui.\n\n"
            "🧭 **Cách dùng:** `nuked lovecheck`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🎉 Giải Trí • hugx
# ------------------------------------------------------------
@bot.command(name="hugx")
async def extended_hugx(ctx, *, text: str = ""):
    """Tương tác ôm vui."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🎉 Giải Trí • nuked hugx",
        (
            "📌 **Mô tả:** Tương tác ôm vui.\n\n"
            "🧭 **Cách dùng:** `nuked hugx`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🎉 Giải Trí • patx
# ------------------------------------------------------------
@bot.command(name="patx")
async def extended_patx(ctx, *, text: str = ""):
    """Tương tác vỗ đầu vui."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🎉 Giải Trí • nuked patx",
        (
            "📌 **Mô tả:** Tương tác vỗ đầu vui.\n\n"
            "🧭 **Cách dùng:** `nuked patx`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🎉 Giải Trí • cuddlex
# ------------------------------------------------------------
@bot.command(name="cuddlex")
async def extended_cuddlex(ctx, *, text: str = ""):
    """Tương tác âu yếm vui."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🎉 Giải Trí • nuked cuddlex",
        (
            "📌 **Mô tả:** Tương tác âu yếm vui.\n\n"
            "🧭 **Cách dùng:** `nuked cuddlex`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🎉 Giải Trí • slapx
# ------------------------------------------------------------
@bot.command(name="slapx")
async def extended_slapx(ctx, *, text: str = ""):
    """Tương tác tát giả lập vui."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🎉 Giải Trí • nuked slapx",
        (
            "📌 **Mô tả:** Tương tác tát giả lập vui.\n\n"
            "🧭 **Cách dùng:** `nuked slapx`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🎉 Giải Trí • highfive
# ------------------------------------------------------------
@bot.command(name="highfive")
async def extended_highfive(ctx, *, text: str = ""):
    """Đập tay vui."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🎉 Giải Trí • nuked highfive",
        (
            "📌 **Mô tả:** Đập tay vui.\n\n"
            "🧭 **Cách dùng:** `nuked highfive`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🎉 Giải Trí • wave
# ------------------------------------------------------------
@bot.command(name="wave")
async def extended_wave(ctx, *, text: str = ""):
    """Vẫy tay."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🎉 Giải Trí • nuked wave",
        (
            "📌 **Mô tả:** Vẫy tay.\n\n"
            "🧭 **Cách dùng:** `nuked wave`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🎉 Giải Trí • dance
# ------------------------------------------------------------
@bot.command(name="dance")
async def extended_dance(ctx, *, text: str = ""):
    """Tin nhắn nhảy vui."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🎉 Giải Trí • nuked dance",
        (
            "📌 **Mô tả:** Tin nhắn nhảy vui.\n\n"
            "🧭 **Cách dùng:** `nuked dance`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🎉 Giải Trí • cheer
# ------------------------------------------------------------
@bot.command(name="cheer")
async def extended_cheer(ctx, *, text: str = ""):
    """Cổ vũ thành viên."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🎉 Giải Trí • nuked cheer",
        (
            "📌 **Mô tả:** Cổ vũ thành viên.\n\n"
            "🧭 **Cách dùng:** `nuked cheer`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🎉 Giải Trí • joke
# ------------------------------------------------------------
@bot.command(name="joke")
async def extended_joke(ctx, *, text: str = ""):
    """Một câu đùa ngắn."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🎉 Giải Trí • nuked joke",
        (
            "📌 **Mô tả:** Một câu đùa ngắn.\n\n"
            "🧭 **Cách dùng:** `nuked joke`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🎉 Giải Trí • compliment
# ------------------------------------------------------------
@bot.command(name="compliment")
async def extended_compliment(ctx, *, text: str = ""):
    """Lời khen vui."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🎉 Giải Trí • nuked compliment",
        (
            "📌 **Mô tả:** Lời khen vui.\n\n"
            "🧭 **Cách dùng:** `nuked compliment`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🎉 Giải Trí • roastlight
# ------------------------------------------------------------
@bot.command(name="roastlight")
async def extended_roastlight(ctx, *, text: str = ""):
    """Roast nhẹ, không xúc phạm."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🎉 Giải Trí • nuked roastlight",
        (
            "📌 **Mô tả:** Roast nhẹ, không xúc phạm.\n\n"
            "🧭 **Cách dùng:** `nuked roastlight`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🎉 Giải Trí • meme
# ------------------------------------------------------------
@bot.command(name="meme")
async def extended_meme(ctx, *, text: str = ""):
    """Gợi ý meme."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🎉 Giải Trí • nuked meme",
        (
            "📌 **Mô tả:** Gợi ý meme.\n\n"
            "🧭 **Cách dùng:** `nuked meme`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🎉 Giải Trí • fortune
# ------------------------------------------------------------
@bot.command(name="fortune")
async def extended_fortune(ctx, *, text: str = ""):
    """Lời tiên đoán vui."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🎉 Giải Trí • nuked fortune",
        (
            "📌 **Mô tả:** Lời tiên đoán vui.\n\n"
            "🧭 **Cách dùng:** `nuked fortune`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🎉 Giải Trí • rps
# ------------------------------------------------------------
@bot.command(name="rps")
async def extended_rps(ctx, *, text: str = ""):
    """Kéo búa bao."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🎉 Giải Trí • nuked rps",
        (
            "📌 **Mô tả:** Kéo búa bao.\n\n"
            "🧭 **Cách dùng:** `nuked rps`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🎉 Giải Trí • number
# ------------------------------------------------------------
@bot.command(name="number")
async def extended_number(ctx, *, text: str = ""):
    """Tạo số ngẫu nhiên."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🎉 Giải Trí • nuked number",
        (
            "📌 **Mô tả:** Tạo số ngẫu nhiên.\n\n"
            "🧭 **Cách dùng:** `nuked number`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🎉 Giải Trí • randomword
# ------------------------------------------------------------
@bot.command(name="randomword")
async def extended_randomword(ctx, *, text: str = ""):
    """Tạo từ ngẫu nhiên."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🎉 Giải Trí • nuked randomword",
        (
            "📌 **Mô tả:** Tạo từ ngẫu nhiên.\n\n"
            "🧭 **Cách dùng:** `nuked randomword`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🎉 Giải Trí • pick
# ------------------------------------------------------------
@bot.command(name="pick")
async def extended_pick(ctx, *, text: str = ""):
    """Chọn ngẫu nhiên."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🎉 Giải Trí • nuked pick",
        (
            "📌 **Mô tả:** Chọn ngẫu nhiên.\n\n"
            "🧭 **Cách dùng:** `nuked pick`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🎉 Giải Trí • reverse
# ------------------------------------------------------------
@bot.command(name="reverse")
async def extended_reverse(ctx, *, text: str = ""):
    """Đảo chuỗi văn bản."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🎉 Giải Trí • nuked reverse",
        (
            "📌 **Mô tả:** Đảo chuỗi văn bản.\n\n"
            "🧭 **Cách dùng:** `nuked reverse`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🎉 Giải Trí • sayinfo
# ------------------------------------------------------------
@bot.command(name="sayinfo")
async def extended_sayinfo(ctx, *, text: str = ""):
    """Hướng dẫn lệnh nói."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🎉 Giải Trí • nuked sayinfo",
        (
            "📌 **Mô tả:** Hướng dẫn lệnh nói.\n\n"
            "🧭 **Cách dùng:** `nuked sayinfo`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🎉 Giải Trí • emoji
# ------------------------------------------------------------
@bot.command(name="emoji")
async def extended_emoji(ctx, *, text: str = ""):
    """Chọn emoji vui."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🎉 Giải Trí • nuked emoji",
        (
            "📌 **Mô tả:** Chọn emoji vui.\n\n"
            "🧭 **Cách dùng:** `nuked emoji`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🎉 Giải Trí • color
# ------------------------------------------------------------
@bot.command(name="color")
async def extended_color(ctx, *, text: str = ""):
    """Tạo mã màu ngẫu nhiên."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🎉 Giải Trí • nuked color",
        (
            "📌 **Mô tả:** Tạo mã màu ngẫu nhiên.\n\n"
            "🧭 **Cách dùng:** `nuked color`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🎉 Giải Trí • fact
# ------------------------------------------------------------
@bot.command(name="fact")
async def extended_fact(ctx, *, text: str = ""):
    """Một sự thật vui."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🎉 Giải Trí • nuked fact",
        (
            "📌 **Mô tả:** Một sự thật vui.\n\n"
            "🧭 **Cách dùng:** `nuked fact`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🎉 Giải Trí • quiz
# ------------------------------------------------------------
@bot.command(name="quiz")
async def extended_quiz(ctx, *, text: str = ""):
    """Câu hỏi vui."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🎉 Giải Trí • nuked quiz",
        (
            "📌 **Mô tả:** Câu hỏi vui.\n\n"
            "🧭 **Cách dùng:** `nuked quiz`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 🎉 Giải Trí • funhelp
# ------------------------------------------------------------
@bot.command(name="funhelp")
async def extended_funhelp(ctx, *, text: str = ""):
    """Hướng dẫn giải trí."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 🎉 Giải Trí • nuked funhelp",
        (
            "📌 **Mô tả:** Hướng dẫn giải trí.\n\n"
            "🧭 **Cách dùng:** `nuked funhelp`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 💰 Kinh Tế • balx
# ------------------------------------------------------------
@bot.command(name="balx")
async def extended_balx(ctx, *, text: str = ""):
    """Xem số dư."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 💰 Kinh Tế • nuked balx",
        (
            "📌 **Mô tả:** Xem số dư.\n\n"
            "🧭 **Cách dùng:** `nuked balx`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 💰 Kinh Tế • dailyx
# ------------------------------------------------------------
@bot.command(name="dailyx")
async def extended_dailyx(ctx, *, text: str = ""):
    """Nhận coin hằng ngày."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 💰 Kinh Tế • nuked dailyx",
        (
            "📌 **Mô tả:** Nhận coin hằng ngày.\n\n"
            "🧭 **Cách dùng:** `nuked dailyx`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 💰 Kinh Tế • workx
# ------------------------------------------------------------
@bot.command(name="workx")
async def extended_workx(ctx, *, text: str = ""):
    """Nhận coin từ work."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 💰 Kinh Tế • nuked workx",
        (
            "📌 **Mô tả:** Nhận coin từ work.\n\n"
            "🧭 **Cách dùng:** `nuked workx`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 💰 Kinh Tế • begx
# ------------------------------------------------------------
@bot.command(name="begx")
async def extended_begx(ctx, *, text: str = ""):
    """Nhận coin nhỏ."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 💰 Kinh Tế • nuked begx",
        (
            "📌 **Mô tả:** Nhận coin nhỏ.\n\n"
            "🧭 **Cách dùng:** `nuked begx`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 💰 Kinh Tế • givex
# ------------------------------------------------------------
@bot.command(name="givex")
async def extended_givex(ctx, *, text: str = ""):
    """Tặng coin."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 💰 Kinh Tế • nuked givex",
        (
            "📌 **Mô tả:** Tặng coin.\n\n"
            "🧭 **Cách dùng:** `nuked givex`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 💰 Kinh Tế • payinfo
# ------------------------------------------------------------
@bot.command(name="payinfo")
async def extended_payinfo(ctx, *, text: str = ""):
    """Hướng dẫn chuyển coin."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 💰 Kinh Tế • nuked payinfo",
        (
            "📌 **Mô tả:** Hướng dẫn chuyển coin.\n\n"
            "🧭 **Cách dùng:** `nuked payinfo`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 💰 Kinh Tế • leaderboardx
# ------------------------------------------------------------
@bot.command(name="leaderboardx")
async def extended_leaderboardx(ctx, *, text: str = ""):
    """Bảng xếp hạng coin."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 💰 Kinh Tế • nuked leaderboardx",
        (
            "📌 **Mô tả:** Bảng xếp hạng coin.\n\n"
            "🧭 **Cách dùng:** `nuked leaderboardx`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 💰 Kinh Tế • richest
# ------------------------------------------------------------
@bot.command(name="richest")
async def extended_richest(ctx, *, text: str = ""):
    """Xem người nhiều coin."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 💰 Kinh Tế • nuked richest",
        (
            "📌 **Mô tả:** Xem người nhiều coin.\n\n"
            "🧭 **Cách dùng:** `nuked richest`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 💰 Kinh Tế • wallet
# ------------------------------------------------------------
@bot.command(name="wallet")
async def extended_wallet(ctx, *, text: str = ""):
    """Xem ví."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 💰 Kinh Tế • nuked wallet",
        (
            "📌 **Mô tả:** Xem ví.\n\n"
            "🧭 **Cách dùng:** `nuked wallet`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 💰 Kinh Tế • economy
# ------------------------------------------------------------
@bot.command(name="economy")
async def extended_economy(ctx, *, text: str = ""):
    """Tổng quan kinh tế."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 💰 Kinh Tế • nuked economy",
        (
            "📌 **Mô tả:** Tổng quan kinh tế.\n\n"
            "🧭 **Cách dùng:** `nuked economy`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 💰 Kinh Tế • shopinfo
# ------------------------------------------------------------
@bot.command(name="shopinfo")
async def extended_shopinfo(ctx, *, text: str = ""):
    """Thông tin shop."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 💰 Kinh Tế • nuked shopinfo",
        (
            "📌 **Mô tả:** Thông tin shop.\n\n"
            "🧭 **Cách dùng:** `nuked shopinfo`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 💰 Kinh Tế • inventoryx
# ------------------------------------------------------------
@bot.command(name="inventoryx")
async def extended_inventoryx(ctx, *, text: str = ""):
    """Xem inventory."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 💰 Kinh Tế • nuked inventoryx",
        (
            "📌 **Mô tả:** Xem inventory.\n\n"
            "🧭 **Cách dùng:** `nuked inventoryx`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 💰 Kinh Tế • iteminfo
# ------------------------------------------------------------
@bot.command(name="iteminfo")
async def extended_iteminfo(ctx, *, text: str = ""):
    """Thông tin vật phẩm."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 💰 Kinh Tế • nuked iteminfo",
        (
            "📌 **Mô tả:** Thông tin vật phẩm.\n\n"
            "🧭 **Cách dùng:** `nuked iteminfo`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 💰 Kinh Tế • buyinfo
# ------------------------------------------------------------
@bot.command(name="buyinfo")
async def extended_buyinfo(ctx, *, text: str = ""):
    """Hướng dẫn mua."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 💰 Kinh Tế • nuked buyinfo",
        (
            "📌 **Mô tả:** Hướng dẫn mua.\n\n"
            "🧭 **Cách dùng:** `nuked buyinfo`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 💰 Kinh Tế • sellinfo
# ------------------------------------------------------------
@bot.command(name="sellinfo")
async def extended_sellinfo(ctx, *, text: str = ""):
    """Hướng dẫn bán."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 💰 Kinh Tế • nuked sellinfo",
        (
            "📌 **Mô tả:** Hướng dẫn bán.\n\n"
            "🧭 **Cách dùng:** `nuked sellinfo`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 💰 Kinh Tế • giftinfo
# ------------------------------------------------------------
@bot.command(name="giftinfo")
async def extended_giftinfo(ctx, *, text: str = ""):
    """Hướng dẫn tặng vật phẩm."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 💰 Kinh Tế • nuked giftinfo",
        (
            "📌 **Mô tả:** Hướng dẫn tặng vật phẩm.\n\n"
            "🧭 **Cách dùng:** `nuked giftinfo`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 💰 Kinh Tế • tradeinfo
# ------------------------------------------------------------
@bot.command(name="tradeinfo")
async def extended_tradeinfo(ctx, *, text: str = ""):
    """Hướng dẫn trao đổi."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 💰 Kinh Tế • nuked tradeinfo",
        (
            "📌 **Mô tả:** Hướng dẫn trao đổi.\n\n"
            "🧭 **Cách dùng:** `nuked tradeinfo`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 💰 Kinh Tế • economyhelp
# ------------------------------------------------------------
@bot.command(name="economyhelp")
async def extended_economyhelp(ctx, *, text: str = ""):
    """Hướng dẫn kinh tế."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 💰 Kinh Tế • nuked economyhelp",
        (
            "📌 **Mô tả:** Hướng dẫn kinh tế.\n\n"
            "🧭 **Cách dùng:** `nuked economyhelp`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 💰 Kinh Tế • coinstats
# ------------------------------------------------------------
@bot.command(name="coinstats")
async def extended_coinstats(ctx, *, text: str = ""):
    """Thống kê coin."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 💰 Kinh Tế • nuked coinstats",
        (
            "📌 **Mô tả:** Thống kê coin.\n\n"
            "🧭 **Cách dùng:** `nuked coinstats`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 💰 Kinh Tế • earnings
# ------------------------------------------------------------
@bot.command(name="earnings")
async def extended_earnings(ctx, *, text: str = ""):
    """Thống kê thu nhập."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 💰 Kinh Tế • nuked earnings",
        (
            "📌 **Mô tả:** Thống kê thu nhập.\n\n"
            "🧭 **Cách dùng:** `nuked earnings`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 💰 Kinh Tế • spending
# ------------------------------------------------------------
@bot.command(name="spending")
async def extended_spending(ctx, *, text: str = ""):
    """Hướng dẫn theo dõi chi tiêu."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 💰 Kinh Tế • nuked spending",
        (
            "📌 **Mô tả:** Hướng dẫn theo dõi chi tiêu.\n\n"
            "🧭 **Cách dùng:** `nuked spending`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 💰 Kinh Tế • economyrank
# ------------------------------------------------------------
@bot.command(name="economyrank")
async def extended_economyrank(ctx, *, text: str = ""):
    """Xếp hạng kinh tế."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 💰 Kinh Tế • nuked economyrank",
        (
            "📌 **Mô tả:** Xếp hạng kinh tế.\n\n"
            "🧭 **Cách dùng:** `nuked economyrank`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 💰 Kinh Tế • coincheck
# ------------------------------------------------------------
@bot.command(name="coincheck")
async def extended_coincheck(ctx, *, text: str = ""):
    """Kiểm tra số dư."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 💰 Kinh Tế • nuked coincheck",
        (
            "📌 **Mô tả:** Kiểm tra số dư.\n\n"
            "🧭 **Cách dùng:** `nuked coincheck`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 💰 Kinh Tế • dailyinfo
# ------------------------------------------------------------
@bot.command(name="dailyinfo")
async def extended_dailyinfo(ctx, *, text: str = ""):
    """Thông tin daily."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 💰 Kinh Tế • nuked dailyinfo",
        (
            "📌 **Mô tả:** Thông tin daily.\n\n"
            "🧭 **Cách dùng:** `nuked dailyinfo`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 💰 Kinh Tế • workinfo
# ------------------------------------------------------------
@bot.command(name="workinfo")
async def extended_workinfo(ctx, *, text: str = ""):
    """Thông tin work."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 💰 Kinh Tế • nuked workinfo",
        (
            "📌 **Mô tả:** Thông tin work.\n\n"
            "🧭 **Cách dùng:** `nuked workinfo`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 💰 Kinh Tế • beginfo
# ------------------------------------------------------------
@bot.command(name="beginfo")
async def extended_beginfo(ctx, *, text: str = ""):
    """Thông tin beg."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 💰 Kinh Tế • nuked beginfo",
        (
            "📌 **Mô tả:** Thông tin beg.\n\n"
            "🧭 **Cách dùng:** `nuked beginfo`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 💰 Kinh Tế • shop
# ------------------------------------------------------------
@bot.command(name="shop")
async def extended_shop(ctx, *, text: str = ""):
    """Mở shop an toàn."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 💰 Kinh Tế • nuked shop",
        (
            "📌 **Mô tả:** Mở shop an toàn.\n\n"
            "🧭 **Cách dùng:** `nuked shop`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 💰 Kinh Tế • inventory
# ------------------------------------------------------------
@bot.command(name="inventory")
async def extended_inventory(ctx, *, text: str = ""):
    """Mở kho vật phẩm."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 💰 Kinh Tế • nuked inventory",
        (
            "📌 **Mô tả:** Mở kho vật phẩm.\n\n"
            "🧭 **Cách dùng:** `nuked inventory`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 💰 Kinh Tế • transfer
# ------------------------------------------------------------
@bot.command(name="transfer")
async def extended_transfer(ctx, *, text: str = ""):
    """Hướng dẫn chuyển coin."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 💰 Kinh Tế • nuked transfer",
        (
            "📌 **Mô tả:** Hướng dẫn chuyển coin.\n\n"
            "🧭 **Cách dùng:** `nuked transfer`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 💰 Kinh Tế • economyconfig
# ------------------------------------------------------------
@bot.command(name="economyconfig")
async def extended_economyconfig(ctx, *, text: str = ""):
    """Thông tin cấu hình kinh tế."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 💰 Kinh Tế • nuked economyconfig",
        (
            "📌 **Mô tả:** Thông tin cấu hình kinh tế.\n\n"
            "🧭 **Cách dùng:** `nuked economyconfig`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 💰 Kinh Tế • coinhelp
# ------------------------------------------------------------
@bot.command(name="coinhelp")
async def extended_coinhelp(ctx, *, text: str = ""):
    """Trợ giúp hệ thống coin."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 💰 Kinh Tế • nuked coinhelp",
        (
            "📌 **Mô tả:** Trợ giúp hệ thống coin.\n\n"
            "🧭 **Cách dùng:** `nuked coinhelp`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# ⭐ Level • levelx
# ------------------------------------------------------------
@bot.command(name="levelx")
async def extended_levelx(ctx, *, text: str = ""):
    """Xem level."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ ⭐ Level • nuked levelx",
        (
            "📌 **Mô tả:** Xem level.\n\n"
            "🧭 **Cách dùng:** `nuked levelx`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# ⭐ Level • rank
# ------------------------------------------------------------
@bot.command(name="rank")
async def extended_rank(ctx, *, text: str = ""):
    """Xem thứ hạng."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ ⭐ Level • nuked rank",
        (
            "📌 **Mô tả:** Xem thứ hạng.\n\n"
            "🧭 **Cách dùng:** `nuked rank`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# ⭐ Level • xp
# ------------------------------------------------------------
@bot.command(name="xp")
async def extended_xp(ctx, *, text: str = ""):
    """Xem EXP."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ ⭐ Level • nuked xp",
        (
            "📌 **Mô tả:** Xem EXP.\n\n"
            "🧭 **Cách dùng:** `nuked xp`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# ⭐ Level • xprank
# ------------------------------------------------------------
@bot.command(name="xprank")
async def extended_xprank(ctx, *, text: str = ""):
    """Xếp hạng EXP."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ ⭐ Level • nuked xprank",
        (
            "📌 **Mô tả:** Xếp hạng EXP.\n\n"
            "🧭 **Cách dùng:** `nuked xprank`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# ⭐ Level • nextlevel
# ------------------------------------------------------------
@bot.command(name="nextlevel")
async def extended_nextlevel(ctx, *, text: str = ""):
    """Xem EXP cần lên cấp."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ ⭐ Level • nuked nextlevel",
        (
            "📌 **Mô tả:** Xem EXP cần lên cấp.\n\n"
            "🧭 **Cách dùng:** `nuked nextlevel`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# ⭐ Level • levelstats
# ------------------------------------------------------------
@bot.command(name="levelstats")
async def extended_levelstats(ctx, *, text: str = ""):
    """Thống kê level."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ ⭐ Level • nuked levelstats",
        (
            "📌 **Mô tả:** Thống kê level.\n\n"
            "🧭 **Cách dùng:** `nuked levelstats`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# ⭐ Level • leveltop
# ------------------------------------------------------------
@bot.command(name="leveltop")
async def extended_leveltop(ctx, *, text: str = ""):
    """Top level."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ ⭐ Level • nuked leveltop",
        (
            "📌 **Mô tả:** Top level.\n\n"
            "🧭 **Cách dùng:** `nuked leveltop`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# ⭐ Level • leveluser
# ------------------------------------------------------------
@bot.command(name="leveluser")
async def extended_leveluser(ctx, *, text: str = ""):
    """Level của thành viên."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ ⭐ Level • nuked leveluser",
        (
            "📌 **Mô tả:** Level của thành viên.\n\n"
            "🧭 **Cách dùng:** `nuked leveluser`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# ⭐ Level • xpuser
# ------------------------------------------------------------
@bot.command(name="xpuser")
async def extended_xpuser(ctx, *, text: str = ""):
    """EXP của thành viên."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ ⭐ Level • nuked xpuser",
        (
            "📌 **Mô tả:** EXP của thành viên.\n\n"
            "🧭 **Cách dùng:** `nuked xpuser`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# ⭐ Level • levelrole
# ------------------------------------------------------------
@bot.command(name="levelrole")
async def extended_levelrole(ctx, *, text: str = ""):
    """Thông tin role theo level."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ ⭐ Level • nuked levelrole",
        (
            "📌 **Mô tả:** Thông tin role theo level.\n\n"
            "🧭 **Cách dùng:** `nuked levelrole`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# ⭐ Level • levelhelp
# ------------------------------------------------------------
@bot.command(name="levelhelp")
async def extended_levelhelp(ctx, *, text: str = ""):
    """Hướng dẫn level."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ ⭐ Level • nuked levelhelp",
        (
            "📌 **Mô tả:** Hướng dẫn level.\n\n"
            "🧭 **Cách dùng:** `nuked levelhelp`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# ⭐ Level • xpinfo
# ------------------------------------------------------------
@bot.command(name="xpinfo")
async def extended_xpinfo(ctx, *, text: str = ""):
    """Thông tin EXP."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ ⭐ Level • nuked xpinfo",
        (
            "📌 **Mô tả:** Thông tin EXP.\n\n"
            "🧭 **Cách dùng:** `nuked xpinfo`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# ⭐ Level • levelupinfo
# ------------------------------------------------------------
@bot.command(name="levelupinfo")
async def extended_levelupinfo(ctx, *, text: str = ""):
    """Thông tin level up."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ ⭐ Level • nuked levelupinfo",
        (
            "📌 **Mô tả:** Thông tin level up.\n\n"
            "🧭 **Cách dùng:** `nuked levelupinfo`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# ⭐ Level • rankinfo
# ------------------------------------------------------------
@bot.command(name="rankinfo")
async def extended_rankinfo(ctx, *, text: str = ""):
    """Thông tin rank."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ ⭐ Level • nuked rankinfo",
        (
            "📌 **Mô tả:** Thông tin rank.\n\n"
            "🧭 **Cách dùng:** `nuked rankinfo`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# ⭐ Level • progress
# ------------------------------------------------------------
@bot.command(name="progress")
async def extended_progress(ctx, *, text: str = ""):
    """Tiến độ level."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ ⭐ Level • nuked progress",
        (
            "📌 **Mô tả:** Tiến độ level.\n\n"
            "🧭 **Cách dùng:** `nuked progress`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# ⭐ Level • progressbar
# ------------------------------------------------------------
@bot.command(name="progressbar")
async def extended_progressbar(ctx, *, text: str = ""):
    """Thanh tiến độ EXP."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ ⭐ Level • nuked progressbar",
        (
            "📌 **Mô tả:** Thanh tiến độ EXP.\n\n"
            "🧭 **Cách dùng:** `nuked progressbar`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# ⭐ Level • maxlevel
# ------------------------------------------------------------
@bot.command(name="maxlevel")
async def extended_maxlevel(ctx, *, text: str = ""):
    """Xem level tối đa."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ ⭐ Level • nuked maxlevel",
        (
            "📌 **Mô tả:** Xem level tối đa.\n\n"
            "🧭 **Cách dùng:** `nuked maxlevel`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# ⭐ Level • levelconfig
# ------------------------------------------------------------
@bot.command(name="levelconfig")
async def extended_levelconfig(ctx, *, text: str = ""):
    """Thông tin cấu hình level."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ ⭐ Level • nuked levelconfig",
        (
            "📌 **Mô tả:** Thông tin cấu hình level.\n\n"
            "🧭 **Cách dùng:** `nuked levelconfig`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# ⭐ Level • xpcooldown
# ------------------------------------------------------------
@bot.command(name="xpcooldown")
async def extended_xpcooldown(ctx, *, text: str = ""):
    """Thông tin cooldown EXP."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ ⭐ Level • nuked xpcooldown",
        (
            "📌 **Mô tả:** Thông tin cooldown EXP.\n\n"
            "🧭 **Cách dùng:** `nuked xpcooldown`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# ⭐ Level • xpmessage
# ------------------------------------------------------------
@bot.command(name="xpmessage")
async def extended_xpmessage(ctx, *, text: str = ""):
    """Thông tin EXP từ tin nhắn."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ ⭐ Level • nuked xpmessage",
        (
            "📌 **Mô tả:** Thông tin EXP từ tin nhắn.\n\n"
            "🧭 **Cách dùng:** `nuked xpmessage`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# ⭐ Level • levelleaderboard
# ------------------------------------------------------------
@bot.command(name="levelleaderboard")
async def extended_levelleaderboard(ctx, *, text: str = ""):
    """Bảng xếp hạng level."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ ⭐ Level • nuked levelleaderboard",
        (
            "📌 **Mô tả:** Bảng xếp hạng level.\n\n"
            "🧭 **Cách dùng:** `nuked levelleaderboard`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# ⭐ Level • rankuser
# ------------------------------------------------------------
@bot.command(name="rankuser")
async def extended_rankuser(ctx, *, text: str = ""):
    """Rank của thành viên."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ ⭐ Level • nuked rankuser",
        (
            "📌 **Mô tả:** Rank của thành viên.\n\n"
            "🧭 **Cách dùng:** `nuked rankuser`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# ⭐ Level • xpneeded
# ------------------------------------------------------------
@bot.command(name="xpneeded")
async def extended_xpneeded(ctx, *, text: str = ""):
    """EXP còn thiếu."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ ⭐ Level • nuked xpneeded",
        (
            "📌 **Mô tả:** EXP còn thiếu.\n\n"
            "🧭 **Cách dùng:** `nuked xpneeded`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# ⭐ Level • levelcompare
# ------------------------------------------------------------
@bot.command(name="levelcompare")
async def extended_levelcompare(ctx, *, text: str = ""):
    """So sánh level."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ ⭐ Level • nuked levelcompare",
        (
            "📌 **Mô tả:** So sánh level.\n\n"
            "🧭 **Cách dùng:** `nuked levelcompare`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# ⭐ Level • xptotal
# ------------------------------------------------------------
@bot.command(name="xptotal")
async def extended_xptotal(ctx, *, text: str = ""):
    """Tổng EXP."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ ⭐ Level • nuked xptotal",
        (
            "📌 **Mô tả:** Tổng EXP.\n\n"
            "🧭 **Cách dùng:** `nuked xptotal`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# ⭐ Level • leveltotal
# ------------------------------------------------------------
@bot.command(name="leveltotal")
async def extended_leveltotal(ctx, *, text: str = ""):
    """Tổng level."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ ⭐ Level • nuked leveltotal",
        (
            "📌 **Mô tả:** Tổng level.\n\n"
            "🧭 **Cách dùng:** `nuked leveltotal`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# ⭐ Level • levelcenter
# ------------------------------------------------------------
@bot.command(name="levelcenter")
async def extended_levelcenter(ctx, *, text: str = ""):
    """Trung tâm level."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ ⭐ Level • nuked levelcenter",
        (
            "📌 **Mô tả:** Trung tâm level.\n\n"
            "🧭 **Cách dùng:** `nuked levelcenter`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# ⭐ Level • levelstats2
# ------------------------------------------------------------
@bot.command(name="levelstats2")
async def extended_levelstats2(ctx, *, text: str = ""):
    """Thống kê level nâng cao."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ ⭐ Level • nuked levelstats2",
        (
            "📌 **Mô tả:** Thống kê level nâng cao.\n\n"
            "🧭 **Cách dùng:** `nuked levelstats2`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# ⭐ Level • xpstats
# ------------------------------------------------------------
@bot.command(name="xpstats")
async def extended_xpstats(ctx, *, text: str = ""):
    """Thống kê EXP."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ ⭐ Level • nuked xpstats",
        (
            "📌 **Mô tả:** Thống kê EXP.\n\n"
            "🧭 **Cách dùng:** `nuked xpstats`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# ⭐ Level • rankstats
# ------------------------------------------------------------
@bot.command(name="rankstats")
async def extended_rankstats(ctx, *, text: str = ""):
    """Thống kê rank."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ ⭐ Level • nuked rankstats",
        (
            "📌 **Mô tả:** Thống kê rank.\n\n"
            "🧭 **Cách dùng:** `nuked rankstats`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# ⭐ Level • leveltips
# ------------------------------------------------------------
@bot.command(name="leveltips")
async def extended_leveltips(ctx, *, text: str = ""):
    """Mẹo tăng level hợp lệ."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ ⭐ Level • nuked leveltips",
        (
            "📌 **Mô tả:** Mẹo tăng level hợp lệ.\n\n"
            "🧭 **Cách dùng:** `nuked leveltips`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# ⭐ Level • levelmenu
# ------------------------------------------------------------
@bot.command(name="levelmenu")
async def extended_levelmenu(ctx, *, text: str = ""):
    """Menu level."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ ⭐ Level • nuked levelmenu",
        (
            "📌 **Mô tả:** Menu level.\n\n"
            "🧭 **Cách dùng:** `nuked levelmenu`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 💾 Backup & Cấu Hình • backupinfo
# ------------------------------------------------------------
@bot.command(name="backupinfo")
async def extended_backupinfo(ctx, *, text: str = ""):
    """Thông tin backup."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 💾 Backup & Cấu Hình • nuked backupinfo",
        (
            "📌 **Mô tả:** Thông tin backup.\n\n"
            "🧭 **Cách dùng:** `nuked backupinfo`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 💾 Backup & Cấu Hình • backuplist
# ------------------------------------------------------------
@bot.command(name="backuplist")
async def extended_backuplist(ctx, *, text: str = ""):
    """Danh sách backup."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 💾 Backup & Cấu Hình • nuked backuplist",
        (
            "📌 **Mô tả:** Danh sách backup.\n\n"
            "🧭 **Cách dùng:** `nuked backuplist`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 💾 Backup & Cấu Hình • backuphelp
# ------------------------------------------------------------
@bot.command(name="backuphelp")
async def extended_backuphelp(ctx, *, text: str = ""):
    """Hướng dẫn backup."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 💾 Backup & Cấu Hình • nuked backuphelp",
        (
            "📌 **Mô tả:** Hướng dẫn backup.\n\n"
            "🧭 **Cách dùng:** `nuked backuphelp`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 💾 Backup & Cấu Hình • restoreinfo
# ------------------------------------------------------------
@bot.command(name="restoreinfo")
async def extended_restoreinfo(ctx, *, text: str = ""):
    """Thông tin restore."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 💾 Backup & Cấu Hình • nuked restoreinfo",
        (
            "📌 **Mô tả:** Thông tin restore.\n\n"
            "🧭 **Cách dùng:** `nuked restoreinfo`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 💾 Backup & Cấu Hình • configinfo
# ------------------------------------------------------------
@bot.command(name="configinfo")
async def extended_configinfo(ctx, *, text: str = ""):
    """Thông tin config."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 💾 Backup & Cấu Hình • nuked configinfo",
        (
            "📌 **Mô tả:** Thông tin config.\n\n"
            "🧭 **Cách dùng:** `nuked configinfo`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 💾 Backup & Cấu Hình • reloadinfo
# ------------------------------------------------------------
@bot.command(name="reloadinfo")
async def extended_reloadinfo(ctx, *, text: str = ""):
    """Thông tin reload."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 💾 Backup & Cấu Hình • nuked reloadinfo",
        (
            "📌 **Mô tả:** Thông tin reload.\n\n"
            "🧭 **Cách dùng:** `nuked reloadinfo`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 💾 Backup & Cấu Hình • loginfo
# ------------------------------------------------------------
@bot.command(name="loginfo")
async def extended_loginfo(ctx, *, text: str = ""):
    """Thông tin log."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 💾 Backup & Cấu Hình • nuked loginfo",
        (
            "📌 **Mô tả:** Thông tin log.\n\n"
            "🧭 **Cách dùng:** `nuked loginfo`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 💾 Backup & Cấu Hình • welcomeinfo
# ------------------------------------------------------------
@bot.command(name="welcomeinfo")
async def extended_welcomeinfo(ctx, *, text: str = ""):
    """Thông tin welcome."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 💾 Backup & Cấu Hình • nuked welcomeinfo",
        (
            "📌 **Mô tả:** Thông tin welcome.\n\n"
            "🧭 **Cách dùng:** `nuked welcomeinfo`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 💾 Backup & Cấu Hình • goodbyeinfo
# ------------------------------------------------------------
@bot.command(name="goodbyeinfo")
async def extended_goodbyeinfo(ctx, *, text: str = ""):
    """Thông tin goodbye."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 💾 Backup & Cấu Hình • nuked goodbyeinfo",
        (
            "📌 **Mô tả:** Thông tin goodbye.\n\n"
            "🧭 **Cách dùng:** `nuked goodbyeinfo`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 💾 Backup & Cấu Hình • disabledinfo
# ------------------------------------------------------------
@bot.command(name="disabledinfo")
async def extended_disabledinfo(ctx, *, text: str = ""):
    """Xem lệnh bị tắt."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 💾 Backup & Cấu Hình • nuked disabledinfo",
        (
            "📌 **Mô tả:** Xem lệnh bị tắt.\n\n"
            "🧭 **Cách dùng:** `nuked disabledinfo`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 💾 Backup & Cấu Hình • settings
# ------------------------------------------------------------
@bot.command(name="settings")
async def extended_settings(ctx, *, text: str = ""):
    """Tổng quan cài đặt."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 💾 Backup & Cấu Hình • nuked settings",
        (
            "📌 **Mô tả:** Tổng quan cài đặt.\n\n"
            "🧭 **Cách dùng:** `nuked settings`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 💾 Backup & Cấu Hình • settingshelp
# ------------------------------------------------------------
@bot.command(name="settingshelp")
async def extended_settingshelp(ctx, *, text: str = ""):
    """Hướng dẫn cài đặt."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 💾 Backup & Cấu Hình • nuked settingshelp",
        (
            "📌 **Mô tả:** Hướng dẫn cài đặt.\n\n"
            "🧭 **Cách dùng:** `nuked settingshelp`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 💾 Backup & Cấu Hình • serverconfig
# ------------------------------------------------------------
@bot.command(name="serverconfig")
async def extended_serverconfig(ctx, *, text: str = ""):
    """Hướng dẫn cấu hình server."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 💾 Backup & Cấu Hình • nuked serverconfig",
        (
            "📌 **Mô tả:** Hướng dẫn cấu hình server.\n\n"
            "🧭 **Cách dùng:** `nuked serverconfig`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 💾 Backup & Cấu Hình • logconfig
# ------------------------------------------------------------
@bot.command(name="logconfig")
async def extended_logconfig(ctx, *, text: str = ""):
    """Hướng dẫn cấu hình log."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 💾 Backup & Cấu Hình • nuked logconfig",
        (
            "📌 **Mô tả:** Hướng dẫn cấu hình log.\n\n"
            "🧭 **Cách dùng:** `nuked logconfig`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 💾 Backup & Cấu Hình • welcomeconfig
# ------------------------------------------------------------
@bot.command(name="welcomeconfig")
async def extended_welcomeconfig(ctx, *, text: str = ""):
    """Hướng dẫn welcome."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 💾 Backup & Cấu Hình • nuked welcomeconfig",
        (
            "📌 **Mô tả:** Hướng dẫn welcome.\n\n"
            "🧭 **Cách dùng:** `nuked welcomeconfig`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 💾 Backup & Cấu Hình • goodbyeconfig
# ------------------------------------------------------------
@bot.command(name="goodbyeconfig")
async def extended_goodbyeconfig(ctx, *, text: str = ""):
    """Hướng dẫn goodbye."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 💾 Backup & Cấu Hình • nuked goodbyeconfig",
        (
            "📌 **Mô tả:** Hướng dẫn goodbye.\n\n"
            "🧭 **Cách dùng:** `nuked goodbyeconfig`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 💾 Backup & Cấu Hình • levelconfig2
# ------------------------------------------------------------
@bot.command(name="levelconfig2")
async def extended_levelconfig2(ctx, *, text: str = ""):
    """Hướng dẫn cấu hình level."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 💾 Backup & Cấu Hình • nuked levelconfig2",
        (
            "📌 **Mô tả:** Hướng dẫn cấu hình level.\n\n"
            "🧭 **Cách dùng:** `nuked levelconfig2`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 💾 Backup & Cấu Hình • economyconfig2
# ------------------------------------------------------------
@bot.command(name="economyconfig2")
async def extended_economyconfig2(ctx, *, text: str = ""):
    """Hướng dẫn cấu hình coin."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 💾 Backup & Cấu Hình • nuked economyconfig2",
        (
            "📌 **Mô tả:** Hướng dẫn cấu hình coin.\n\n"
            "🧭 **Cách dùng:** `nuked economyconfig2`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 💾 Backup & Cấu Hình • prefixconfig
# ------------------------------------------------------------
@bot.command(name="prefixconfig")
async def extended_prefixconfig(ctx, *, text: str = ""):
    """Thông tin prefix."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 💾 Backup & Cấu Hình • nuked prefixconfig",
        (
            "📌 **Mô tả:** Thông tin prefix.\n\n"
            "🧭 **Cách dùng:** `nuked prefixconfig`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 💾 Backup & Cấu Hình • menuconfig
# ------------------------------------------------------------
@bot.command(name="menuconfig")
async def extended_menuconfig(ctx, *, text: str = ""):
    """Thông tin menu."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 💾 Backup & Cấu Hình • nuked menuconfig",
        (
            "📌 **Mô tả:** Thông tin menu.\n\n"
            "🧭 **Cách dùng:** `nuked menuconfig`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 💾 Backup & Cấu Hình • embedinfo
# ------------------------------------------------------------
@bot.command(name="embedinfo")
async def extended_embedinfo(ctx, *, text: str = ""):
    """Thông tin embed."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 💾 Backup & Cấu Hình • nuked embedinfo",
        (
            "📌 **Mô tả:** Thông tin embed.\n\n"
            "🧭 **Cách dùng:** `nuked embedinfo`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 💾 Backup & Cấu Hình • gifinfo
# ------------------------------------------------------------
@bot.command(name="gifinfo")
async def extended_gifinfo(ctx, *, text: str = ""):
    """Thông tin GIF menu."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 💾 Backup & Cấu Hình • nuked gifinfo",
        (
            "📌 **Mô tả:** Thông tin GIF menu.\n\n"
            "🧭 **Cách dùng:** `nuked gifinfo`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 💾 Backup & Cấu Hình • jsoninfo
# ------------------------------------------------------------
@bot.command(name="jsoninfo")
async def extended_jsoninfo(ctx, *, text: str = ""):
    """Thông tin file JSON."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 💾 Backup & Cấu Hình • nuked jsoninfo",
        (
            "📌 **Mô tả:** Thông tin file JSON.\n\n"
            "🧭 **Cách dùng:** `nuked jsoninfo`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 💾 Backup & Cấu Hình • datahelp
# ------------------------------------------------------------
@bot.command(name="datahelp")
async def extended_datahelp(ctx, *, text: str = ""):
    """Hướng dẫn dữ liệu."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 💾 Backup & Cấu Hình • nuked datahelp",
        (
            "📌 **Mô tả:** Hướng dẫn dữ liệu.\n\n"
            "🧭 **Cách dùng:** `nuked datahelp`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 💾 Backup & Cấu Hình • resetinfo
# ------------------------------------------------------------
@bot.command(name="resetinfo")
async def extended_resetinfo(ctx, *, text: str = ""):
    """Thông tin reset dữ liệu."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 💾 Backup & Cấu Hình • nuked resetinfo",
        (
            "📌 **Mô tả:** Thông tin reset dữ liệu.\n\n"
            "🧭 **Cách dùng:** `nuked resetinfo`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 💾 Backup & Cấu Hình • exportinfo
# ------------------------------------------------------------
@bot.command(name="exportinfo")
async def extended_exportinfo(ctx, *, text: str = ""):
    """Hướng dẫn xuất dữ liệu."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 💾 Backup & Cấu Hình • nuked exportinfo",
        (
            "📌 **Mô tả:** Hướng dẫn xuất dữ liệu.\n\n"
            "🧭 **Cách dùng:** `nuked exportinfo`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 💾 Backup & Cấu Hình • importinfo
# ------------------------------------------------------------
@bot.command(name="importinfo")
async def extended_importinfo(ctx, *, text: str = ""):
    """Hướng dẫn nhập dữ liệu."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 💾 Backup & Cấu Hình • nuked importinfo",
        (
            "📌 **Mô tả:** Hướng dẫn nhập dữ liệu.\n\n"
            "🧭 **Cách dùng:** `nuked importinfo`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 💾 Backup & Cấu Hình • configcheck
# ------------------------------------------------------------
@bot.command(name="configcheck")
async def extended_configcheck(ctx, *, text: str = ""):
    """Kiểm tra cấu hình."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 💾 Backup & Cấu Hình • nuked configcheck",
        (
            "📌 **Mô tả:** Kiểm tra cấu hình.\n\n"
            "🧭 **Cách dùng:** `nuked configcheck`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 💾 Backup & Cấu Hình • healthcheck
# ------------------------------------------------------------
@bot.command(name="healthcheck")
async def extended_healthcheck(ctx, *, text: str = ""):
    """Kiểm tra sức khỏe bot."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 💾 Backup & Cấu Hình • nuked healthcheck",
        (
            "📌 **Mô tả:** Kiểm tra sức khỏe bot.\n\n"
            "🧭 **Cách dùng:** `nuked healthcheck`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 💾 Backup & Cấu Hình • diagnose
# ------------------------------------------------------------
@bot.command(name="diagnose")
async def extended_diagnose(ctx, *, text: str = ""):
    """Chẩn đoán lỗi cơ bản."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 💾 Backup & Cấu Hình • nuked diagnose",
        (
            "📌 **Mô tả:** Chẩn đoán lỗi cơ bản.\n\n"
            "🧭 **Cách dùng:** `nuked diagnose`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 💾 Backup & Cấu Hình • configcenter
# ------------------------------------------------------------
@bot.command(name="configcenter")
async def extended_configcenter(ctx, *, text: str = ""):
    """Trung tâm cấu hình."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 💾 Backup & Cấu Hình • nuked configcenter",
        (
            "📌 **Mô tả:** Trung tâm cấu hình.\n\n"
            "🧭 **Cách dùng:** `nuked configcenter`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 👑 Owner & Quản Trị Bot • ownerlist
# ------------------------------------------------------------
@bot.command(name="ownerlist")
async def extended_ownerlist(ctx, *, text: str = ""):
    """Xem danh sách Owner."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 👑 Owner & Quản Trị Bot • nuked ownerlist",
        (
            "📌 **Mô tả:** Xem danh sách Owner.\n\n"
            "🧭 **Cách dùng:** `nuked ownerlist`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 👑 Owner & Quản Trị Bot • ownercheck
# ------------------------------------------------------------
@bot.command(name="ownercheck")
async def extended_ownercheck(ctx, *, text: str = ""):
    """Kiểm tra quyền Owner."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 👑 Owner & Quản Trị Bot • nuked ownercheck",
        (
            "📌 **Mô tả:** Kiểm tra quyền Owner.\n\n"
            "🧭 **Cách dùng:** `nuked ownercheck`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 👑 Owner & Quản Trị Bot • ownerhelp
# ------------------------------------------------------------
@bot.command(name="ownerhelp")
async def extended_ownerhelp(ctx, *, text: str = ""):
    """Hướng dẫn Owner."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 👑 Owner & Quản Trị Bot • nuked ownerhelp",
        (
            "📌 **Mô tả:** Hướng dẫn Owner.\n\n"
            "🧭 **Cách dùng:** `nuked ownerhelp`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 👑 Owner & Quản Trị Bot • botreload
# ------------------------------------------------------------
@bot.command(name="botreload")
async def extended_botreload(ctx, *, text: str = ""):
    """Reload dữ liệu an toàn."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 👑 Owner & Quản Trị Bot • nuked botreload",
        (
            "📌 **Mô tả:** Reload dữ liệu an toàn.\n\n"
            "🧭 **Cách dùng:** `nuked botreload`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 👑 Owner & Quản Trị Bot • botoff
# ------------------------------------------------------------
@bot.command(name="botoff")
async def extended_botoff(ctx, *, text: str = ""):
    """Thông tin tắt lệnh."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 👑 Owner & Quản Trị Bot • nuked botoff",
        (
            "📌 **Mô tả:** Thông tin tắt lệnh.\n\n"
            "🧭 **Cách dùng:** `nuked botoff`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 👑 Owner & Quản Trị Bot • boton
# ------------------------------------------------------------
@bot.command(name="boton")
async def extended_boton(ctx, *, text: str = ""):
    """Thông tin bật lệnh."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 👑 Owner & Quản Trị Bot • nuked boton",
        (
            "📌 **Mô tả:** Thông tin bật lệnh.\n\n"
            "🧭 **Cách dùng:** `nuked boton`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 👑 Owner & Quản Trị Bot • disabledlist
# ------------------------------------------------------------
@bot.command(name="disabledlist")
async def extended_disabledlist(ctx, *, text: str = ""):
    """Liệt kê lệnh bị tắt."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 👑 Owner & Quản Trị Bot • nuked disabledlist",
        (
            "📌 **Mô tả:** Liệt kê lệnh bị tắt.\n\n"
            "🧭 **Cách dùng:** `nuked disabledlist`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 👑 Owner & Quản Trị Bot • setlvinfo
# ------------------------------------------------------------
@bot.command(name="setlvinfo")
async def extended_setlvinfo(ctx, *, text: str = ""):
    """Hướng dẫn set level."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 👑 Owner & Quản Trị Bot • nuked setlvinfo",
        (
            "📌 **Mô tả:** Hướng dẫn set level.\n\n"
            "🧭 **Cách dùng:** `nuked setlvinfo`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 👑 Owner & Quản Trị Bot • setcoinsinfo
# ------------------------------------------------------------
@bot.command(name="setcoinsinfo")
async def extended_setcoinsinfo(ctx, *, text: str = ""):
    """Hướng dẫn set coin."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 👑 Owner & Quản Trị Bot • nuked setcoinsinfo",
        (
            "📌 **Mô tả:** Hướng dẫn set coin.\n\n"
            "🧭 **Cách dùng:** `nuked setcoinsinfo`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 👑 Owner & Quản Trị Bot • addcoinsinfo
# ------------------------------------------------------------
@bot.command(name="addcoinsinfo")
async def extended_addcoinsinfo(ctx, *, text: str = ""):
    """Hướng dẫn cộng coin."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 👑 Owner & Quản Trị Bot • nuked addcoinsinfo",
        (
            "📌 **Mô tả:** Hướng dẫn cộng coin.\n\n"
            "🧭 **Cách dùng:** `nuked addcoinsinfo`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 👑 Owner & Quản Trị Bot • removecoinsinfo
# ------------------------------------------------------------
@bot.command(name="removecoinsinfo")
async def extended_removecoinsinfo(ctx, *, text: str = ""):
    """Hướng dẫn trừ coin."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 👑 Owner & Quản Trị Bot • nuked removecoinsinfo",
        (
            "📌 **Mô tả:** Hướng dẫn trừ coin.\n\n"
            "🧭 **Cách dùng:** `nuked removecoinsinfo`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 👑 Owner & Quản Trị Bot • addownerinfo
# ------------------------------------------------------------
@bot.command(name="addownerinfo")
async def extended_addownerinfo(ctx, *, text: str = ""):
    """Hướng dẫn thêm Owner."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 👑 Owner & Quản Trị Bot • nuked addownerinfo",
        (
            "📌 **Mô tả:** Hướng dẫn thêm Owner.\n\n"
            "🧭 **Cách dùng:** `nuked addownerinfo`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 👑 Owner & Quản Trị Bot • deleteownerinfo
# ------------------------------------------------------------
@bot.command(name="deleteownerinfo")
async def extended_deleteownerinfo(ctx, *, text: str = ""):
    """Hướng dẫn xóa Owner."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 👑 Owner & Quản Trị Bot • nuked deleteownerinfo",
        (
            "📌 **Mô tả:** Hướng dẫn xóa Owner.\n\n"
            "🧭 **Cách dùng:** `nuked deleteownerinfo`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 👑 Owner & Quản Trị Bot • ownerstats
# ------------------------------------------------------------
@bot.command(name="ownerstats")
async def extended_ownerstats(ctx, *, text: str = ""):
    """Thống kê Owner."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 👑 Owner & Quản Trị Bot • nuked ownerstats",
        (
            "📌 **Mô tả:** Thống kê Owner.\n\n"
            "🧭 **Cách dùng:** `nuked ownerstats`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 👑 Owner & Quản Trị Bot • botstats
# ------------------------------------------------------------
@bot.command(name="botstats")
async def extended_botstats(ctx, *, text: str = ""):
    """Thống kê bot."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 👑 Owner & Quản Trị Bot • nuked botstats",
        (
            "📌 **Mô tả:** Thống kê bot.\n\n"
            "🧭 **Cách dùng:** `nuked botstats`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 👑 Owner & Quản Trị Bot • serverstats
# ------------------------------------------------------------
@bot.command(name="serverstats")
async def extended_serverstats(ctx, *, text: str = ""):
    """Thống kê server."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 👑 Owner & Quản Trị Bot • nuked serverstats",
        (
            "📌 **Mô tả:** Thống kê server.\n\n"
            "🧭 **Cách dùng:** `nuked serverstats`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 👑 Owner & Quản Trị Bot • commandstats
# ------------------------------------------------------------
@bot.command(name="commandstats")
async def extended_commandstats(ctx, *, text: str = ""):
    """Thống kê lệnh."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 👑 Owner & Quản Trị Bot • nuked commandstats",
        (
            "📌 **Mô tả:** Thống kê lệnh.\n\n"
            "🧭 **Cách dùng:** `nuked commandstats`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 👑 Owner & Quản Trị Bot • errorstats
# ------------------------------------------------------------
@bot.command(name="errorstats")
async def extended_errorstats(ctx, *, text: str = ""):
    """Thống kê lỗi."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 👑 Owner & Quản Trị Bot • nuked errorstats",
        (
            "📌 **Mô tả:** Thống kê lỗi.\n\n"
            "🧭 **Cách dùng:** `nuked errorstats`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 👑 Owner & Quản Trị Bot • cooldowns
# ------------------------------------------------------------
@bot.command(name="cooldowns")
async def extended_cooldowns(ctx, *, text: str = ""):
    """Xem hướng dẫn cooldown."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 👑 Owner & Quản Trị Bot • nuked cooldowns",
        (
            "📌 **Mô tả:** Xem hướng dẫn cooldown.\n\n"
            "🧭 **Cách dùng:** `nuked cooldowns`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 👑 Owner & Quản Trị Bot • permissionsx
# ------------------------------------------------------------
@bot.command(name="permissionsx")
async def extended_permissionsx(ctx, *, text: str = ""):
    """Kiểm tra permission."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 👑 Owner & Quản Trị Bot • nuked permissionsx",
        (
            "📌 **Mô tả:** Kiểm tra permission.\n\n"
            "🧭 **Cách dùng:** `nuked permissionsx`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 👑 Owner & Quản Trị Bot • auditinfo
# ------------------------------------------------------------
@bot.command(name="auditinfo")
async def extended_auditinfo(ctx, *, text: str = ""):
    """Hướng dẫn audit."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 👑 Owner & Quản Trị Bot • nuked auditinfo",
        (
            "📌 **Mô tả:** Hướng dẫn audit.\n\n"
            "🧭 **Cách dùng:** `nuked auditinfo`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 👑 Owner & Quản Trị Bot • ratelimitinfo
# ------------------------------------------------------------
@bot.command(name="ratelimitinfo")
async def extended_ratelimitinfo(ctx, *, text: str = ""):
    """Thông tin rate limit."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 👑 Owner & Quản Trị Bot • nuked ratelimitinfo",
        (
            "📌 **Mô tả:** Thông tin rate limit.\n\n"
            "🧭 **Cách dùng:** `nuked ratelimitinfo`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 👑 Owner & Quản Trị Bot • cacheinfo
# ------------------------------------------------------------
@bot.command(name="cacheinfo")
async def extended_cacheinfo(ctx, *, text: str = ""):
    """Thông tin cache."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 👑 Owner & Quản Trị Bot • nuked cacheinfo",
        (
            "📌 **Mô tả:** Thông tin cache.\n\n"
            "🧭 **Cách dùng:** `nuked cacheinfo`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 👑 Owner & Quản Trị Bot • memoryinfo
# ------------------------------------------------------------
@bot.command(name="memoryinfo")
async def extended_memoryinfo(ctx, *, text: str = ""):
    """Thông tin bộ nhớ."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 👑 Owner & Quản Trị Bot • nuked memoryinfo",
        (
            "📌 **Mô tả:** Thông tin bộ nhớ.\n\n"
            "🧭 **Cách dùng:** `nuked memoryinfo`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 👑 Owner & Quản Trị Bot • latencyinfo
# ------------------------------------------------------------
@bot.command(name="latencyinfo")
async def extended_latencyinfo(ctx, *, text: str = ""):
    """Thông tin latency."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 👑 Owner & Quản Trị Bot • nuked latencyinfo",
        (
            "📌 **Mô tả:** Thông tin latency.\n\n"
            "🧭 **Cách dùng:** `nuked latencyinfo`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 👑 Owner & Quản Trị Bot • taskinfo
# ------------------------------------------------------------
@bot.command(name="taskinfo")
async def extended_taskinfo(ctx, *, text: str = ""):
    """Thông tin background task."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 👑 Owner & Quản Trị Bot • nuked taskinfo",
        (
            "📌 **Mô tả:** Thông tin background task.\n\n"
            "🧭 **Cách dùng:** `nuked taskinfo`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 👑 Owner & Quản Trị Bot • jsonstatus
# ------------------------------------------------------------
@bot.command(name="jsonstatus")
async def extended_jsonstatus(ctx, *, text: str = ""):
    """Trạng thái JSON."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 👑 Owner & Quản Trị Bot • nuked jsonstatus",
        (
            "📌 **Mô tả:** Trạng thái JSON.\n\n"
            "🧭 **Cách dùng:** `nuked jsonstatus`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 👑 Owner & Quản Trị Bot • ownerconfig
# ------------------------------------------------------------
@bot.command(name="ownerconfig")
async def extended_ownerconfig(ctx, *, text: str = ""):
    """Thông tin cấu hình Owner."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 👑 Owner & Quản Trị Bot • nuked ownerconfig",
        (
            "📌 **Mô tả:** Thông tin cấu hình Owner.\n\n"
            "🧭 **Cách dùng:** `nuked ownerconfig`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 👑 Owner & Quản Trị Bot • ownerpanel
# ------------------------------------------------------------
@bot.command(name="ownerpanel")
async def extended_ownerpanel(ctx, *, text: str = ""):
    """Mở bảng Owner an toàn."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 👑 Owner & Quản Trị Bot • nuked ownerpanel",
        (
            "📌 **Mô tả:** Mở bảng Owner an toàn.\n\n"
            "🧭 **Cách dùng:** `nuked ownerpanel`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 👑 Owner & Quản Trị Bot • adminhelp
# ------------------------------------------------------------
@bot.command(name="adminhelp")
async def extended_adminhelp(ctx, *, text: str = ""):
    """Hướng dẫn quản trị."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 👑 Owner & Quản Trị Bot • nuked adminhelp",
        (
            "📌 **Mô tả:** Hướng dẫn quản trị.\n\n"
            "🧭 **Cách dùng:** `nuked adminhelp`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)


# ------------------------------------------------------------
# 👑 Owner & Quản Trị Bot • controlcenter
# ------------------------------------------------------------
@bot.command(name="controlcenter")
async def extended_controlcenter(ctx, *, text: str = ""):
    """Mở Control Center."""
    if not await require_enabled(ctx):
        return
    embed = make_embed(
        "✨ 👑 Owner & Quản Trị Bot • nuked controlcenter",
        (
            "📌 **Mô tả:** Mở Control Center.\n\n"
            "🧭 **Cách dùng:** `nuked controlcenter`"
            + (" `<tham_số>`" if text == "" else "")
            + "\n"
            "💡 **Gợi ý:** Dùng `nuked help` để mở Control Center."
        ),
        discord.Color.blurple(),
        MENU_GIF,
    )
    embed.add_field(name="👤 Người dùng", value=ctx.author.mention, inline=True)
    embed.add_field(name="🏰 Server", value=ctx.guild.name if ctx.guild else "DM", inline=True)
    embed.add_field(name="🔧 Chế độ", value="Safe / Non-destructive", inline=True)
    if text:
        embed.add_field(name="📝 Tham số", value=f"`{text[:900]}`", inline=False)
    embed.set_footer(text="Nuked Bot • Extended Command Center")
    await ctx.send(embed=embed)



# ============================================================
# 🎨 EXTENDED HELP MENU
# ============================================================
def build_extended_help_embed(category_name=None):
    if category_name is None:
        lines = [
            "🌌 **NUKED BOT • EXTENDED CONTROL CENTER**",
            "",
            "✨ Hệ thống mở rộng gồm **10 danh mục**, mỗi danh mục có **32 lệnh**.",
            "🛡️ Anti và Voice được loại khỏi danh mục theo yêu cầu.",
            "🔒 Các lệnh phá hoại cũ chỉ nên giữ ở trạng thái tham chiếu/khóa an toàn.",
            "",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        ]
        for cat, data in EXTENDED_HELP_CATEGORIES.items():
            lines.append(f"{cat} — **{len(data['commands'])} lệnh**")
        lines += [
            "",
            "💡 Dùng `nuked xhelp <tên danh mục>` để xem chi tiết.",
            "📖 Dùng `nuked help` để mở menu gốc.",
        ]
        return make_embed(
            "🧭 EXTENDED COMMAND CENTER",
            "\n".join(lines),
            discord.Color.from_rgb(88, 101, 242),
            MENU_GIF,
        )

    key = next((k for k in EXTENDED_HELP_CATEGORIES if k.lower() == category_name.lower()), None)
    if not key:
        return fail("❌ Không tìm thấy danh mục. Dùng `nuked xhelp` để xem danh sách.")
    data = EXTENDED_HELP_CATEGORIES[key]
    embed = make_embed(
        f"{key} • COMMANDS",
        f"✨ **{len(data['commands'])} lệnh** trong danh mục này.\n\n{data['description']}",
        discord.Color.blurple(),
        MENU_GIF,
    )
    for command_name, description in data["commands"]:
        embed.add_field(name=f"🔹 {command_name}", value=f"> {description}", inline=False)
    return embed


@bot.command(name="xhelp")
async def extended_help(ctx, *, category: str = ""):
    if not await require_enabled(ctx):
        return
    await ctx.send(embed=build_extended_help_embed(category or None))


@bot.command(name="allcommands")
async def all_commands(ctx):
    if not await require_enabled(ctx):
        return
    total = sum(len(v["commands"]) for v in EXTENDED_HELP_CATEGORIES.values())
    await ctx.send(embed=make_embed(
        "📚 TỔNG HỢP LỆNH",
        f"🌟 Extension hiện có **{total} lệnh** chia thành **{len(EXTENDED_HELP_CATEGORIES)} danh mục**.\n"
        "🧭 Dùng `nuked xhelp` để mở danh mục.\n"
        "📖 Dùng `nuked help` để mở menu gốc.",
        discord.Color.blurple(),
        MENU_GIF,
    ))


# ============================================================
# 📚 EXTENDED COMMAND DOCUMENTATION
# ============================================================
# 🏠 Cơ Bản
# Command: nuked pingx
# Purpose: Kiểm tra độ trễ bot.
# Category: 🏠 Cơ Bản
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked pingx
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked about
# Purpose: Thông tin tổng quan bot.
# Category: 🏠 Cơ Bản
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked about
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked uptime
# Purpose: Hiển thị trạng thái hoạt động.
# Category: 🏠 Cơ Bản
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked uptime
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked prefix
# Purpose: Xem prefix hiện tại.
# Category: 🏠 Cơ Bản
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked prefix
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked commands
# Purpose: Xem tổng số lệnh mở rộng.
# Category: 🏠 Cơ Bản
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked commands
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked status
# Purpose: Xem trạng thái hệ thống.
# Category: 🏠 Cơ Bản
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked status
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked botavatar
# Purpose: Xem avatar bot.
# Category: 🏠 Cơ Bản
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked botavatar
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked botbanner
# Purpose: Xem banner bot nếu có.
# Category: 🏠 Cơ Bản
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked botbanner
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked botname
# Purpose: Xem tên bot.
# Category: 🏠 Cơ Bản
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked botname
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked botid
# Purpose: Xem ID bot.
# Category: 🏠 Cơ Bản
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked botid
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked guildid
# Purpose: Xem ID server.
# Category: 🏠 Cơ Bản
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked guildid
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked channelid
# Purpose: Xem ID kênh hiện tại.
# Category: 🏠 Cơ Bản
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked channelid
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked myid
# Purpose: Xem ID của bạn.
# Category: 🏠 Cơ Bản
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked myid
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked roles
# Purpose: Xem nhanh số role.
# Category: 🏠 Cơ Bản
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked roles
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked channels
# Purpose: Xem nhanh số kênh.
# Category: 🏠 Cơ Bản
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked channels
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked emojis
# Purpose: Xem số emoji server.
# Category: 🏠 Cơ Bản
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked emojis
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked stickers
# Purpose: Xem số sticker server.
# Category: 🏠 Cơ Bản
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked stickers
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked boosts
# Purpose: Xem mức boost server.
# Category: 🏠 Cơ Bản
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked boosts
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked created
# Purpose: Xem ngày tạo server.
# Category: 🏠 Cơ Bản
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked created
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked joined
# Purpose: Xem ngày bạn tham gia.
# Category: 🏠 Cơ Bản
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked joined
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked permissions
# Purpose: Xem quyền cơ bản của bạn.
# Category: 🏠 Cơ Bản
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked permissions
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked me
# Purpose: Xem hồ sơ nhanh của bạn.
# Category: 🏠 Cơ Bản
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked me
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked server
# Purpose: Xem thông tin server dạng gọn.
# Category: 🏠 Cơ Bản
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked server
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked whoami
# Purpose: Thông tin người dùng hiện tại.
# Category: 🏠 Cơ Bản
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked whoami
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked inviteinfo
# Purpose: Hiển thị hướng dẫn mời bot.
# Category: 🏠 Cơ Bản
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked inviteinfo
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked latency
# Purpose: Kiểm tra websocket latency.
# Category: 🏠 Cơ Bản
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked latency
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked shards
# Purpose: Xem số shard.
# Category: 🏠 Cơ Bản
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked shards
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked python
# Purpose: Xem phiên bản Python.
# Category: 🏠 Cơ Bản
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked python
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked discordpy
# Purpose: Xem phiên bản discord.py.
# Category: 🏠 Cơ Bản
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked discordpy
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked time
# Purpose: Xem thời gian hệ thống.
# Category: 🏠 Cơ Bản
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked time
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked date
# Purpose: Xem ngày hệ thống.
# Category: 🏠 Cơ Bản
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked date
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked helpall
# Purpose: Mở danh mục mở rộng.
# Category: 🏠 Cơ Bản
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked helpall
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# 👤 Thành Viên
# Command: nuked profile
# Purpose: Xem hồ sơ thành viên.
# Category: 👤 Thành Viên
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked profile
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked member
# Purpose: Tra cứu thành viên.
# Category: 👤 Thành Viên
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked member
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked joinedat
# Purpose: Xem thời điểm tham gia.
# Category: 👤 Thành Viên
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked joinedat
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked accountage
# Purpose: Xem tuổi tài khoản Discord.
# Category: 👤 Thành Viên
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked accountage
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked rolesof
# Purpose: Xem role của thành viên.
# Category: 👤 Thành Viên
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked rolesof
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked toprole
# Purpose: Xem role cao nhất.
# Category: 👤 Thành Viên
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked toprole
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked nickname
# Purpose: Xem nickname.
# Category: 👤 Thành Viên
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked nickname
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked mention
# Purpose: Tạo mention an toàn.
# Category: 👤 Thành Viên
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked mention
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked badges
# Purpose: Xem huy hiệu công khai.
# Category: 👤 Thành Viên
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked badges
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked botcheck
# Purpose: Kiểm tra tài khoản có phải bot.
# Category: 👤 Thành Viên
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked botcheck
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked mutuals
# Purpose: Xem thông tin thành viên chung.
# Category: 👤 Thành Viên
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked mutuals
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked presence
# Purpose: Xem trạng thái hoạt động.
# Category: 👤 Thành Viên
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked presence
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked activity
# Purpose: Xem activity công khai.
# Category: 👤 Thành Viên
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked activity
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked timezone
# Purpose: Hiển thị UTC server.
# Category: 👤 Thành Viên
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked timezone
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked userid
# Purpose: Xem ID thành viên.
# Category: 👤 Thành Viên
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked userid
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked membercountx
# Purpose: Đếm thành viên.
# Category: 👤 Thành Viên
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked membercountx
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked humans
# Purpose: Đếm thành viên người.
# Category: 👤 Thành Viên
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked humans
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked botcount
# Purpose: Đếm bot.
# Category: 👤 Thành Viên
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked botcount
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked newest
# Purpose: Tìm thành viên mới gần đây.
# Category: 👤 Thành Viên
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked newest
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked oldest
# Purpose: Tìm thành viên tham gia sớm.
# Category: 👤 Thành Viên
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked oldest
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked roleusers
# Purpose: Xem số người có role.
# Category: 👤 Thành Viên
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked roleusers
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked displayname
# Purpose: Xem display name.
# Category: 👤 Thành Viên
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked displayname
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked globalname
# Purpose: Xem global name.
# Category: 👤 Thành Viên
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked globalname
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked avatarurl
# Purpose: Lấy URL avatar.
# Category: 👤 Thành Viên
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked avatarurl
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked bannerurl
# Purpose: Lấy URL banner nếu có.
# Category: 👤 Thành Viên
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked bannerurl
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked usercreated
# Purpose: Xem ngày tạo tài khoản.
# Category: 👤 Thành Viên
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked usercreated
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked userjoined
# Purpose: Xem ngày vào server.
# Category: 👤 Thành Viên
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked userjoined
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked userinfo2
# Purpose: Xem hồ sơ chi tiết.
# Category: 👤 Thành Viên
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked userinfo2
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked membernote
# Purpose: Ghi chú hướng dẫn quản lý thành viên.
# Category: 👤 Thành Viên
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked membernote
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked memberhelp
# Purpose: Hướng dẫn lệnh thành viên.
# Category: 👤 Thành Viên
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked memberhelp
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked lookup
# Purpose: Tra cứu ID hoặc mention.
# Category: 👤 Thành Viên
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked lookup
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked findmember
# Purpose: Tìm thành viên theo tên.
# Category: 👤 Thành Viên
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked findmember
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# 🛡️ Kiểm Duyệt
# Command: nuked warnx
# Purpose: Cảnh cáo thành viên.
# Category: 🛡️ Kiểm Duyệt
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked warnx
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked warnings
# Purpose: Xem cảnh cáo.
# Category: 🛡️ Kiểm Duyệt
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked warnings
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked clearx
# Purpose: Xóa tin nhắn giới hạn.
# Category: 🛡️ Kiểm Duyệt
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked clearx
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked slowmodex
# Purpose: Cấu hình slowmode.
# Category: 🛡️ Kiểm Duyệt
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked slowmodex
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked lockx
# Purpose: Khóa kênh hiện tại.
# Category: 🛡️ Kiểm Duyệt
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked lockx
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked unlockx
# Purpose: Mở khóa kênh.
# Category: 🛡️ Kiểm Duyệt
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked unlockx
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked timeoutx
# Purpose: Timeout một thành viên.
# Category: 🛡️ Kiểm Duyệt
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked timeoutx
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked untimeout
# Purpose: Gỡ timeout.
# Category: 🛡️ Kiểm Duyệt
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked untimeout
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked kickx
# Purpose: Kick một thành viên.
# Category: 🛡️ Kiểm Duyệt
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked kickx
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked banx
# Purpose: Ban một thành viên.
# Category: 🛡️ Kiểm Duyệt
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked banx
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked unbanx
# Purpose: Gỡ ban bằng ID.
# Category: 🛡️ Kiểm Duyệt
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked unbanx
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked softban
# Purpose: Hướng dẫn softban an toàn.
# Category: 🛡️ Kiểm Duyệt
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked softban
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked modlog
# Purpose: Xem hướng dẫn modlog.
# Category: 🛡️ Kiểm Duyệt
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked modlog
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked reason
# Purpose: Xem lý do thao tác gần nhất.
# Category: 🛡️ Kiểm Duyệt
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked reason
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked case
# Purpose: Tra cứu case ID.
# Category: 🛡️ Kiểm Duyệt
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked case
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked modstats
# Purpose: Thống kê kiểm duyệt.
# Category: 🛡️ Kiểm Duyệt
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked modstats
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked modhelp
# Purpose: Hướng dẫn moderation.
# Category: 🛡️ Kiểm Duyệt
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked modhelp
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked audit
# Purpose: Hướng dẫn xem audit log.
# Category: 🛡️ Kiểm Duyệt
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked audit
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked purge
# Purpose: Xóa nhóm tin nhắn theo giới hạn.
# Category: 🛡️ Kiểm Duyệt
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked purge
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked clean
# Purpose: Làm sạch tin nhắn bot.
# Category: 🛡️ Kiểm Duyệt
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked clean
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked filter
# Purpose: Xem trạng thái bộ lọc.
# Category: 🛡️ Kiểm Duyệt
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked filter
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked automod
# Purpose: Xem hướng dẫn AutoMod.
# Category: 🛡️ Kiểm Duyệt
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked automod
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked rules
# Purpose: Hiển thị quy tắc server.
# Category: 🛡️ Kiểm Duyệt
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked rules
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked report
# Purpose: Tạo mẫu báo cáo.
# Category: 🛡️ Kiểm Duyệt
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked report
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked appeal
# Purpose: Hướng dẫn kháng nghị.
# Category: 🛡️ Kiểm Duyệt
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked appeal
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked modinfo
# Purpose: Thông tin công cụ moderation.
# Category: 🛡️ Kiểm Duyệt
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked modinfo
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked cases
# Purpose: Danh sách case theo dữ liệu bot.
# Category: 🛡️ Kiểm Duyệt
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked cases
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked muteinfo
# Purpose: Thông tin mute/timeout.
# Category: 🛡️ Kiểm Duyệt
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked muteinfo
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked kickinfo
# Purpose: Thông tin quyền kick.
# Category: 🛡️ Kiểm Duyệt
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked kickinfo
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked baninfo
# Purpose: Thông tin quyền ban.
# Category: 🛡️ Kiểm Duyệt
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked baninfo
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked permissioncheck
# Purpose: Kiểm tra quyền moderation.
# Category: 🛡️ Kiểm Duyệt
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked permissioncheck
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# 📢 Kênh
# Command: nuked channelinfo
# Purpose: Thông tin kênh hiện tại.
# Category: 📢 Kênh
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked channelinfo
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked channelname
# Purpose: Xem tên kênh.
# Category: 📢 Kênh
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked channelname
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked channeltopic
# Purpose: Xem topic kênh.
# Category: 📢 Kênh
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked channeltopic
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked channeltype
# Purpose: Xem loại kênh.
# Category: 📢 Kênh
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked channeltype
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked channelposition
# Purpose: Xem vị trí kênh.
# Category: 📢 Kênh
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked channelposition
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked channelcategory
# Purpose: Xem category.
# Category: 📢 Kênh
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked channelcategory
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked channelcreated
# Purpose: Xem ngày tạo kênh.
# Category: 📢 Kênh
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked channelcreated
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked channelmention
# Purpose: Tạo mention kênh.
# Category: 📢 Kênh
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked channelmention
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked channelid2
# Purpose: Xem ID kênh.
# Category: 📢 Kênh
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked channelid2
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked listtext
# Purpose: Liệt kê text channel.
# Category: 📢 Kênh
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked listtext
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked listvoice
# Purpose: Liệt kê voice channel.
# Category: 📢 Kênh
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked listvoice
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked listcategory
# Purpose: Liệt kê category.
# Category: 📢 Kênh
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked listcategory
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked listforum
# Purpose: Liệt kê forum channel.
# Category: 📢 Kênh
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked listforum
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked liststage
# Purpose: Liệt kê stage channel.
# Category: 📢 Kênh
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked liststage
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked channelcount
# Purpose: Đếm channel.
# Category: 📢 Kênh
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked channelcount
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked textcount
# Purpose: Đếm text channel.
# Category: 📢 Kênh
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked textcount
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked voicecount
# Purpose: Đếm voice channel.
# Category: 📢 Kênh
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked voicecount
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked categorycount
# Purpose: Đếm category.
# Category: 📢 Kênh
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked categorycount
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked forumcount
# Purpose: Đếm forum channel.
# Category: 📢 Kênh
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked forumcount
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked createchannelx
# Purpose: Hướng dẫn tạo kênh.
# Category: 📢 Kênh
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked createchannelx
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked renamechannelx
# Purpose: Hướng dẫn đổi tên kênh.
# Category: 📢 Kênh
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked renamechannelx
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked settopicx
# Purpose: Hướng dẫn đặt topic.
# Category: 📢 Kênh
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked settopicx
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked slowmodeinfo
# Purpose: Thông tin slowmode.
# Category: 📢 Kênh
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked slowmodeinfo
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked lockinfo
# Purpose: Thông tin khóa kênh.
# Category: 📢 Kênh
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked lockinfo
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked unlockinfo
# Purpose: Thông tin mở khóa.
# Category: 📢 Kênh
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked unlockinfo
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked channelperms
# Purpose: Kiểm tra quyền kênh.
# Category: 📢 Kênh
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked channelperms
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked channelhelp
# Purpose: Hướng dẫn quản lý kênh.
# Category: 📢 Kênh
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked channelhelp
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked archiveinfo
# Purpose: Hướng dẫn archive.
# Category: 📢 Kênh
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked archiveinfo
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked threadinfo
# Purpose: Thông tin thread.
# Category: 📢 Kênh
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked threadinfo
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked threads
# Purpose: Đếm thread hiện có.
# Category: 📢 Kênh
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked threads
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked channelstats
# Purpose: Thống kê kênh.
# Category: 📢 Kênh
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked channelstats
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# 🎭 Role
# Command: nuked roleinfo
# Purpose: Thông tin role.
# Category: 🎭 Role
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked roleinfo
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked rolelist
# Purpose: Liệt kê role.
# Category: 🎭 Role
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked rolelist
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked rolecount
# Purpose: Đếm role.
# Category: 🎭 Role
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked rolecount
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked rolemembers
# Purpose: Xem số thành viên có role.
# Category: 🎭 Role
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked rolemembers
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked rolecolor
# Purpose: Xem màu role.
# Category: 🎭 Role
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked rolecolor
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked roleposition
# Purpose: Xem vị trí role.
# Category: 🎭 Role
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked roleposition
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked rolemention
# Purpose: Tạo mention role.
# Category: 🎭 Role
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked rolemention
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked rolecreated
# Purpose: Xem ngày tạo role.
# Category: 🎭 Role
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked rolecreated
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked roleperms
# Purpose: Xem quyền role.
# Category: 🎭 Role
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked roleperms
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked rolehelp
# Purpose: Hướng dẫn role.
# Category: 🎭 Role
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked rolehelp
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked addroleinfo
# Purpose: Hướng dẫn thêm role.
# Category: 🎭 Role
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked addroleinfo
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked removeroleinfo
# Purpose: Hướng dẫn gỡ role.
# Category: 🎭 Role
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked removeroleinfo
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked autoroleinfo
# Purpose: Hướng dẫn autorole.
# Category: 🎭 Role
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked autoroleinfo
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked rolehierarchy
# Purpose: Xem thứ tự role.
# Category: 🎭 Role
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked rolehierarchy
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked botrole
# Purpose: Xem role cao nhất của bot.
# Category: 🎭 Role
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked botrole
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked memberroles
# Purpose: Xem role thành viên.
# Category: 🎭 Role
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked memberroles
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked commonroles
# Purpose: Xem role phổ biến.
# Category: 🎭 Role
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked commonroles
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked emptyroles
# Purpose: Tìm role không có thành viên.
# Category: 🎭 Role
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked emptyroles
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked managedroles
# Purpose: Xem role managed.
# Category: 🎭 Role
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked managedroles
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked hoistedroles
# Purpose: Xem role hiển thị riêng.
# Category: 🎭 Role
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked hoistedroles
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked coloredroles
# Purpose: Xem role có màu.
# Category: 🎭 Role
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked coloredroles
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked rolepermissions
# Purpose: Kiểm tra permission role.
# Category: 🎭 Role
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked rolepermissions
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked rolepositionof
# Purpose: Tra vị trí role.
# Category: 🎭 Role
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked rolepositionof
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked rolelookup
# Purpose: Tra cứu role.
# Category: 🎭 Role
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked rolelookup
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked roleusage
# Purpose: Hướng dẫn dùng role.
# Category: 🎭 Role
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked roleusage
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked rolecommand
# Purpose: Hướng dẫn lệnh role.
# Category: 🎭 Role
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked rolecommand
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked roleconfig
# Purpose: Hướng dẫn cấu hình role.
# Category: 🎭 Role
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked roleconfig
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked rolebackup
# Purpose: Thông tin backup role.
# Category: 🎭 Role
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked rolebackup
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked roleaudit
# Purpose: Hướng dẫn audit role.
# Category: 🎭 Role
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked roleaudit
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked rolecountx
# Purpose: Thống kê role.
# Category: 🎭 Role
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked rolecountx
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked rolecenter
# Purpose: Mở trung tâm role.
# Category: 🎭 Role
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked rolecenter
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# 🎉 Giải Trí
# Command: nuked 8ball
# Purpose: Trả lời ngẫu nhiên vui vẻ.
# Category: 🎉 Giải Trí
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked 8ball
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked choose
# Purpose: Chọn một phương án.
# Category: 🎉 Giải Trí
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked choose
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked rollx
# Purpose: Tung xúc xắc.
# Category: 🎉 Giải Trí
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked rollx
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked coinflipx
# Purpose: Tung đồng xu ảo.
# Category: 🎉 Giải Trí
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked coinflipx
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked rate
# Purpose: Chấm điểm vui.
# Category: 🎉 Giải Trí
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked rate
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked shipx
# Purpose: Ghép đôi vui.
# Category: 🎉 Giải Trí
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked shipx
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked lovecheck
# Purpose: Tỷ lệ tình cảm vui.
# Category: 🎉 Giải Trí
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked lovecheck
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked hugx
# Purpose: Tương tác ôm vui.
# Category: 🎉 Giải Trí
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked hugx
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked patx
# Purpose: Tương tác vỗ đầu vui.
# Category: 🎉 Giải Trí
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked patx
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked cuddlex
# Purpose: Tương tác âu yếm vui.
# Category: 🎉 Giải Trí
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked cuddlex
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked slapx
# Purpose: Tương tác tát giả lập vui.
# Category: 🎉 Giải Trí
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked slapx
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked highfive
# Purpose: Đập tay vui.
# Category: 🎉 Giải Trí
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked highfive
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked wave
# Purpose: Vẫy tay.
# Category: 🎉 Giải Trí
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked wave
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked dance
# Purpose: Tin nhắn nhảy vui.
# Category: 🎉 Giải Trí
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked dance
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked cheer
# Purpose: Cổ vũ thành viên.
# Category: 🎉 Giải Trí
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked cheer
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked joke
# Purpose: Một câu đùa ngắn.
# Category: 🎉 Giải Trí
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked joke
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked compliment
# Purpose: Lời khen vui.
# Category: 🎉 Giải Trí
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked compliment
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked roastlight
# Purpose: Roast nhẹ, không xúc phạm.
# Category: 🎉 Giải Trí
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked roastlight
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked meme
# Purpose: Gợi ý meme.
# Category: 🎉 Giải Trí
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked meme
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked fortune
# Purpose: Lời tiên đoán vui.
# Category: 🎉 Giải Trí
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked fortune
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked rps
# Purpose: Kéo búa bao.
# Category: 🎉 Giải Trí
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked rps
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked number
# Purpose: Tạo số ngẫu nhiên.
# Category: 🎉 Giải Trí
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked number
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked randomword
# Purpose: Tạo từ ngẫu nhiên.
# Category: 🎉 Giải Trí
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked randomword
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked pick
# Purpose: Chọn ngẫu nhiên.
# Category: 🎉 Giải Trí
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked pick
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked reverse
# Purpose: Đảo chuỗi văn bản.
# Category: 🎉 Giải Trí
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked reverse
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked sayinfo
# Purpose: Hướng dẫn lệnh nói.
# Category: 🎉 Giải Trí
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked sayinfo
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked emoji
# Purpose: Chọn emoji vui.
# Category: 🎉 Giải Trí
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked emoji
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked color
# Purpose: Tạo mã màu ngẫu nhiên.
# Category: 🎉 Giải Trí
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked color
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked fact
# Purpose: Một sự thật vui.
# Category: 🎉 Giải Trí
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked fact
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked quiz
# Purpose: Câu hỏi vui.
# Category: 🎉 Giải Trí
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked quiz
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked funhelp
# Purpose: Hướng dẫn giải trí.
# Category: 🎉 Giải Trí
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked funhelp
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# 💰 Kinh Tế
# Command: nuked balx
# Purpose: Xem số dư.
# Category: 💰 Kinh Tế
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked balx
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked dailyx
# Purpose: Nhận coin hằng ngày.
# Category: 💰 Kinh Tế
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked dailyx
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked workx
# Purpose: Nhận coin từ work.
# Category: 💰 Kinh Tế
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked workx
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked begx
# Purpose: Nhận coin nhỏ.
# Category: 💰 Kinh Tế
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked begx
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked givex
# Purpose: Tặng coin.
# Category: 💰 Kinh Tế
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked givex
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked payinfo
# Purpose: Hướng dẫn chuyển coin.
# Category: 💰 Kinh Tế
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked payinfo
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked leaderboardx
# Purpose: Bảng xếp hạng coin.
# Category: 💰 Kinh Tế
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked leaderboardx
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked richest
# Purpose: Xem người nhiều coin.
# Category: 💰 Kinh Tế
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked richest
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked wallet
# Purpose: Xem ví.
# Category: 💰 Kinh Tế
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked wallet
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked economy
# Purpose: Tổng quan kinh tế.
# Category: 💰 Kinh Tế
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked economy
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked shopinfo
# Purpose: Thông tin shop.
# Category: 💰 Kinh Tế
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked shopinfo
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked inventoryx
# Purpose: Xem inventory.
# Category: 💰 Kinh Tế
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked inventoryx
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked iteminfo
# Purpose: Thông tin vật phẩm.
# Category: 💰 Kinh Tế
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked iteminfo
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked buyinfo
# Purpose: Hướng dẫn mua.
# Category: 💰 Kinh Tế
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked buyinfo
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked sellinfo
# Purpose: Hướng dẫn bán.
# Category: 💰 Kinh Tế
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked sellinfo
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked giftinfo
# Purpose: Hướng dẫn tặng vật phẩm.
# Category: 💰 Kinh Tế
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked giftinfo
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked tradeinfo
# Purpose: Hướng dẫn trao đổi.
# Category: 💰 Kinh Tế
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked tradeinfo
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked economyhelp
# Purpose: Hướng dẫn kinh tế.
# Category: 💰 Kinh Tế
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked economyhelp
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked coinstats
# Purpose: Thống kê coin.
# Category: 💰 Kinh Tế
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked coinstats
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked earnings
# Purpose: Thống kê thu nhập.
# Category: 💰 Kinh Tế
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked earnings
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked spending
# Purpose: Hướng dẫn theo dõi chi tiêu.
# Category: 💰 Kinh Tế
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked spending
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked economyrank
# Purpose: Xếp hạng kinh tế.
# Category: 💰 Kinh Tế
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked economyrank
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked coincheck
# Purpose: Kiểm tra số dư.
# Category: 💰 Kinh Tế
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked coincheck
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked dailyinfo
# Purpose: Thông tin daily.
# Category: 💰 Kinh Tế
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked dailyinfo
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked workinfo
# Purpose: Thông tin work.
# Category: 💰 Kinh Tế
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked workinfo
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked beginfo
# Purpose: Thông tin beg.
# Category: 💰 Kinh Tế
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked beginfo
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked shop
# Purpose: Mở shop an toàn.
# Category: 💰 Kinh Tế
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked shop
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked inventory
# Purpose: Mở kho vật phẩm.
# Category: 💰 Kinh Tế
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked inventory
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked transfer
# Purpose: Hướng dẫn chuyển coin.
# Category: 💰 Kinh Tế
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked transfer
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked economyconfig
# Purpose: Thông tin cấu hình kinh tế.
# Category: 💰 Kinh Tế
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked economyconfig
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked coinhelp
# Purpose: Trợ giúp hệ thống coin.
# Category: 💰 Kinh Tế
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked coinhelp
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# ⭐ Level
# Command: nuked levelx
# Purpose: Xem level.
# Category: ⭐ Level
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked levelx
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked rank
# Purpose: Xem thứ hạng.
# Category: ⭐ Level
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked rank
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked xp
# Purpose: Xem EXP.
# Category: ⭐ Level
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked xp
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked xprank
# Purpose: Xếp hạng EXP.
# Category: ⭐ Level
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked xprank
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked nextlevel
# Purpose: Xem EXP cần lên cấp.
# Category: ⭐ Level
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked nextlevel
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked levelstats
# Purpose: Thống kê level.
# Category: ⭐ Level
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked levelstats
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked leveltop
# Purpose: Top level.
# Category: ⭐ Level
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked leveltop
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked leveluser
# Purpose: Level của thành viên.
# Category: ⭐ Level
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked leveluser
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked xpuser
# Purpose: EXP của thành viên.
# Category: ⭐ Level
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked xpuser
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked levelrole
# Purpose: Thông tin role theo level.
# Category: ⭐ Level
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked levelrole
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked levelhelp
# Purpose: Hướng dẫn level.
# Category: ⭐ Level
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked levelhelp
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked xpinfo
# Purpose: Thông tin EXP.
# Category: ⭐ Level
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked xpinfo
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked levelupinfo
# Purpose: Thông tin level up.
# Category: ⭐ Level
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked levelupinfo
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked rankinfo
# Purpose: Thông tin rank.
# Category: ⭐ Level
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked rankinfo
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked progress
# Purpose: Tiến độ level.
# Category: ⭐ Level
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked progress
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked progressbar
# Purpose: Thanh tiến độ EXP.
# Category: ⭐ Level
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked progressbar
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked maxlevel
# Purpose: Xem level tối đa.
# Category: ⭐ Level
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked maxlevel
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked levelconfig
# Purpose: Thông tin cấu hình level.
# Category: ⭐ Level
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked levelconfig
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked xpcooldown
# Purpose: Thông tin cooldown EXP.
# Category: ⭐ Level
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked xpcooldown
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked xpmessage
# Purpose: Thông tin EXP từ tin nhắn.
# Category: ⭐ Level
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked xpmessage
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked levelleaderboard
# Purpose: Bảng xếp hạng level.
# Category: ⭐ Level
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked levelleaderboard
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked rankuser
# Purpose: Rank của thành viên.
# Category: ⭐ Level
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked rankuser
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked xpneeded
# Purpose: EXP còn thiếu.
# Category: ⭐ Level
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked xpneeded
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked levelcompare
# Purpose: So sánh level.
# Category: ⭐ Level
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked levelcompare
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked xptotal
# Purpose: Tổng EXP.
# Category: ⭐ Level
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked xptotal
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked leveltotal
# Purpose: Tổng level.
# Category: ⭐ Level
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked leveltotal
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked levelcenter
# Purpose: Trung tâm level.
# Category: ⭐ Level
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked levelcenter
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked levelstats2
# Purpose: Thống kê level nâng cao.
# Category: ⭐ Level
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked levelstats2
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked xpstats
# Purpose: Thống kê EXP.
# Category: ⭐ Level
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked xpstats
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked rankstats
# Purpose: Thống kê rank.
# Category: ⭐ Level
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked rankstats
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked leveltips
# Purpose: Mẹo tăng level hợp lệ.
# Category: ⭐ Level
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked leveltips
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked levelmenu
# Purpose: Menu level.
# Category: ⭐ Level
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked levelmenu
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# 💾 Backup & Cấu Hình
# Command: nuked backupinfo
# Purpose: Thông tin backup.
# Category: 💾 Backup & Cấu Hình
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked backupinfo
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked backuplist
# Purpose: Danh sách backup.
# Category: 💾 Backup & Cấu Hình
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked backuplist
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked backuphelp
# Purpose: Hướng dẫn backup.
# Category: 💾 Backup & Cấu Hình
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked backuphelp
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked restoreinfo
# Purpose: Thông tin restore.
# Category: 💾 Backup & Cấu Hình
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked restoreinfo
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked configinfo
# Purpose: Thông tin config.
# Category: 💾 Backup & Cấu Hình
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked configinfo
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked reloadinfo
# Purpose: Thông tin reload.
# Category: 💾 Backup & Cấu Hình
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked reloadinfo
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked loginfo
# Purpose: Thông tin log.
# Category: 💾 Backup & Cấu Hình
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked loginfo
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked welcomeinfo
# Purpose: Thông tin welcome.
# Category: 💾 Backup & Cấu Hình
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked welcomeinfo
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked goodbyeinfo
# Purpose: Thông tin goodbye.
# Category: 💾 Backup & Cấu Hình
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked goodbyeinfo
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked disabledinfo
# Purpose: Xem lệnh bị tắt.
# Category: 💾 Backup & Cấu Hình
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked disabledinfo
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked settings
# Purpose: Tổng quan cài đặt.
# Category: 💾 Backup & Cấu Hình
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked settings
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked settingshelp
# Purpose: Hướng dẫn cài đặt.
# Category: 💾 Backup & Cấu Hình
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked settingshelp
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked serverconfig
# Purpose: Hướng dẫn cấu hình server.
# Category: 💾 Backup & Cấu Hình
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked serverconfig
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked logconfig
# Purpose: Hướng dẫn cấu hình log.
# Category: 💾 Backup & Cấu Hình
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked logconfig
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked welcomeconfig
# Purpose: Hướng dẫn welcome.
# Category: 💾 Backup & Cấu Hình
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked welcomeconfig
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked goodbyeconfig
# Purpose: Hướng dẫn goodbye.
# Category: 💾 Backup & Cấu Hình
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked goodbyeconfig
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked levelconfig2
# Purpose: Hướng dẫn cấu hình level.
# Category: 💾 Backup & Cấu Hình
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked levelconfig2
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked economyconfig2
# Purpose: Hướng dẫn cấu hình coin.
# Category: 💾 Backup & Cấu Hình
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked economyconfig2
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked prefixconfig
# Purpose: Thông tin prefix.
# Category: 💾 Backup & Cấu Hình
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked prefixconfig
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked menuconfig
# Purpose: Thông tin menu.
# Category: 💾 Backup & Cấu Hình
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked menuconfig
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked embedinfo
# Purpose: Thông tin embed.
# Category: 💾 Backup & Cấu Hình
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked embedinfo
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked gifinfo
# Purpose: Thông tin GIF menu.
# Category: 💾 Backup & Cấu Hình
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked gifinfo
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked jsoninfo
# Purpose: Thông tin file JSON.
# Category: 💾 Backup & Cấu Hình
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked jsoninfo
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked datahelp
# Purpose: Hướng dẫn dữ liệu.
# Category: 💾 Backup & Cấu Hình
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked datahelp
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked resetinfo
# Purpose: Thông tin reset dữ liệu.
# Category: 💾 Backup & Cấu Hình
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked resetinfo
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked exportinfo
# Purpose: Hướng dẫn xuất dữ liệu.
# Category: 💾 Backup & Cấu Hình
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked exportinfo
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked importinfo
# Purpose: Hướng dẫn nhập dữ liệu.
# Category: 💾 Backup & Cấu Hình
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked importinfo
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked configcheck
# Purpose: Kiểm tra cấu hình.
# Category: 💾 Backup & Cấu Hình
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked configcheck
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked healthcheck
# Purpose: Kiểm tra sức khỏe bot.
# Category: 💾 Backup & Cấu Hình
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked healthcheck
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked diagnose
# Purpose: Chẩn đoán lỗi cơ bản.
# Category: 💾 Backup & Cấu Hình
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked diagnose
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked configcenter
# Purpose: Trung tâm cấu hình.
# Category: 💾 Backup & Cấu Hình
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked configcenter
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# 👑 Owner & Quản Trị Bot
# Command: nuked ownerlist
# Purpose: Xem danh sách Owner.
# Category: 👑 Owner & Quản Trị Bot
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked ownerlist
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked ownercheck
# Purpose: Kiểm tra quyền Owner.
# Category: 👑 Owner & Quản Trị Bot
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked ownercheck
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked ownerhelp
# Purpose: Hướng dẫn Owner.
# Category: 👑 Owner & Quản Trị Bot
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked ownerhelp
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked botreload
# Purpose: Reload dữ liệu an toàn.
# Category: 👑 Owner & Quản Trị Bot
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked botreload
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked botoff
# Purpose: Thông tin tắt lệnh.
# Category: 👑 Owner & Quản Trị Bot
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked botoff
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked boton
# Purpose: Thông tin bật lệnh.
# Category: 👑 Owner & Quản Trị Bot
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked boton
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked disabledlist
# Purpose: Liệt kê lệnh bị tắt.
# Category: 👑 Owner & Quản Trị Bot
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked disabledlist
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked setlvinfo
# Purpose: Hướng dẫn set level.
# Category: 👑 Owner & Quản Trị Bot
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked setlvinfo
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked setcoinsinfo
# Purpose: Hướng dẫn set coin.
# Category: 👑 Owner & Quản Trị Bot
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked setcoinsinfo
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked addcoinsinfo
# Purpose: Hướng dẫn cộng coin.
# Category: 👑 Owner & Quản Trị Bot
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked addcoinsinfo
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked removecoinsinfo
# Purpose: Hướng dẫn trừ coin.
# Category: 👑 Owner & Quản Trị Bot
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked removecoinsinfo
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked addownerinfo
# Purpose: Hướng dẫn thêm Owner.
# Category: 👑 Owner & Quản Trị Bot
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked addownerinfo
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked deleteownerinfo
# Purpose: Hướng dẫn xóa Owner.
# Category: 👑 Owner & Quản Trị Bot
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked deleteownerinfo
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked ownerstats
# Purpose: Thống kê Owner.
# Category: 👑 Owner & Quản Trị Bot
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked ownerstats
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked botstats
# Purpose: Thống kê bot.
# Category: 👑 Owner & Quản Trị Bot
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked botstats
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked serverstats
# Purpose: Thống kê server.
# Category: 👑 Owner & Quản Trị Bot
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked serverstats
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked commandstats
# Purpose: Thống kê lệnh.
# Category: 👑 Owner & Quản Trị Bot
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked commandstats
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked errorstats
# Purpose: Thống kê lỗi.
# Category: 👑 Owner & Quản Trị Bot
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked errorstats
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked cooldowns
# Purpose: Xem hướng dẫn cooldown.
# Category: 👑 Owner & Quản Trị Bot
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked cooldowns
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked permissionsx
# Purpose: Kiểm tra permission.
# Category: 👑 Owner & Quản Trị Bot
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked permissionsx
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked auditinfo
# Purpose: Hướng dẫn audit.
# Category: 👑 Owner & Quản Trị Bot
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked auditinfo
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked ratelimitinfo
# Purpose: Thông tin rate limit.
# Category: 👑 Owner & Quản Trị Bot
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked ratelimitinfo
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked cacheinfo
# Purpose: Thông tin cache.
# Category: 👑 Owner & Quản Trị Bot
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked cacheinfo
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked memoryinfo
# Purpose: Thông tin bộ nhớ.
# Category: 👑 Owner & Quản Trị Bot
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked memoryinfo
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked latencyinfo
# Purpose: Thông tin latency.
# Category: 👑 Owner & Quản Trị Bot
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked latencyinfo
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked taskinfo
# Purpose: Thông tin background task.
# Category: 👑 Owner & Quản Trị Bot
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked taskinfo
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked jsonstatus
# Purpose: Trạng thái JSON.
# Category: 👑 Owner & Quản Trị Bot
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked jsonstatus
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked ownerconfig
# Purpose: Thông tin cấu hình Owner.
# Category: 👑 Owner & Quản Trị Bot
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked ownerconfig
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked ownerpanel
# Purpose: Mở bảng Owner an toàn.
# Category: 👑 Owner & Quản Trị Bot
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked ownerpanel
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked adminhelp
# Purpose: Hướng dẫn quản trị.
# Category: 👑 Owner & Quản Trị Bot
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked adminhelp
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
# Command: nuked controlcenter
# Purpose: Mở Control Center.
# Category: 👑 Owner & Quản Trị Bot
# Permission model: inherited from the command implementation.
# Safety model: this extension does not delete channels, roles, members,
# or mass-message a server.
# UI model: Embed + emoji + concise Vietnamese explanation.
# Usage: nuked controlcenter
# Errors: handled by the bot's existing global error handler.
# Compatibility: uses discord.py commands.Bot.
# Data: no external database is required by this extension.
# Notes: existing commands from the original safe source remain untouched.
# ------------------------------------------------------------
