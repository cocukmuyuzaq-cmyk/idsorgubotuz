# Kurulum: pip install discord.py aiohttp
# Render > Environment Variables: KEY = TOKEN , VALUE = bot_tokenin

import os
import time
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler

import discord
from discord import app_commands
from discord.ext import commands
import aiohttp

# --- Render Web Service için port dinleyici (ZORUNLU) ---
class Ping(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")
    def log_message(self, *a):
        pass

def run_server():
    port = int(os.getenv("PORT", 10000))
    HTTPServer(("0.0.0.0", port), Ping).serve_forever()

Thread(target=run_server, daemon=True).start()
# --------------------------------------------------------

API_BASE = "https://prox0959.netlify.app/api/search"
TOKEN = os.getenv("TOKEN")

ALLOWED_GUILD_ID = 1546912458793287725
COOLDOWN_SECONDS = 60

cooldowns = {}


class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="/", intents=intents, help_command=None)

    async def setup_hook(self):
        guild = discord.Object(id=ALLOWED_GUILD_ID)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)
        print(f"Slash komutlar senkronize edildi: guild {ALLOWED_GUILD_ID}")

    async def on_ready(self):
        await self.change_presence(
            status=discord.Status.dnd,
            activity=discord.Game(name="/idsorgu")
        )
        print(f"Bot hazır: {self.user}")


bot = MyBot()


@bot.tree.command(name="idsorgu", description="ID sorgular")
@app_commands.describe(id="Sorgulanacak ID")
async def idsorgu(interaction: discord.Interaction, id: str):
    if interaction.guild is None or interaction.guild.id != ALLOWED_GUILD_ID:
        await interaction.response.send_message("Bu komut burada kullanılamaz.", ephemeral=True)
        return

    user_id = interaction.user.id
    now = time.time()
    last_used = cooldowns.get(user_id, 0)
    remaining = COOLDOWN_SECONDS - (now - last_used)

    if remaining > 0:
        await interaction.response.send_message(
            f"⏳ Çok hızlısın! Tekrar kullanmak için **{int(remaining)} saniye** bekle.",
            ephemeral=True
        )
        return

    cooldowns[user_id] = now

    await interaction.response.defer()

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{API_BASE}?id={id}") as resp:
                if resp.status != 200:
                    await interaction.followup.send(f"HTTP {resp.status}")
                    return
                data = await resp.json()

        if not data.get("success"):
            await interaction.followup.send("API başarısız yanıt döndü.")
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
        await interaction.followup.send(embed=embed)

    except Exception as e:
        print(e)
        try:
            await interaction.followup.send(f"Hata: {e}")
        except Exception:
            pass


bot.run(TOKEN)
