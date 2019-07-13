from loguru import logger
import discord
from discord.ext import commands
from datetime import datetime, timedelta
from random import randint
from config import settings


class Background(commands.Cog):
    """Cog for background tasks. No real commands here."""
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if isinstance(message.channel, discord.DMChannel):
            await message.channel.send("Thanks for chatting, but I'm really not set up for that. Perhaps try a "
                                       "command like `++help`.")
            return
        if message.guild.id != settings['discord']['rcsGuildId']:
            return
        logger.debug("New message received.")
        if message.author == self.bot.user:
            return
        if settings['rcsRoles']['members'] not in [role.id for role in message.author.roles]:
            logger.debug("No member role.\n{} has the following roles.\n{}",
                         message.author.display_name, message.author.roles)
            return
        logger.debug("User has member role.")
        conn = self.bot.db.pool
        logger.debug("Postgresql connection established.")
        row = await conn.fetchrow(f"SELECT * FROM rcs_discord WHERE discord_id = {message.author.id}")
        points = randint(7, 14)
        if row:
            if datetime.now() > row['last_message'] + timedelta(minutes=1):
                await conn.execute(f"UPDATE rcs_discord "
                                   f"SET message_points = {row['message_points']+points}, "
                                   f"last_message = '{datetime.now()}', "
                                   f"message_count = {row['message_count']+1} "
                                   f"WHERE discord_id = {message.author.id}")
                logger.info("{} receives {} for their message", message.author.display_name, points)
            else:
                await conn.execute(f"UPDATE rcs_discord "
                                   f"SET last_message = '{datetime.now()}' "
                                   f"WHERE discord_id = {message.author.id}")
                logger.info("{} posted within the last minute. No points awarded.", message.author.display_name)
        else:
            await conn.execute(f"INSERT INTO rcs_discord "
                               f"VALUES ({message.author.id}, {points}, 0, '{datetime.now()}', 1)")
            logger.info("Added {} to the rcs_discord table for message tracking", message.author.display_name)


def setup(bot):
    bot.add_cog(Background(bot))
