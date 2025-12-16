from flask import render_template, request, redirect, url_for, flash, session
from routes.base_route import BaseRoute
from models.user import User
from models.database import get_db_connection
from utils.otp import generate_otp, store_otp, verify_otp
import re
import os
from datetime import datetime
from werkzeug.utils import secure_filename

class UserRoute(BaseRoute):
    """User related routes"""
    
    def __init__(self, app):
        super().__init__()
        self.app = app
    
    def profile(self):
        """Handle user profile"""
        user = self.require_login()
        if not user:
            return redirect(url_for('login'))
        
        if request.method == 'POST':
            # Handle profile updates
            username = request.form.get('username', '').strip()
            profile_image = request.files.get('profile_image')
            
            # Update username
            if username and username != user.username:
                conn = get_db_connection()
                cursor = conn.cursor()
                try:
                    cursor.execute('UPDATE users SET username = %s WHERE id = %s', (username, user.id))
                    conn.commit()
                    flash('Username updated successfully!', 'success')
                except Exception as e:
                    flash('Error updating username. Please try again.', 'error')
                finally:
                    cursor.close()
                    conn.close()
            
            # Update profile image
            if profile_image and self.allowed_file(profile_image.filename):
                filename = secure_filename(profile_image.filename)
                # Add user ID and timestamp to filename to avoid conflicts
                name, ext = os.path.splitext(filename)
                filename = f"profile_{user.id}_{int(datetime.now().timestamp())}{ext}"
                image_path = os.path.join('uploads/profiles', filename)
                
                # Create profiles directory if it doesn't exist
                profiles_dir = os.path.join(self.app.config['UPLOAD_FOLDER'], 'profiles')
                if not os.path.exists(profiles_dir):
                    os.makedirs(profiles_dir)
                
                profile_image.save(os.path.join(profiles_dir, filename))
                
                # Update database
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute('UPDATE users SET profile_image = %s WHERE id = %s', (f"uploads/profiles/{filename}", user.id))
                conn.commit()
                cursor.close()
                conn.close()
                
                flash('Profile image updated successfully!', 'success')
            
            # Refresh user data
            user = self.get_current_user()
        
        return render_template('profile.html', user=user)
    
    def change_email(self):
        """Handle email change request"""
        user = self.require_login()
        if not user:
            return redirect(url_for('login'))
        
        if request.method == 'POST':
            new_email = request.form.get('new_email', '').strip().lower()
            
            # Validation
            if not new_email:
                flash('Email address is required.', 'error')
                return render_template('change_email.html')
            
            # Validate email format
            if not re.match(r'^[^@]+@[^@]+\.[^@]+$', new_email):
                flash('Please enter a valid email address.', 'error')
                return render_template('change_email.html')
            
            # Check if email is already taken
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM users WHERE email = %s', (new_email,))
            existing_user = cursor.fetchone()
            cursor.close()
            conn.close()
            
            if existing_user:
                flash('This email address is already registered.', 'error')
                return render_template('change_email.html')
            
            # Store the new email in session for verification
            session['pending_email_change'] = {
                'user_id': user.id,
                'new_email': new_email
            }
            
            # Generate and send OTP
            otp = generate_otp()
            store_otp(email=new_email, otp=otp)
            session['current_otp'] = otp  # Store in session for development display
            
            flash('OTP sent to your new email address.', 'success')
            return redirect(url_for('verify_email_change_otp'))
        
        return render_template('change_email.html')
    
    def verify_email_change_otp(self):
        """Handle email change OTP verification"""
        # Check if user initiated email change
        if 'pending_email_change' not in session:
            flash('No email change request found.', 'error')
            return redirect(url_for('profile'))
        
        user = self.require_login()
        if not user:
            return redirect(url_for('login'))
        
        pending_change = session['pending_email_change']
        new_email = pending_change['new_email']
        
        if request.method == 'POST':
            # Check if user wants to resend OTP
            if 'resend_otp' in request.form:
                # Generate and resend OTP
                new_otp = generate_otp()
                store_otp(email=new_email, otp=new_otp)
                session['current_otp'] = new_otp  # Store in session for development display
                flash('New OTP sent to your email address.', 'success')
                return redirect(url_for('verify_email_change_otp'))
            
            # Handle OTP verification
            entered_otp = request.form.get('otp', '').strip()
            
            if not entered_otp:
                flash('Please enter the OTP.', 'error')
                return render_template('verify_email_change_otp.html', user=user)
            
            # Verify OTP
            if verify_otp(email=new_email, otp=entered_otp):
                # Store the pending email change in database for admin approval
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO pending_email_changes (user_id, new_email) 
                    VALUES (%s, %s)
                ''', (pending_change['user_id'], new_email))
                conn.commit()
                cursor.close()
                conn.close()
                
                # Clear session data
                session.pop('pending_email_change', None)
                session.pop('current_otp', None)
                
                flash('Email change request submitted! It will be updated once approved by an administrator.', 'success')
                return redirect(url_for('profile'))
            else:
                flash('Invalid OTP. Please try again.', 'error')
        
        return render_template('verify_email_change_otp.html', user=user)
    
    def change_phone(self):
        """Handle phone change request"""
        user = self.require_login()
        if not user:
            return redirect(url_for('login'))
        
        if request.method == 'POST':
            new_phone = request.form.get('new_phone', '').strip()
            
            # Validation
            if not new_phone:
                flash('Phone number is required.', 'error')
                return render_template('change_phone.html')
            
            # Validate phone format (10 digits)
            if not re.match(r'^[0-9]{10}$', new_phone):
                flash('Please enter a valid 10-digit phone number.', 'error')
                return render_template('change_phone.html')
            
            # Format phone with +91 prefix
            formatted_phone = f"+91{new_phone}"
            
            # Check if phone is already taken
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM users WHERE phone = %s', (formatted_phone,))
            existing_user = cursor.fetchone()
            cursor.close()
            conn.close()
            
            if existing_user:
                flash('This phone number is already registered.', 'error')
                return render_template('change_phone.html')
            
            # Store the new phone in session for verification
            session['pending_phone_change'] = {
                'user_id': user.id,
                'new_phone': formatted_phone
            }
            
            # Generate and send OTP
            otp = generate_otp()
            store_otp(phone=formatted_phone, otp=otp)
            session['current_otp'] = otp  # Store in session for development display
            
            flash('OTP sent to your new phone number.', 'success')
            return redirect(url_for('verify_phone_change_otp'))
        
        return render_template('change_phone.html')
    
    def verify_phone_change_otp(self):
        """Handle phone change OTP verification"""
        # Check if user initiated phone change
        if 'pending_phone_change' not in session:
            flash('No phone change request found.', 'error')
            return redirect(url_for('profile'))
        
        user = self.require_login()
        if not user:
            return redirect(url_for('login'))
        
        pending_change = session['pending_phone_change']
        new_phone = pending_change['new_phone']
        
        if request.method == 'POST':
            # Check if user wants to resend OTP
            if 'resend_otp' in request.form:
                # Generate and resend OTP
                new_otp = generate_otp()
                store_otp(phone=new_phone, otp=new_otp)
                session['current_otp'] = new_otp  # Store in session for development display
                flash('New OTP sent to your phone number.', 'success')
                return redirect(url_for('verify_phone_change_otp'))
            
            # Handle OTP verification
            entered_otp = request.form.get('otp', '').strip()
            
            if not entered_otp:
                flash('Please enter the OTP.', 'error')
                return render_template('verify_phone_change_otp.html', user=user)
            
            # Verify OTP
            if verify_otp(phone=new_phone, otp=entered_otp):
                # Store the pending phone change in database for admin approval
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO pending_phone_changes (user_id, new_phone) 
                    VALUES (%s, %s)
                ''', (pending_change['user_id'], new_phone))
                conn.commit()
                cursor.close()
                conn.close()
                
                # Clear session data
                session.pop('pending_phone_change', None)
                session.pop('current_otp', None)
                
                flash('Phone change request submitted! It will be updated once approved by an administrator.', 'success')
                return redirect(url_for('profile'))
            else:
                flash('Invalid OTP. Please try again.', 'error')
        
        return render_template('verify_phone_change_otp.html', user=user)
    
    def allowed_file(self, filename):
        """Check if file extension is allowed"""
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in self.app.config['ALLOWED_EXTENSIONS']