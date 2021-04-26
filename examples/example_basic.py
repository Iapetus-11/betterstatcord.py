from statcord import StatcordClient
from discord.ext import commands

def main():
    bot = commands.Bot(command_prefix="!")

    bot.statcord_client = StatcordClient(bot, "my statcord key")

    bot.run("TOKEN")

if __name__ == "__main__":
    main()
