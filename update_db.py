import sqlite3

# Connect to the database
conn = sqlite3.connect("mediadatabase.db")
cursor = conn.cursor()

# Add the new column if it doesn't exist
try:
    cursor.execute("ALTER TABLE media ADD COLUMN thumb_id TEXT;")
    conn.commit()
    print("✅ Column 'thumb_id' added successfully!")
except sqlite3.OperationalError as e:
    print(f"⚠️ Error: {e}")

# Close the connection
conn.close()
