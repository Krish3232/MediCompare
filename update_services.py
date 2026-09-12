import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATABASE_NAME = os.path.join(
    BASE_DIR,
    "database",
    "medicompare.db"
)

conn = sqlite3.connect(DATABASE_NAME)
cursor = conn.cursor()


# Check existing columns
cursor.execute("PRAGMA table_info(services)")
columns = [column[1] for column in cursor.fetchall()]


# Add hospital_id if it does not exist
if "hospital_id" not in columns:

    cursor.execute("""
        ALTER TABLE services
        ADD COLUMN hospital_id INTEGER
    """)

    print("hospital_id column added.")


# Add description if it does not exist
if "description" not in columns:

    cursor.execute("""
        ALTER TABLE services
        ADD COLUMN description TEXT
    """)

    print("description column added.")


# Add cost if it does not exist
if "cost" not in columns:

    cursor.execute("""
        ALTER TABLE services
        ADD COLUMN cost INTEGER
    """)

    print("cost column added.")


conn.commit()
conn.close()

print("Services table updated successfully.")