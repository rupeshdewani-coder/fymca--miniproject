from models.database import get_db_connection
import pymysql.cursors
from datetime import date

class Item:
    def __init__(self, id=None, user_id=None, item_name=None, description=None, location=None, 
                 date=None, image_url=None, contact_methods=None, status='lost', created_at=None):
        self.id = id
        self.user_id = user_id
        self.item_name = item_name
        self.description = description
        self.location = location
        self.date = date
        self.image_url = image_url
        self.contact_methods = contact_methods
        self.status = status
        self.created_at = created_at
    
    @staticmethod
    def get_by_id(item_id):
        """Get item by ID"""
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute('SELECT * FROM lost_items WHERE id = %s', (item_id,))
        item_data = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if item_data:
            return Item(**item_data)
        return None
    
    @staticmethod
    def get_by_user_id(user_id):
        """Get items by user ID"""
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute('SELECT * FROM lost_items WHERE user_id = %s', (user_id,))
        items_data = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return [Item(**item_data) for item_data in items_data]
    
    @staticmethod
    def get_all():
        """Get all items"""
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute('SELECT * FROM lost_items')
        items_data = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return [Item(**item_data) for item_data in items_data]
    
    @staticmethod
    def get_unverified():
        """Get unverified items (items with status 'lost')"""
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute('SELECT * FROM lost_items WHERE status = "lost"')
        items_data = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return [Item(**item_data) for item_data in items_data]
    
    def save(self):
        """Save item to database"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if self.id:
            # Update existing item
            cursor.execute('''
                UPDATE lost_items SET user_id=%s, item_name=%s, description=%s, location=%s, 
                date=%s, image_url=%s, contact_methods=%s, status=%s 
                WHERE id=%s
            ''', (self.user_id, self.item_name, self.description, self.location, 
                  self.date, self.image_url, self.contact_methods, self.status, self.id))
        else:
            # Insert new item
            cursor.execute('''
                INSERT INTO lost_items (user_id, item_name, description, location, date, image_url, contact_methods, status) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ''', (self.user_id, self.item_name, self.description, self.location, 
                  self.date, self.image_url, self.contact_methods, self.status))
            self.id = cursor.lastrowid
        
        conn.commit()
        cursor.close()
        conn.close()
    
    def delete(self):
        """Delete item from database"""
        if self.id:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('DELETE FROM lost_items WHERE id = %s', (self.id,))
            conn.commit()
            cursor.close()
            conn.close()
    
    @staticmethod
    def delete_by_id(item_id):
        """Delete item by ID"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM lost_items WHERE id = %s', (item_id,))
        conn.commit()
        cursor.close()
        conn.close()