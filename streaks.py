#!/usr/bin/env python3
import discord
import json
import os
from datetime import timedelta, timezone, datetime, time
from discord.ext import commands, tasks

# --- Initialize --- 

class StreaksCog(commands.Cog):

    def __init__(self, bot: commands.Bot, channel: discord.TextChannel, logger):
        self.bot = bot
        self.channel = channel
        self._last_member = None
        self.logger = logger

        # Ensure streaks.json exists in current
        if not os.path.exists("./streaks.json"):
            open("streaks.json", "w").close()

        # Initialize data store
        self.data = {}
        with open("streaks.json", "r") as file:
            try:
                self.data = json.load(file)
            except Exception as e:
                self.logger.error(f"ERROR: Could not load JSON from streaks.json: {e}")
                self.data = {}
        self.logger.info(f"Streaks data initialized to {self.data}.")

    def increment_streak(self, user: discord.User) -> int:
        """Increments the user's streak by one (defaulting to 1 if there user is not found in dict) if the user has not already had their streak incremented today. 

        In the data store, the values are arrays of this format:
        [userName, timestamp, streakCount, maxStreakCount]

        Returns the length of the user's new streak or -1 if the user's streak cannot be incremented
        """
        streak = self.data.get(str(user.id), [user.name, None, 0, 0])
        previousDate = None if streak[1] is None else datetime.fromtimestamp(streak[1]).date()
        today = datetime.today().date()
        
        self.logger.info(f"Checking streak for {user.name}")
        self.logger.info(f"\tCurrent streak: {streak[2]}")
        self.logger.info(f"\tLast recorded update: {previousDate}")
        self.logger.info(f"\tToday: {today}")

        if streak[1] is None or previousDate != today:
            # Valid window to increase streak
            self.logger.info("\tValid. Advancing streak")
            streak[1] = datetime.timestamp(datetime.now()) # Update timestamp
            streak[2] += 1 # Increment streak
            streak[3] = max(streak[2], streak[3]) # Adjust user high score
            self.data[str(user.id)] = streak # Save updated chungus to data store
            return streak[2]
        else:
            return -1
        
    def save(self) -> None:
        """Save's instance's data dict to streaks.json in the working directory"""
        self.logger.info("Running save job...")
        with open("streaks.json", "w") as file:
            try:
                json.dump(self.data, file)
                self.logger.info("Save complete.")
            except Exception as e:
                self.logger.error(f"ERROR: Could not save streak data: {e}")

    @tasks.loop(time=time(hour=0, minute=0, second=0, tzinfo=timezone.utc))
    async def eod_manage_streaks(self) -> None:
        """Prune expired streaks every day at 12:00 AM (midnight)."""
        self.logger.info("Peforming daily streak pruning...")
        today = datetime.now().date()
        updatedData = {}
        prunedUsers = []
        for key, value in self.data.items():
            if value[2] == 0:
                # Skip users with no streak
                continue
            if today - datetime.fromtimestamp(value[1]).date() >= timedelta(days=1):
                # Streak has expired, update streak and append username to message list
                updatedData[key] = value[:2] + [0, max(value[2], value[3])]
                prunedUsers.append(self.bot.get_user(int(key)).mention)
            else:
                updatedData[key] = value
        self.logger.info('\tStreaks broken: ' + ' '.join(prunedUsers))
        self.data = updatedData
        await self.channel.send('Streaks broken: ' + ' '.join(prunedUsers))
        self.save()
        self.logger.info("Done.")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """Handles messages sent to the channel configured to run the streaks game.
        The streaks game works as follows: users extend their streak each day by sending
        an image to this channel. If any user fails to send an image to the channel by midnight,
        their streak gets dropped. A leaderboard exists for current longest streak and all
        time longest streak.
        """
        # Guard cases the class doesn't care about
        if message.author == self.bot.user:
            return
        if message.channel is not self.channel:
            return
        
        for attachment in message.attachments:
            if attachment.content_type and attachment.content_type.startswith('image/'):
                streak = self.increment_streak(message.author)
                if streak > 0:
                    unit = 'days' if streak > 1 else 'day'
                    await message.channel.send(f"{message.author.mention} has been in the dungeon for {streak} {unit}!")
                    self.save()
            break
