import sqlite3
from werkzeug.security import generate_password_hash
import os

DATABASE = "lab_booking.db"

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Users Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'student'
        )
    ''')

    # Equipment Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS equipment (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            lab_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            available_quantity INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'Available'
        )
    ''')

    # Bookings Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            equipment_id INTEGER NOT NULL,
            booking_date TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            purpose TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Pending',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (equipment_id) REFERENCES equipment(id)
        )
    ''')

    # Returns Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS returns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            booking_id INTEGER NOT NULL,
            returned_date TEXT NOT NULL,
            condition TEXT NOT NULL,
            remarks TEXT,
            FOREIGN KEY (booking_id) REFERENCES bookings(id)
        )
    ''')

    # Create default admin account if not exists
    cursor.execute("SELECT id FROM users WHERE email = 'admin@lab.com'")
    if not cursor.fetchone():
        hashed_password = generate_password_hash("admin123")
        cursor.execute('''
            INSERT INTO users (name, email, password, role)
            VALUES (?, ?, ?, ?)
        ''', ("Administrator", "admin@lab.com", hashed_password, "admin"))

    # Schema Migration for Departments
    # Check if 'department' column exists in 'users'
    cursor.execute("PRAGMA table_info(users)")
    columns = [info[1] for info in cursor.fetchall()]
    if 'department' not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN department TEXT DEFAULT 'Information Technology'")
        
    # Check if 'department' column exists in 'equipment'
    cursor.execute("PRAGMA table_info(equipment)")
    columns = [info[1] for info in cursor.fetchall()]
    if 'department' not in columns:
        cursor.execute("ALTER TABLE equipment ADD COLUMN department TEXT DEFAULT 'Information Technology'")

    # Migration for new Bookings columns
    cursor.execute("PRAGMA table_info(bookings)")
    b_cols = [info[1] for info in cursor.fetchall()]
    new_b_cols = [
        ("expected_return_date", "TEXT"),
        ("expected_return_time", "TEXT"),
        ("issued_date", "TEXT"),
        ("issued_time", "TEXT"),
        ("issued_by", "TEXT"),
        ("issue_condition", "TEXT"),
        ("issue_remarks", "TEXT")
    ]
    for col_name, col_type in new_b_cols:
        if col_name not in b_cols:
            cursor.execute(f"ALTER TABLE bookings ADD COLUMN {col_name} {col_type}")

    # Migration for new Returns columns
    cursor.execute("PRAGMA table_info(returns)")
    r_cols = [info[1] for info in cursor.fetchall()]
    if 'returned_time' not in r_cols:
        cursor.execute("ALTER TABLE returns ADD COLUMN returned_time TEXT")

    # Maintenance Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS maintenance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            equipment_id INTEGER NOT NULL,
            maintenance_date TEXT NOT NULL,
            reason TEXT NOT NULL,
            condition TEXT,
            remarks TEXT,
            performed_by TEXT,
            next_maintenance_date TEXT,
            FOREIGN KEY (equipment_id) REFERENCES equipment(id)
        )
    ''')

    # Insert sample equipment if table is empty
    cursor.execute("SELECT COUNT(*) FROM equipment")
    count = cursor.fetchone()[0]
    if count == 0:
        sample_equipment = [
            ("Digital Oscilloscope", "2-channel, 100MHz digital storage oscilloscope", "Electronics Lab", "Electronics and Communication Engineering", 5, 5, "Available"),
            ("Function Generator", "20MHz arbitrary waveform generator", "Electronics Lab", "Electronics and Communication Engineering", 4, 4, "Available"),
            ("Arduino Uno", "Microcontroller board based on the ATmega328P", "IoT Lab", "Information Technology", 15, 15, "Available"),
            ("Raspberry Pi", "Raspberry Pi 4 Model B, 4GB RAM", "Embedded Systems Lab", "Computer Science and Engineering", 10, 10, "Available"),
            ("Digital Multimeter", "True-RMS digital multimeter", "Electronics Lab", "Electrical and Electronics Engineering", 20, 20, "Available"),
            ("Soldering Station", "Temperature controlled soldering iron", "Innovation Lab", "Mechanical Engineering", 8, 8, "Available"),
            ("FPGA Development Kit", "Basys 3 Artix-7 FPGA Trainer Board", "VLSI Lab", "Electronics and Communication Engineering", 6, 6, "Available"),
            ("3D Printer", "FDM 3D Printer for rapid prototyping", "Innovation Lab", "Mechanical Engineering", 2, 2, "Available"),
            ("Logic Analyzer", "16-channel, 100MS/s logic analyzer", "VLSI Lab", "Electronics and Communication Engineering", 3, 3, "Available"),
            ("DC Power Supply", "0-30V, 0-5A Variable DC Power Supply", "Electronics Lab", "Electrical and Electronics Engineering", 12, 12, "Available")
        ]
        cursor.executemany('''
            INSERT INTO equipment (name, description, lab_name, department, quantity, available_quantity, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', sample_equipment)

    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
    print("Database initialized successfully.")
