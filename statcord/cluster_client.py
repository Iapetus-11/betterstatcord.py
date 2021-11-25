from collections import defaultdict
import psutil

from statcord.client import StatcordClient, HEADERS

STAT_ENDPOINT = "https://api.statcord.com/v3/clusters"


class StatcordClusterClient(StatcordClient):
    def __init__(self, bot, statcord_key: str, cluster_id: str, resource_stats: bool = True) -> None:
        super().__init__(bot, statcord_key, resource_stats=resource_stats)
        self.cluster_id = cluster_id

    async def post_stats(self) -> None:
        """Helper method used to actually post the stats to Statcord."""

        self.logger.debug("Posting stats to Statcord...")

        if self.resource_stats:
            mem = psutil.virtual_memory()
            mem_used = str(mem.used)
            mem_load = str(mem.percent)

            cpu_load = str(psutil.cpu_percent())

            net_io_counter = psutil.net_io_counters()
            total_net_usage = net_io_counter.bytes_sent + net_io_counter.bytes_recv  # current net usage
            period_net_usage = str(total_net_usage - self._prev_net_usage)  # net usage to be sent
            self._prev_net_usage = total_net_usage  # update previous net usage counter
        else:
            mem_used = "0"
            mem_load = "0"

            cpu_load = "0"

            period_net_usage = "0"

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
        if resp.status == 429:
            self.logger.warning("Statcord is ratelimiting us.")
        elif resp.status != 200:
            raise Exception(f"Statcord server response status was not 200 OK (Was {resp.status}):\n{await resp.text()}")
        else:
            self.logger.debug("Successfully posted stats to Statcord.")
