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
    
    # Find the user who is not 'admin' and make them main_admin
    cursor.execute("SELECT id, username FROM users WHERE username != 'admin' LIMIT 1")
    user = cursor.fetchone()
    
    if user:
        user_id, username = user
        print(f"Found user: {username} (ID: {user_id})")
        
        # Update user to main_admin
        cursor.execute("UPDATE users SET role = 'main_admin', verified = TRUE WHERE id = %s", (user_id,))
        conn.commit()
        print(f"User {username} has been promoted to Main Admin!")
    else:
        print("No non-admin users found!")
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"Error: {e}")