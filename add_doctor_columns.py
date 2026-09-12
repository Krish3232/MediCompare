import sys
import os

# Add database folder to Python path
sys.path.append(
    os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "database"
    )
)

from db import get_connection


conn = get_connection()
cursor = conn.cursor()


try:
    cursor.execute("""
        ALTER TABLE doctors
        ADD COLUMN qualification TEXT
    """)
    print("Added qualification column.")

except Exception as e:
    print("qualification column:", e)


try:
    cursor.execute("""
        ALTER TABLE doctors
        ADD COLUMN available_days TEXT
    """)
    print("Added available_days column.")

except Exception as e:
    print("available_days column:", e)


try:
    cursor.execute("""
        ALTER TABLE doctors
        ADD COLUMN available_time TEXT
    """)
    print("Added available_time column.")

except Exception as e:
    print("available_time column:", e)


conn.commit()
conn.close()

print("Doctor table update completed!")