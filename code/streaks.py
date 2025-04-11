import discord
import json
import os
from datetime import timedelta, timezone, datetime, time
from discord.ext import commands, tasks

# --- Cog Definition ---

DATA_STORE_PATH = "./data/streaks.json"

class StreaksCog(commands.Cog):

    # --- Initialize ---
    def __init__(self, bot: commands.Bot, channel: discord.TextChannel):
        self.bot = bot
        self.channel = channel
        self._last_member = None

        # Ensure path to streaks.json exists
        if not os.path.exists(DATA_STORE_PATH):
            os.mkdir("/data")
            open(DATA_STORE_PATH, "w").close()

        # Initialize data store
        self.data = {}
        with open(DATA_STORE_PATH, "r") as file:
            try:
                self.data = json.load(file)
            except Exception as e:
                self.data = {}

    # --- Method Definitions --- 
    def increment_streak(self, user: discord.User) -> int:
        """Increments the user's streak by one (defaulting to 1 if there user is not found in dict) if the user has not already had their streak incremented today.

        Returns the length of the user's new streak or -1 if the user's streak cannot be incremented
        """
        streak = self.data.get(
            str(user.id), 
            {
                "timestamp": None, 
                "streak": 0, 
                "highscore": 0
            }
        )
        try:
            previousDate = datetime.fromtimestamp(streak["timestamp"]).date()
        except Exception:
            previousDate = None
        
        today = datetime.today().date()

        if previousDate is None or previousDate != today:
            # Valid window to increase streak
            streak["timestamp"] = datetime.timestamp(datetime.now()) # Update timestamp
            streak["streak"] += 1 # Increment streak
            streak["highscore"] = max(streak['streak'], streak['highscore']) # Adjust user high score
            self.data[str(user.id)] = streak # Save updated chungus to data store
            return streak["streak"]
        else:
            return -1
        
    def save(self) -> None:
        """Save's instance's data dict to streaks.json in the working directory"""
        with open(DATA_STORE_PATH, "w") as file:
            try:
                json.dump(self.data, file)
            except Exception as e:
                pass

    # --- Scheduled Tasks ---

    @tasks.loop(time=time(hour=0, minute=0, second=0, tzinfo=timezone.utc))
    async def eod_manage_streaks(self) -> None:
        """Prune expired streaks every day at 12:00 AM (midnight)."""
        today = datetime.now().date()
        updatedData = {}
        prunedUsers = []
        for key, value in self.data.items():
            if value['streak'] == 0:
                # Skip users with no streak
                continue
            if today - datetime.fromtimestamp(value['timestamp']).date() >= timedelta(days=1):
                # Streak has expired, update streak and append username to message list
                updatedData[key] = {
                    "streak": 0,
                    "timestamp": datetime.timestamp(),
                    "highscore": max(value['streak'], value['highscore'])
                }
                prunedUsers.append(self.bot.get_user(int(key)).mention)
            else:
                updatedData[key] = value
        self.data = updatedData
        await self.channel.send('Streaks broken: ' + ' '.join(prunedUsers))
        self.save()

    # --- Commands ---

    @commands.command()
    async def highscore(self, context: commands.Context):
        """Sends the author's streaks high score to the streaks channel."""

        # Guard channels that this cog doesn't care about
        if not context.channel.id == self.channel.id:
            return
        
        streak = self.data.get(str(context.author.id))

        if streak is None:
            await context.channel.send(
                f"{context.author.mention}, you've never been in the dungeon. Send a photo of yourself in the dungeon to begin a streak!"
            )
        else:
            await context.channel.send(
                f"{context.author.mention}, your highest dungeon streak is {streak['highscore']} {"day" if int(streak['highscore']) == 1 else "days"}."
            )

    @commands.command()
    async def leaderboard(self, context: commands.Context):
        """Sends a leaderboard of the top [n] streaks."""

        # Guard channels that this cog doesn't care about
        if not context.channel.id == self.channel.id:
            return
        
        # Declere message array to store pieces of final message
        message = []

        # Print header and return if no data
        if len(self.data) > 0:
            message.append(f"{context.author.mention}, here is the current streaks leaderboard:")
        else:
            message.append(f"{context.author.mention}, here is the current streaks leaderboard:")

        # Sort data on highscore, high to low
        sortedStreaks = sorted(self.data.items(), key=lambda x: x[1]['highscore'])

        # Get the top argument
        args = context.message.content.split()
        try:
            n = int(args[1])
        except Exception as e:
            n = 10

        message.append('```') # Put leaderboard in code block bc monospace is cool

        # Recall that sorted is a list of tuples: (str: userID, dict: streak)
        for index, item in enumerate(sortedStreaks):
            # Dont print more than user asked for
            if n is not None:
                if index >= n:
                    break

            user = self.bot.get_user(int(item[0]))
            if user is None:
                break

            highscore = int(item[1]['highscore'])
            message.append(f"{index + 1}. {user.display_name:<25} {highscore} {"day" if highscore == 1 else "days"}")
        
        await context.channel.send('\n'.join(message) + '```')

    # --- Main Listener --- 

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
