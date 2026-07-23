import sqlite3

conn = sqlite3.connect("travel.db")

cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    name TEXT NOT NULL,

    email TEXT UNIQUE NOT NULL,

    password TEXT NOT NULL

)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS favorites(

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    user_email TEXT,

    place_name TEXT,

    FOREIGN KEY(user_email) REFERENCES users(email)

)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS reviews(

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    place_name TEXT,

    user_name TEXT,
               
    user_email TEXT,

    rating INTEGER,

    review TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS trip_plans(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_email TEXT,
    trip_name TEXT,
    places TEXT,
    num_days INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS contact_messages(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    email TEXT,
    message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS message_replies(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id INTEGER,
    user_name TEXT,
    reply TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

conn.commit()
conn.close()

print("Database Created Successfully!")