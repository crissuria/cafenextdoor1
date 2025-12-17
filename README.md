# Cafe Next Door - Flask Web Application

A simple web application for a coffee shop to showcase menu items, manage inventory, and handle customer contact inquiries.

## Features

- **Home Page**: Welcome page with cafe information
- **Menu Page**: Displays all menu items from SQLite database
- **Contact Form**: Allows customers to send messages (saved to database)
- **Admin Authentication**: Secure login system for admin access
- **Admin Dashboard**: Central hub for managing cafe operations
- **Menu Management**: Full CRUD operations (Create, Read, Update, Delete) for menu items
- **Message Viewing**: Admin can view all customer messages from contact form

## Installation

### Development Setup

1. Install Python 3.8 or higher
2. Create a virtual environment (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Create `.env` file from `env.example`:
   ```bash
   cp env.example .env
   # Edit .env with your configuration
   ```
5. Generate a secret key:
   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```
   Add it to your `.env` file as `SECRET_KEY`

## Running the Application

### Development Mode

1. Run the Flask application:
   ```bash
   python app.py
   ```

2. Open your browser and navigate to:
   ```
   http://localhost:5000
   ```

### Production Deployment

For production deployment, see `DEPLOYMENT.md` for detailed instructions.

Quick start with Gunicorn:
```bash
gunicorn wsgi:application --bind 0.0.0.0:5000
```

**Important:** Before deploying to production:
- Review `PRODUCTION_CHECKLIST.md`
- Set all required environment variables in `.env`
- Change default admin password
- Configure SSL/HTTPS
- Set up database backups

## Project Structure

```
project/
│ app.py                 # Main Flask application
│ requirements.txt       # Python dependencies
│ README.md             # This file
├── templates/           # HTML templates
│   base.html
│   index.html
│   menu.html
│   contact.html
│   admin_add.html
├── static/             # Static files (CSS, JS, images)
│   ├── css/
│   │   style.css
│   └── js/
│       main.js
└── database/           # SQLite database
    cafe.db
```

## Database

The application uses SQLite database (`database/cafe.db`) to store:
- Menu items
- Admin users (for authentication)
- Contact messages

The database is automatically initialized and seeded with sample data on first run. A default admin user is created with credentials: `admin` / `admin123`.

## Routes

- `/` - Home page
- `/menu` - Menu page (displays all items)
- `/contact` - Contact form page
- `/login` - Admin login page
- `/admin` - Admin dashboard (requires login)
- `/admin/menu` - Manage menu items (view, edit, delete)
- `/admin/add` - Add new menu item
- `/admin/edit/<id>` - Edit menu item
- `/admin/messages` - View contact messages

## Admin Access

**Default Admin Credentials (Development Only):**
- Username: `admin`
- Password: `admin123`

⚠️ **CRITICAL SECURITY WARNING:** 
- **NEVER use default credentials in production!**
- Change the admin password immediately after first login
- Use the admin panel to update the password
- The default password is only for initial setup

## Production Deployment

This application is production-ready. Before deploying:

1. **Review Security Checklist**: See `PRODUCTION_CHECKLIST.md`
2. **Follow Deployment Guide**: See `DEPLOYMENT.md` for step-by-step instructions
3. **Configure Environment**: Set all variables in `.env` file
4. **Change Default Credentials**: Update admin password immediately

### Key Production Files

- `wsgi.py` - WSGI entry point for production servers
- `DEPLOYMENT.md` - Complete deployment guide
- `PRODUCTION_CHECKLIST.md` - Pre-deployment checklist
- `env.example` - Environment variables template
- `.gitignore` - Excludes sensitive files from version control

## Technologies Used

- Python 3.8+
- Flask 3.0.0
- SQLite3
- Gunicorn (production WSGI server)
- Flask-Mail (email notifications)
- ReportLab (PDF generation)
- HTML5/CSS3/JavaScript

## License

This project is created for educational purposes.

