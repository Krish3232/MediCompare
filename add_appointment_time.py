import sqlite3

DATABASE_NAME = "database/medicompare.db"

try:
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    # Check whether appointment_time already exists
    cursor.execute("PRAGMA table_info(appointments)")
    columns = [column[1] for column in cursor.fetchall()]

    if "appointment_time" not in columns:

        cursor.execute("""
            ALTER TABLE appointments
            ADD COLUMN appointment_time TEXT
        """)

        conn.commit()

        print("appointment_time column added successfully!")

    else:

        print("appointment_time column already exists.")

    conn.close()

except sqlite3.Error as e:

    print("Database error:", e)