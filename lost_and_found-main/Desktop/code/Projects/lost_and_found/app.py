from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import os
from datetime import datetime, timedelta
import hashlib
import re
from werkzeug.utils import secure_filename
import pymysql
from pymysql.cursors import DictCursor
from flask_socketio import SocketIO, emit, join_room, leave_room

# Import our modules
from models.database import init_db, get_db_connection
from models.user import User
from models.item import Item
from routes.base_route import BaseRoute
from routes.user_routes import UserRoute
from routes.admin_routes import AdminRoute
from routes.item_routes import ItemRoute
from routes.chat_routes import ChatRoute
from utils.otp import generate_otp, store_otp, verify_otp

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# Initialize SocketIO
socketio = SocketIO(app, cors_allowed_origins="*")

# Image upload configuration
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['ALLOWED_EXTENSIONS'] = ALLOWED_EXTENSIONS

# Create upload directory if it doesn't exist
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Initialize route handlers
base_route = BaseRoute()
user_route = UserRoute(app)
admin_route = AdminRoute()
item_route = ItemRoute(app)
chat_route = ChatRoute()

# Make functions available to templates
def is_admin(user):
    return user and hasattr(user, 'role') and user.role in ['admin', 'main_admin']

def is_main_admin(user):
    return user and hasattr(user, 'role') and user.role == 'main_admin'

def get_current_user():
    if 'user_id' in session:
        return User.get_by_id(session['user_id'])
    return None

app.jinja_env.globals.update(is_admin=is_admin)
app.jinja_env.globals.update(is_main_admin=is_main_admin)
app.jinja_env.globals.update(get_current_user=get_current_user)

# Routes
@app.route('/')
def index():
    # Check if user is logged in
    user = None
    try:
        user_id = session.get('user_id')
        if user_id:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))
            user_data = cursor.fetchone()
            if user_data:
                user = User(user_data['id'], user_data['username'], user_data['email'], user_data['phone'], 
                           user_data['role'], user_data['verified'], user_data['phone_verified'])
            cursor.close()
            conn.close()
    except Exception as e:
        print(f"Error checking user session: {e}")
        user = None
    
    # Get filter parameters
    category = request.args.get('category', '')
    location = request.args.get('location', '')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Build query for items with filters
    query = '''
        SELECT li.*, u.username as poster_name 
        FROM lost_items li 
        JOIN users u ON li.user_id = u.id 
        WHERE li.status = "found"
    '''
    params = []
    
    if category:
        query += ' AND li.category = %s'
        params.append(category)
    
    if location:
        query += ' AND li.location LIKE %s'
        params.append(f'%{location}%')
    
    query += ' ORDER BY li.created_at DESC LIMIT 20'
    
    cursor.execute(query, params)
    items = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('index.html', user=user, items=items, category_filter=category, location_filter=location)

@app.route('/register', methods=['GET', 'POST'])
def register():
    from routes.auth_routes import register as register_func
    return register_func()

