import discord
from discord.ext import commands
import asyncio

# Thiết lập intents (bắt buộc với discord.py 2.x)
intents = discord.Intents.default()
intents.message_content = True
intents.members = True  # Cần để lấy thông tin thành viên

bot = commands.Bot(command_prefix="!", intents=intents)

# Sự kiện khi bot sẵn sàng
@bot.event
async def on_ready():
    print(f"Bot đã đăng nhập với tên: {bot.user.name}")
    print(f"ID: {bot.user.id}")

# Lệnh kick
@bot.command(name="kick")
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason="Không có lý do"):
    await member.kick(reason=reason)
    await ctx.send(f"✅ Đã kick {member.mention} | Lý do: {reason}")

# Lệnh ban
@bot.command(name="ban")
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason="Không có lý do"):
    await member.ban(reason=reason)
    await ctx.send(f"🔨 Đã ban {member.mention} | Lý do: {reason}")

# Lệnh unban
@bot.command(name="unban")
@commands.has_permissions(ban_members=True)
async def unban(ctx, *, member_name):
    banned_users = [entry async for entry in ctx.guild.bans()]
    for ban_entry in banned_users:
        user = ban_entry.user
        if user.name.lower() == member_name.lower() or f"{user.name}#{user.discriminator}".lower() == member_name.lower():
            await ctx.guild.unban(user)
            await ctx.send(f"🔓 Đã bỏ ban {user.mention}")
            return
    await ctx.send("❌ Không tìm thấy người dùng trong danh sách ban.")

# Lệnh xóa tin nhắn
@bot.command(name="clear")
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int):
    if amount <= 0:
        await ctx.send("⚠️ Số lượng phải lớn hơn 0.")
        return
    deleted = await ctx.channel.purge(limit=amount + 1)  # +1 để xóa cả lệnh
    await ctx.send(f"🧹 Đã xóa {len(deleted) - 1} tin nhắn.", delete_after=5)

# Lệnh mute (yêu cầu có role tên "Muted")
@bot.command(name="mute")
@commands.has_permissions(manage_roles=True)
async def mute(ctx, member: discord.Member, *, reason="Không có lý do"):
    muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
    if not muted_role:
        # Tạo role Muted nếu chưa có
        muted_role = await ctx.guild.create_role(name="Muted", reason="Tạo role Muted cho lệnh mute")
        # Ẩn quyền gửi tin nhắn ở tất cả kênh
        for channel in ctx.guild.channels:
            await channel.set_permissions(muted_role, send_messages=False, speak=False)
    await member.add_roles(muted_role, reason=reason)
    await ctx.send(f"🔇 Đã mute {member.mention} | Lý do: {reason}")

# Lệnh unmute
@bot.command(name="unmute")
@commands.has_permissions(manage_roles=True)
async def unmute(ctx, member: discord.Member):
    muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
    if muted_role and muted_role in member.roles:
        await member.remove_roles(muted_role)
        await ctx.send(f"🔊 Đã bỏ mute {member.mention}")
    else:
        await ctx.send("❌ Người này không bị mute hoặc role Muted không tồn tại.")

# Xử lý lỗi quyền hạn
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("⛔ Bạn không có quyền sử dụng lệnh này.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("⚠️ Thiếu tham số. Vui lòng kiểm tra lại lệnh.")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("⚠️ Tham số không hợp lệ.")
    else:
        await ctx.send(f"❌ Đã xảy ra lỗi: {error}")

# Chạy bot (thay TOKEN bằng token thật của bạn)
bot.run("YOUR_BOT_TOKEN")
