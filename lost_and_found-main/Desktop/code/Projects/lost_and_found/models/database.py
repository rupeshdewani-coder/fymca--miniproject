import pymysql
from pymysql.cursors import DictCursor
import os

# Database configuration for XAMPP MySQL
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'lost_and_found',
    'port': 3306,
    'charset': 'utf8mb4'
}

def get_db_connection():
    """Create and return a database connection"""
    return pymysql.connect(cursorclass=DictCursor, **DB_CONFIG)

def init_db():
    """Initialize the database with all required tables"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50) NOT NULL,
            email VARCHAR(100) NOT NULL UNIQUE,
            password VARCHAR(255) NOT NULL,
            phone VARCHAR(15),
            phone_verified TINYINT(1) DEFAULT 0,
            role ENUM('student', 'admin', 'main_admin') DEFAULT 'student',
            verified TINYINT(1) DEFAULT 0,
            profile_image VARCHAR(255) DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Add profile_image column if it doesn't exist
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN profile_image VARCHAR(255) DEFAULT NULL")
    except:
        pass  # Column might already exist
    
    # Create index on email for faster lookups
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)')
    
    # Create index on phone for faster lookups
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_phone ON users(phone)')
    
    # Create lost_items table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS lost_items (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT,
            item_name VARCHAR(100) NOT NULL,
            description TEXT,
            location VARCHAR(255),
            date DATE,
            image_url VARCHAR(255),
            contact_methods JSON,
            status ENUM('lost', 'found', 'claimed', 'resolved') DEFAULT 'lost',
            claimed_by INT DEFAULT NULL,
            claimed_at TIMESTAMP NULL DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (claimed_by) REFERENCES users(id) ON DELETE SET NULL
        )
    ''')
    
    # Add missing columns if they don't exist (for existing databases)
    try:
        cursor.execute("ALTER TABLE lost_items ADD COLUMN location VARCHAR(255)")
    except:
        pass  # Column might already exist
    
    try:
        cursor.execute("ALTER TABLE lost_items ADD COLUMN date DATE")
    except:
        pass  # Column might already exist
    
    try:
        cursor.execute("ALTER TABLE lost_items ADD COLUMN image_url VARCHAR(255)")
    except:
        pass  # Column might already exist
    
    try:
        cursor.execute("ALTER TABLE lost_items ADD COLUMN contact_methods JSON")
    except:
        pass  # Column might already exist
    
    try:
        cursor.execute("ALTER TABLE lost_items ADD COLUMN status ENUM('lost', 'found', 'claimed', 'resolved') DEFAULT 'lost'")
    except:
        pass  # Column might already exist
    
    try:
        cursor.execute("ALTER TABLE lost_items ADD COLUMN claimed_by INT DEFAULT NULL")
    except:
        pass  # Column might already exist
    
    try:
        cursor.execute("ALTER TABLE lost_items ADD COLUMN claimed_at TIMESTAMP NULL DEFAULT NULL")
    except:
        pass  # Column might already exist
    
    # Add foreign key constraint for claimed_by if it doesn't exist
    try:
        cursor.execute("ALTER TABLE lost_items ADD CONSTRAINT fk_claimed_by FOREIGN KEY (claimed_by) REFERENCES users(id) ON DELETE SET NULL")
    except:
        pass  # Constraint might already exist
    
    # Create claims table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS claims (
            id INT AUTO_INCREMENT PRIMARY KEY,
            item_id INT,
            user_id INT,
            status ENUM('pending', 'approved', 'rejected') DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (item_id) REFERENCES lost_items(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')
    
    # Create notifications table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notifications (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT,
            message TEXT,
            is_read BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')
    
    # Create otp_verifications table
    # First drop the table if it exists with incorrect schema
    cursor.execute('DROP TABLE IF EXISTS otp_verifications')
    
    cursor.execute('''
        CREATE TABLE otp_verifications (
            id INT AUTO_INCREMENT PRIMARY KEY,
            phone VARCHAR(15) NULL,
            email VARCHAR(100) NULL,
            otp VARCHAR(6),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create index on phone for faster lookups in otp_verifications
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_otp_phone ON otp_verifications(phone)')
    
    # Create index on email for faster lookups in otp_verifications
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_otp_email ON otp_verifications(email)')
    
    # Create pending_email_changes table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pending_email_changes (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT,
            new_email VARCHAR(100),
            requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            approved BOOLEAN DEFAULT FALSE,
            approved_at TIMESTAMP NULL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')
    
    # Create pending_phone_changes table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pending_phone_changes (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT,
            new_phone VARCHAR(15),
            requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            approved BOOLEAN DEFAULT FALSE,
            approved_at TIMESTAMP NULL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')
    
    # Create chat_messages table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INT AUTO_INCREMENT PRIMARY KEY,
            item_id INT NOT NULL,
            sender_id INT NOT NULL,
            message TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (item_id) REFERENCES lost_items(id) ON DELETE CASCADE,
            FOREIGN KEY (sender_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')
    
    conn.commit()
    cursor.close()
    conn.close()