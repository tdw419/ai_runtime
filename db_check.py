import sqlite3

db_path = "ai_native.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

query = "SELECT kind, COUNT(*) FROM objects GROUP BY kind;"
cursor.execute(query)
rows = cursor.fetchall()

for row in rows:
    print(f"{row[0]}|{row[1]}")

conn.close()
