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
    
    # Check if users table exists
    cursor.execute("SHOW TABLES LIKE 'users'")
    users_table = cursor.fetchone()
    
    if users_table:
        print("Users table exists")
        # Check users in the database
        cursor.execute("SELECT * FROM users")
        users = cursor.fetchall()
        print(f"Number of users: {len(users)}")
        for user in users:
            print(f"User ID: {user[0]}, Username: {user[1]}, Email: {user[2]}")
    else:
        print("Users table does not exist")
    
    # Check if lost_items table exists
    cursor.execute("SHOW TABLES LIKE 'lost_items'")
    items_table = cursor.fetchone()
    
    if items_table:
        print("Lost items table exists")
    else:
        print("Lost items table does not exist")
        
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"Error connecting to database: {e}")