@app.route('/login', methods=['GET', 'POST'])
def login():
    from routes.auth_routes import login as login_func
    return login_func()

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    user = base_route.require_login()
    # If user is not logged in, require_login returns a redirect response
    if not hasattr(user, 'id'):
        return user  # Return the redirect response
    
    conn = get_db_connection()
    cursor = conn.cursor()  # DictCursor is now default
    
    # Get user's lost items
    cursor.execute('SELECT * FROM lost_items WHERE user_id = %s ORDER BY created_at DESC', (user.id,))
    my_items = cursor.fetchall()
    
    # Get items claimed by user
    cursor.execute('''
        SELECT li.*, u.username as poster_name 
        FROM lost_items li 
        JOIN users u ON li.user_id = u.id 
        WHERE li.claimed_by = %s 
        ORDER BY li.claimed_at DESC
    ''', (user.id,))
    claimed_items = cursor.fetchall()
    
    # Get unverified users (for admins)
    unverified_users = []
    if user.role in ['admin', 'main_admin']:
        cursor.execute('SELECT id, username, email, phone, role, verified, phone_verified FROM users WHERE verified = 0 AND role = "student"')
        unverified_users = cursor.fetchall()
        print(f"DEBUG: Found {len(unverified_users)} unverified users")
        if unverified_users:
            print(f"DEBUG: First unverified user: {unverified_users[0]}")
    
    # Get unverified items (for admins) - items with status 'lost' are considered unverified
    unverified_items = []
    if user.role in ['admin', 'main_admin']:
        # Use a simpler query first to check what columns exist
        cursor.execute('SELECT li.id, li.item_name, u.username as poster_name FROM lost_items li JOIN users u ON li.user_id = u.id WHERE li.status = "lost"')
        unverified_items = cursor.fetchall()
        print(f"DEBUG: Found {len(unverified_items)} unverified items")
        if unverified_items:
            print(f"DEBUG: First unverified item: {unverified_items[0]}")
    
    # Get all users and items for main admin management panel
    all_users = []
    all_items = []
    if user.role == 'main_admin':
        # Get all users with their details
        cursor.execute('SELECT id, username, email, phone, role, verified FROM users ORDER BY created_at DESC')
        all_users = cursor.fetchall()
        
        # Get all items with poster names, claimer names, and satisfaction ratings
        cursor.execute('''
            SELECT li.id, li.item_name, li.status, li.claimed, li.recovered, li.satisfaction_rating, 
                   u.username as poster_name, u2.username as claimer_name
            FROM lost_items li 
            JOIN users u ON li.user_id = u.id 
            LEFT JOIN users u2 ON li.claimed_by = u2.id
            ORDER BY li.created_at DESC
        ''')
        all_items = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('dashboard.html', user=user, my_items=my_items, claimed_items=claimed_items, 
                         unverified_users=unverified_users, unverified_items=unverified_items,
                         all_users=all_users, all_items=all_items)

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        phone = request.form.get('phone', '').strip()
        
        # Validate phone format (10 digits)
        if not re.match(r'^[0-9]{10}$', phone):
            flash('Please enter a valid 10-digit phone number.', 'error')
            return render_template('forgot_password.html')
        
        # Format phone with +91 prefix
        formatted_phone = f"+91{phone}"
        
        # Check if user exists with this phone number
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE phone = %s', (formatted_phone,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not user:
            flash('No account found with this phone number.', 'error')
            return render_template('forgot_password.html')
        
        # Generate and send OTP
        otp = generate_otp()
        store_otp(phone=formatted_phone, otp=otp)
        session['current_otp'] = otp  # Store in session for development display
        session['forgot_password_phone'] = formatted_phone  # Store phone for later use
        
        flash('OTP sent to your phone number.', 'success')
        return redirect(url_for('verify_forgot_password_otp'))
    
    return render_template('forgot_password.html')

@app.route('/verify_forgot_password_otp', methods=['GET', 'POST'])
def verify_forgot_password_otp():
    # Check if user initiated forgot password flow
    if 'forgot_password_phone' not in session:
        flash('No forgot password request found.', 'error')
        return redirect(url_for('login'))
    
    phone = session['forgot_password_phone']
    
    if request.method == 'POST':
        # Check if user wants to resend OTP
        if 'resend_otp' in request.form:
            # Generate and resend OTP
            new_otp = generate_otp()
            store_otp(phone=phone, otp=new_otp)
            session['current_otp'] = new_otp  # Store in session for development display
            flash('New OTP sent to your phone number.', 'success')
            return redirect(url_for('verify_forgot_password_otp'))
        
        # Handle OTP verification
        entered_otp = request.form.get('otp', '').strip()
        
        if not entered_otp:
            flash('Please enter the OTP.', 'error')
            return render_template('verify_forgot_password_otp.html')
        
        # Verify OTP
        if verify_otp(phone=phone, otp=entered_otp):
            # OTP is correct, allow password reset
            flash('OTP verified successfully! Please set a new password.', 'success')
            return redirect(url_for('reset_forgot_password'))
        else:
            flash('Invalid OTP. Please try again.', 'error')
    
    return render_template('verify_forgot_password_otp.html')

