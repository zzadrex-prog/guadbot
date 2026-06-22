import discord
from discord.ext import commands
import os
from flask import Flask
from threading import Thread
import json
import asyncio
import re

# --- Flask Web Sunucusu ---
app = Flask('')
@app.route('/')
def home(): return "Bot Aktif!"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive():
    t = Thread(target=run)
    t.start()

# --- Bot Ayarları ---
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

# --- AYAR KOMUTLARI ---
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
    guild_id = str(ctx.guild.id)
    if "ban_roles" not in config: config["ban_roles"] = {}
    if guild_id not in config["ban_roles"]: config["ban_roles"][guild_id] = []
    
    roles_list = config["ban_roles"][guild_id]
    if role.id in roles_list:
        await ctx.send(f"⚠️ **{role.name}** zaten yasaklı listede.")
        return
    if len(roles_list) >= 5:
        await ctx.send("❌ Maksimum 5 yasaklı rol ekleyebilirsin!")
        return
    
    roles_list.append(role.id)
    save_config(config)
    await ctx.send(f"✅ Yasaklı rol eklendi: **{role.name}**")

# --- KORUMA SİSTEMİ (ETİKET VE LİNK) ---
@bot.event
async def on_message(message):
    if message.author.bot or not message.guild: return
    
    config = load_config()
    ban_roles = config.get("ban_roles", {}).get(str(message.guild.id), [])
    user_has_banned_role = any(role.id in ban_roles for role in message.author.roles)
    
    if user_has_banned_role:
        url_pattern = r'(https?://\S+|www\.\S+)'
        has_url = re.search(url_pattern, message.content)
        is_tagging = "@everyone" in message.content or "@here" in message.content
        
        if is_tagging or has_url:
            try:
                # Ban sebebi ve log mesajı
                sebep = "URL Paylaşımı" if has_url else "Etiket Kullanımı"
                await message.delete()
                await message.author.ban(reason=f"Yasaklı rolde {sebep}!")
                
                embed = discord.Embed(title="🔨 OTOMATİK BAN", color=discord.Color.dark_red())
                embed.add_field(name="Kullanıcı", value=f"{message.author} ({message.author.id})", inline=True)
                embed.add_field(name="İşlem", value=f"**{message.author.name}** adlı oyuncu yasaklı rolde **{sebep}** yaptığı için banlandı.", inline=False)
                embed.set_footer(text="Koruma Sistemi Aktif")
                await send_log(message.guild, embed)
            except: pass
            
    await bot.process_commands(message)

# --- DİĞER TAKİP EVENTLERİ ---
@bot.event
async def on_guild_update(before, after):
    await asyncio.sleep(1)
    async for entry in after.audit_logs(action=discord.AuditLogAction.guild_update, limit=1):
        embed = discord.Embed(title="⚙️ Sunucu Ayarları Güncellendi", color=discord.Color.gold())
        embed.add_field(name="İşlemi Yapan", value=entry.user.mention, inline=False)
        await send_log(after, embed)
        break

@bot.event
async def on_guild_role_create(role):
    await asyncio.sleep(1)
    async for entry in role.guild.audit_logs(action=discord.AuditLogAction.role_create, limit=1):
        embed = discord.Embed(title="🆕 Yeni Rol Oluşturuldu", color=discord.Color.green())
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

if __name__ == "__main__":
    keep_alive()
    bot.run(os.environ.get("DISCORD_TOKEN"))
