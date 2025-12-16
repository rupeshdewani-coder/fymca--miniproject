from models.database import get_db_connection
import pymysql.cursors
import hashlib

class User:
    def __init__(self, id=None, username=None, email=None, password=None, phone=None, 
                 phone_verified=0, role='student', verified=0, profile_image=None, created_at=None):
        self.id = id
        self.username = username
        self.email = email
        self.password = password
        self.phone = phone
        self.phone_verified = phone_verified
        self.role = role
        self.verified = verified
        self.profile_image = profile_image
        self.created_at = created_at
    
    @staticmethod
    def get_by_id(user_id):
        """Get user by ID"""
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))
        user_data = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if user_data:
            return User(**user_data)
        return None
    
    @staticmethod
    def get_by_email(email):
        """Get user by email"""
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
        user_data = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if user_data:
            return User(**user_data)
        return None
    
    @staticmethod
    def get_by_phone(phone):
        """Get user by phone"""
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute('SELECT * FROM users WHERE phone = %s', (phone,))
        user_data = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if user_data:
            return User(**user_data)
        return None
    
    @staticmethod
    def get_by_username(username):
        """Get user by username"""
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
        user_data = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if user_data:
            return User(**user_data)
        return None
    
    @staticmethod
    def hash_password(password):
        """Hash a password using SHA-256"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def save(self):
        """Save user to database"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if self.id:
            # Update existing user
            cursor.execute('''
                UPDATE users SET username=%s, email=%s, password=%s, phone=%s, 
                phone_verified=%s, role=%s, verified=%s, profile_image=%s 
                WHERE id=%s
            ''', (self.username, self.email, self.password, self.phone, 
                  self.phone_verified, self.role, self.verified, self.profile_image, self.id))
        else:
            # Insert new user
            cursor.execute('''
                INSERT INTO users (username, email, password, phone, phone_verified, role, verified, profile_image) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ''', (self.username, self.email, self.password, self.phone, 
                  self.phone_verified, self.role, self.verified, self.profile_image))
            self.id = cursor.lastrowid
        
        conn.commit()
        cursor.close()
        conn.close()
    
    def is_admin(self):
        """Check if user is admin or main admin"""
        return self.role in ['admin', 'main_admin']
    
    def is_main_admin(self):
        """Check if user is main admin"""
        return self.role == 'main_admin'
    
    @staticmethod
    def get_all():
        """Get all users"""
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute('SELECT * FROM users')
        users_data = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return [User(**user_data) for user_data in users_data]
    
    @staticmethod
    def delete(user_id):
        """Delete user by ID"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM users WHERE id = %s', (user_id,))
        conn.commit()
        cursor.close()
        conn.close()