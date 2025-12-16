from flask import Flask, render_template, request, redirect, url_for, flash, session
import pymysql
import os
from datetime import datetime, timedelta
import secrets
import re
from werkzeug.utils import secure_filename
from typing import Optional
from flask_socketio import SocketIO, emit, join_room, leave_room
from sms_service import send_otp_sms
app = Flask(__name__)
app.secret_key = 'your_secret_key_here'
socketio = SocketIO(app, cors_allowed_origins="*")

# Make functions available to templates
def is_admin(user):
    return user and user.get('role') in ['admin', 'main_admin']

def is_main_admin(user):
    return user and user.get('role') == 'main_admin'

app.jinja_env.globals.update(is_admin=is_admin, is_main_admin=is_main_admin)

# Database configuration for XAMPP MySQL
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'lost_and_found',
    'port': 3306,
    'charset': 'utf8mb4'
}

# Image upload configuration
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Create upload directory if it doesn't exist
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_db_connection():
    return pymysql.connect(**DB_CONFIG)

def init_db():
    # Connect without specifying database first
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create database if it doesn't exist
    cursor.execute("CREATE DATABASE IF NOT EXISTS lost_and_found")
    cursor.execute("USE lost_and_found")
    
    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            email VARCHAR(100) UNIQUE NOT NULL,
            password VARCHAR(255) NOT NULL,
            phone VARCHAR(15) UNIQUE,
            role ENUM('user', 'admin', 'main_admin') DEFAULT 'user',
            verified BOOLEAN DEFAULT FALSE,
            phone_verified BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create lost_items table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS lost_items (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT,
            item_name VARCHAR(100) NOT NULL,
            description TEXT,
            location_lost VARCHAR(100),
            date_lost DATE,
            contact_info VARCHAR(100),
            image_path VARCHAR(255),
            claimed BOOLEAN DEFAULT FALSE,
            claimed_by INT,
            claimed_at TIMESTAMP NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            recovered BOOLEAN DEFAULT FALSE,
            satisfaction_rating INT NULL,
            verified BOOLEAN DEFAULT FALSE,
            category ENUM('electronics', 'academics', 'keys', 'accessories', 'others'),
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (claimed_by) REFERENCES users(id)
        )
    ''')
    
    # Create otp_verifications table for storing OTPs
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS otp_verifications (
            id INT AUTO_INCREMENT PRIMARY KEY,
            phone VARCHAR(15),
            email VARCHAR(100),
            otp VARCHAR(6) NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX(phone),
            INDEX(email)
        )
    ''')
    
    # Add indexes if they don't exist
    try:
        cursor.execute("ALTER TABLE otp_verifications ADD INDEX idx_phone (phone)")
    except:
        pass  # Index might already exist
    
    try:
        cursor.execute("ALTER TABLE otp_verifications ADD INDEX idx_email (email)")
    except:
        pass  # Index might already exist
    
    # Create chat_messages table for item-specific chats
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INT AUTO_INCREMENT PRIMARY KEY,
            item_id INT NOT NULL,
            sender_id INT NOT NULL,
            message TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (item_id) REFERENCES lost_items(id),
            FOREIGN KEY (sender_id) REFERENCES users(id)
        )
    ''')
    
    conn.commit()
    cursor.close()
    conn.close()

# Helper functions
def is_logged_in():
    return 'user_id' in session

def get_current_user():
    if not is_logged_in():
        return None
    
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute('SELECT * FROM users WHERE id = %s', (session['user_id'],))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    return user

def is_admin(user):
    return user and user['role'] in ['admin', 'main_admin']

# These functions are defined globally above and added to Jinja environment

# Routes
@app.route('/')
def index():
    # Get filter parameters
    category_filter = request.args.get('category', '')
    location_filter = request.args.get('location', '')
    
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    
    # Build query with filters
    query = '''
        SELECT li.*, u.username as poster_name, c.username as claimed_by_username
        FROM lost_items li 
        JOIN users u ON li.user_id = u.id 
        LEFT JOIN users c ON li.claimed_by = c.id
        WHERE li.claimed = FALSE AND li.verified = TRUE
    '''
    
    params = []
    
    # Add category filter if provided
    if category_filter:
        query += " AND li.category = %s"
        params.append(category_filter)
    
    # Add location filter if provided (case-insensitive)
    if location_filter:
        query += " AND UPPER(li.location_lost) LIKE UPPER(%s)"
        params.append(f"%{location_filter}%")
    
    query += " ORDER BY li.created_at DESC"
    
    cursor.execute(query, params)
    lost_items = cursor.fetchall()
    cursor.close()
    conn.close()
    
    # Get distinct categories and locations for filter dropdowns
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT category FROM lost_items WHERE category IS NOT NULL")
    categories = [row[0] for row in cursor.fetchall()]
    
    cursor.execute("SELECT DISTINCT location_lost FROM lost_items WHERE location_lost IS NOT NULL")
    locations = [row[0] for row in cursor.fetchall()]
    
    cursor.close()
    conn.close()
    
    return render_template('index.html', items=lost_items, user=get_current_user(), 
                          is_admin=is_admin, is_main_admin=is_main_admin,
                          category_filter=category_filter, location_filter=location_filter,
                          categories=categories, locations=locations)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        phone_digits = request.form['phone']
        
        # Prepend +91 to the phone number
        phone = f"+91{phone_digits}"
        
        # Validate phone number format (must be exactly 10 digits)
        if not re.match(r'^\d{10}$', phone_digits):
            flash('Please enter a valid 10-digit Indian mobile number', 'error')
            return render_template('register.html', is_admin=is_admin, is_main_admin=is_main_admin)        
        if password != confirm_password:
            flash('Passwords do not match!', 'error')
            return render_template('register.html', is_admin=is_admin, is_main_admin=is_main_admin)
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Check if phone already exists
            cursor.execute("SELECT id FROM users WHERE phone = %s", (phone,))
            if cursor.fetchone():
                flash('Phone number already registered!', 'error')
                cursor.close()
                conn.close()
                return render_template('register.html', is_admin=is_admin, is_main_admin=is_main_admin)
            
            # Check if user is admin to set verification status
            is_admin_user = False
            cursor.execute("SELECT COUNT(*) FROM users WHERE username != 'admin'")
            user_count = cursor.fetchone()[0]
            if user_count == 0:
                # If no non-admin users exist, make first user main admin
                role = 'main_admin'
                is_admin_user = True
            else:
                role = 'student'
            
            # Insert user with role and verification status
            # Note: User is not verified by admin until phone is verified
            cursor.execute('INSERT INTO users (username, email, password, phone, role, verified) VALUES (%s, %s, %s, %s, %s, %s)',
                         (username, email, password, phone, role, False))
            conn.commit()
            cursor.close()
            conn.close()
            
            # Generate and store OTP
            otp = generate_otp()
            store_otp(phone, otp)
            
            # Store user info in session for OTP verification
            session['pending_registration'] = {
                'username': username,
                'email': email,
                'phone': phone,
                'password': password,
                'role': role,
                'user_id': cursor.lastrowid if hasattr(cursor, 'lastrowid') else None
            }
            
            flash(f'OTP sent to {phone}. Please verify your phone number.', 'success')
            return redirect(url_for('verify_phone'))
        except pymysql.IntegrityError as e:
            flash('Username or email already exists!', 'error')
            return render_template('register.html', is_admin=is_admin, is_main_admin=is_main_admin)
    
    return render_template('register.html', is_admin=is_admin, is_main_admin=is_main_admin)

def generate_otp():
    """Generate a 6-digit OTP"""
    return ''.join([str(secrets.randbelow(10)) for _ in range(6)])

def store_otp(phone, otp):
    """Store OTP in database with expiration time (10 minutes) and send via SMS"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Delete any existing OTP for this phone
    cursor.execute("DELETE FROM otp_verifications WHERE phone = %s", (phone,))
    
    # Insert new OTP with expiration time
    expires_at = datetime.now() + timedelta(minutes=10)
    cursor.execute('''
        INSERT INTO otp_verifications (phone, email, otp, expires_at) 
        VALUES (%s, %s, %s, %s)
    ''', (phone, None, otp, expires_at))
    
    conn.commit()
    cursor.close()
    conn.close()
    
    # Store OTP in session for display during development
    session['current_otp'] = otp
    
    # Send OTP via SMS
    send_otp_sms(phone, otp)

def verify_otp(phone, otp):
    """Verify OTP and return True if valid, False otherwise"""
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    
    # Get OTP record
    cursor.execute('''
        SELECT * FROM otp_verifications 
        WHERE phone = %s AND otp = %s
    ''', (phone, otp))
    
    otp_record = cursor.fetchone()
    
    if not otp_record:
        cursor.close()
        conn.close()
        return False
    
    # Check if OTP is expired
    if datetime.now() > otp_record['expires_at']:
        # Delete expired OTP
        cursor.execute("DELETE FROM otp_verifications WHERE phone = %s", (phone,))
        conn.commit()
        cursor.close()
        conn.close()
        return False
    
    # Delete used OTP
    cursor.execute("DELETE FROM otp_verifications WHERE phone = %s", (phone,))
    conn.commit()
    cursor.close()
    conn.close()
    
    # Remove OTP from session
    session.pop('current_otp', None)
    
    return True

@app.route('/verify_phone', methods=['GET', 'POST'])
def verify_phone():
    if request.method == 'POST':
        otp = request.form.get('otp', '')
        
        # Check if there's a pending registration
        if 'pending_registration' not in session or not session.get('pending_registration'):
            flash('No pending registration.', 'error')
            return redirect(url_for('register'))
        
        pending_reg = session['pending_registration']
        phone = pending_reg['phone']
        
        # Check if user wants to resend OTP
        if 'resend_otp' in request.form:
            # Generate and resend OTP
            new_otp = generate_otp()
            store_otp(phone, new_otp)
            flash(f'New OTP sent to {phone}.', 'success')
            return render_template('verify_phone.html', is_admin=is_admin, is_main_admin=is_main_admin)
        
        # Verify OTP
        if verify_otp(phone, otp):
            # Update user as phone verified
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Update user's phone verification status
            cursor.execute("UPDATE users SET phone_verified = TRUE WHERE phone = %s", (phone,))
            conn.commit()
            cursor.close()
            conn.close()
            
            # Remove pending registration from session
            session.pop('pending_registration', None)
            
            flash('Phone number verified successfully! Your account is now pending admin verification.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Invalid or expired OTP! Please try again.', 'error')
            return render_template('verify_phone.html', is_admin=is_admin, is_main_admin=is_main_admin)
    
    # Check if there's a pending registration
    if 'pending_registration' not in session or not session.get('pending_registration'):
        flash('No pending registration.', 'info')
        return redirect(url_for('register'))
    
    return render_template('verify_phone.html', is_admin=is_admin, is_main_admin=is_main_admin)
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Get the identifier (could be username, email, or phone)
        identifier = request.form.get('identifier') or request.form.get('username')
        password = request.form['password']
        
        # Print debug information
        print(f"Login attempt - Identifier: {identifier}, Password: {password}")
        
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        # Check if identifier is phone number, email, or username
        if identifier:
            if '@' in identifier:
                # Email login
                cursor.execute('SELECT * FROM users WHERE email = %s AND password = %s',
                               (identifier, password))
            elif identifier.isdigit() and len(identifier) >= 10:
                # Phone login
                cursor.execute('SELECT * FROM users WHERE phone = %s AND password = %s',
                               (identifier, password))
            else:
                # Username login
                cursor.execute('SELECT * FROM users WHERE username = %s AND password = %s',
                               (identifier, password))
            
            user = cursor.fetchone()
            cursor.close()
            conn.close()
            
            print(f"User found: {user}")  # Debug print
            
            if user:
                # Check if user is verified (except for main admin)
                if user['role'] == 'main_admin' or user['verified']:
                    session['user_id'] = user['id']
                    flash('Logged in successfully!', 'success')
                    return redirect(url_for('dashboard'))
                else:
                    flash('Your account is pending verification by an administrator.', 'info')
                    return render_template('login.html', is_admin=is_admin, is_main_admin=is_main_admin)
            else:
                flash('Invalid credentials!', 'error')
                print("Invalid credentials - user not found or password mismatch")
        else:
            flash('Please enter your username, email, or phone number.', 'error')
    
    return render_template('login.html', is_admin=is_admin, is_main_admin=is_main_admin)

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        phone = request.form.get('phone', '').strip()
        
        if not phone:
            flash('Please enter your phone number.', 'error')
            return render_template('forgot_password.html')
        
        # Validate phone number format (10 digits)
        if not re.match(r'^[0-9]{10}$', phone):
            flash('Please enter a valid 10-digit phone number.', 'error')
            return render_template('forgot_password.html')
        
        # Format phone number with +91 prefix
        formatted_phone = f"+91{phone}"
        
        # Check if user exists with this phone number
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute('SELECT * FROM users WHERE phone = %s', (formatted_phone,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not user:
            flash('No account found with that phone number.', 'error')
            return render_template('forgot_password.html')
        
        # Store user info in session for next steps
        session['reset_user_id'] = user['id']
        session['reset_phone'] = formatted_phone
        
        # Generate and send OTP
        otp = generate_otp()
        store_otp(formatted_phone, otp)
        flash(f'OTP sent to your phone {formatted_phone}', 'success')
        
        return redirect(url_for('verify_forgot_password_otp'))
    
    return render_template('forgot_password.html', is_admin=is_admin, is_main_admin=is_main_admin)

@app.route('/verify_forgot_password_otp', methods=['GET', 'POST'])
def verify_forgot_password_otp():
    if 'reset_user_id' not in session:
        flash('Session expired. Please start over.', 'error')
        return redirect(url_for('forgot_password'))
    
    if request.method == 'POST':
        otp = request.form.get('otp', '').strip()
        
        if not otp:
            flash('Please enter the OTP.', 'error')
            return render_template('verify_forgot_password_otp.html')
        
        # Get phone number from session
        phone = session['reset_phone']
        
        # Verify OTP
        if verify_otp(phone, otp):
            session['otp_verified'] = True
            flash('OTP verified successfully. You can now reset your password.', 'success')
            return redirect(url_for('reset_forgot_password'))
        else:
            flash('Invalid or expired OTP. Please try again.', 'error')
    
    return render_template('verify_forgot_password_otp.html', is_admin=is_admin, is_main_admin=is_main_admin)

@app.route('/reset_forgot_password', methods=['GET', 'POST'])
def reset_forgot_password():
    if 'reset_user_id' not in session or not session.get('otp_verified'):
        flash('Access denied. Please verify OTP first.', 'error')
        return redirect(url_for('forgot_password'))
    
    if request.method == 'POST':
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        if not password or not confirm_password:
            flash('Please fill in all fields.', 'error')
            return render_template('reset_forgot_password.html')
        
        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template('reset_forgot_password.html')
        
        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'error')
            return render_template('reset_forgot_password.html')
        
        # Update password in database
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Hash the password
        import hashlib
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        
        cursor.execute('UPDATE users SET password = %s WHERE id = %s', (hashed_password, session['reset_user_id']))
        conn.commit()
        cursor.close()
        conn.close()
        
        # Clear session
        session.pop('reset_user_id', None)
        session.pop('reset_phone', None)
        session.pop('otp_verified', None)
        
        flash('Password reset successfully. You can now log in with your new password.', 'success')
        return redirect(url_for('login'))
    
    return render_template('reset_forgot_password.html', is_admin=is_admin, is_main_admin=is_main_admin)

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    if not is_logged_in():
        flash('Please log in to access the dashboard.', 'error')
        return redirect(url_for('login'))
    
    user = get_current_user()
    if user is None:
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    
    # Get items posted by the user
    cursor.execute('''
        SELECT * FROM lost_items 
        WHERE user_id = %s 
        ORDER BY created_at DESC
    ''', (user['id'],))
    my_items = cursor.fetchall()
    
    # Get items claimed by the user
    cursor.execute('''
        SELECT li.*, u.username as poster_name, c.username as claimed_by_username
        FROM lost_items li 
        JOIN users u ON li.user_id = u.id 
        LEFT JOIN users c ON li.claimed_by = c.id
        WHERE li.claimed_by = %s 
        ORDER BY li.claimed_at DESC
    ''', (user['id'],))
    claimed_items = cursor.fetchall()
    
    # If user is admin, also get unverified users and items
    unverified_users = []
    unverified_items = []
    all_users = []
    all_items = []
    if is_admin(user):
        cursor.execute("SELECT * FROM users WHERE verified = FALSE AND role = 'student'")
        unverified_users = cursor.fetchall()
        
        cursor.execute('''
            SELECT li.*, u.username as poster_name, c.username as claimed_by_username
            FROM lost_items li 
            JOIN users u ON li.user_id = u.id 
            LEFT JOIN users c ON li.claimed_by = c.id
            WHERE li.verified = FALSE
        ''')
        unverified_items = cursor.fetchall()
        
    # If user is main admin, also get all users and items
    if is_main_admin(user):
        cursor.execute("SELECT * FROM users ORDER BY role, username")
        all_users = cursor.fetchall()
        
        cursor.execute('''
            SELECT li.*, u.username as poster_name, c.username as claimed_by_username
            FROM lost_items li 
            JOIN users u ON li.user_id = u.id 
            LEFT JOIN users c ON li.claimed_by = c.id
            ORDER BY li.created_at DESC
        ''')
        all_items = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('dashboard.html', user=user, my_items=my_items, claimed_items=claimed_items, 
                          unverified_users=unverified_users, unverified_items=unverified_items,
                          all_users=all_users, all_items=all_items, is_admin=is_admin, is_main_admin=is_main_admin)

@app.route('/post_item', methods=['GET', 'POST'])
def post_item():
    if not is_logged_in():
        flash('Please log in to post a lost item.', 'error')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        item_name = request.form['item_name']
        description = request.form['description']
        location_lost = request.form['location_lost'].upper()  # Convert to uppercase
        date_lost = request.form['date_lost']
        contact_info = request.form['contact_info']
        category = request.form['category']
        
        # Validate mandatory fields
        if not item_name or not location_lost or not category:
            flash('Item name, location, and category are required!', 'error')
            return render_template('post_item.html', user=get_current_user(), is_admin=is_admin, is_main_admin=is_main_admin)
        
        # Handle image upload
        image_path = None
        if 'item_image' in request.files:
            file = request.files['item_image']
            if file and file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(file.filename)  # type: ignore
                # Add timestamp to filename to make it unique
                filename = str(int(datetime.timestamp(datetime.now()))) + '_' + filename
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                image_path = 'uploads/' + filename
        elif not request.files.get('item_image'):
            # Image is not provided
            pass
        else:
            flash('Please upload a valid image file (png, jpg, jpeg, gif)!', 'error')
            return render_template('post_item.html', user=get_current_user(), is_admin=is_admin, is_main_admin=is_main_admin)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if user is admin to set verification status
        user = get_current_user()
        verified = is_admin(user)
        
        cursor.execute('''
            INSERT INTO lost_items (user_id, item_name, description, location_lost, date_lost, contact_info, image_path, verified, category)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (session['user_id'], item_name, description, location_lost, date_lost, contact_info, image_path, verified, category))
        conn.commit()
        cursor.close()
        conn.close()
        
        flash('Lost item posted successfully!', 'success')
        return redirect(url_for('index'))
    
    return render_template('post_item.html', user=get_current_user(), is_admin=is_admin, is_main_admin=is_main_admin)

