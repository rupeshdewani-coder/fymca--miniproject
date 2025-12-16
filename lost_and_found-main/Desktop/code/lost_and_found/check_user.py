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
    
    # Check all users
    cursor.execute("SELECT id, username, role, verified FROM users")
    users = cursor.fetchall()
    print("All users:")
    for user in users:
        print(f"ID: {user[0]}, Username: {user[1]}, Role: {user[2]}, Verified: {user[3]}")
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"Error: {e}")