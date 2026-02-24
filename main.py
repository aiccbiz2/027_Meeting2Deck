import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import logging

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    logging.info(f"Meeting2Deck Bot 로그인: {bot.user}")
    await bot.load_extension("cogs.meeting2deck_bot")
    logging.info("meeting2deck_bot cog 로드 완료")


bot.run(os.getenv("DISCORD_TOKEN"))
