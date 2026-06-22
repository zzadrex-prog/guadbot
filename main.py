import discord
from discord.ext import commands
import os
import json
import asyncio
import re
from flask import Flask
from threading import Thread

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
    return {"logs": {}, "ban_roles": {}} # ban_roles artık liste tutacak

def save_config(config):
    with open(CONFIG_FILE, "w") as f: json.dump(config, f)

async def send_log(guild, embed):
    config = load_config()
    channel_id = config["logs"].get(str(guild.id))
    if channel_id:
        channel = guild.get_channel(int(channel_id))
        if channel: await channel.send(embed=embed)

@bot.command()
@commands.has_permissions(administrator=True)
async def log(ctx, channel_id: int):
    config = load_config()
    config["logs"][str(ctx.guild.id)] = channel_id
    save_config(config)
    await ctx.send(f"✅ Log kanalı **{channel_id}** olarak ayarlandı.")

@bot.command()
@commands.has_permissions(administrator=True)
async def rol(ctx, *role_ids: int):
    if len(role_ids) > 3:
        await ctx.send("❌ En fazla 3 rol ID'si ekleyebilirsin!")
        return
    config = load_config()
    config["ban_roles"][str(ctx.guild.id)] = list(role_ids)
    save_config(config)
    await ctx.send(f"✅ Yasaklı roller güncellendi: {list(role_ids)}")

@bot.event
async def on_message(message):
    if message.author.bot or not message.guild or message.author.guild_permissions.administrator:
        await bot.process_commands(message)
        return

    config = load_config()
    banned_roles = config.get("ban_roles", {}).get(str(message.guild.id), [])
    
    # Kullanıcının rollerinden herhangi biri ban listesinde mi?
    if any(role.id in banned_roles for role in message.author.roles):
        has_url = re.search(r'(https?://\S+|www\.\S+)', message.content)
        has_tag = "@everyone" in message.content or "@here" in message.content
        
        if has_url or has_tag:
            reason = "URL Paylaşımı" if has_url else "Etiket Kullanımı"
            try:
                await message.delete()
                await message.author.ban(reason=f"Yasaklı rolde {reason}")
                embed = discord.Embed(title="🔨 OTOMATİK BAN", color=discord.Color.dark_red())
                embed.add_field(name="Kullanıcı", value=f"{message.author.name} ({message.author.id})")
                embed.add_field(name="Sebep", value=reason)
                await send_log(message.guild, embed)
            except: pass
    await bot.process_commands(message)

@bot.event
async def on_guild_role_delete(role):
    await asyncio.sleep(1)
    async for entry in role.guild.audit_logs(action=discord.AuditLogAction.role_delete, limit=1):
        embed = discord.Embed(title="🗑️ Rol Silindi", color=discord.Color.red())
        embed.add_field(name="Silinen", value=role.name)
        embed.add_field(name="Yapan", value=entry.user.mention)
        await send_log(role.guild, embed)
        break

@bot.event
async def on_guild_update(before, after):
    await asyncio.sleep(1)
    if before.name != after.name:
        embed = discord.Embed(title="⚙️ Sunucu Adı Değişti", color=discord.Color.gold())
        embed.add_field(name="Eski", value=before.name)
        embed.add_field(name="Yeni", value=after.name)
        await send_log(after, embed)

if __name__ == "__main__":
    keep_alive()
    bot.run(os.environ.get("DISCORD_TOKEN"))