@app.route('/reset_forgot_password', methods=['GET', 'POST'])
def reset_forgot_password():
    # Check if user initiated forgot password flow
    if 'forgot_password_phone' not in session:
        flash('No forgot password request found.', 'error')
        return redirect(url_for('login'))
    
    phone = session['forgot_password_phone']
    
    if request.method == 'POST':
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # Validation
        if not password or not confirm_password:
            flash('All fields are required.', 'error')
            return render_template('reset_forgot_password.html')
        
        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template('reset_forgot_password.html')
        
        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'error')
            return render_template('reset_forgot_password.html')
        
        # Hash password
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        
        # Update password in database
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET password = %s WHERE phone = %s', (hashed_password, phone))
        conn.commit()
        cursor.close()
        conn.close()
        
        # Clear session data
        session.pop('forgot_password_phone', None)
        session.pop('current_otp', None)
        
        flash('Password reset successfully! You can now login with your new password.', 'success')
        return redirect(url_for('login'))
    
    return render_template('reset_forgot_password.html')

@app.route('/verify_phone', methods=['GET', 'POST'])
def verify_phone():
    if 'pending_registration' not in session:
        flash('No pending registration.', 'error')
        return redirect(url_for('register'))
    
    pending_reg = session['pending_registration']
    phone = pending_reg['phone']
    
    # Check if there's a recently resent OTP to display
    resent_otp = session.pop('resent_otp', None)  # Pop it so it's only shown once
    
    if request.method == 'POST':
        # Check if user wants to resend OTP
        if 'resend_otp' in request.form:
            # Check if enough time has passed since last OTP (2 minutes)
            conn = get_db_connection()
            cursor = conn.cursor()  # DictCursor is now default
            cursor.execute("SELECT created_at FROM otp_verifications WHERE phone = %s", (phone,))
            otp_record = cursor.fetchone()
            cursor.close()
            conn.close()
            
            # If there's an existing OTP record, check the cooldown period
            if otp_record:
                time_since_last_otp = datetime.now() - otp_record['created_at']
                if time_since_last_otp < timedelta(minutes=2):
                    # Calculate remaining time
                    remaining_seconds = int((timedelta(minutes=2) - time_since_last_otp).total_seconds())
                    flash(f'Please wait {remaining_seconds} seconds before requesting a new OTP.', 'info')
                    return redirect(url_for('verify_phone'))
            
            # Generate and resend OTP (no cooldown restriction or cooldown has expired)
            new_otp = generate_otp()
            store_otp(phone=phone, otp=new_otp)
            session['current_otp'] = new_otp  # Store in session for development display
            session['resent_otp'] = new_otp  # Flag that we just resent an OTP
            flash(f'New OTP sent to {phone}.', 'success')
            return redirect(url_for('verify_phone'))
        
        # Handle OTP verification
        entered_otp = request.form.get('otp', '').strip()
        
        if not entered_otp:
            flash('Please enter the OTP.', 'error')
            return render_template('verify_phone.html')
        
        # Verify OTP
        if verify_otp(phone=phone, otp=entered_otp):
            # OTP is correct, update user's phone verification status
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Update user's phone_verified status
            cursor.execute('''
                UPDATE users SET phone_verified = %s WHERE phone = %s
            ''', (1, phone))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            # Clear session data
            session.pop('pending_registration', None)
            session.pop('current_otp', None)
            
            flash('Phone verification completed! Your registration is now pending admin approval.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Invalid OTP. Please try again.', 'error')
    
    # For GET requests, just show the verification page
    return render_template('verify_phone.html', resent_otp=resent_otp)

# User routes
@app.route('/profile', methods=['GET', 'POST'])
def profile():
    return user_route.profile()

@app.route('/change_email', methods=['GET', 'POST'])
def change_email():
    return user_route.change_email()

@app.route('/verify_email_change_otp', methods=['GET', 'POST'])
def verify_email_change_otp():
    return user_route.verify_email_change_otp()

@app.route('/change_phone', methods=['GET', 'POST'])
def change_phone():
    return user_route.change_phone()

@app.route('/verify_phone_change_otp', methods=['GET', 'POST'])
def verify_phone_change_otp():
    return user_route.verify_phone_change_otp()

# Item routes
@app.route('/post_item', methods=['GET', 'POST'])
def post_item():
    return item_route.post_item()

@app.route('/item/<int:item_id>')
def item_detail(item_id):
    return item_route.item_detail(item_id)