@app.route('/claim_item/<int:item_id>')
def claim_item(item_id):
    if not is_logged_in():
        flash('Please log in to claim an item.', 'error')
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute('SELECT * FROM lost_items WHERE id = %s', (item_id,))
    item = cursor.fetchone()
    
    if not item:
        flash('Item not found!', 'error')
        cursor.close()
        conn.close()
        return redirect(url_for('index'))
    
    if item['claimed']:
        flash('This item has already been claimed!', 'error')
        cursor.close()
        conn.close()
        return redirect(url_for('index'))
    
    # Update item as claimed
    cursor.execute('''
        UPDATE lost_items 
        SET claimed = TRUE, claimed_by = %s, claimed_at = CURRENT_TIMESTAMP 
        WHERE id = %s
    ''', (session['user_id'], item_id))
    
    # Get claimer username for notifications
    cursor.execute('SELECT username FROM users WHERE id = %s', (session['user_id'],))
    claimer = cursor.fetchone()
    claimer_username = claimer['username'] if claimer else 'Unknown'
    conn.commit()
    cursor.close()
    conn.close()
    
    flash(f'Item claimed successfully! Please contact the owner using the provided information. You can now chat with the owner.', 'success')
    return redirect(url_for('index'))

@app.route('/item/<int:item_id>')
def item_detail(item_id):
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute('''
        SELECT li.*, u.username as poster_name, c.username as claimed_by_username
        FROM lost_items li 
        JOIN users u ON li.user_id = u.id 
        LEFT JOIN users c ON li.claimed_by = c.id
        WHERE li.id = %s
    ''', (item_id,))
    item = cursor.fetchone()
    
    if not item:
        flash('Item not found!', 'error')
        cursor.close()
        conn.close()
        return redirect(url_for('index'))
    
    cursor.close()
    conn.close()
    return render_template('item_detail.html', item=item, user=get_current_user(), is_admin=is_admin, is_main_admin=is_main_admin)

