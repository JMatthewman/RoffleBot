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
from tabulate import tabulate

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
COOLDOWN_LIMIT = os.getenv("COOLDOWN_LIMIT")
COOLDOWN_TIME = os.getenv("COOLDOWN_TIME")
if TIDY:
  tidySuffix = " (This message will self-destruct in 10 seconds)"
else:
  tidySuffix = ""
banned_roles = set(os.getenv("BANNED_ROLES").split(','))
admin_roles = os.getenv("ADMIN_ROLES").split(',')

con = sqlite3.connect('roffleBot.db')
con.row_factory = sqlite3.Row
cur = con.cursor()

def query(query, parameters={}):
  cur.execute(query, parameters)
  return cur.fetchall()

def createMultiList():
  """ Function to fetch the allowed list of multi codes from the database """
  global multi  
  cur.execute("""SELECT code FROM tickets WHERE tickets.multi_use = 1""")
  multi = [row['code'] for row in cur.fetchall()]
  
def createWordList(): 
  """ Function that creates word list from the text file """
  global cleanwords
  global luhn
  cleanwords = []
  luhn = []
  with open('supercleanwords.csv','r') as file:
    for line in file:
        cleanwords.append(line.replace('\n', ''))
  with open('LuhnNumbers.csv','r') as file:
    for line in file:
        luhn.append(line.replace('\n', ''))
  
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
    code_number = code[:3]+code[-3:]
    nSum = 0
    isSecond = False

    for i in range(5, -1, -1):
      d = ord(code_number[i]) - ord('0')
      if (isSecond == True):
        d = d * 2
      nSum += d // 10
      nSum += d % 10

      isSecond = not isSecond
    return nSum % 10 == 0
  except:
    return False

def create_code():
  try: 
    cleanwords
    luhn
  except: 
    createWordList()
  
  first = random.choice(cleanwords)
  second = random.choice(cleanwords)
  luhn_no = random.choice(luhn)
  return f'{luhn_no[0:3]}_{first}_{second}_{luhn_no[3:]}'

def claimTicket(code, user):
  code = code.lower()

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
      
    userTickets = countUserTickets(user)
    return f"You've succesfully claimed a ticket `{tickets[0]['code']}` for {tickets[0]['source']}. You now have {userTickets} ticket(s) in the raffle! Good luck!"
  else:
    return f"Something went wrong trying to claim your ticket..."

def countUserTickets(user):
  cur.execute('SELECT COUNT(*) AS count FROM claims WHERE user_id = :user_id', {"user_id": user.id})
  userTickets = cur.fetchone()
  return userTickets['count']

@bot.event
async def on_ready():
  logging.info(f"Logged in as {bot.user.name}({bot.user.id})")

@bot.event
async def on_command(ctx):
  logging.info(f"'{ctx.message.content}' called by {ctx.author} ({ctx.author.id}) in '{ctx.guild}': '{ctx.channel}'")


@bot.event
async def on_command_error(ctx, error):
  if isinstance(error, commands.CommandNotFound):
    logging.warning(f"Invalid command: '{ctx.message.content}' called by {ctx.author} ({ctx.author.id}) in '{ctx.guild}': '{ctx.channel}'")
  elif isinstance(error, commands.MissingRequiredArgument):
    logging.warning(f"Missing Arguments: '{ctx.message.content}' called by {ctx.author} ({ctx.author.id}) in '{ctx.guild}': '{ctx.channel}'")
  elif isinstance(error, commands.MissingPermissions):
    logging.warning(f"Missing Permissions: '{ctx.message.content}' called by {ctx.author} ({ctx.author.id}) in '{ctx.guild}': '{ctx.channel}'")
  else:
    logging.error(f"{error}: '{ctx.message.content}' called by {ctx.author} ({ctx.author.id}) in '{ctx.guild}': '{ctx.channel}'")


@bot.command()
async def deleteusertickets(ctx):
  reply = await ctx.reply(f'https://tenor.com/bmcQR.gif{tidySuffix}')
  if TIDY:
    await ctx.message.delete(delay=10)
    await reply.delete(delay=10)

@bot.command()
async def checktickets(ctx):
  userTickets = countUserTickets(ctx.author)
  reply = await ctx.reply(f"You have {userTickets} ticket(s) in the raffle! Good luck!{tidySuffix}")
  if TIDY:
    await ctx.message.delete(delay=10)
    await reply.delete(delay=10)