@app.route('/claim_item/<int:item_id>')
def claim_item(item_id):
    return item_route.claim_item(item_id)

@app.route('/mark_recovered/<int:item_id>', methods=['POST'])
def mark_recovered(item_id):
    return item_route.mark_recovered(item_id)

@app.route('/rate_satisfaction/<int:item_id>', methods=['POST'])
def rate_satisfaction(item_id):
    return item_route.rate_satisfaction(item_id)

# Chat routes
@app.route('/chat/<int:item_id>')
def chat(item_id):
    return chat_route.chat(item_id)

@app.route('/send_message/<int:item_id>', methods=['POST'])
def send_message(item_id):
    return jsonify(chat_route.send_message(item_id))

@app.route('/get_messages/<int:item_id>')
def get_messages(item_id):
    return jsonify(chat_route.get_messages(item_id))

@app.route('/monitor_chats')
def monitor_chats():
    return chat_route.monitor_chats()

# Admin routes
@app.route('/admin/verify_user/<int:user_id>', methods=['POST'])
def verify_user(user_id):
    return admin_route.verify_user(user_id)

@app.route('/admin/reject_user/<int:user_id>', methods=['POST'])
def reject_user(user_id):
    return admin_route.reject_user(user_id)

@app.route('/admin/verify_item/<int:item_id>', methods=['POST'])
def verify_item(item_id):
    return admin_route.verify_item(item_id)

@app.route('/admin/reject_item/<int:item_id>', methods=['POST'])
def reject_item(item_id):
    return admin_route.reject_item(item_id)

@app.route('/admin/promote/<int:user_id>', methods=['POST'])
def promote_user(user_id):
    return admin_route.promote_user(user_id)

@app.route('/admin/demote/<int:user_id>', methods=['POST'])
def demote_admin(user_id):
    return admin_route.demote_admin(user_id)

@app.route('/admin/remove/<int:user_id>', methods=['POST'])
def remove_user(user_id):
    return admin_route.remove_user(user_id)

@app.route('/admin/remove_item/<int:item_id>', methods=['POST'])
def remove_item(item_id):
    return admin_route.remove_item(item_id)

