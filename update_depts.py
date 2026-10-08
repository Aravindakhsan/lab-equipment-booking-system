import sqlite3

conn = sqlite3.connect('lab_booking.db')
cursor = conn.cursor()

updates = [
    ("Electronics and Communication Engineering", "Digital Oscilloscope"),
    ("Electronics and Communication Engineering", "Function Generator"),
    ("Information Technology", "Arduino Uno"),
    ("Computer Science and Engineering", "Raspberry Pi"),
    ("Electrical and Electronics Engineering", "Digital Multimeter"),
    ("Mechanical Engineering", "Soldering Station"),
    ("Electronics and Communication Engineering", "FPGA Development Kit"),
    ("Mechanical Engineering", "3D Printer"),
    ("Electronics and Communication Engineering", "Logic Analyzer"),
    ("Electrical and Electronics Engineering", "DC Power Supply")
]

for dept, name in updates:
    cursor.execute("UPDATE equipment SET department = ? WHERE name = ?", (dept, name))

conn.commit()
conn.close()
print("Departments updated.")
