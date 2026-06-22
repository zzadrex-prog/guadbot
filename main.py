import discord
from discord.ext import commands
import os
from flask import Flask
from threading import Thread
import json
import re
import asyncio

# --- Flask Web Sunucusu (Render Uyumluluğu İçin) ---
app = Flask('')

@app.route('/')
def home():
    return "Bot Aktif! Made by Zadrex"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()

# --- Discord Bot Ayarları ---
intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)

# Verileri saklamak için dosya sistemi
LOG_DATA_FILE = "log_config.json"

def load_config():
    if os.path.exists(LOG_DATA_FILE):
        try:
            with open(LOG_DATA_FILE, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_config(config):
    with open(LOG_DATA_FILE, "w") as f:
        json.dump(config, f, indent=4)

# URL tespiti için en güçlü Regex
URL_REGEX = r"(https?:\/\/[^\s]+)|(discord\.gg\/[^\s]+)|(www\.[^\s]+)|([a-zA-Z0-9-]+\.[a-z]{2,10})"

@bot.event
async def on_ready():
    print(f'Giriş yapıldı: {bot.user.name}')
    await bot.change_presence(activity=discord.Game(name="Zadrex Guard 7/24"))

# --- Log Kanalı Ayarlama ---
@bot.command()
@commands.has_permissions(administrator=True)
async def log(ctx, channel: discord.TextChannel):
    config = load_config()
    guild_id = str(ctx.guild.id)
    if guild_id not in config: config[guild_id] = {}
    config[guild_id]["log_channel"] = channel.id
    save_config(config)
    await ctx.send(f"✅ Log kanalı başarıyla {channel.mention} olarak ayarlandı.")

# --- 3 Yasaklı Rol Sistemi ---
@bot.command()
@commands.has_permissions(administrator=True)
async def rol(ctx, role: discord.Role):
    config = load_config()
    guild_id = str(ctx.guild.id)
    if guild_id not in config: config[guild_id] = {}
    
    if "protected_roles" not in config[guild_id]:
        config[guild_id]["protected_roles"] = []
    
    if role.id in config[guild_id]["protected_roles"]:
        await ctx.send(f"⚠️ {role.name} zaten yasaklı listede.")
        return

    if len(config[guild_id]["protected_roles"]) >= 3:
        config[guild_id]["protected_roles"].pop(0)
        config[guild_id]["protected_roles"].append(role.id)
        await ctx.send(f"♻️ Limit doldu. En eski rol çıkarıldı, {role.mention} yasaklı listeye eklendi.")
    else:
        config[guild_id]["protected_roles"].append(role.id)
        await ctx.send(f"🛡️ {role.mention} yasaklı listeye eklendi. Tüm kanallarda takipte!")
    
    save_config(config)

@bot.command()
@commands.has_permissions(administrator=True)
async def rolliste(ctx):
    config = load_config()
    roles = config.get(str(ctx.guild.id), {}).get("protected_roles", [])
    if not roles:
        await ctx.send("📋 Yasaklı rol listesi boş.")
    else:
        mentions = [f"<@&{r_id}>" for r_id in roles]
        await ctx.send(f"📋 Yasaklı Roller: {', '.join(mentions)}")

# --- Log Gönderme Fonksiyonu ---
async def send_log(guild, embed):
    config = load_config()
    channel_id = config.get(str(guild.id), {}).get("log_channel")
    if channel_id:
        channel = guild.get_channel(int(channel_id))
        if channel:
            try:
                await channel.send(embed=embed)
            except:
                pass

# --- ANA KORUMA SİSTEMİ (TÜM KANALLAR) ---
@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        return

    config = load_config()
    guild_data = config.get(str(message.guild.id), {})
    protected_roles = guild_data.get("protected_roles", [])

    # Kullanıcıda yasaklı rollerden biri var mı?
    has_protected_role = any(r.id in protected_roles for r in message.author.roles)

    if has_protected_role:
        contains_mention = "@everyone" in message.content or "@here" in message.content
        contains_url = re.search(URL_REGEX, message.content.lower())

        if contains_mention or contains_url:
            try:
                await message.delete()
                await message.author.ban(reason="Yasaklı rolde link/etiket paylaşımı (Zadrex Guard)", delete_message_days=1)
                
                embed = discord.Embed(title="🚨 Guard Sistemi: Kullanıcı Banlandı!", color=discord.Color.red())
                embed.add_field(name="Kullanıcı", value=f"{message.author.mention} ({message.author.id})", inline=False)
                embed.add_field(name="Kanal", value=message.channel.mention, inline=True)
                embed.add_field(name="Sebep", value="Yasaklı rolde link veya etiket kullanımı.", inline=False)
                embed.add_field(name="İçerik", value=f"||{message.content}||", inline=False)
                await send_log(message.guild, embed)
                return
            except Exception as e:
                print(f"Ban Hatası: {e}")

    await bot.process_commands(message)

# --- EK LOG ÖZELLİKLERİ (İLK KODDAKİ TÜM ÖZELLİKLER) ---

@bot.event
async def on_member_update(before, after):
    if before.roles != after.roles:
        added_roles = [role for role in after.roles if role not in before.roles]
        removed_roles = [role for role in before.roles if role not in after.roles]
        if added_roles or removed_roles:
            embed = discord.Embed(title="🛡️ Rol Değişikliği", color=discord.Color.blue())
            embed.add_field(name="Kullanıcı", value=after.mention, inline=False)
            if added_roles: embed.add_field(name="Verilen Roller", value=", ".join([r.mention for r in added_roles]), inline=False)
            if removed_roles: embed.add_field(name="Alınan Roller", value=", ".join([r.mention for r in removed_roles]), inline=False)
            await send_log(after.guild, embed)

@bot.event
async def on_guild_channel_create(channel):
    embed = discord.Embed(title="🆕 Yeni Kanal Oluşturuldu", color=discord.Color.green())
    embed.add_field(name="Kanal Adı", value=channel.name, inline=True)
    embed.add_field(name="Tür", value=str(channel.type), inline=True)
    await send_log(channel.guild, embed)

@bot.event
async def on_guild_channel_delete(channel):
    embed = discord.Embed(title="🗑️ Kanal Silindi", color=discord.Color.dark_red())
    embed.add_field(name="Kanal Adı", value=channel.name, inline=True)
    await send_log(channel.guild, embed)

@bot.event
async def on_member_remove(member):
    embed = discord.Embed(title="🚪 Kullanıcı Ayrıldı", color=discord.Color.orange())
    embed.add_field(name="Kullanıcı", value=f"{member.name} ({member.id})", inline=False)
    await send_log(member.guild, embed)

# Hata Yönetimi
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ Bu komutu kullanmak için 'Yönetici' yetkisine sahip olmalısınız.")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("❌ Geçersiz argüman! Örnek: `!log #kanal` veya `!rol @rol`")

if __name__ == "__main__":
    keep_alive()
    token = os.environ.get("DISCORD_TOKEN")
    if token:
        bot.run(token)
    else:
        print("HATA: 'DISCORD_TOKEN' çevre değişkeni bulunamadı!")