@app.route('/mark_recovered/<int:item_id>', methods=['POST'])
def mark_recovered(item_id):
    if not is_logged_in():
        flash('Please log in to perform this action.', 'error')
        return redirect(url_for('login'))
    
    user = get_current_user()
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    
    # Check if the user owns this item
    cursor.execute('SELECT * FROM lost_items WHERE id = %s AND user_id = %s', (item_id, user['id']))
    item = cursor.fetchone()
    
    if not item:
        flash('Item not found or you do not have permission to modify it.', 'error')
        cursor.close()
        conn.close()
        return redirect(url_for('dashboard'))
    
    # Mark item as recovered
    cursor.execute('UPDATE lost_items SET recovered = TRUE WHERE id = %s', (item_id,))
    conn.commit()
    cursor.close()
    conn.close()
    
    # Emit WebSocket event for real-time update
    socketio.emit('item_recovered', {'item_id': item_id, 'user_id': user['id']}, room=f"user_{user['id']}")
    
    flash('Item marked as recovered!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/rate_satisfaction/<int:item_id>', methods=['POST'])
def rate_satisfaction(item_id):
    if not is_logged_in():
        flash('Please log in to perform this action.', 'error')
        return redirect(url_for('login'))
    
    rating = int(request.form.get('rating', 0))
    if rating < 1 or rating > 5:
        flash('Invalid rating. Please select a rating between 1 and 5.', 'error')
        return redirect(url_for('dashboard'))
    
    user = get_current_user()
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    
    # Check if the user owns this item and it's claimed
    cursor.execute('SELECT * FROM lost_items WHERE id = %s AND user_id = %s AND claimed = TRUE', (item_id, user['id']))
    item = cursor.fetchone()
    
    if not item:
        flash('Item not found or you do not have permission to rate it.', 'error')
        cursor.close()
        conn.close()
        return redirect(url_for('dashboard'))
    
    # Update satisfaction rating
    cursor.execute('UPDATE lost_items SET satisfaction_rating = %s WHERE id = %s', (rating, item_id))
    conn.commit()
    cursor.close()
    conn.close()
    
    # Emit WebSocket event for real-time update
    socketio.emit('satisfaction_rated', {'item_id': item_id, 'rating': rating, 'user_id': user['id']}, room=f"user_{user['id']}")
    
    flash('Thank you for your feedback!', 'success')
    return redirect(url_for('dashboard'))

