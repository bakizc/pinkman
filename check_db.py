import sqlite3

conn = sqlite3.connect("mediadatabase.db")
cursor = conn.cursor()

cursor.execute("SELECT * FROM media")
rows = cursor.fetchall()

if rows:
    for row in rows:
        print(row)
else:
    print("No media found in the database.")

conn.close()
