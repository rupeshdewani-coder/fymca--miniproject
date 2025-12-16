from flask import render_template, request, redirect, url_for, flash, session
from models.user import User
from utils.otp import generate_otp, store_otp, verify_otp
from models.database import get_db_connection
import re
import hashlib
import pymysql.cursors

def register():
    """Handle user registration"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        phone = request.form.get('phone', '').strip()
        
        # Validation
        if not username or not email or not password or not phone:
            flash('All fields are required.', 'error')
            return render_template('register.html')
        
        # Validate email format
        if not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
            flash('Please enter a valid email address.', 'error')
            return render_template('register.html')
        
        # Validate phone format (10 digits)
        if not re.match(r'^[0-9]{10}$', phone):
            flash('Please enter a valid 10-digit phone number.', 'error')
            return render_template('register.html')
        
        # Format phone with +91 prefix
        formatted_phone = f"+91{phone}"
        
        # Check if user already exists
        if User.get_by_email(email):
            flash('Email address already registered.', 'error')
            return render_template('register.html')
        
        if User.get_by_phone(formatted_phone):
            flash('Phone number already registered.', 'error')
            return render_template('register.html')
        
        if User.get_by_username(username):
            flash('Username already taken.', 'error')
            return render_template('register.html')
        
        # Hash password
        hashed_password = User.hash_password(password)
        
        # Check if this is the first user (main admin)
        all_users = User.get_all()
        if not all_users:
            # First user becomes main admin
            user = User(
                username=username,
                email=email,
                password=hashed_password,
                phone=formatted_phone,
                phone_verified=1,  # Main admin is auto phone verified
                role='main_admin',
                verified=1  # Main admin is auto verified
            )
            user.save()
            flash('Registration completed successfully! You are now the main administrator.', 'success')
            return redirect(url_for('login'))
        else:
            # Regular user registration
            user = User(
                username=username,
                email=email,
                password=hashed_password,
                phone=formatted_phone,
                phone_verified=0,  # Students need phone verification
                role='student',
                verified=0  # Students need admin verification
            )
            user.save()
            
            # Store registration info in session for phone verification
            session['pending_registration'] = {
                'username': username,
                'email': email,
                'password': password,  # Store plain password temporarily for verification
                'phone': formatted_phone,
                'role': 'student'
            }
            
            # Generate and send OTP
            otp = generate_otp()
            store_otp(phone=formatted_phone, otp=otp)
            session['current_otp'] = otp  # Store in session for development display
            
            flash('Registration completed! Verification pending admin approval.', 'success')
            return redirect(url_for('verify_phone'))
    
    return render_template('register.html')

def login():
    """Handle user login"""
    if request.method == 'POST':
        # Get the identifier (email or phone only, removed username login)
        identifier = request.form.get('identifier') or request.form.get('username')
        password = request.form['password']
        
        # Print debug information
        print(f"Login attempt - Identifier: {identifier}, Password: {password}")
        
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        # Check if identifier is phone number or email (removed username login)
        if identifier:
            # Hash the password for comparison
            hashed_password = hashlib.sha256(password.encode()).hexdigest()
            
            if '@' in identifier:
                # Email login
                cursor.execute('SELECT * FROM users WHERE email = %s AND password = %s',
                               (identifier, hashed_password))
            elif identifier.isdigit() and len(identifier) >= 10:
                # Phone login (without country code)
                cursor.execute('SELECT * FROM users WHERE phone = %s AND password = %s',
                               (f"+91{identifier}", hashed_password))
            elif identifier.startswith('+91') and identifier[3:].isdigit() and len(identifier[3:]) >= 10:
                # Phone login (with country code)
                cursor.execute('SELECT * FROM users WHERE phone = %s AND password = %s',
                               (identifier, hashed_password))
            elif identifier.startswith('91') and identifier[2:].isdigit() and len(identifier[2:]) >= 10:
                # Phone login (with 91 prefix but without +)
                cursor.execute('SELECT * FROM users WHERE phone = %s AND password = %s',
                               (f"+{identifier}", hashed_password))
            else:
                # Invalid identifier format
                flash('Please enter a valid email or phone number.', 'error')
                cursor.close()
                conn.close()
                return render_template('login.html')
            
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
                    return render_template('login.html')
            else:
                flash('Invalid credentials!', 'error')
                print("Invalid credentials - user not found or password mismatch")
        else:
            flash('Please enter your email or phone number.', 'error')
    
    return render_template('login.html')