# Admin verification routes
@app.route('/admin/verify_user/<int:user_id>', methods=['POST'])
def verify_user(user_id):
    user = get_current_user()
    if not user or not is_admin(user):
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard'))
    
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    
    # Check if user has verified their phone number
    cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))
    target_user = cursor.fetchone()
    
    if not target_user:
        flash('User not found.', 'error')
        cursor.close()
        conn.close()
        return redirect(url_for('dashboard'))
    
    # Only verify users who have verified their phone numbers
    if not target_user['phone_verified']:
        flash('Cannot verify user: Phone number not verified.', 'error')
        cursor.close()
        conn.close()
        return redirect(url_for('dashboard'))
    
    # Proceed with verification
    cursor.execute('UPDATE users SET verified = TRUE WHERE id = %s', (user_id,))
    conn.commit()
    cursor.close()
    conn.close()
    
    flash('User verified successfully.', 'success')
    return redirect(url_for('dashboard'))

@app.route('/admin/reject_user/<int:user_id>', methods=['POST'])
def reject_user(user_id):
    user = get_current_user()
    if not user or not is_admin(user):
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM users WHERE id = %s', (user_id,))
    conn.commit()
    cursor.close()
    conn.close()
    
    flash('User registration rejected.', 'success')
    return redirect(url_for('dashboard'))

