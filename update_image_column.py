from database.db import get_connection

conn = get_connection()
cursor = conn.cursor()

try:
    cursor.execute("""
    ALTER TABLE hospitals
    ADD COLUMN image TEXT
    """)

    conn.commit()
    print("Hospital image column added.")

except Exception as e:
    print(e)

conn.close()