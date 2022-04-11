import sqlite3

con = sqlite3.connect('roffleBot.db')
cur = con.cursor()

#cur.execute('DROP TABLE tickets')
cur.execute('CREATE TABLE tickets (ticket_id INTEGER PRIMARY KEY, code TEXT, source TEXT, created TEXT, multi_use INTEGER)')
cur.execute('CREATE TABLE claims (claim_id INTEGER PRIMARY KEY, ticket_id INTEGER, user_id INTEGER, user_name TEXT, claimed TEXT)')