@app.route('/admin/verify_item/<int:item_id>', methods=['POST'])
def verify_item(item_id):
    user = get_current_user()
    if not user or not is_admin(user):
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE lost_items SET verified = TRUE WHERE id = %s', (item_id,))
    conn.commit()
    cursor.close()
    conn.close()
    
    flash('Item verified successfully.', 'success')
    return redirect(url_for('dashboard'))

@app.route('/admin/reject_item/<int:item_id>', methods=['POST'])
def reject_item(item_id):
    user = get_current_user()
    if not user or not is_admin(user):
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM lost_items WHERE id = %s', (item_id,))
    conn.commit()
    cursor.close()
    conn.close()
    
    flash('Item rejected.', 'success')
    return redirect(url_for('dashboard'))

# Chat routes
@app.route('/chat/<int:item_id>')
def chat(item_id):
    if not is_logged_in():
        flash('Please log in to access the chat.', 'error')
        return redirect(url_for('login'))
    
    user = get_current_user()
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    
    # Get item details
    cursor.execute('''
        SELECT li.*, u.username as poster_name, c.username as claimed_by_username
        FROM lost_items li 
        JOIN users u ON li.user_id = u.id 
        LEFT JOIN users c ON li.claimed_by = c.id
        WHERE li.id = %s
    ''', (item_id,))
    item = cursor.fetchone()
    
    if not item:
        flash('Item not found.', 'error')
        cursor.close()
        conn.close()
        return redirect(url_for('index'))
    
    # Check if user can access chat (owner or claimer)
    if user['id'] != item['user_id'] and user['id'] != item['claimed_by']:
        flash('Access denied.', 'error')
        cursor.close()
        conn.close()
        return redirect(url_for('index'))
    
    # Get chat messages
    cursor.execute('''
        SELECT m.*, u.username as sender_name 
        FROM messages m 
        JOIN users u ON m.sender_id = u.id 
        WHERE m.item_id = %s 
        ORDER BY m.created_at ASC
    ''', (item_id,))
    messages = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('chat.html', user=user, item=item, messages=messages, is_admin=is_admin, is_main_admin=is_main_admin)

