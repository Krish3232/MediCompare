from database.db import get_connection

conn = get_connection()
cursor = conn.cursor()

columns = [
    ("qualification", "TEXT"),
    ("available_days", "TEXT"),
    ("available_time", "TEXT")
]

for column_name, column_type in columns:
    try:
        cursor.execute(
            f"ALTER TABLE doctors ADD COLUMN {column_name} {column_type}"
        )
        print(f"Added column: {column_name}")
    except Exception as e:
        print(f"{column_name}: {e}")

conn.commit()
conn.close()

print("Doctors table updated successfully.")