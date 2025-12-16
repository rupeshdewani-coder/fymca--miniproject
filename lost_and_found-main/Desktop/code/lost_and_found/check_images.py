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
    
    # Check items with images
    cursor.execute("SELECT id, item_name, image_path FROM lost_items WHERE image_path IS NOT NULL LIMIT 5")
    items = cursor.fetchall()
    print("Items with images:")
    for item in items:
        print(f"ID: {item[0]}, Name: {item[1]}, Image Path: {item[2]}")
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"Error connecting to database: {e}")