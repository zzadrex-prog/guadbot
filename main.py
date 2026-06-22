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
    return "Bot Aktif!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- Discord Bot Ayarları ---
intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)

# Verileri saklamak için dosya sistemi
LOG_DATA_FILE = "log_config.json"

def load_config():
    if os.path.exists(LOG_DATA_FILE):
        with open(LOG_DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_config(config):
    with open(LOG_DATA_FILE, "w") as f:
        json.dump(config, f)

# URL tespiti için Regex (Düzenli İfade)
URL_REGEX = r"(https?:\/\/[^\s]+)"

@bot.event
async def on_ready():
    print(f'Giriş yapıldı: {bot.user.name}')
    await bot.change_presence(activity=discord.Game(name="Güvenlik Sağlanıyor"))

# --- Log Kanalı Ayarlama Komutu ---
@bot.command()
@commands.has_permissions(administrator=True)
async def log(ctx, channel: discord.TextChannel):
    config = load_config()
    if str(ctx.guild.id) not in config:
        config[str(ctx.guild.id)] = {}
    config[str(ctx.guild.id)]["log_channel"] = channel.id
    save_config(config)
    await ctx.send(f"✅ Log kanalı başarıyla {channel.mention} olarak ayarlandı.")

# --- Korunan Rol Ayarlama Komutu ---
@bot.command()
@commands.has_permissions(administrator=True)
async def rol(ctx, role: discord.Role):
    config = load_config()
    if str(ctx.guild.id) not in config:
        config[str(ctx.guild.id)] = {}
    config[str(ctx.guild.id)]["protected_role"] = role.id
    save_config(config)
    await ctx.send(f"🛡️ Korunan rol başarıyla {role.mention} olarak ayarlandı. Bu role sahip kişiler link veya everyone/here atarsa banlanacak.")

# Hata Yönetimi
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ Bu komutu kullanmak için 'Yönetici' yetkisine sahip olmalısınız.")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("❌ Geçersiz argüman! Örnek kullanım:\n`!log #kanal` veya `!rol @rol`")

# --- Log Gönderme Fonksiyonu (Rate Limit Korumalı) ---
async def send_log(guild, embed):
    config = load_config()
    guild_data = config.get(str(guild.id), {})
    channel_id = guild_data.get("log_channel")
    
    if channel_id:
        channel = guild.get_channel(int(channel_id))
        if channel:
            try:
                await channel.send(embed=embed)
                await asyncio.sleep(1) # Rate limit yememek için her log arası 1 saniye bekleme
            except discord.errors.HTTPException:
                pass # Yoğun istek dalgalarında çökmesini önler

# --- Olay Takip Sistemleri ---

# 1. Mesaj ve Link/Etiket Koruması
@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        return

    config = load_config()
    guild_data = config.get(str(message.guild.id), {})
    protected_role_id = guild_data.get("protected_role")

    # Kullanıcıda korunan rol var mı kontrol et
    has_protected_role = False
    if protected_role_id:
        has_protected_role = any(r.id == int(protected_role_id) for r in message.author.roles)

    if has_protected_role:
        contains_mention = "@everyone" in message.content or "@here" in message.content
        contains_url = re.search(URL_REGEX, message.content)

        if contains_mention or contains_url:
            reason = "Korunan roldeyken yasaklı eylem (Link veya Everyone/Here Etiketi)"
            try:
                # Önce mesajı sil
                await message.delete()
                # Kullanıcıyı banla
                await message.author.ban(reason=reason, delete_message_days=1)
                
                # Log Bilgisi Oluştur
                embed = discord.Embed(title="🚨 Guard Sistemi: Kullanıcı Banlandı!", color=discord.Color.red())
                embed.add_field(name="Kullanıcı", value=f"{message.author.mention} ({message.author.id})", inline=False)
                embed.add_field(name="Sebep", value="Korumalı rolde olmasına rağmen link paylaştı veya etiket attı.", inline=False)
                embed.add_field(name="İçerik", value=f"||{message.content}||", inline=False)
                await send_log(message.guild, embed)
                return # Tetiklenme durumunda komut işlemeyi durdur
            except discord.Forbidden:
                print(f"Yetki Yetersiz: {message.author.name} banlanamadı. Botun rolü üyenin rolünden üstte olmalı.")
            except discord.HTTPException:
                await asyncio.sleep(5) # Rate limit durumunda güvenli bekleme

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
    token = os.environ.get("DISCORD_TOKEN")
    if token:
        bot.run(token)
    else:
        print("HATA: 'DISCORD_TOKEN' çevre değişkeni bulunamadı!")
