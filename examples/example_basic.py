from discord.ext import commands

from statcord import StatcordClient


def main():
    bot = commands.Bot(command_prefix="!")

    bot.statcord_client = StatcordClient(bot, "my statcord key")

    bot.run("TOKEN")


if __name__ == "__main__":
    main()
