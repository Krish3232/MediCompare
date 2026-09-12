from database.db import get_connection

conn = get_connection()
cursor = conn.cursor()

email = input("Enter your admin account email: ")

cursor.execute("""
    UPDATE users
    SET role='admin'
    WHERE email=?
""", (email,))

conn.commit()

if cursor.rowcount > 0:
    print("User successfully changed to admin.")
else:
    print("No user found with that email.")

conn.close()