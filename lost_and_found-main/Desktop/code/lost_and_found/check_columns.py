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
    
    # Check columns in lost_items table
    cursor.execute("DESCRIBE lost_items")
    columns = cursor.fetchall()
    print("Current columns in lost_items table:")
    for col in columns:
        print(f"{col[0]} - {col[1]} - {col[2]}")
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"Error connecting to database: {e}")