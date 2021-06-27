from statcord import StatcordClusterClient
from discord.ext import commands


def main():
    bot = commands.Bot(command_prefix="!")

    bot.statcord_client = StatcordClusterClient(bot, "my statcord key", "cluster id")

    bot.run("TOKEN")


if __name__ == "__main__":
    main()
