import sqlite3
import random
import string

from dotenv import load_dotenv
load_dotenv()

con = sqlite3.connect('roffleBot.db')
con.row_factory = sqlite3.Row
cur = con.cursor()

def claimTicket(code, userID):
  cur.execute('SELECT COUNT(*) AS count FROM tickets WHERE code = ?', [code])
  ticketCount = cur.fetchone()
  if ticketCount['count'] == 0:
    return f"We couldn't find any tickets matching `{code}`!"
  elif ticketCount['count'] == 1:
    cur.execute('SELECT * FROM tickets WHERE code = ?', [code])
    ticket = cur.fetchone()
    if ticket['claimee'] == None:
      cur.execute('UPDATE tickets SET claimee = ?, claimed = CURRENT_TIMESTAMP WHERE ticket_id = ?', [userID, ticket['ticket_id']])
      con.commit()
      
      cur.execute('SELECT COUNT(*) AS count FROM tickets WHERE claimee = ?', [userID])
      userTickets = cur.fetchone()
      return f"You've succesfully claimed ticket `{ticket['code']}` from {ticket['source']}. You now have {userTickets['count']} ticket(s) in the raffle! Good luck!"
    else:
      return f"That ticket has already been claimed!"
  else:
    return f"Oh no! We found {ticketCount['count']} tickets matching your code, and that's just not right..."


import os
import discord
from discord.ext import commands
import csv
#from io import StringIO, BytesIO
#import codecs
import io
#import time

bot = commands.Bot(command_prefix="!")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

@bot.event
async def on_ready():
  print(f"Logged in as {bot.user.name}({bot.user.id})")


@bot.command()
@commands.has_role("Roffle Admin")
async def create(ctx, count, source):
  print(f"Received request to generate new tickets from {ctx.author}")
  count = int(count)
  chars = string.ascii_letters + string.digits
  codes = []
  for i in range(count):
    newCode = ''.join(random.sample(chars, 6))
    cur.execute('INSERT INTO tickets (code, source, created) VALUES (?, ?, CURRENT_TIMESTAMP)', [newCode, source])
    codes.append(newCode)
  con.commit()
  print(type(codes))
  print(type(codes[0]))
  if count <= 100:
    codesList = '\n'.join(codes)
    await ctx.author.send(f"Your {count} new raffle ticket codes for '{source}' are: ```\n{codesList}```")
  else:
    with io.BytesIO() as buffer:
      sb = io.TextIOWrapper(buffer, 'utf-8', newline='')
      csv.writer(sb).writerow(['Raffle Code','Code Source'])
      for code in codes:
        csv.writer(sb).writerow([code,source])
      sb.flush()
      buffer.seek(0)
      discoFile = discord.File(sb, filename=f'Raffle Codes - {source}.csv')
      await ctx.author.send(f"Your {count} new raffle ticket codes for '{source}' are attached.", file=discoFile)

  reply = await ctx.reply(f"I've DMed you your new raffle ticket codes.")
  if TIDY:
    await ctx.message.delete(delay=10)
    await reply.delete(delay=10)
  print(f"Replied to {ctx.author} with generated tickets")
@create.error
async def create_error(ctx, error):
  if isinstance(error, commands.MissingRole):
    reply = await ctx.reply(":warning: You must have the `Roffle Admin` role to do that!")
    if TIDY:
      await ctx.message.delete(delay=10)
      await reply.delete(delay=10)
  else:
    raise error

@bot.command()
async def claim(ctx, code):
  reply = await ctx.reply(response + ' Self destructing in 10 seconds.')
  print(f"Received claim request from {ctx.author} ({ctx.author.id})")
  response = claimTicket(code, ctx.author.id)
  print(f"Processed claim request from {ctx.author} ({ctx.author.id})")
  if TIDY:
    await ctx.message.delete(delay=10)
    await reply.delete(delay=10)


if __name__ == "__main__":
  bot.run(DISCORD_TOKEN)