import discord

from discord.ext import commands
from cogs.utils.db import Sql
from cogs.utils.helper import get_emoji_url
from cogs.utils import challenges
from datetime import datetime


class Halloween(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.title = "🎃 RCS Trick or Treat Adventure 🎃"
        self.color = discord.Color.dark_orange()

    def build_embed(self, data):
        embed = discord.Embed(title=self.title, description=data['challenge'], color=self.color)
        embed.add_field(name="Players:", value=data['num_players'], inline=True)
        embed.add_field(name="Players Finished:", value=data['num_finished'], inline=True)
        embed.add_field(name="Your progress:", value=f"{data['cur_challenge'] - 1}/15", inline=True)
        embed.add_field(name="Skips:", value=data['skips'], inline=True)
        embed.set_footer(text=f"{data['elapsed']} elapsed in your adventure",
                         icon_url="https://cdn.discordapp.com/emojis/629481616091119617.png")
        return embed

    @staticmethod
    def get_elapsed(start_time):
        date_fmt = "%Y-%m-%d %H:%M:%S.%f"
        elapsed = datetime.utcnow() - start_time   # datetime.strptime(start_time, date_fmt)
        hours, rem = divmod(elapsed.seconds, 3600)
        mins, secs = divmod(rem, 60)
        return f"{hours:2.0f}:{mins:2.0f}:{secs:2.0f}"

    @property
    def invite_link(self):
        perms = discord.Permissions.none()
        perms.read_messages = True
        perms.external_emojis = True
        perms.send_messages = True
        perms.manage_channels = True
        perms.manage_messages = True
        perms.embed_links = True
        perms.read_message_history = True
        perms.add_reactions = True
        perms.attach_files = True
        return discord.utils.oauth_url(self.bot.client_id, perms)

    @commands.group(name="halloween", aliases=["h"])
    async def halloween(self, ctx):
        """[Group] Let the halloween fun begin!  Trick or treat!"""
        if ctx.invoked_subcommand is None:
            return await ctx.send_help(ctx.command)

    @halloween.command(name="install", hidden=True)
    @commands.is_owner()
    async def halloween_install(self, ctx):
        with Sql(as_dict=True) as cursor:
            sql = "SELECT discord_id FROM rcs_halloween_clans"
            cursor.execute(sql)
            fetch = cursor.fetchall()
        for clan in fetch:
            guild = ctx.bot.get_guild(clan['discord_id'])
            found = False
            for channel in guild.channels:
                if channel.name == "trick-or-treat":
                    found = True
                    await ctx.send(f"#trick-or-treat already exists on the {guild.name} server.")
                    perms = channel.permissions_for(guild.me)
                    if not perms.manage_channels:
                        await ctx.send(f"I found #trick-or-treat on the {guild.name} server, but I don't have "
                                       f"perms to manage the channel.")
                        break
                    break
            # if not found:
            #     try:
            #         overwrites = {
            #             ctx.me: discord.PermissionOverwrite(read_messages=True, send_messages=True,
            #                                                 read_message_history=True, embed_links=True,
            #                                                 manage_messages=True, add_reactions=True,
            #                                                 external_emojis=True),
            #             guild.default_role: discord.PermissionOverwrite(read_messages=False,
            #                                                             send_messages=False,
            #                                                             read_message_history=False)
            #         }
            #         reason = "Channel created by RCS-Bot"
            #         channel = await guild.create_text_channel(name="trick-or-treat",
            #                                                   overwrites=overwrites,
            #                                                   reason=reason)
            #         await ctx.send(f"{channel.name} created on the {guild.name} server.")
            #     except discord.Forbidden:
            #         await ctx.send(f"No perms to create a channel in {guild.name}.")
            #         break
            # with Sql(as_dict=True) as cursor:
            #     sql = "UPDATE rcs_halloween_clans SET channel_id = %d WHERE discord_id = %d"
            #     cursor.execute(sql, (channel.id, guild.id))
            # await channel.send("🎃 **Halloween is coming** 🎃\n\n"
            #                    "The RCS has something mysterious planned for you.  If you would like to participate, "
            #                    "type `++halloween join` and we will send you a message when the fun begins!")

    @halloween.command(name="join", aliases=["register"])
    async def halloween_join(self, ctx):
        """ - Issue this command to register for the event"""
        async with ctx.typing():
            with Sql() as cursor:
                sql = ("INSERT INTO rcs_halloween_players (discord_id) "
                       "OUTPUT Inserted.discord_id "
                       "SELECT %d "
                       "EXCEPT SELECT discord_id FROM rcs_halloween_players WHERE discord_id = %d")
                cursor.execute(sql, (ctx.author.id, ctx.author.id))
                fetch = cursor.fetchone()
        if not fetch:
            await ctx.send("You're already registered for the event. I'll send you a DM when the event is "
                           "ready to begin!")
        else:
            await ctx.send("I've registered you for the event.  I'll send you a DM when the event is ready to begin!")

    @halloween.command(name="start")
    async def halloween_start(self, ctx):
        """ - Issue this command to start the event."""
        async with ctx.typing():
            with Sql() as cursor:
                # Check to see if they've already started
                sql = "SELECT start_time FROM rcs_halloween_players WHERE discord_id = %d"
                cursor.execute(sql, ctx.author.id)
                fetch = cursor.fetchone()
                if fetch[0]:
                    start_time = fetch[0]
                    return await ctx.send(f"You started the event at {start_time} UTC. If you need a reminder "
                                          f"about your next challenge, just type `++halloween remind`.")
                # Initiate time and issue the first clue
                start_time = datetime.utcnow()
                cursor.callproc("rcs_halloween_start", (ctx.author.id, start_time))
                sql = "SELECT COUNT(discord_id) FROM rcs_halloween_players WHERE start_time IS NOT NULL"
                cursor.execute(sql)
                fetch = cursor.fetchone()
                num_players = fetch[0]
                sql = "SELECT channel_ID, invite_link FROM rcs_halloween_clans WHERE discord_id = %d"
                cursor.execute(sql, 437848948204634113)
                fetch = cursor.fetchone()
                electrum_channel = fetch[0]
                electrum_invite = fetch[1]
        desc = ("Congratulations! Your time has started and you have officially begun the RCS Trick or Treat "
                "Adventure! You will now be offered 15 challenges to accomplish. You will have 3 skips that you "
                "can use strategically throughout the event. Use them wisely! The member completing the challenges "
                "in the shortest amount of time wins!")
        clue = (f"Head over to the Reddit Electrum Discord server ({electrum_invite}), "
                     f"find the <#{electrum_channel}> channel, and type `++challenge` to begin your first challenge.")
        embed = discord.Embed(description=desc, title=self.title, color=self.color)
        embed.add_field(name="Prize Info:",
                        value="Sexy role color, maybe a t-shirt, maybe some Clash swag",
                        inline=False)
        embed.add_field(name="Clue #1",
                        value=clue,
                        inline=False)
        embed.set_footer(text=f"{num_players} currently participating",
                         icon_url=get_emoji_url(301032036779425812))
        await ctx.send(embed=embed)

    @commands.command(name="remind", aliases=["reminder"])
    async def remind(self, ctx):
        async with ctx.typing():
            with Sql() as cursor:
                sql = ("SELECT last_completed, skip_count, start_time "
                       "FROM rcs_halloween_players "
                       "WHERE discord_id = %s")
                cursor.execute(sql, ctx.author.id)
                fetch = cursor.fetchone()
                stats = {"last_completed": fetch[0], "skip_count": fetch[1], "start_time": fetch[2]}
                sql = ("SELECT count(discord_id) as num_players, "
                       "(SELECT count(discord_id) FROM rcs_halloween_players WHERE finish_time IS NOT NULL) as done "
                       "FROM rcs_halloween_players")
                cursor.execute(sql)
                fetch = cursor.fetchone()
            embed_data = {
                "num_players": fetch[0],
                "num_finished": fetch[1],
                "cur_challenge": stats["last_completed"] + 1,
                "skips": f"{stats['skip_count']}/3",
                "elapsed": self.get_elapsed(stats["start_time"])
            }
            if embed_data['cur_challenge'] != 2:
                func_call = getattr(challenges, f"challenge_{embed_data['cur_challenge']}")
            else:
                func_call = getattr(challenges, f"challenge_{embed_data['cur_challenge']}a")
            if embed_data['cur_challenge'] in (1, 4, 11, 13):
                embed_data['challenge'], image = func_call()
            else:
                embed_data['challenge'] = func_call()
                image = None
        embed = self.build_embed(embed_data)
        await ctx.send(f"Sure thing {ctx.author.display_name}!  I'll shoot you a DM with a reminder of where you are.",
                       delete_after=30)
        await ctx.author.send(embed=embed)
        if image:
            await ctx.author.send(file=image)
        if isinstance(ctx.message.channel, discord.TextChannel):
            try:
                await ctx.message.delete(delay=29)
            except discord.Forbidden:
                self.bot.logger.error(f"Couldn't remove command message on {ctx.message.guild}. Darned perms!")


def setup(bot):
    bot.add_cog(Halloween(bot))