import discord
from discord.ext import commands
import os
from flask import Flask
from threading import Thread
import json

# --- Flask Web Sunucusu (Render Uyumluluğu İçin) ---
app = Flask('')

@app.route('/')
def home():
    return "Bot Aktif!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- Discord Bot Ayarları ---
intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)

# Log kanalı verisini saklamak için basit bir dosya sistemi
LOG_DATA_FILE = "log_config.json"

def load_log_config():
    if os.path.exists(LOG_DATA_FILE):
        with open(LOG_DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_log_config(config):
    with open(LOG_DATA_FILE, "w") as f:
        json.dump(config, f)

@bot.event
async def on_ready():
    print(f'Giriş yapıldı: {bot.user.name}')
    await bot.change_presence(activity=discord.Game(name="Güvenlik Sağlanıyor"))

# --- Log Kanalı Ayarlama Komutu ---
@bot.command()
@commands.has_permissions(administrator=True)
async def log(ctx, channel: discord.TextChannel):
    config = load_log_config()
    config[str(ctx.guild.id)] = channel.id
    save_log_config(config)
    await ctx.send(f"✅ Log kanalı başarıyla {channel.mention} olarak ayarlandı.")

@log.error
async def log_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ Bu komutu kullanmak için 'Yönetici' yetkisine sahip olmalısınız.")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("❌ Lütfen geçerli bir kanal etiketleyin veya ID girin. Örn: `!log #kanal`")

# --- Olay Takip Sistemleri ---

async def send_log(guild, embed):
    config = load_log_config()
    channel_id = config.get(str(guild.id))
    if channel_id:
        channel = guild.get_channel(int(channel_id))
        if channel:
            await channel.send(embed=embed)

# 1. Mesaj Takibi (Everyone/Here Etiketi)
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if "@everyone" in message.content or "@here" in message.content:
        embed = discord.Embed(title="⚠️ Etiket Algılandı", color=discord.Color.red())
        embed.add_field(name="Kullanıcı", value=message.author.mention, inline=True)
        embed.add_field(name="Kanal", value=message.channel.mention, inline=True)
        embed.add_field(name="Mesaj İçeriği", value=message.content, inline=False)
        await send_log(message.guild, embed)

    await bot.process_commands(message)

# 2. Rol Güncellemeleri
@bot.event
async def on_member_update(before, after):
    if before.roles != after.roles:
        added_roles = [role for role in after.roles if role not in before.roles]
        removed_roles = [role for role in before.roles if role not in after.roles]

        if added_roles or removed_roles:
            embed = discord.Embed(title="🛡️ Rol Değişikliği", color=discord.Color.blue())
            embed.add_field(name="Kullanıcı", value=after.mention, inline=False)
            
            if added_roles:
                embed.add_field(name="Verilen Roller", value=", ".join([r.mention for r in added_roles]), inline=False)
            if removed_roles:
                embed.add_field(name="Alınan Roller", value=", ".join([r.mention for r in removed_roles]), inline=False)
            
            await send_log(after.guild, embed)

# 3. Kanal Oluşturma/Silme
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

# 4. Sunucudan Ayrılma/Atılma
@bot.event
async def on_member_remove(member):
    embed = discord.Embed(title="🚪 Kullanıcı Ayrıldı", color=discord.Color.orange())
    embed.add_field(name="Kullanıcı", value=f"{member.name} ({member.id})", inline=False)
    await send_log(member.guild, embed)

# --- Botu Çalıştır ---
if __name__ == "__main__":
    keep_alive()
    # Token'ı çevre değişkeninden al (Güvenlik için)
    token = os.environ.get("DISCORD_TOKEN")
    if token:
        bot.run(token)
    else:
        print("HATA: 'DISCORD_TOKEN' çevre değişkeni bulunamadı!")
