import discord
from discord.ext import commands
import os
from flask import Flask
from threading import Thread
import json

# --- Flask Web Sunucusu (Render Uyumluluğu) ---
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
    print(f'Bot {bot.user.name} olarak aktif!')

# --- Komutlar ---

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
    """Kullanımı: !rol 1234567890 veya !rol @RolAdı"""
    config = load_config()
    config["ban_roles"][str(ctx.guild.id)] = role.id
    save_config(config)
    await ctx.send(f"🚫 Yasaklı rol ayarlandı: **{role.name}**. Bu roldekiler everyone/here atarsa banlanacak!")

# --- Olay Takibi ---

async def send_log(guild, embed):
    config = load_config()
    channel_id = config["logs"].get(str(guild.id))
    if channel_id:
        channel = guild.get_channel(int(channel_id))
        if channel: await channel.send(embed=embed)

@bot.event
async def on_message(message):
    if message.author.bot or not message.guild: return

    # Everyone veya Here etiketi kontrolü
    if "@everyone" in message.content or "@here" in message.content:
        config = load_config()
        ban_role_id = config["ban_roles"].get(str(message.guild.id))
        
        # Eğer sunucu için bir yasaklı rol ayarlanmışsa ve kullanıcı bu role sahipse
        if ban_role_id and discord.utils.get(message.author.roles, id=int(ban_role_id)):
            try:
                # Önce log gönderelim (banlandıktan sonra bilgi almak zor olabilir)
                embed = discord.Embed(title="🔨 OTOMATİK BAN", color=discord.Color.red())
                embed.add_field(name="Kullanıcı", value=f"{message.author} ({message.author.id})", inline=False)
                embed.add_field(name="Sebep", value="Yasaklı rolde olmasına rağmen everyone/here etiketi kullandı.", inline=False)
                embed.add_field(name="Mesaj", value=message.content, inline=False)
                await send_log(message.guild, embed)
                
                # Kullanıcıyı banla
                await message.author.ban(reason="Yasaklı rolde etiket kullanımı (Guard Bot)")
                
                # Mesajı sil (opsiyonel, kalabalık yapmasın)
                await message.delete()
                return
            except Exception as e:
                print(f"Banlama sırasında hata oluştu: {e}")

    await bot.process_commands(message)

if __name__ == "__main__":
    keep_alive()
    token = os.environ.get("DISCORD_TOKEN")
    if token:
        bot.run(token)
    else:
        print("HATA: DISCORD_TOKEN bulunamadı!")
