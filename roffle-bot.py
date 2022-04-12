import sqlite3
import random
import string
import os
import discord
from discord.ext import commands
import csv
import io
import logging
from logging.handlers import TimedRotatingFileHandler

logFormat = logging.Formatter('%(asctime)s : %(levelname)s :: %(message)s')
rootLogger = logging.getLogger()
rootLogger.setLevel('INFO')

fileLog = TimedRotatingFileHandler('logs/roffleBot.log', when='D')
fileLog.setFormatter(logFormat)
rootLogger.addHandler(fileLog)

consoleLog = logging.StreamHandler()
consoleLog.setFormatter(logFormat)
rootLogger.addHandler(consoleLog)

from dotenv import load_dotenv
load_dotenv()

bot = commands.Bot(command_prefix="!", help_command=None)
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
TIDY = os.getenv("TIDY") == "True"
COOLDOWN_TIME = os.getenv("COOLDOWN_TIME")
if TIDY:
  tidySuffix = " (This message will self-destruct in 10 seconds)"
else:
  tidySuffix = ""
banned_roles = set(os.getenv("BANNED_ROLES").split(','))

con = sqlite3.connect('roffleBot.db')
con.row_factory = sqlite3.Row
cur = con.cursor()

def createMultiList():
  """ Function to fetch the allowed list of multi codes from the database """
  global multi  
  cur.execute("""SELECT code FROM tickets WHERE tickets.multi_use = 1""")
  multi = [row['code'] for row in cur.fetchall()]
  
def createWordList(): 
  """ Function that creates word list from the text file """
  global cleanwords
  cleanwords = []
  with open('supercleanwords.csv','r') as file:
    for line in file:
        cleanwords.append(line.replace('\n', ''))
  
def validate(code):
  """ Check if a code is in the MultiList - Create multilist if it doesn't exist
      Check if the checksum works
  """ 
  try:
    multi
  except:
    createMultiList() 

  if code in multi: 
    return True 

  try:
    first = int(code[0])
    second = int(code[1])
    third = int(code[2])
    final = int(code[-2:])
    return (first * second) + third + final == 68
  except:
    return False

def create_code():
  try: 
    cleanwords
  except: 
    createWordList()
  
  first = random.randint(1,9)
  second = random.randint(1,6)
  third = random.randint(1,7)
  final = 68 - ((first * second) + third)
  word = random.choice(cleanwords)
  return f'{first}{second}{third}_{word}_{final}'

def claimTicket(code, user):
  
  ## Check if the code is in the MultiList or is valid.
  if validate(code) == False:
    return f"Sorry that code isn't a valid ticket"
  
  cur.execute('SELECT *, (SELECT COUNT(*) FROM claims WHERE claims.ticket_id = tickets.ticket_id) AS claims, (SELECT COUNT(*) FROM claims WHERE claims.ticket_id = tickets.ticket_id AND claims.user_id = :user_id) AS my_claims FROM tickets WHERE code = :code', {"user_id": user.id, "code": code})
  tickets = cur.fetchall()
  if len(tickets) == 0:
    return f"We couldn't find any tickets matching `{code}`!"
  elif len(tickets) > 1:
    return f"Something went wrong trying to claim your ticket..."
  elif tickets[0]['my_claims'] > 0:
    return f"You've already claimed that ticket!"
  elif tickets[0]['multi_use'] == 0 and tickets[0]['claims'] > 0:
    return f"That ticket has already been claimed!"
  elif tickets[0]['multi_use'] == 1 or tickets[0]['claims'] == 0:
    cur.execute('INSERT INTO claims (ticket_id, user_id, user_name, claimed) VALUES (:ticket_id, :user_id, :user_name, CURRENT_TIMESTAMP)', {"ticket_id": tickets[0]['ticket_id'], "user_id": user.id, "user_name": str(user)})
    con.commit()
      
    cur.execute('SELECT COUNT(*) AS count FROM claims WHERE user_id = :user_id', {"user_id": user.id})
    userTickets = cur.fetchone()
    return f"You've succesfully claimed ticket `{tickets[0]['code']}` from {tickets[0]['source']}. You now have {userTickets['count']} ticket(s) in the raffle! Good luck!"
  else:
    return f"Something went wrong trying to claim your ticket..."



@bot.event
async def on_ready():
  logging.info(f"Logged in as {bot.user.name}({bot.user.id})")


@bot.command()
@commands.has_role("Roffle Admin")
async def create(ctx, count, *args):
  logging.info(f"Received request to generate new tickets from {ctx.author}")
  count = int(count)
  source = ' '.join(args)
  
  codes = []
  for i in range(count):
    newCode = create_code()
    cur.execute('INSERT INTO tickets (code, source, multi_use, created) VALUES (:code, :source, 0, CURRENT_TIMESTAMP)', {"code": newCode, "source": source})
    codes.append(newCode)
  con.commit()
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
      await ctx.author.send(f"Your {count} new raffle ticket codes for '{source}' are attached.{tidySuffix}", file=discoFile)

  reply = await ctx.reply(f"I've DMed you your new raffle ticket codes.{tidySuffix}")
  if TIDY:
    await ctx.message.delete(delay=10)
    await reply.delete(delay=10)
  logging.info(f"Replied to {ctx.author} with generated tickets")
