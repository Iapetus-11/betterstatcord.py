from discord.ext import commands

from statcord import StatcordClient


class MyStatcordCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.statcord_client = StatcordClient(bot, "Statcord API key", self.custom_graph_1)

    def cog_unload(self):
        self.statcord_client.close()

    async def custom_graph_1(self):
        return 1 + 2 + 3


def setup(bot):
    bot.add_cog(MyStatcordCog(bot))
