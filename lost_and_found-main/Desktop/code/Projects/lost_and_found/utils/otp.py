from models.database import get_db_connection
import pymysql.cursors
import secrets
import string
import threading
import time

class OTPUtil:
    """OTP utility class with threading support"""
    
    def __init__(self):
        pass
    
    def generate_otp(self, length=6):
        """Generate a random OTP of specified length"""
        characters = string.digits
        return ''.join(secrets.choice(characters) for _ in range(length))
    
    def store_otp(self, phone=None, email=None, otp=None):
        """Store OTP in database for phone or email"""
        if not otp:
            otp = self.generate_otp()
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Remove existing OTP for this phone/email
        if phone:
            cursor.execute("DELETE FROM otp_verifications WHERE phone = %s", (phone,))
        if email:
            cursor.execute("DELETE FROM otp_verifications WHERE email = %s", (email,))
        
        # Store new OTP - handle cases where phone or email might be None
        if phone and email:
            cursor.execute('''
                INSERT INTO otp_verifications (phone, email, otp) 
                VALUES (%s, %s, %s)
            ''', (phone, email, otp))
        elif phone:
            cursor.execute('''
                INSERT INTO otp_verifications (phone, email, otp) 
                VALUES (%s, NULL, %s)
            ''', (phone, otp))
        elif email:
            cursor.execute('''
                INSERT INTO otp_verifications (phone, email, otp) 
                VALUES (NULL, %s, %s)
            ''', (email, otp))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return otp
    
    def verify_otp(self, phone=None, email=None, otp=None):
        """Verify OTP for phone or email"""
        if not otp:
            return False
        
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        if phone:
            cursor.execute('''
                SELECT * FROM otp_verifications 
                WHERE phone = %s AND otp = %s
            ''', (phone, otp))
        elif email:
            cursor.execute('''
                SELECT * FROM otp_verifications 
                WHERE email = %s AND otp = %s
            ''', (email, otp))
        else:
            cursor.close()
            conn.close()
            return False
        
        otp_record = cursor.fetchone()
        cursor.close()
        conn.close()
        
        # Remove the OTP after verification (one-time use)
        if otp_record:
            conn = get_db_connection()
            cursor = conn.cursor()
            if phone:
                cursor.execute("DELETE FROM otp_verifications WHERE phone = %s", (phone,))
            elif email:
                cursor.execute("DELETE FROM otp_verifications WHERE email = %s", (email,))
            conn.commit()
            cursor.close()
            conn.close()
            return True
        
        return False
    
    def resend_otp_threaded(self, phone=None, email=None):
        """Resend OTP using threading for better performance"""
        def resend_task():
            otp = self.generate_otp()
            self.store_otp(phone=phone, email=email, otp=otp)
            return otp
        
        # Create and start thread
        thread = threading.Thread(target=resend_task)
        thread.start()
        return thread

# Create a global instance
otp_util = OTPUtil()

# Export functions for backward compatibility
generate_otp = otp_util.generate_otp
store_otp = otp_util.store_otp
verify_otp = otp_util.verify_otp