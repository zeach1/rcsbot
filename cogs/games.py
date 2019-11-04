import coc
import math
import re

from discord.ext import commands
from cogs.utils.converters import ClanConverter, PlayerConverter
from cogs.utils.db import Sql
from cogs.utils import formats
from config import settings

tag_validator = re.compile("^#?[PYLQGRJCUV0289]+$")


class Games(commands.Cog):
    """Cog for Clan Games"""
    def __init__(self, bot):
        self.bot = bot

    @commands.group(invoke_without_command=True)
    async def games(self, ctx, *, clan: ClanConverter = None):
        """[Group] Commands for clan games"""
        if ctx.invoked_subcommand is not None:
            return

        if not clan:
            await ctx.invoke(self.games_all)
        else:
            await ctx.invoke(self.games_clan, clan=clan)

    @games.command(name="all")
    async def games_all(self, ctx):
        with Sql(as_dict=True) as cursor:
            cursor.execute("SELECT TOP 1 clanPoints "
                           "FROM rcs_events "
                           "WHERE eventType = 5 "
                           "ORDER BY eventId DESC")
            row = cursor.fetchone()
            clan_points = row['clanPoints']
            cursor.callproc("rcs_spClanGamesTotal")
            data = []
            for clan in cursor:
                if clan['clanTotal'] >= clan_points:
                    data.append([clan['clanTotal'], "* " + clan['clanName']])
                else:
                    data.append([clan['clanTotal'], clan['clanName']])
        page_count = math.ceil(len(data) / 25)
        title = "RCS Clan Games Points"
        ctx.icon = "https://cdn.discordapp.com/emojis/639623355770732545.png"
        p = formats.TablePaginator(ctx, data=data, title=title, page_count=page_count)
        await p.paginate()

    @games.command(name="average", aliases=["avg", "averages"])
    async def games_average(self, ctx):
        with Sql(as_dict=True) as cursor:
            data = []
            cursor.callproc("rcs_spClanGamesAverage")
            for clan in cursor:
                data.append([clan['clanAverage'], clan['clanName']])
        page_count = math.ceil(len(data) / 25)
        title = "RCS Clan Games Averages"
        ctx.icon = "https://cdn.discordapp.com/emojis/639623355770732545.png"
        p = formats.TablePaginator(ctx, data=data, title=title, page_count=page_count)
        await p.paginate()

    @games.command(name="clan")
    async def games_clan(self, ctx, clan: ClanConverter = None):
        async with ctx.typing():
            with Sql(as_dict=True) as cursor:
                cursor.execute("SELECT TOP 1 playerPoints, startTime "
                               "FROM rcs_events "
                               "WHERE eventType = 5 "
                               "ORDER BY eventId DESC")
                row = cursor.fetchone()
                player_points = row['playerPoints']
                cursor.execute("CREATE TABLE #rcs_players (playerTag varchar(15), playerName nvarchar(50)) "
                               "INSERT INTO #rcs_players "
                               "SELECT DISTINCT playerTag, playerName FROM rcs_members")
                cursor.execute(f"SELECT '#' + playerTag as tag, CASE WHEN (currentPoints - startingPoints) > {player_points} "
                               f"THEN {player_points} ELSE (currentPoints - startingPoints) END AS points "
                               f"FROM rcs_clanGames "
                               f"WHERE eventId = (SELECT MAX(eventId) FROM rcs_events WHERE eventType = 5) "
                               f"AND clanTag = '{clan.tag[1:]}' "
                               f"ORDER BY points DESC")
                fetched = cursor.fetchall()
                cursor.callproc("rcs_spClanGamesAverage")
                for row in cursor:
                    if clan.name.lower() == row['clanName'].lower():
                        clan_average = row['clanAverage']
                        break
                clan_total = 0
                data = []
                for member in fetched:
                    clan_total += member['points']
                    player = await self.bot.coc.get_player(member['tag'], cache=True)
                    if member['points'] >= player_points:
                        data.append([member['points'], "* " + player.name])
                    else:
                        data.append([member['points'], player.name])
        page_count = math.ceil(len(data) / 25)
        title = f"{clan.name} Points {clan_total}"
        ctx.icon = "https://cdn.discordapp.com/emojis/639623355770732545.png"
        p = formats.TablePaginator(ctx, data=data, title=title, page_count=page_count)
        await p.paginate()

    @games.command(name="add", aliases=["games+", "ga"], hidden=True)
    @commands.has_any_role(settings['rcs_roles']['council'],
                           settings['rcs_roles']['chat_mods'],
                           settings['rcs_roles']['leaders'])
    async def games_add(self, ctx, player: PlayerConverter = None, clan: ClanConverter = None, games_points: int = 0):
        """Add player who missed the initial pull"""
        if not player:
            return await ctx.send("Please provide a valid player tag.")
        if not clan:
            return await ctx.send("Please provide a valid clan tag.")
        if player.clan.tag == clan.tag:
            with Sql(as_dict=True) as cursor:
                cursor.execute("SELECT MAX(eventId) as eventId FROM rcs_events WHERE eventType = 5")
                row = cursor.fetchone()
                event_id = row['eventId']
                try:
                    starting_points = player.achievements_dict['Games Champion'].value - games_points
                    current_points = player.achievements_dict['Games Champion'].value
                except:
                    self.bot.logger.debug("points assignment failed for some reason")
                sql = (f"INSERT INTO rcs_clanGames (eventId, playerTag, clanTag, startingPoints, currentPoints) "
                       f"VALUES (%d, %s, %s, %d,. %d)")
                cursor.execute(sql, (event_id, player.tag[1:], player.clan.tag[1:], starting_points, current_points))
            await ctx.send(f"{player.name} ({player.clan.name}) has been added to the games database.")
        else:
            response = f"{player.name}({player.tag}) is not currently in {clan.name}({clan.tag})."
            await ctx.send(response)


def setup(bot):
    bot.add_cog(Games(bot))
