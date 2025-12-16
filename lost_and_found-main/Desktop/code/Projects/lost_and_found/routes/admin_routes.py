from flask import render_template, request, redirect, url_for, flash, session
from routes.base_route import BaseRoute
from models.user import User
from models.item import Item
from models.database import get_db_connection

class AdminRoute(BaseRoute):
    """Admin related routes"""
    
    def __init__(self):
        super().__init__()
    
    def verify_user(self, user_id):
        """Verify a user"""
        admin = self.require_admin()
        if not admin:
            return redirect(url_for('dashboard'))
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET verified = 1 WHERE id = %s', (user_id,))
        conn.commit()
        cursor.close()
        conn.close()
        
        flash('User verified successfully!', 'success')
        return redirect(url_for('dashboard'))
    
    def reject_user(self, user_id):
        """Reject and remove a user"""
        admin = self.require_admin()
        if not admin:
            return redirect(url_for('dashboard'))
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM users WHERE id = %s', (user_id,))
        conn.commit()
        cursor.close()
        conn.close()
        
        flash('User rejected and removed successfully!', 'success')
        return redirect(url_for('dashboard'))
    
    def verify_item(self, item_id):
        """Verify an item"""
        admin = self.require_admin()
        if not admin:
            return redirect(url_for('dashboard'))
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE lost_items SET status = "found" WHERE id = %s', (item_id,))
        conn.commit()
        cursor.close()
        conn.close()
        
        flash('Item verified successfully!', 'success')
        return redirect(url_for('dashboard'))
    
    def reject_item(self, item_id):
        """Reject an item"""
        admin = self.require_admin()
        if not admin:
            return redirect(url_for('dashboard'))
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE lost_items SET status = "resolved" WHERE id = %s', (item_id,))
        conn.commit()
        cursor.close()
        conn.close()
        
        flash('Item rejected successfully!', 'success')
        return redirect(url_for('dashboard'))
    
    def promote_user(self, user_id):
        """Promote a user to admin"""
        admin = self.require_admin()
        if not admin or not self.is_main_admin(admin):
            flash('Access denied. Only main administrators can promote users.', 'error')
            return redirect(url_for('dashboard'))
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET role = "admin" WHERE id = %s', (user_id,))
        conn.commit()
        cursor.close()
        conn.close()
        
        flash('User promoted to admin successfully!', 'success')
        return redirect(url_for('dashboard'))
    
    def remove_user(self, user_id):
        """Remove a user completely"""
        admin = self.require_admin()
        if not admin or not self.is_main_admin(admin):
            flash('Access denied. Only main administrators can remove users.', 'error')
            return redirect(url_for('dashboard'))
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM users WHERE id = %s', (user_id,))
        conn.commit()
        cursor.close()
        conn.close()
        
        flash('User removed successfully!', 'success')
        return redirect(url_for('dashboard'))
    
    def demote_admin(self, user_id):
        """Demote an admin to student"""
        admin = self.require_admin()
        if not admin or not self.is_main_admin(admin):
            flash('Access denied. Only main administrators can demote admins.', 'error')
            return redirect(url_for('dashboard'))
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET role = "student" WHERE id = %s', (user_id,))
        conn.commit()
        cursor.close()
        conn.close()
        
        flash('Admin demoted to student successfully!', 'success')
        return redirect(url_for('dashboard'))
    
    def remove_item(self, item_id):
        """Remove an item completely"""
        admin = self.require_admin()
        if not admin or not self.is_main_admin(admin):
            flash('Access denied. Only main administrators can remove items.', 'error')
            return redirect(url_for('dashboard'))
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # First delete associated chat messages to avoid foreign key constraint violation
        cursor.execute('DELETE FROM chat_messages WHERE item_id = %s', (item_id,))
        
        # Then delete the item
        cursor.execute('DELETE FROM lost_items WHERE id = %s', (item_id,))
        conn.commit()
        cursor.close()
        conn.close()
        
        flash('Item removed successfully!', 'success')
        return redirect(url_for('dashboard'))