@app.route('/send_message/<int:item_id>', methods=['POST'])
def send_message(item_id):
    if not is_logged_in():
        flash('Please log in to send messages.', 'error')
        return redirect(url_for('login'))
    
    user = get_current_user()
    message = request.form['message']
    
    if not message.strip():
        flash('Message cannot be empty.', 'error')
        return redirect(url_for('chat', item_id=item_id))
    
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    
    # Get item details
    cursor.execute('SELECT * FROM lost_items WHERE id = %s', (item_id,))
    item = cursor.fetchone()
    
    if not item:
        flash('Item not found.', 'error')
        cursor.close()
        conn.close()
        return redirect(url_for('index'))
    
    # Check if user can send message (owner or claimer)
    if user['id'] != item['user_id'] and user['id'] != item['claimed_by']:
        flash('Access denied.', 'error')
        cursor.close()
        conn.close()
        return redirect(url_for('index'))
    
    # Determine receiver
    receiver_id = item['user_id'] if user['id'] == item['claimed_by'] else item['claimed_by']
    
    # Insert message
    cursor.execute('''
        INSERT INTO messages (item_id, sender_id, receiver_id, message) 
        VALUES (%s, %s, %s, %s)
    ''', (item_id, user['id'], receiver_id, message))
    conn.commit()
    
    # Get the inserted message with sender name for real-time update
    cursor.execute('''
        SELECT m.*, u.username as sender_name 
        FROM messages m 
        JOIN users u ON m.sender_id = u.id 
        WHERE m.id = %s
    ''', (cursor.lastrowid,))
    new_message = cursor.fetchone()
    
    cursor.close()
    conn.close()
    
    # Convert datetime objects to strings for JSON serialization
    if new_message and 'created_at' in new_message and new_message['created_at']:
        new_message['created_at'] = new_message['created_at'].isoformat()
    
    # Emit real-time message event to both users
    socketio.emit('new_message', new_message, room=f"user_{user['id']}")
    socketio.emit('new_message', new_message, room=f"user_{receiver_id}")
    
    # Also emit to main admin for monitoring (if main admin is not one of the participants)
    # First, get main admin user ID
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT id FROM users WHERE role = 'main_admin' LIMIT 1")
    main_admin = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if main_admin and main_admin['id'] != user['id'] and main_admin['id'] != receiver_id:
        socketio.emit('new_message', new_message, room=f"user_{main_admin['id']}")
    
    # If it's an AJAX request, return success response
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return '', 200
    
    return redirect(url_for('chat', item_id=item_id))