@create.error
async def create_error(ctx, error):
  if isinstance(error, commands.MissingRole):
    reply = await ctx.reply(f":warning: You must have the `Roffle Admin` role to do that!{tidySuffix}")
    if TIDY:
      await ctx.message.delete(delay=10)
      await reply.delete(delay=10)
  elif isinstance(error, commands.NoPrivateMessage):
    await ctx.reply("You cannot use this command in private messages")
  else:
    raise error

@bot.command()
@commands.has_role("Roffle Admin")
async def addMulti(ctx, code, *args):
  logging.info(f"Received request to add multi_use code '{code}' from {ctx.author}")
  source = ' '.join(args)
  cur.execute('INSERT INTO tickets (code, source, multi_use, created) VALUES (:code, :source, 1, CURRENT_TIMESTAMP)', {"code": code, "source": source})
  con.commit()
  reply = await ctx.reply(f"Multi-use code added!{tidySuffix}")
  createMultiList()
  if TIDY:
    await ctx.message.delete(delay=10)
    await reply.delete(delay=10)
@addMulti.error
async def addMulti_error(ctx, error):
  if isinstance(error, commands.MissingRole):
    reply = await ctx.reply(f":warning: You must have the `Roffle Admin` role to do that!{tidySuffix}")
    if TIDY:
      await ctx.message.delete(delay=10)
      await reply.delete(delay=10)
  elif isinstance(error, commands.NoPrivateMessage):
    await ctx.reply("You cannot use this command in private messages")
  else:
    raise error

@bot.command()
@commands.has_role("Roffle Admin")
async def giftTicket(ctx, *args):
  logging.info(f"Received request to gift ticket from {ctx.author}")

  for user in ctx.message.mentions:
    newCode = create_code()
    cur.execute('INSERT INTO tickets (code, source, multi_use, created) VALUES (:code, :source, 0, CURRENT_TIMESTAMP)', {"code": newCode, "source": f"Gifted by {ctx.author}"})
    con.commit()
    result = claimTicket(newCode, user)
    reply = await ctx.reply(f"{result}{tidySuffix}")
  if TIDY:
    await ctx.message.delete(delay=10)
    await reply.delete(delay=10)
@giftTicket.error
async def giftTicket_error(ctx, error):
  if isinstance(error, commands.MissingRole):
    reply = await ctx.reply(f":warning: You must have the `Roffle Admin` role to do that!{tidySuffix}")
    if TIDY:
      await ctx.message.delete(delay=10)
      await reply.delete(delay=10)
  elif isinstance(error, commands.NoPrivateMessage):
    await ctx.reply("You cannot use this command in private messages")
  else:
    raise error

@bot.command()
@commands.cooldown(1, COOLDOWN_TIME, commands.BucketType.user)
async def claim(ctx, code):
  logging.info(f"Received claim request for '{code}' from {ctx.author} ({ctx.author.id})")

  user_roles = set([role.name for role in ctx.author.roles])
  disqualifications = user_roles.intersection(banned_roles)
  if len(disqualifications) > 0:
    #reply = await ctx.reply(f"Sorry, {random.choice(list(disqualifications))}s are not allowed to enter the raffle.{tidySuffix}")
    reply = await ctx.reply(f"Sorry, staff / volunteers are not allowed to enter the raffle.{tidySuffix}")
    if TIDY:
      await ctx.message.delete(delay=10)
      await reply.delete(delay=10)
  else:
    response = claimTicket(code, ctx.author)
    reply = await ctx.reply(response + tidySuffix)
    logging.info(f"Processed claim request for '{code}' from {ctx.author} ({ctx.author.id})")
    if TIDY:
      await ctx.message.delete(delay=10)
      await reply.delete(delay=10)
@claim.error
async def claim_error(ctx, error):
  if isinstance(error, commands.CommandOnCooldown):
    logging.warning(f"Rate limiting claim request from {ctx.author} ({ctx.author.id})")
    reply = await ctx.reply("You must wait 30 seconds between requests")
    if TIDY:
      await ctx.message.delete(delay=10)
      await reply.delete(delay=10)
  else:
    raise error

@bot.command()
@commands.has_role("Roffle Admin")
async def ping(ctx):
  await ctx.reply("Pong!")

@bot.command()
@commands.has_role("Roffle Admin")
async def quit(ctx):
  await ctx.reply("Exiting script, Goodbye!")
  await bot.close()
  exit()

if __name__ == "__main__":
  bot.run(DISCORD_TOKEN)
