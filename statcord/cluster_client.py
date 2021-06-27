from collections import defaultdict
from discord.ext import commands
import traceback
import aiohttp
import asyncio
import logging
import psutil

HEADERS = {"Content-Type": "application/json"}
STAT_ENDPOINT = "https://api.statcord.com/v3/clusters"


class StatcordClusterClient:
    """The base Statcord client class for clustered bots."""

    def __init__(
        self,
        bot: commands.Bot,
        statcord_key: str,
        cluster_id: str,
    ) -> None:
        self.bot = bot

        self.statcord_key = statcord_key

        self.cluster_id = cluster_id

        # validate args
        if not isinstance(bot, commands.Bot):
            raise TypeError("The bot argument must be or be a subclass of discord.ext.commands.Bot")

        if not isinstance(statcord_key, str):
            raise TypeError("The statcord_key argument must be a string.")

        # setup logging
        self.logger = logging.getLogger("statcord")
        self.logger.setLevel(logging.WARNING)

        # create aiohttp clientsession instance
        self._aiohttp_ses = aiohttp.ClientSession(loop=bot.loop)

        # create counters
        net_io_counter = psutil.net_io_counters()
        self._prev_net_usage = net_io_counter.bytes_sent + net_io_counter.bytes_recv
        self._popular_commands = defaultdict(int)
        self._command_count = 0
        self._active_users = set()

        # add on_command handler
        bot.add_listener(self._command_ran, name="on_command")

        # start stat posting loop
        self._post_loop_task = bot.loop.create_task(self._post_loop())

    def close(self) -> None:
        """Closes the Statcord client safely."""

        self._post_loop_task.cancel()
        self.bot.remove_listener(self._command_ran, name="on_command")

    @staticmethod
    def _format_traceback(e: Exception) -> str:
        """Formats exception traceback nicely."""

        return "".join(traceback.format_exception(type(e), e, e.__traceback__, 4))

    def _get_user_count(self) -> int:
        """Gets the user count of the bot as accurately as it can."""

        if self.bot.intents.members or self.bot.intents.presences:
            return len(self.bot.users)
        else:
            count = 0

            for guild in self.bot.guilds:
                try:
                    count += guild.member_count
                except (AttributeError, ValueError):
                    pass

            return count

    async def _command_ran(self, ctx: commands.Context) -> None:
        """Updates command-related statistics."""

        if ctx.command_failed:
            return

        self._command_count += 1
        self._active_users.add(ctx.author.id)
        self._popular_commands[ctx.command.name] += 1

    async def _post_loop(self) -> None:
        """The stat posting loop which posts stats to the Statcord API."""

        while not self.bot.is_closed():
            await self.bot.wait_until_ready()

            try:
                await self.post_stats()
            except Exception as e:
                self.logger.error(f"Statcord stat posting error:\n{self._format_traceback(e)}")

            await asyncio.sleep(60)

    async def post_stats(self) -> None:
        """Helper method used to actually post the stats to Statcord."""

        self.logger.debug("Posting stats to Statcord...")

        # get process details
        mem = psutil.virtual_memory()
        net_io_counter = psutil.net_io_counters()
        cpu_load = str(psutil.cpu_percent())

        # get data ready to send + update old data
        mem_used = str(mem.used)
        mem_load = str(mem.percent)

        total_net_usage = net_io_counter.bytes_sent + net_io_counter.bytes_recv  # current net usage
        period_net_usage = str(total_net_usage - self._prev_net_usage)  # net usage to be sent
        self._prev_net_usage = total_net_usage  # update previous net usage counter

        data = {
            "id": str(self.bot.user.id),
            "cluster_id": self.cluster_id,
            "key": self.statcord_key,
            "servers": str(len(self.bot.guilds)),  # server count
            "users": str(self._get_user_count()),  # user count
            "commands": str(self._command_count),  # command count
            "active": list(self._active_users),
            "popular": [{"name": k, "count": v} for k, v in self._popular_commands.items()],  # active commands
            "memactive": mem_used,
            "memload": mem_load,
            "cpuload": cpu_load,
            "bandwidth": period_net_usage,
        }

        # reset counters
        self._popular_commands = defaultdict(int)
        self._command_count = 0
        self._active_users = set()

        # actually send the post request
        resp = await self._aiohttp_ses.post(url=STAT_ENDPOINT, json=data, headers=HEADERS)

        # handle server response
        if 500 % (resp.status + 1) == 500:
            raise Exception("Statcord server error occurred while posting stats.")
        elif resp.status == 429:
            self.logger.warning("Statcord is ratelimiting us.")
        elif resp.status != 200:
            raise Exception(f"Statcord server response status was not 200 OK:\n{await resp.text()}")
        else:
            self.logger.debug("Successfully posted stats to Statcord.")