# Main admin routes
@app.route('/admin/promote/<int:user_id>', methods=['POST'])
def promote_admin(user_id):
    user = get_current_user()
    if not user or not is_main_admin(user):
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET role = %s WHERE id = %s', ('admin', user_id))
    conn.commit()
    cursor.close()
    conn.close()
    
    flash('User promoted to admin.', 'success')
    return redirect(url_for('dashboard'))

@app.route('/admin/demote/<int:user_id>', methods=['POST'])
def demote_admin(user_id):
    user = get_current_user()
    if not user or not is_main_admin(user):
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET role = %s WHERE id = %s', ('student', user_id))
    conn.commit()
    cursor.close()
    conn.close()
    
    flash('Admin demoted to student.', 'success')
    return redirect(url_for('dashboard'))

@app.route('/admin/remove_user/<int:user_id>', methods=['POST'])
def remove_user(user_id):
    user = get_current_user()
    if not user or not is_main_admin(user):
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # First, unclaim any items claimed by this user
        cursor.execute('UPDATE lost_items SET claimed = FALSE, claimed_by = NULL, claimed_at = NULL WHERE claimed_by = %s', (user_id,))
        
        # Delete any messages sent by this user
        cursor.execute('DELETE FROM messages WHERE sender_id = %s', (user_id,))
        
        # Delete any messages received by this user
        cursor.execute('DELETE FROM messages WHERE receiver_id = %s', (user_id,))
        
        # Delete the user
        cursor.execute('DELETE FROM users WHERE id = %s', (user_id,))
        conn.commit()
        
        flash('User removed successfully.', 'success')
    except pymysql.IntegrityError as e:
        conn.rollback()
        flash('Could not remove user due to database constraints. Please ensure all related items and messages are handled first.', 'error')
    except Exception as e:
        conn.rollback()
        flash('An error occurred while removing the user.', 'error')
    finally:
        cursor.close()
        conn.close()
    
    return redirect(url_for('dashboard'))

