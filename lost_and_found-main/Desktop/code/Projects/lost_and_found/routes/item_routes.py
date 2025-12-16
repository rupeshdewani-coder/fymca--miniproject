from flask import render_template, request, redirect, url_for, flash, session
from routes.base_route import BaseRoute
from models.user import User
from models.item import Item
from models.database import get_db_connection
import os
from datetime import datetime
from werkzeug.utils import secure_filename

class ItemRoute(BaseRoute):
    """Item related routes"""
    
    def __init__(self, app):
        super().__init__()
        self.app = app
    
    def post_item(self):
        """Handle posting a new item"""
        user = self.require_login()
        if not hasattr(user, 'id'):
            return user
        
        if request.method == 'POST':
            item_name = request.form.get('item_name', '').strip()
            category = request.form.get('category', '').strip()
            description = request.form.get('description', '').strip()
            location = request.form.get('location', '').strip()
            date_str = request.form.get('date', '')
            contact_info = request.form.get('contact_info', '').strip()
            image = request.files.get('image') or request.files.get('item_image')
            
            # Validation - only check mandatory fields
            if not item_name or not category or not location or not image:
                flash('Please fill in all mandatory fields (Item Name, Category, Location, and Image).', 'error')
                return render_template('post_item.html')
            
            # Process image upload
            image_path = None
            if image and self.allowed_file(image.filename):
                filename = secure_filename(image.filename)
                # Add timestamp to filename to avoid conflicts
                name, ext = os.path.splitext(filename)
                filename = f"{name}_{int(datetime.now().timestamp())}{ext}"
                image.save(os.path.join(self.app.config['UPLOAD_FOLDER'], filename))
                # Store only the filename, not the full path
                image_path = filename
            
            # Determine item status - admins don't need verification
            item_status = 'found' if user.role in ['admin', 'main_admin'] else 'lost'
            
            # Save item to database
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO lost_items (user_id, item_name, category, description, location, date, image_url, contact_methods, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (user.id, item_name, category, description, location, date_str, image_path, contact_info, item_status))
            conn.commit()
            cursor.close()
            conn.close()
            
            # Different success message based on user role
            if user.role in ['admin', 'main_admin']:
                flash('Item posted successfully! As an admin, your item is immediately visible.', 'success')
            else:
                flash('Item posted successfully! The item has gone for verification and will be visible once approved by an administrator.', 'success')
            return redirect(url_for('dashboard'))
        
        return render_template('post_item.html')
    
    def item_detail(self, item_id):
        """Show item details"""
        user = self.require_login()
        if not hasattr(user, 'id'):
            return user
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get item details
        cursor.execute('''
            SELECT li.*, u.username as poster_name 
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
        
        # Check if user can claim this item (item is not already claimed/resolved and user is not the owner)
        can_claim = (item['user_id'] != user.id) and (item['status'] not in ['claimed', 'resolved'])
        
        cursor.close()
        conn.close()
        
        return render_template('item_detail.html', user=user, item=item, can_claim=can_claim)
    
    def claim_item(self, item_id):
        """Claim an item"""
        user = self.require_login()
        if not hasattr(user, 'id'):
            return user
            
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get item details
        cursor.execute('SELECT * FROM lost_items WHERE id = %s', (item_id,))
        item = cursor.fetchone()
        
        if not item:
            flash('Item not found.', 'error')
            cursor.close()
            conn.close()
            return redirect(url_for('dashboard'))
        
        # Check if user can claim this item
        if item['user_id'] == user.id:
            flash('You cannot claim your own item.', 'error')
            cursor.close()
            conn.close()
            return redirect(url_for('item_detail', item_id=item_id))
        
        if item['status'] in ['claimed', 'resolved']:
            flash('This item has already been claimed.', 'error')
            cursor.close()
            conn.close()
            return redirect(url_for('item_detail', item_id=item_id))
        
        # Update item status to claimed
        cursor.execute('''
            UPDATE lost_items 
            SET status = 'claimed', claimed_by = %s, claimed_at = NOW() 
            WHERE id = %s
        ''', (user.id, item_id))
        conn.commit()
        
        cursor.close()
        conn.close()
        
        flash('Item claimed successfully! Please contact the owner to arrange pickup.', 'success')
        return redirect(url_for('item_detail', item_id=item_id))
    
    def mark_recovered(self, item_id):
        """Mark an item as recovered"""
        user = self.require_login()
        if not hasattr(user, 'id'):
            return user
            
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get item details
        cursor.execute('SELECT * FROM lost_items WHERE id = %s', (item_id,))
        item = cursor.fetchone()
        
        if not item:
            flash('Item not found.', 'error')
            cursor.close()
            conn.close()
            return redirect(url_for('dashboard'))
        
        # Check if user can mark this item as recovered
        # Only the owner or admin can mark as recovered
        if item['user_id'] != user.id and user.role not in ['admin', 'main_admin']:
            flash('You do not have permission to mark this item as recovered.', 'error')
            cursor.close()
            conn.close()
            return redirect(url_for('item_detail', item_id=item_id))
        
        # Update item status to resolved
        cursor.execute('''
            UPDATE lost_items 
            SET status = 'resolved', recovered = 1 
            WHERE id = %s
        ''', (item_id,))
        conn.commit()
        
        cursor.close()
        conn.close()
        
        flash('Item marked as recovered successfully!', 'success')
        return redirect(url_for('dashboard'))
    
    def rate_satisfaction(self, item_id):
        """Rate satisfaction for a recovered item"""
        user = self.require_login()
        if not hasattr(user, 'id'):
            return user
            
        if request.method == 'POST':
            rating = request.form.get('rating')
            
            # Validate rating
            try:
                rating = int(rating)
                if rating < 1 or rating > 5:
                    raise ValueError("Rating must be between 1 and 5")
            except (ValueError, TypeError):
                flash('Invalid rating. Please select a rating between 1 and 5.', 'error')
                return redirect(url_for('dashboard'))
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Get item details
            cursor.execute('SELECT * FROM lost_items WHERE id = %s', (item_id,))
            item = cursor.fetchone()
            
            if not item:
                flash('Item not found.', 'error')
                cursor.close()
                conn.close()
                return redirect(url_for('dashboard'))
            
            # Check if user can rate satisfaction for this item
            # Only the claimer (person who claimed the item) can rate satisfaction
            if item['claimed_by'] != user.id:
                flash('You do not have permission to rate satisfaction for this item.', 'error')
                cursor.close()
                conn.close()
                return redirect(url_for('item_detail', item_id=item_id))
            
            # Check if item is recovered
            if not item['recovered']:
                flash('Item must be marked as recovered before rating satisfaction.', 'error')
                cursor.close()
                conn.close()
                return redirect(url_for('item_detail', item_id=item_id))
            
            # Check if already rated
            if item['satisfaction_rating'] is not None:
                flash('Satisfaction has already been rated for this item.', 'error')
                cursor.close()
                conn.close()
                return redirect(url_for('dashboard'))
            
            # Update satisfaction rating
            cursor.execute('''
                UPDATE lost_items 
                SET satisfaction_rating = %s 
                WHERE id = %s
            ''', (rating, item_id))
            conn.commit()
            
            cursor.close()
            conn.close()
            
            flash('Thank you for rating your satisfaction!', 'success')
            return redirect(url_for('dashboard'))
        
        # If not POST request, redirect to dashboard
        return redirect(url_for('dashboard'))
    
    def allowed_file(self, filename):
        """Check if file extension is allowed"""
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in self.app.config['ALLOWED_EXTENSIONS']