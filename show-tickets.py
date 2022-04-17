import sqlite3
rawCon = sqlite3.connect('roffleBot.db')

rawCur = rawCon.cursor()

rawCur.execute('SELECT * FROM tickets')
data = rawCur.fetchall()

rawCur.close()
rawCon.close()

for row in data:
  print(row)
