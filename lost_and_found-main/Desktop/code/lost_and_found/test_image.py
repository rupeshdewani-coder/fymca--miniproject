import os
from flask import Flask, url_for

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads'

# Test the path
with app.test_request_context():
    # Test what the template would generate
    test_path = os.path.join('uploads', 'test_image.png')
    url = url_for('static', filename=test_path)
    print(f"Test path: {test_path}")
    print(f"Generated URL: {url}")
    
    # Check if file exists
    full_path = os.path.join(app.config['UPLOAD_FOLDER'], 'test_image.png')
    print(f"Full file path: {full_path}")
    print(f"File exists: {os.path.exists(full_path)}")