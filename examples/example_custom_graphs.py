from statcord import StatcordClient
from discord.ext import commands


async def custom_graph_1():
    return 420


def custom_graph_2():
    return "69"


def main():
    bot = commands.Bot(command_prefix="!")

    bot.statcord_client = StatcordClient(bot, "my statcord key", custom_graph_1, custom_graph_2)

    bot.run("TOKEN")


if __name__ == "__main__":
    main()
