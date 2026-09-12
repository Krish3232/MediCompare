import sqlite3
import os

db_path = os.path.join("database", "medicompare.db")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    cursor.execute("""
        ALTER TABLE hospitals
        ADD COLUMN map_link TEXT
    """)
    print("✅ map_link column added successfully.")
except Exception as e:
    print("Error:", e)

conn.commit()
conn.close()