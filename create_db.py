import sqlite3

connection = sqlite3.connect("Desktop_pet.db")
cursor = connection.cursor()

cursor.execute("""
    CREATE TABLE IF NOT EXISTS websites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            url TEXT NOT NULL,
            synchronized INTEGER NOT NULL,
            deletflag INTEGER  NOT NULL 
    )
""")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS termine(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            datum DATE NOT NULL,        
            uhrzeitstart TIME,
            uhrzeitende TIME,
            ort TEXT,
            repeate TEXT NOT NULL,
            synchronized INTEGER NOT NULL,
            deletflag INTEGER  NOT NULL 
    )
""")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS todo(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            date DATE NOT NULL,
            text TEXT NOT NULL,
            state TEXT NOT NULL,      
            synchronized INTEGER NOT NULL,
            deletflag INTEGER  NOT NULL 
    )
""")


connection.commit()
connection.close()

print("DB erstellt")