@bot.command()
@commands.has_any_role(*admin_roles)
async def stats(ctx):
  multiUsage = query('''SELECT code, (SELECT COUNT(*) FROM claims WHERE claims.ticket_id = tickets.ticket_id) AS 'Uses' from "tickets" WHERE multi_use = 1''')
  claims = query('''SELECT COUNT(*) AS 'Total Claims', COUNT(DISTINCT user_id) AS 'Unique Users' FROM claims''')
  topSources = query('''SELECT source, COUNT(claim_id) FROM claims LEFT JOIN tickets ON claims.ticket_id = tickets.ticket_id GROUP BY source ORDER BY COUNT(claim_id) DESC LIMIT 10''')
  
  multiTable = tabulate(multiUsage, ['Code', 'Claims'], tablefmt="github")
  sourceTable = tabulate(topSources, ['Source', 'Claims'], tablefmt="github")

  statsText = f"**Total Tickets Claimed:**\n"
  statsText += f"{claims[0]['Total Claims']}\n\n"
  statsText += f"**Unique Participants:**\n"
  statsText += f"{claims[0]['Unique Users']}\n\n"
  statsText += f"**Multi-Use Code Claims:**\n"
  statsText += f"```{multiTable}```\n\n"
  statsText += f"**Top Claim Sources:**\n"
  statsText += f"```{sourceTable}```"
  await ctx.reply(statsText)

@bot.command()
@commands.has_any_role(*admin_roles)
async def announceWinners(ctx):
  winners = query("SELECT user_id, prize FROM winner JOIN prizes ON winner.prize_id = prizes.prize_id JOIN claims on winner.claim_id = claims.claim_id")

  #winnersDict = []
  #for winner in winners:
  #  my_dict = {'user_tag': f"<@{winner['user_id']}>", 'prize': winner['prize']}
  #  winnersDict.append(my_dict)
  #rows = [x.values() for x in winnersDict]
  #winnerTable = tabulate(rows, headers=['Winner', 'Prize'], tablefmt="github")
  #await ctx.reply(f"**Insomnia 68 BYOC Raffle Winners:**\n\n```{winnerTable}```")

  announceText = "**Insomnia 68 BYOC Raffle Winners:**\n\n"
  for winner in winners:
    announceText += f"<@{winner['user_id']}> won `{winner['prize']}`\n"
  await ctx.reply(announceText)


@bot.command()
@commands.has_any_role(*admin_roles)
async def notifyWinners(ctx):
  winners = query("SELECT user_id, prize, password FROM winner JOIN prizes ON winner.prize_id = prizes.prize_id JOIN claims on winner.claim_id = claims.claim_id")

  for win in winners:
    winner = await bot.fetch_user(win['user_id'])
    await winner.send(f"Congratulations <@{win['user_id']}>!, you have won `{win['prize']}` in the Insomnia 68 BYOC Raffle; You must be on-site at Insomnia68 and have a BYOC ticket to claim this prize. Please visit helpdesk, tell them you have won, and provide the password `{win['password']}` in order to claim your prize.")


@bot.command()
@commands.cooldown(1, 600, commands.BucketType.channel)
async def leaderboard(ctx):

  leaderData = query('''SELECT user_name, COUNT(*) from claims GROUP BY user_id ORDER BY COUNT(*) DESC LIMIT 10''')
  leaderTable = tabulate(leaderData, ['Rank','User', 'Tickets'], tablefmt="github", showindex=[i for i in range(1,len(leaderData)+1)])
 
  leaderboardText = f"**Current leaderboard:**\n"
  leaderboardText += f"```{leaderTable}```"
  await ctx.reply(leaderboardText)

@bot.command()
@commands.has_any_role(*admin_roles)
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
    reply = await ctx.reply(f":warning: You must have the `Discord Admin` role to do that!{tidySuffix}")
    if TIDY:
      await ctx.message.delete(delay=10)
      await reply.delete(delay=10)
  elif isinstance(error, commands.NoPrivateMessage):
    await ctx.reply("You cannot use this command in private messages")
  else:
    raise error

@bot.command()
@commands.has_any_role(*admin_roles)
async def addMulti(ctx, code, *args):
  logging.info(f"Received request to add multi_use code '{code}' from {ctx.author}")
  source = ' '.join(args)
  cur.execute('INSERT INTO tickets (code, source, multi_use, created) VALUES (:code, :source, 1, CURRENT_TIMESTAMP)', {"code": code.lower(), "source": source})
  con.commit()
  reply = await ctx.reply(f"Multi-use code added!{tidySuffix}")
  createMultiList()
  if TIDY:
    await ctx.message.delete(delay=10)
    await reply.delete(delay=10)
