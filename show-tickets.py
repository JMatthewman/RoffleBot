import sqlite3
rawCon = sqlite3.connect('roffleBot.db')

rawCur = rawCon.cursor()

rawCur.execute('UPDATE tickets set source = "PubQuizzing" WHERE source = "raffling"' )
data = rawCur.fetchall()
rawCon.commit()

rawCur.close()
rawCon.close()

exit()