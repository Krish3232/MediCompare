from db import get_connection

conn = get_connection()
cursor = conn.cursor()

# Users Table
cursor.execute("""
CREATE TABLE IF NOT EXISTS users(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    role TEXT DEFAULT 'user'
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS favorites (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    hospital_id INTEGER NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(id),
    FOREIGN KEY(hospital_id) REFERENCES hospitals(id),
    UNIQUE(user_id, hospital_id)
)
""")


# Hospitals Table
cursor.execute("""
CREATE TABLE IF NOT EXISTS hospitals(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hospital_name TEXT NOT NULL,
    city TEXT NOT NULL,
    phone TEXT,
    hospital_type TEXT,
    rating REAL,
    emergency INTEGER DEFAULT 0,
    ambulance INTEGER DEFAULT 0,
    icu INTEGER DEFAULT 0,
    map_link TEXT
)
""")



# Services Table
cursor.execute("""
CREATE TABLE IF NOT EXISTS services (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    service_name TEXT NOT NULL,
    hospital_id INTEGER,
    description TEXT,
    cost INTEGER,
    FOREIGN KEY(hospital_id) REFERENCES hospitals(id)
)
""")

# Doctors Table
cursor.execute("""
CREATE TABLE IF NOT EXISTS doctors(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hospital_id INTEGER,
    doctor_name TEXT,
    specialization TEXT,
    qualification TEXT,
    experience INTEGER,
    consultation_fee INTEGER,
    available_days TEXT,
    available_time TEXT,
    FOREIGN KEY(hospital_id) REFERENCES hospitals(id)
)
""")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS services (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        hospital_id INTEGER NOT NULL,
        service_name TEXT NOT NULL,
        cost REAL DEFAULT 0,
        description TEXT,
        FOREIGN KEY (hospital_id)
            REFERENCES hospitals(id)
    )
""")


# Reviews Table
cursor.execute("""
CREATE TABLE IF NOT EXISTS reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hospital_id INTEGER,
    user_id INTEGER,
    rating INTEGER,
    comment TEXT,
    review_date TEXT,
    FOREIGN KEY(hospital_id) REFERENCES hospitals(id),
    FOREIGN KEY(user_id) REFERENCES users(id)
)
""")

# Hospital Services Table
cursor.execute("DROP TABLE IF EXISTS hospital_services")

cursor.execute("""
CREATE TABLE IF NOT EXISTS hospital_services (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hospital_id INTEGER NOT NULL,
    service_name TEXT NOT NULL,
    estimated_cost INTEGER NOT NULL,
    FOREIGN KEY(hospital_id) REFERENCES hospitals(id)
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS favorites (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    hospital_id INTEGER,
    FOREIGN KEY(user_id) REFERENCES users(id),
    FOREIGN KEY(hospital_id) REFERENCES hospitals(id),
    UNIQUE(user_id, hospital_id)
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS appointments(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    hospital_id INTEGER NOT NULL,
    doctor_id INTEGER NOT NULL,
    appointment_date TEXT NOT NULL,
    appointment_time TEXT NOT NULL,
    reason TEXT,
    status TEXT DEFAULT 'Pending',

    FOREIGN KEY(user_id) REFERENCES users(id),
    FOREIGN KEY(hospital_id) REFERENCES hospitals(id),
    FOREIGN KEY(doctor_id) REFERENCES doctors(id)
)
""")
conn.commit()
conn.close()

print("Database created successfully!")