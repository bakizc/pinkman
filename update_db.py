import sqlite3

# Connect to the database
conn = sqlite3.connect("mediadatabase.db")
cursor = conn.cursor()

# Check if 'thumb_id' column already exists
cursor.execute("PRAGMA table_info(media)")
columns = [col[1] for col in cursor.fetchall()]

if "thumb_id" not in columns:
    cursor.execute("ALTER TABLE media ADD COLUMN thumb_id TEXT")
    conn.commit()
    print("✅ Successfully added 'thumb_id' column!")
else:
    print("⚠️ Column 'thumb_id' already exists.")

# Display the updated table schema
cursor.execute("PRAGMA table_info(media)")
print("📌 Current Table Schema:")
for col in cursor.fetchall():
    print(col)

# Close the connection
conn.close()
