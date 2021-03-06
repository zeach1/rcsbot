from discord.ext import commands, tasks
from cogs.utils.season import get_season_end, update_season
from datetime import date, datetime
from dateutil import relativedelta


class SeasonConfig(commands.Cog, command_attrs=dict(hidden=True)):
    def __init__(self, bot):
        self.bot = bot
        self.start_new_season.start()

    def cog_unload(self):
        self.start_new_season.cancel()

    @staticmethod
    def next_last_monday():
        now = date.today()
        day = now + relativedelta.relativedelta(month=now.month + 1,
                                                weekday=relativedelta.MO(1))
        return day

    @tasks.loop(minutes=15.0)
    async def start_new_season(self):
        now = datetime.utcnow()
        season_end = get_season_end()
        end = datetime(year=season_end[:4], month=season_end[5:7], day=season_end[-2:], hour=5)
        if now > end:
            update_season(self.next_last_monday())


def setup(bot):
    bot.add_cog(SeasonConfig(bot))
