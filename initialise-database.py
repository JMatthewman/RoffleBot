import sqlite3

con = sqlite3.connect('roffleBot.db')
cur = con.cursor()

#cur.execute('DROP TABLE tickets')
cur.execute('CREATE TABLE tickets (ticket_id INTEGER PRIMARY KEY, code TEXT, source TEXT, created TEXT, claimee INTEGER, claimed TEXT)')
