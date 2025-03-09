import sqlite3

# Connect to the existing database
conn = sqlite3.connect("mediadatabase.db")
cursor = conn.cursor()

# Add the missing column if it doesn't exist
try:
    cursor.execute("ALTER TABLE media ADD COLUMN thumb_id TEXT")
    conn.commit()
    print("✅ Successfully added 'thumb_id' column!")
except sqlite3.OperationalError:
    print("⚠️ Column 'thumb_id' already exists.")

# Verify the updated schema
cursor.execute("PRAGMA table_info(media)")
columns = cursor.fetchall()
print("📌 Current Table Schema:")
for col in columns:
    print(col)

conn.close()
