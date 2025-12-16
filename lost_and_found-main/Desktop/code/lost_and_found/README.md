# Lost and Found System

A web application for students to post lost items and claim found items.

## Features

- User registration and authentication
- Post lost items with details (name, description, location, date, contact info)
- Browse all unclaimed lost items
- Claim items posted by other students
- User dashboard to manage posted items and claimed items
- Responsive design using Bootstrap

## Technologies Used

- Python Flask (Web Framework)
- SQLite (Database)
- HTML/CSS/JavaScript
- Bootstrap 5 (Frontend Framework)
- Jinja2 (Template Engine)

## Installation

1. Clone or download this repository
2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

## Running the Application

1. Navigate to the project directory
2. Run the application:
   ```
   python app.py
   ```
3. Open your web browser and go to `http://localhost:5000`

## Default Admin User

- Username: admin
- Password: admin123

## Project Structure

```
lost_and_found/
│
├── app.py              # Main Flask application
├── lost_and_found.db   # SQLite database (created automatically)
├── requirements.txt    # Python dependencies
├── README.md           # This file
│
├── templates/          # HTML templates
│   ├── base.html       # Base template
│   ├── index.html      # Home page
│   ├── register.html   # User registration
│   ├── login.html      # User login
│   ├── dashboard.html  # User dashboard
│   ├── post_item.html  # Post lost item form
│   └── item_detail.html # Item details page
│
└── static/             # Static files (CSS, JS, images)
    └── uploads/        # Item images (if implemented)
```

## How to Use

1. **Register** for a new account or **Login** with existing credentials
2. **Post Lost Items** by clicking "Post Lost Item" in the navigation bar
3. **Browse Items** on the home page to see all unclaimed lost items
4. **Claim Items** by clicking the "Claim Item" button on an item
5. **Manage Items** through your dashboard:
   - View items you've posted
   - View items you've claimed

## Database Schema

The application uses SQLite with two main tables:

1. **users** - Stores user information
2. **lost_items** - Stores lost item information and claim status

## Future Enhancements

- Add image upload functionality for items
- Implement email notifications
- Add search and filter capabilities
- Implement item categories
- Add admin panel for managing users and items
- Improve UI/UX design

## License

This project is created for educational purposes as a college mini project.