@addMulti.error
async def addMulti_error(ctx, error):
  if isinstance(error, commands.MissingRole):
    reply = await ctx.reply(f":warning: You must have the `Discord Admin` role to do that!{tidySuffix}")
    if TIDY:
      await ctx.message.delete(delay=10)
      await reply.delete(delay=10)
  elif isinstance(error, commands.NoPrivateMessage):
    await ctx.reply("You cannot use this command in private messages")
  else:
    raise error

@bot.command()
@commands.has_any_role(*admin_roles) 
async def listmulti(ctx):
  createMultiList()
  await ctx.reply(multi)
    
@bot.command(name='pet_rofflebot', aliases=['ruffle_rofflebot', 'tickle_bot'])
@commands.has_any_role(*admin_roles) 
async def pet_rofflebot(ctx):
  choices = ['teehehehehehhe', 'ooooohhhhh mooommmyyy', 'me likely', 'sscrrattcchheessss']
  reply = await ctx.reply(random.choice(choices))
  if TIDY:
    await ctx.message.delete(delay=10)
    await reply.delete(delay=10)
@pet_rofflebot.error
async def petrofflebot_error(ctx, error):
  choices = ['No touchy the RoffleBot.', 'Have you heard of consent?', 'botty going to bitey you', 'YOU ARE NOT MY MUMMY.']
  reply = await ctx.reply(random.choice(choices))
  if TIDY:
    await ctx.message.delete(delay=10)
    await reply.delete(delay=10)
    
@bot.command()
@commands.has_any_role(*admin_roles)
async def giftTicket(ctx, *args):
  logging.info(f"Received request to gift ticket from {ctx.author}")

  for user in ctx.message.mentions:
    newCode = create_code()
    cur.execute('INSERT INTO tickets (code, source, multi_use, created) VALUES (:code, :source, 0, CURRENT_TIMESTAMP)', {"code": newCode.lower(), "source": f"Gifted by {ctx.author}"})
    con.commit()
    result = claimTicket(newCode, user)
    reply = await ctx.reply(f"{result}{tidySuffix}")
  if TIDY:
    await ctx.message.delete(delay=10)
    await reply.delete(delay=10)
@giftTicket.error
async def giftTicket_error(ctx, error):
  if isinstance(error, commands.MissingRole):
    reply = await ctx.reply(f":warning: You must have the `Discord Admin` role to do that!{tidySuffix}")
    if TIDY:
      await ctx.message.delete(delay=10)
      await reply.delete(delay=10)
  elif isinstance(error, commands.NoPrivateMessage):
    await ctx.reply("You cannot use this command in private messages")
  else:
    raise error

@bot.command(name='raffle', aliases=['Raffle', 'RAFFLE'])
@commands.cooldown(COOLDOWN_LIMIT, COOLDOWN_TIME, commands.BucketType.user)
async def raffle(ctx, code):
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
@raffle.error
async def raffle_error(ctx, error):
  if isinstance(error, commands.CommandOnCooldown):
    logging.warning(f"Rate limiting claim request from {ctx.author} ({ctx.author.id})")
    reply = await ctx.reply(f"You're being rate limited :angry:. Please wait {error.retry_after:.0f} seconds before trying again!{tidySuffix}'")
    if TIDY:
      await ctx.message.delete(delay=10)
      await reply.delete(delay=10)
  elif isinstance(error, commands.MissingRequiredArgument):
      reply = await ctx.reply(f"You need to enter a code! You may be given these through the event, but you can get started with `Insomnia68` for free.{tidySuffix}")
      if TIDY:
        await ctx.message.delete(delay=10)
        await reply.delete(delay=10)
  else:
    raise error

@bot.command()
@commands.has_any_role(*admin_roles)
async def ping(ctx):
  await ctx.reply("Pong!")
  
@bot.command()
async def help(ctx):
  await ctx.reply("Taking part in the Insomnia Gaming Festival BYOC Raffle is super easy! \n Just say !raffle and then your code. Example: \n !raffle rafflesareawesome \n That's it! \n Happy Raffle ")

@bot.command()
async def when(ctx):
  await ctx.reply("The raffle will be drawn at 12pm on Monday! \n The top prizes (such as Fifa 17) are drawn live, the rest on Discord. \n Winners will get a Discord messages straight from RoffleBot \n You must be at the event to claim. \n Happy Raffle ")


@bot.command()
@commands.has_any_role(*admin_roles)
async def quit(ctx):
  await ctx.reply("Exiting script, Goodbye!")
  await bot.close()
  exit()

if __name__ == "__main__":
  bot.run(DISCORD_TOKEN)
