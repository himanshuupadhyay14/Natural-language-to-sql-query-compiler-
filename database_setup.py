import sqlite3

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        marks INTEGER,
        department TEXT
    )
    """
)

students_data = [
    ("Alice", 85, "sales"),
    ("Bob", 72, "marketing"),
    ("Charlie", 90, "sales"),
    ("David", 60, "hr"),
    ("Eva", 78, "marketing"),
]

cursor.execute("SELECT COUNT(*) FROM students")
row_count = cursor.fetchone()[0]

if row_count == 0:
    cursor.executemany(
        "INSERT INTO students (name, marks, department) VALUES (?, ?, ?)",
        students_data,
    )

conn.commit()
conn.close()

print("Database created successfully!")