@app.route('/admin/remove_item/<int:item_id>', methods=['POST'])
def remove_item(item_id):
    user = get_current_user()
    if not user or not is_main_admin(user):
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # First, delete any messages associated with this item
        cursor.execute('DELETE FROM messages WHERE item_id = %s', (item_id,))
        
        # Then delete the item
        cursor.execute('DELETE FROM lost_items WHERE id = %s', (item_id,))
        conn.commit()
        
        flash('Item removed successfully.', 'success')
    except pymysql.IntegrityError as e:
        conn.rollback()
        flash('Could not remove item due to database constraints. Please ensure all related messages are handled first.', 'error')
    except Exception as e:
        conn.rollback()
        flash('An error occurred while removing the item.', 'error')
    finally:
        cursor.close()
        conn.close()
    
    return redirect(url_for('dashboard'))

# Admin chat monitoring route
@app.route('/admin/monitor_chats')
def monitor_chats():
    user = get_current_user()
    if not user or not is_main_admin(user):
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard'))
    
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    
    # Get all claimed items with their chat messages
    cursor.execute('''
        SELECT li.*, u.username as poster_name, c.username as claimed_by_username
        FROM lost_items li 
        JOIN users u ON li.user_id = u.id 
        LEFT JOIN users c ON li.claimed_by = c.id
        WHERE li.claimed = TRUE
        ORDER BY li.claimed_at DESC
    ''')
    claimed_items = cursor.fetchall()
    
    # Get recent messages for each claimed item
    for item in claimed_items:
        cursor.execute('''
            SELECT m.*, u.username as sender_name 
            FROM messages m 
            JOIN users u ON m.sender_id = u.id 
            WHERE m.item_id = %s 
            ORDER BY m.created_at DESC 
            LIMIT 10
        ''', (item['id'],))
        item['messages'] = cursor.fetchall()
        
        # Convert datetime objects to strings for JSON serialization
        for message in item['messages']:
            if 'created_at' in message and message['created_at']:
                message['created_at'] = message['created_at'].isoformat()
    
    cursor.close()
    conn.close()
    
    return render_template('monitor_chats.html', user=user, claimed_items=claimed_items, 
                          is_admin=is_admin, is_main_admin=is_main_admin)

@socketio.on('connect')
def handle_connect():
    if 'user_id' in session:
        join_room(f"user_{session['user_id']}")
        print(f"User {session['user_id']} connected and joined room")

@socketio.on('disconnect')
def handle_disconnect():
    if 'user_id' in session:
        leave_room(f"user_{session['user_id']}")
        print(f"User {session['user_id']} disconnected and left room")

if __name__ == '__main__':
    init_db()
    socketio.run(app, debug=True)
