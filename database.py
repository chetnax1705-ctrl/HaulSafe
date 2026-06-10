import sqlite3
import os

def get_db():
    db = sqlite3.connect("haulsafe.db")
    db.row_factory = sqlite3.Row
    return db

def init_db():
    db = get_db()
    cursor = db.cursor()

    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('manager', 'driver'))
        )
    """)

    # Trips table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trips (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            manager_id INTEGER NOT NULL,
            driver_id INTEGER,
            origin TEXT NOT NULL,
            destination TEXT NOT NULL,
            cargo_type TEXT NOT NULL,
            cargo_fragile INTEGER DEFAULT 0,
            cargo_temp_sensitive INTEGER DEFAULT 0,
            status TEXT DEFAULT 'Planned',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (manager_id) REFERENCES users(id),
            FOREIGN KEY (driver_id) REFERENCES users(id)
        )
    """)

    # Compliance logs table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS compliance_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trip_id INTEGER NOT NULL,
            driver_id INTEGER NOT NULL,
            event_type TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            note TEXT,
            FOREIGN KEY (trip_id) REFERENCES trips(id),
            FOREIGN KEY (driver_id) REFERENCES users(id)
        )
    """)

    db.commit()
    db.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized.")