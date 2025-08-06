import sqlite3

DATABASE_NAME = "sustainability.db"

def create_database():
    """Creates the database and the 'readings' table if they don't exist."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            estimated_watts REAL NOT NULL,
            carbon_intensity INTEGER NOT NULL,
            gco2eq REAL NOT NULL
        )
    ''')
    
    conn.commit()
    conn.close()
    print(f"Database '{DATABASE_NAME}' and table 'readings' are ready.")

def add_reading(watts, intensity, gco2):
    """Adds a new monitoring reading to the database."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO readings (estimated_watts, carbon_intensity, gco2eq)
        VALUES (?, ?, ?)
    ''', (watts, intensity, gco2))
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    create_database()