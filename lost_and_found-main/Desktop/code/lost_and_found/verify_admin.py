import pymysql

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'lost_and_found',
    'port': 3306,
    'charset': 'utf8mb4'
}

try:
    conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    # Check if admin user exists
    cursor.execute("SELECT * FROM users WHERE username = 'admin'")
    admin_user = cursor.fetchone()
    
    if admin_user:
        print("Admin user found:")
        print(f"ID: {admin_user[0]}")
        print(f"Username: {admin_user[1]}")
        print(f"Email: {admin_user[2]}")
        print("Login with username: admin and password: admin123")
    else:
        print("Admin user not found")
        # Insert admin user
        cursor.execute("INSERT INTO users (username, email, password) VALUES (%s, %s, %s)",
                       ('admin', 'admin@college.edu', 'admin123'))
        conn.commit()
        print("Admin user created with username: admin and password: admin123")
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"Error: {e}")