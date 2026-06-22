import discord
from discord.ext import commands
import os
from flask import Flask
from threading import Thread
import json
import asyncio

app = Flask('')
@app.route('/')
def home(): return "Bot Aktif!"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive():
    t = Thread(target=run)
    t.start()

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)
CONFIG_FILE = "config.json"

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f: return json.load(f)
    return {"logs": {}, "ban_roles": {}}

def save_config(config):
    with open(CONFIG_FILE, "w") as f: json.dump(config, f)

@bot.event
async def on_ready():
    print(f'{bot.user.name} Sunucu Koruma Sistemi Aktif!')

async def send_log(guild, embed):
    config = load_config()
    channel_id = config["logs"].get(str(guild.id))
    if channel_id:
        channel = guild.get_channel(int(channel_id))
        if channel: await channel.send(embed=embed)

@bot.command()
@commands.has_permissions(administrator=True)
async def log(ctx, channel: discord.TextChannel):
    config = load_config()
    config["logs"][str(ctx.guild.id)] = channel.id
    save_config(config)
    await ctx.send(f"✅ Log kanalı {channel.mention} olarak ayarlandı.")

@bot.command()
@commands.has_permissions(administrator=True)
async def rol(ctx, role: discord.Role):
    config = load_config()
    config["ban_roles"][str(ctx.guild.id)] = role.id
    save_config(config)
    await ctx.send(f"🚫 Yasaklı rol: **{role.name}**.")

@bot.event
async def on_guild_update(before, after):
    await asyncio.sleep(1)
    async for entry in after.audit_logs(action=discord.AuditLogAction.guild_update, limit=1):
        embed = discord.Embed(title="⚙️ Sunucu Ayarları Güncellendi", color=discord.Color.gold())
        embed.add_field(name="İşlemi Yapan", value=entry.user.mention, inline=False)
        if before.name != after.name: embed.add_field(name="Ad Değişimi", value=f"Eski: {before.name}\nYeni: {after.name}")
        if before.icon != after.icon: embed.add_field(name="İkon", value="İkon değiştirildi.")
        await send_log(after, embed)
        break

@bot.event
async def on_guild_role_create(role):
    await asyncio.sleep(1)
    async for entry in role.guild.audit_logs(action=discord.AuditLogAction.role_create, limit=1):
        embed = discord.Embed(title="🆕 Yeni Rol", color=discord.Color.green())
        embed.add_field(name="Rol", value=role.name, inline=True)
        embed.add_field(name="Yapan", value=entry.user.mention, inline=True)
        await send_log(role.guild, embed)
        break

@bot.event
async def on_guild_role_delete(role):
    await asyncio.sleep(1)
    async for entry in role.guild.audit_logs(action=discord.AuditLogAction.role_delete, limit=1):
        embed = discord.Embed(title="🗑️ Rol Silindi", color=discord.Color.red())
        embed.add_field(name="Silinen Rol", value=role.name, inline=True)
        embed.add_field(name="Yapan", value=entry.user.mention, inline=True)
        await send_log(role.guild, embed)
        break

@bot.event
async def on_guild_channel_create(channel):
    await asyncio.sleep(1)
    async for entry in channel.guild.audit_logs(action=discord.AuditLogAction.channel_create, limit=1):
        embed = discord.Embed(title="📁 Yeni Kanal", color=discord.Color.blue())
        embed.add_field(name="Kanal", value=channel.name, inline=True)
        embed.add_field(name="Yapan", value=entry.user.mention, inline=True)
        await send_log(channel.guild, embed)
        break

@bot.event
async def on_message(message):
    if message.author.bot or not message.guild: return
    if "@everyone" in message.content or "@here" in message.content:
        config = load_config()
        ban_role_id = config["ban_roles"].get(str(message.guild.id))
        if ban_role_id and discord.utils.get(message.author.roles, id=int(ban_role_id)):
            try:
                await message.author.ban(reason="Yasaklı rolde etiket!")
                embed = discord.Embed(title="🔨 OTOMATİK BAN", color=discord.Color.dark_red())
                embed.add_field(name="Kullanıcı", value=f"{message.author}")
                await send_log(message.guild, embed)
            except: pass
    await bot.process_commands(message)

if __name__ == "__main__":
    keep_alive()
    bot.run(os.environ.get("DISCORD_TOKEN"))
