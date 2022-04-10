import discord
import os
from datetime import date
from discord.ext import commands

from dotenv import load_dotenv
load_dotenv()

intents = discord.Intents.default()
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
TOKEN = os.getenv("DISCORD_TOKEN")

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name}({bot.user.id})")

@bot.command()
async def trigger(ctx):
    userString = 'Leeesa#5576'
    user = discord.utils.get(ctx.guild.members, name=userString.split('#')[0], discriminator=userString.split('#')[1])
    print(f"userString is: '{userString}'")
    print(f"Looking for name '{userString.split('#')[0]}', discriminator '{userString.split('#')[1]}', in guild '{ctx.guild}'")
    print(f"All members in guild are: '{ctx.guild.members}'")
    print(f"user found was: '{user}' ({user.id})")
    #     await bot.fetch_user("Leeesa#5576")
    await ctx.author.send(f"<@{user.id}> is a muppet.")

if __name__ == "__main__":
    bot.run(TOKEN)
