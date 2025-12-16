from flask import render_template, request, redirect, url_for, flash, session
from routes.base_route import BaseRoute
from models.user import User
from models.item import Item
from models.database import get_db_connection
import json
import threading
import time

class ChatRoute(BaseRoute):
    """Chat related routes"""
    
    def __init__(self):
        super().__init__()
        # In-memory storage for chat messages (in production, use a proper database)
        self.chat_rooms = {}
        self.chat_lock = threading.Lock()
    
    def chat(self, item_id):
        """Handle item chat between owner and claimer"""
        user = self.require_login()
        if not user:
            return redirect(url_for('login'))
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get item details
        cursor.execute('''
            SELECT li.*, u.username as owner_name
            FROM lost_items li 
            JOIN users u ON li.user_id = u.id 
            WHERE li.id = %s
        ''', (item_id,))
        item = cursor.fetchone()
        
        if not item:
            flash('Item not found.', 'error')
            cursor.close()
            conn.close()
            return redirect(url_for('dashboard'))
        
        # Check if user can access this chat
        # Either the owner or the person who claimed the item can chat
        can_access = (
            item['user_id'] == user.id or  # User is the owner
            (item['claimed_by'] is not None and item['claimed_by'] == user.id) or  # User is the claimer
            item['status'] == 'claimed'  # Item is claimed
        )
        
        if not can_access:
            flash('You do not have permission to access this chat.', 'error')
            cursor.close()
            conn.close()
            return redirect(url_for('dashboard'))
        
        # Get chat messages for this item
        cursor.execute('''
            SELECT cm.*, u.username 
            FROM chat_messages cm
            JOIN users u ON cm.sender_id = u.id
            WHERE cm.item_id = %s
            ORDER BY cm.timestamp ASC
        ''', (item_id,))
        messages = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return render_template('chat.html', user=user, item=item, messages=messages)
    
    def send_message(self, item_id):
        """Send a chat message"""
        user = self.require_login()
        if not user:
            return {'error': 'Authentication required'}, 401
        
        message = request.form.get('message', '').strip()
        
        if not message:
            return {'error': 'Message cannot be empty'}, 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verify user can send message to this item
        cursor.execute('''
            SELECT user_id, claimed_by FROM lost_items 
            WHERE id = %s AND (user_id = %s OR claimed_by = %s)
        ''', (item_id, user.id, user.id))
        item = cursor.fetchone()
        
        if not item:
            cursor.close()
            conn.close()
            return {'error': 'Access denied. You must be either the owner or claimer of this item to chat.'}, 403
        
        # Insert message
        cursor.execute('''
            INSERT INTO chat_messages (item_id, sender_id, message)
            VALUES (%s, %s, %s)
        ''', (item_id, user.id, message))
        conn.commit()
        
        # Get the inserted message with username
        cursor.execute('''
            SELECT cm.*, u.username 
            FROM chat_messages cm
            JOIN users u ON cm.sender_id = u.id
            WHERE cm.id = %s
        ''', (cursor.lastrowid,))
        new_message = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        return {'message': new_message}, 200
    
    def get_messages(self, item_id):
        """Get chat messages for an item"""
        user = self.require_login()
        if not user:
            return {'error': 'Authentication required'}, 401
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verify user can access messages for this item
        cursor.execute('''
            SELECT user_id, claimed_by FROM lost_items 
            WHERE id = %s AND (user_id = %s OR claimed_by = %s)
        ''', (item_id, user.id, user.id))
        item = cursor.fetchone()
        
        if not item:
            cursor.close()
            conn.close()
            return {'error': 'Access denied'}, 403
        
        # Get messages for this item
        cursor.execute('''
            SELECT cm.*, u.username 
            FROM chat_messages cm
            JOIN users u ON cm.sender_id = u.id
            WHERE cm.item_id = %s
            ORDER BY cm.timestamp ASC
        ''', (item_id,))
        messages = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return {'messages': messages}, 200
    
    def monitor_chats(self):
        """Monitor all chats (main admin only)"""
        admin = self.require_admin()
        if not admin:
            return redirect(url_for('dashboard'))
        
        # Check if user is main admin
        if admin.role != 'main_admin':
            flash('Access denied. Only main administrators can monitor chats.', 'error')
            return redirect(url_for('dashboard'))
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get all items with chat messages
        cursor.execute('''
            SELECT DISTINCT li.id, li.item_name, li.status, u1.username as owner_name, 
                   u2.username as claimer_name, COUNT(cm.id) as message_count
            FROM lost_items li
            LEFT JOIN users u1 ON li.user_id = u1.id
            LEFT JOIN users u2 ON li.claimed_by = u2.id
            LEFT JOIN chat_messages cm ON li.id = cm.item_id
            WHERE li.status IN ('claimed', 'resolved')
            GROUP BY li.id, li.item_name, li.status, u1.username, u2.username
            HAVING COUNT(cm.id) > 0
            ORDER BY COUNT(cm.id) DESC
        ''')
        chat_items = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return render_template('monitor_chats.html', user=admin, chat_items=chat_items)