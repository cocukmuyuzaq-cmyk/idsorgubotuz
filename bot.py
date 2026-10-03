# Kurulum: pip install discord.py aiohttp
# Render > Environment Variables: KEY = TOKEN , VALUE = bot_tokenin

import os
import discord
from discord.ext import commands
import aiohttp

API_BASE = "https://prox0959.netlify.app/api/search"
TOKEN = os.getenv("TOKEN")

# Sadece bu sunucuda çalışsın — kendi sunucu ID'ni buraya yaz
ALLOWED_GUILD_ID = 123456789012345678  # <<< BURAYI DEĞİŞTİR

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="/", intents=intents, help_command=None)


@bot.event
async def on_ready():
    # Rahatsız etme durumu
    await bot.change_presence(
        status=discord.Status.dnd,
        activity=discord.Game(name="/idsorgu")
    )
    print(f"Bot hazır: {bot.user}")


@bot.check
async def globally_allowed(ctx):
    # DM'de çalışmasın
    if ctx.guild is None:
        return False
    # Sadece izin verilen sunucuda çalışsın
    if ctx.guild.id != ALLOWED_GUILD_ID:
        return False
    return True


@bot.command(name="idsorgu")
async def idsorgu(ctx, id: str = None):
    if not id:
        await ctx.reply("Kullanım: `/idsorgu <ID>`")
        return

    loading = await ctx.reply("Sorgulanıyor...")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{API_BASE}?id={id}") as resp:
                if resp.status != 200:
                    await loading.edit(content=f"HTTP {resp.status}")
                    return
                data = await resp.json()

        if not data.get("success"):
            await loading.edit(content="API başarısız yanıt döndü.")
            return

        found = data.get("found", False)
        embed = discord.Embed(
            title="Kayıt Bulundu" if found else "Kayıt Bulunamadı",
            color=0x00E676 if found else 0xFFC107,
        )
        embed.add_field(name="Sorgu ID", value=f"`{data.get('queryId', '-')}`", inline=True)
        embed.add_field(name="Eşleşme", value=str(data.get("totalMatches", 0)), inline=True)
        embed.add_field(name="Global Arama", value=str(data.get("totalGlobalSearches", 0)), inline=True)

        matches = data.get("matches", []) or []
        if found and matches:
            for i, m in enumerate(matches[:5]):
                content = m.get("content", "")
                dev = m.get("dev", "-")
                line = m.get("lineNumber", "?")
                embed.add_field(
                    name=f"Eşleşme #{i + 1} (Satır {line})",
                    value=f"```{content}```\nKaynak: `{dev}`",
                    inline=False,
                )

        embed.set_footer(text="Prox0959 ID Sorgu")
        await loading.edit(content="", embed=embed)

    except Exception as e:
        print(e)
        await loading.edit(content=f"Hata: {e}")


@bot.event
async def on_command_error(ctx, error):
    # CheckFailed / komut bulunamadı vs. sessizce yut — DM ve diğer sunucularda cevap vermesin
    if isinstance(error, commands.CheckFailure):
        return
    if isinstance(error, commands.CommandNotFound):
        return
    # Diğer hataları sadece izin verilen sunucuda göster
    if ctx.guild and ctx.guild.id == ALLOWED_GUILD_ID:
        try:
            await ctx.reply(f"Hata: {error}")
        except Exception:
            pass


bot.run(TOKEN)
