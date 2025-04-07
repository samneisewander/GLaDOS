#!/usr/bin/env python3

# --- Imports ---
import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import streaks

# --- Configuration ---
load_dotenv(override=True)
DISCORD_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
STREAKS_CHANNEL_ID = int(os.getenv("STREAKS_CHANNEL_ID", 0))
print(f"Loaded dotenv: {DISCORD_TOKEN}")

# --- Discord Bot Configuration ---
intents = discord.Intents.default()
intents.messages = True
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# --- Ready up ---
@bot.event
async def on_ready() -> None:
    print(f'Logged in as {bot.user.name} (ID: {bot.user.id})')

    # --- Attach cogs ---
    await bot.add_cog(streaks.StreaksCog(bot, bot.get_channel(STREAKS_CHANNEL_ID)))

# --- Start bot ---
if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)