@app.route('/admin/pending_email_changes')
def admin_pending_email_changes():
    admin = base_route.require_admin()
    if not admin:
        return redirect(url_for('dashboard'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get pending email changes
    cursor.execute('''
        SELECT pec.*, u.username, u.email as current_email
        FROM pending_email_changes pec
        JOIN users u ON pec.user_id = u.id
        WHERE pec.approved = FALSE
        ORDER BY pec.requested_at DESC
    ''')
    pending_email_changes = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('admin_pending_email_changes.html', user=admin, pending_email_changes=pending_email_changes)

@app.route('/admin/pending_phone_changes')
def admin_pending_phone_changes():
    admin = base_route.require_admin()
    if not admin:
        return redirect(url_for('dashboard'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get pending phone changes
    cursor.execute('''
        SELECT ppc.*, u.username, u.phone as current_phone
        FROM pending_phone_changes ppc
        JOIN users u ON ppc.user_id = u.id
        WHERE ppc.approved = FALSE
        ORDER BY ppc.requested_at DESC
    ''')
    pending_phone_changes = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('admin_pending_phone_changes.html', user=admin, pending_phone_changes=pending_phone_changes)

@app.route('/admin/approve_email_change/<int:change_id>', methods=['POST'])
def approve_email_change(change_id):
    admin = base_route.require_admin()
    if not admin:
        return redirect(url_for('dashboard'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get the pending change
    cursor.execute('SELECT * FROM pending_email_changes WHERE id = %s AND approved = FALSE', (change_id,))
    pending_change = cursor.fetchone()
    
    if pending_change:
        # Update user's email
        cursor.execute('UPDATE users SET email = %s WHERE id = %s', 
                      (pending_change['new_email'], pending_change['user_id']))
        
        # Mark change as approved
        cursor.execute('UPDATE pending_email_changes SET approved = TRUE, approved_at = NOW() WHERE id = %s', 
                      (change_id,))
        
        conn.commit()
        flash('Email change approved successfully!', 'success')
    else:
        flash('Invalid request.', 'error')
    
    cursor.close()
    conn.close()
    
    return redirect(url_for('admin_pending_email_changes'))

@app.route('/admin/reject_email_change/<int:change_id>', methods=['POST'])
def reject_email_change(change_id):
    admin = base_route.require_admin()
    if not admin:
        return redirect(url_for('dashboard'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Delete the pending change
    cursor.execute('DELETE FROM pending_email_changes WHERE id = %s', (change_id,))
    conn.commit()
    
    cursor.close()
    conn.close()
    
    flash('Email change request rejected.', 'info')
    return redirect(url_for('admin_pending_email_changes'))

@app.route('/admin/approve_phone_change/<int:change_id>', methods=['POST'])
def approve_phone_change(change_id):
    admin = base_route.require_admin()
    if not admin:
        return redirect(url_for('dashboard'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get the pending change
    cursor.execute('SELECT * FROM pending_phone_changes WHERE id = %s AND approved = FALSE', (change_id,))
    pending_change = cursor.fetchone()
    
    if pending_change:
        # Update user's phone
        cursor.execute('UPDATE users SET phone = %s WHERE id = %s', 
                      (pending_change['new_phone'], pending_change['user_id']))
        
        # Mark change as approved
        cursor.execute('UPDATE pending_phone_changes SET approved = TRUE, approved_at = NOW() WHERE id = %s', 
                      (change_id,))
        
        conn.commit()
        flash('Phone change approved successfully!', 'success')
    else:
        flash('Invalid request.', 'error')
    
    cursor.close()
    conn.close()
    
    return redirect(url_for('admin_pending_phone_changes'))

@app.route('/admin/reject_phone_change/<int:change_id>', methods=['POST'])
def reject_phone_change(change_id):
    admin = base_route.require_admin()
    if not admin:
        return redirect(url_for('dashboard'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Delete the pending change
    cursor.execute('DELETE FROM pending_phone_changes WHERE id = %s', (change_id,))
    conn.commit()
    
    cursor.close()
    conn.close()
    
    flash('Phone change request rejected.', 'info')
    return redirect(url_for('admin_pending_phone_changes'))

# SocketIO event handlers
@socketio.on('join')
def on_join(data):
    item_id = data['item_id']
    user_id = data['user_id']
    room = f"item_{item_id}"
    join_room(room)
    # Emit a welcome message to the user
    emit('status', {'msg': f'You have entered the room for item {item_id}'})

@socketio.on('leave')
def on_leave(data):
    item_id = data['item_id']
    user_id = data['user_id']
    room = f"item_{item_id}"
    leave_room(room)
    # Emit a leave message to the user
    emit('status', {'msg': f'You have left the room for item {item_id}'})

@socketio.on('send_message')
def handle_send_message(data):
    item_id = data['item_id']
    user_id = data['user_id']
    message = data['message']
    username = data['username']
    
    if not message.strip():
        return
    
    # Save message to database
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Verify user can send message to this item
        cursor.execute('''
            SELECT user_id, claimed_by FROM lost_items 
            WHERE id = %s AND (user_id = %s OR claimed_by = %s)
        ''', (item_id, user_id, user_id))
        item = cursor.fetchone()
        
        if not item:
            emit('error', {'msg': 'Access denied. You must be either the owner or claimer of this item to chat.'})
            return
        
        # Insert message
        cursor.execute('''
            INSERT INTO chat_messages (item_id, sender_id, message)
            VALUES (%s, %s, %s)
        ''', (item_id, user_id, message))
        conn.commit()
        
        # Get the inserted message with username
        cursor.execute('''
            SELECT cm.*, u.username 
            FROM chat_messages cm
            JOIN users u ON cm.sender_id = u.id
            WHERE cm.id = %s
        ''', (cursor.lastrowid,))
        new_message = cursor.fetchone()
        
        # Broadcast message to room
        room = f"item_{item_id}"
        emit('receive_message', {
            'id': new_message['id'],
            'sender_id': new_message['sender_id'],
            'username': new_message['username'],
            'message': new_message['message'],
            'timestamp': new_message['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
        }, room=room)
        
    except Exception as e:
        emit('error', {'msg': f'Error sending message: {str(e)}'})
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    init_db()
    socketio.run(app, debug=True)
