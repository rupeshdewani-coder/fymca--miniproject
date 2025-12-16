from flask import render_template, request, redirect, url_for, flash, session
from models.user import User
from models.database import get_db_connection

class BaseRoute:
    """Base class for all routes"""
    
    def __init__(self):
        pass
    
    def get_current_user(self):
        """Get current logged in user"""
        if 'user_id' in session:
            return User.get_by_id(session['user_id'])
        return None
    
    def is_admin(self, user):
        """Check if user is admin or main admin"""
        return user and hasattr(user, 'role') and user.role in ['admin', 'main_admin']
    
    def is_main_admin(self, user):
        """Check if user is main admin"""
        return user and hasattr(user, 'role') and user.role == 'main_admin'
    
    def require_login(self):
        """Require user to be logged in"""
        user = self.get_current_user()
        if not user:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login'))
        return user
    
    def require_admin(self):
        """Require user to be admin"""
        user = self.require_login()
        if not self.is_admin(user):
            flash('Access denied. Administrator privileges required.', 'error')
            return redirect(url_for('dashboard'))
        return user