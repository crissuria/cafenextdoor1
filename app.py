"""
Cafe Next Door - Flask Web Application
A simple web system for showcasing menu, managing items, and contact information.
"""

from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_mail import Mail, Message
import sqlite3
import os
from datetime import datetime, timedelta
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'cafe_next_door_secret_key_2024'

# Email configuration - sends to cafe email
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'True').lower() in ['true', '1', 'yes']
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', 'kalititilaokk@gmail.com')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', '')  # Set via environment variable
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', 'kalititilaokk@gmail.com')
app.config['CAFE_EMAIL'] = 'kalititilaokk@gmail.com'  # Cafe's email address

# Initialize Flask-Mail
mail = Mail(app)

# Database configuration
DATABASE_DIR = 'database'
DATABASE_PATH = os.path.join(DATABASE_DIR, 'cafe.db')

# File upload configuration
UPLOAD_FOLDER = 'static/images/menu'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

def allowed_file(filename):
    """Check if file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def init_database():
    """Initialize the database and create tables if they don't exist."""
    try:
        # Create database directory if it doesn't exist
        os.makedirs(DATABASE_DIR, exist_ok=True)
        
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
    except Exception as e:
        print(f"Error initializing database directory: {str(e)}")
        raise
    
    # Create menu_items table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS menu_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            price REAL NOT NULL,
            category TEXT NOT NULL,
            image_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create users table for admin authentication
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create contact_messages table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS contact_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            message TEXT NOT NULL,
            archived INTEGER DEFAULT 0,
            ip_address TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create rate_limiting table for spam protection
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS rate_limiting (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip_address TEXT NOT NULL,
            email TEXT,
            submission_count INTEGER DEFAULT 1,
            last_submission TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Add archived column if it doesn't exist (for existing databases)
    try:
        cursor.execute('ALTER TABLE contact_messages ADD COLUMN archived INTEGER DEFAULT 0')
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    # Add ip_address column if it doesn't exist (for existing databases)
    try:
        cursor.execute('ALTER TABLE contact_messages ADD COLUMN ip_address TEXT')
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    # Check if database is empty and seed it
    cursor.execute('SELECT COUNT(*) FROM menu_items')
    count = cursor.fetchone()[0]
    
    if count == 0:
        seed_database(cursor)
    
    # Create default admin user if it doesn't exist
    cursor.execute('SELECT COUNT(*) FROM users')
    user_count = cursor.fetchone()[0]
    
    if user_count == 0:
        # Default admin credentials: username='admin', password='admin123'
        # In production, change this password immediately!
        default_password = generate_password_hash('admin123')
        cursor.execute('''
            INSERT INTO users (username, password_hash)
            VALUES (?, ?)
        ''', ('admin', default_password))
    
    conn.commit()
    conn.close()

def seed_database(cursor):
    """Seed the database with initial menu items."""
    menu_items = [
        ('Espresso', 'Strong and bold Italian coffee', 2.50, 'Hot Drinks', 'https://images.unsplash.com/photo-1510591509098-f4fdc6d0ff04?w=400&h=300&fit=crop'),
        ('Cappuccino', 'Espresso with steamed milk and foam', 3.50, 'Hot Drinks', 'https://images.unsplash.com/photo-1572442388796-11668a67e53d?w=400&h=300&fit=crop'),
        ('Latte', 'Smooth espresso with steamed milk', 3.75, 'Hot Drinks', 'https://images.unsplash.com/photo-1461023058943-07fcbe16d735?w=400&h=300&fit=crop'),
        ('Americano', 'Espresso with hot water', 2.75, 'Hot Drinks', 'https://images.unsplash.com/photo-1509042239860-f550ce710b93?w=400&h=300&fit=crop'),
        ('Iced Coffee', 'Cold brewed coffee over ice', 3.25, 'Cold Drinks', 'https://images.unsplash.com/photo-1517487881594-2787fef5ebf7?w=400&h=300&fit=crop'),
        ('Frappuccino', 'Blended coffee with ice and cream', 4.50, 'Cold Drinks', 'https://images.unsplash.com/photo-1572490122747-3968b75cc699?w=400&h=300&fit=crop'),
        ('Croissant', 'Buttery French pastry', 2.00, 'Pastries', 'https://images.unsplash.com/photo-1555507036-ab1f4038808a?w=400&h=300&fit=crop'),
        ('Blueberry Muffin', 'Fresh baked with blueberries', 2.50, 'Pastries', 'https://images.unsplash.com/photo-1607958996333-41aef7caefaa?w=400&h=300&fit=crop'),
        ('Chocolate Cake', 'Rich chocolate layer cake', 4.00, 'Desserts', 'https://images.unsplash.com/photo-1578985545062-69928b1d9587?w=400&h=300&fit=crop'),
        ('Cheesecake', 'Creamy New York style cheesecake', 4.50, 'Desserts', 'https://images.unsplash.com/photo-1524351199678-94160358e893?w=400&h=300&fit=crop'),
    ]
    
    cursor.executemany('''
        INSERT INTO menu_items (name, description, price, category, image_url)
        VALUES (?, ?, ?, ?, ?)
    ''', menu_items)

def get_db_connection():
    """Get a database connection."""
    try:
        # Ensure database directory exists
        os.makedirs(DATABASE_DIR, exist_ok=True)
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        print(f"Error connecting to database: {str(e)}")
        raise

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    """Handle 404 errors."""
    return render_template('error.html', error_code=404, error_message='Page not found'), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    print(f"Internal server error: {str(error)}")
    return render_template('error.html', error_code=500, error_message='Internal server error. Please try again later.'), 500

@app.errorhandler(Exception)
def handle_exception(e):
    """Handle all other exceptions."""
    print(f"Unhandled exception: {str(e)}")
    return render_template('error.html', error_code=500, error_message='An unexpected error occurred. Please try again later.'), 500

@app.route('/')
def index():
    """Home page route."""
    try:
        return render_template('index.html')
    except Exception as e:
        print(f"Error in index route: {str(e)}")
        raise

@app.route('/menu')
def menu():
    """Menu page route - displays all menu items."""
    try:
        conn = get_db_connection()
        rows = conn.execute('SELECT * FROM menu_items ORDER BY category, name').fetchall()
        conn.close()
        # Convert Row objects to dictionaries and group by category
        items = [dict(row) for row in rows]
        
        # Group items by category
        categories = {}
        for item in items:
            category = item['category']
            if category not in categories:
                categories[category] = []
            categories[category].append(item)
        
        return render_template('menu.html', categories=categories)
    except Exception as e:
        print(f"Error in menu route: {str(e)}")
        raise

def get_client_ip():
    """Get the client's IP address."""
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    return request.remote_addr

def check_rate_limit(ip_address, email, message):
    """Check if the user has exceeded rate limits."""
    conn = get_db_connection()
    
    # Check IP-based rate limiting (max 3 messages per hour)
    one_hour_ago = datetime.now() - timedelta(hours=1)
    ip_submissions = conn.execute('''
        SELECT COUNT(*) FROM contact_messages 
        WHERE ip_address = ? AND created_at > ?
    ''', (ip_address, one_hour_ago.strftime('%Y-%m-%d %H:%M:%S'))).fetchone()[0]
    
    if ip_submissions >= 3:
        conn.close()
        return False, 'Too many messages sent. Please wait an hour before sending another message.'
    
    # Check email-based rate limiting (max 2 messages per hour)
    if email:
        email_submissions = conn.execute('''
            SELECT COUNT(*) FROM contact_messages 
            WHERE email = ? AND created_at > ?
        ''', (email, one_hour_ago.strftime('%Y-%m-%d %H:%M:%S'))).fetchone()[0]
        
        if email_submissions >= 2:
            conn.close()
            return False, 'Too many messages from this email. Please wait an hour before sending another message.'
    
    conn.close()
    return True, None

def delete_duplicate_messages(email, message):
    """Delete older duplicate messages, keeping only the most recent one.
    This function should be called AFTER inserting a new message."""
    conn = get_db_connection()
    
    # Check for duplicates within the last 24 hours (same email + same message content)
    one_day_ago = datetime.now() - timedelta(hours=24)
    
    # Find all duplicate messages (ordered by most recent first)
    duplicates = conn.execute('''
        SELECT id, created_at FROM contact_messages 
        WHERE email = ? AND message = ? AND created_at > ?
        ORDER BY created_at DESC
    ''', (email, message, one_day_ago.strftime('%Y-%m-%d %H:%M:%S'))).fetchall()
    
    # If there are duplicates, delete all except the most recent one
    if len(duplicates) > 1:  # More than one means we have duplicates
        # Keep the most recent (first in DESC order), delete the rest
        duplicate_ids = [row['id'] for row in duplicates[1:]]  # Skip the first (most recent)
        
        if duplicate_ids:
            placeholders = ','.join(['?'] * len(duplicate_ids))
            conn.execute(f'''
                DELETE FROM contact_messages 
                WHERE id IN ({placeholders})
            ''', duplicate_ids)
            conn.commit()
            deleted_count = len(duplicate_ids)
            conn.close()
            return deleted_count
    
    conn.close()
    return 0

def send_contact_email_to_cafe(name, email, message):
    """Send contact form submission to the cafe's email address."""
    # Only send email if MAIL_PASSWORD is configured
    if not app.config['MAIL_PASSWORD']:
        print("WARNING: MAIL_PASSWORD not configured. Email will not be sent.")
        print("To enable email, set the MAIL_PASSWORD environment variable.")
        return
    
    try:
        subject = f'New Contact Message from {name} - Cafe Next Door'
        body = f'''
A new message has been received through the Cafe Next Door contact form.

From: {name}
Email: {email}
Date: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

Message:
{message}

---
This is an automated message from the Cafe Next Door website.
Please reply directly to {email} to respond to this inquiry.
'''
        
        msg = Message(
            subject=subject,
            recipients=[app.config['CAFE_EMAIL']],  # Send to cafe's email
            body=body,
            reply_to=email  # Set reply-to to customer's email for easy response
        )
        
        mail.send(msg)
        print(f"Email sent successfully to {app.config['CAFE_EMAIL']}")
    except Exception as e:
        print(f"ERROR sending email: {str(e)}")
        raise e

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    """Contact page route - handles contact form submission."""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        message = request.form.get('message', '').strip()
        honeypot = request.form.get('website', '')  # Honeypot field
        
        # Honeypot check - if filled, it's likely a bot
        if honeypot:
            flash('Spam detected. Your message was not sent.', 'error')
            return render_template('contact.html')
        
        # Validate form data
        if not name or not email or not message:
            flash('Please fill in all fields.', 'error')
            return render_template('contact.html')
        
        # Basic email validation
        if '@' not in email or '.' not in email.split('@')[-1]:
            flash('Please enter a valid email address.', 'error')
            return render_template('contact.html')
        
        # Get client IP address
        ip_address = get_client_ip()
        
        # Check rate limits
        allowed, error_message = check_rate_limit(ip_address, email, message)
        if not allowed:
            flash(error_message, 'error')
            return render_template('contact.html')
        
        # Save message to database first
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO contact_messages (name, email, message, ip_address)
            VALUES (?, ?, ?, ?)
        ''', (name, email, message, ip_address))
        conn.commit()
        conn.close()
        
        # After inserting, check for and delete duplicate messages (keep only the most recent)
        deleted_count = delete_duplicate_messages(email, message)
        
        # Send email to cafe
        try:
            send_contact_email_to_cafe(name, email, message)
        except Exception as e:
            # Log error but don't fail the request
            print(f"Error sending email: {str(e)}")
            # Email sending failed, but message is still saved to database
        
        if deleted_count > 0:
            flash(f'Thank you, {name}! Your message has been received. {deleted_count} duplicate message(s) were automatically removed.', 'success')
        else:
            flash(f'Thank you, {name}! Your message has been received. We will get back to you soon.', 'success')
        return redirect(url_for('contact'))
    
    return render_template('contact.html')

# Authentication decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page route."""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            flash('Please enter both username and password.', 'error')
            return render_template('login.html')
        
        conn = get_db_connection()
        user = conn.execute(
            'SELECT * FROM users WHERE username = ?', (username,)
        ).fetchone()
        conn.close()
        
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            flash(f'Welcome back, {username}!', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid username or password.', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Logout route."""
    session.clear()
    flash('You have been logged out successfully.', 'success')
    return redirect(url_for('index'))

@app.route('/admin', methods=['GET'])
@login_required
def admin_dashboard():
    """Admin dashboard - main admin page."""
    return render_template('admin_dashboard.html')

@app.route('/admin/menu', methods=['GET'])
@login_required
def admin_menu():
    """Admin menu management page - view all menu items."""
    conn = get_db_connection()
    rows = conn.execute('SELECT * FROM menu_items ORDER BY category, name').fetchall()
    conn.close()
    items = [dict(row) for row in rows]
    return render_template('admin_menu.html', items=items)

@app.route('/admin/add', methods=['GET', 'POST'])
@login_required
def admin_add():
    """Admin page route - allows adding new menu items."""
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        price = request.form.get('price')
        category = request.form.get('category')
        image_url = request.form.get('image_url', '')
        
        # Validate form data
        if not name or not price or not category:
            flash('Please fill in all required fields (name, price, category).', 'error')
            return render_template('admin_add.html')
        
        try:
            price = float(price)
        except ValueError:
            flash('Please enter a valid price.', 'error')
            return render_template('admin_add.html')
        
        # Handle file upload
        if 'image_file' in request.files:
            file = request.files['image_file']
            if file and file.filename != '' and allowed_file(file.filename):
                # Create upload directory if it doesn't exist
                os.makedirs(UPLOAD_FOLDER, exist_ok=True)
                
                # Generate secure filename
                filename = secure_filename(file.filename)
                # Add timestamp to make filename unique
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                name_part = secure_filename(name).replace(' ', '_')
                file_ext = filename.rsplit('.', 1)[1].lower()
                unique_filename = f"{name_part}_{timestamp}.{file_ext}"
                
                filepath = os.path.join(UPLOAD_FOLDER, unique_filename)
                file.save(filepath)
                image_url = url_for('static', filename=f'images/menu/{unique_filename}')
        
        # Insert into database
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO menu_items (name, description, price, category, image_url)
            VALUES (?, ?, ?, ?, ?)
        ''', (name, description, price, category, image_url))
        conn.commit()
        conn.close()
        
        flash(f'Menu item "{name}" has been added successfully!', 'success')
        return redirect(url_for('admin_menu'))
    
    return render_template('admin_add.html')

@app.route('/admin/edit/<int:item_id>', methods=['GET', 'POST'])
@login_required
def admin_edit(item_id):
    """Admin page route - allows editing menu items."""
    conn = get_db_connection()
    
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        price = request.form.get('price')
        category = request.form.get('category')
        image_url = request.form.get('image_url', '')
        
        # Validate form data
        if not name or not price or not category:
            flash('Please fill in all required fields (name, price, category).', 'error')
            item = conn.execute('SELECT * FROM menu_items WHERE id = ?', (item_id,)).fetchone()
            conn.close()
            return render_template('admin_edit.html', item=dict(item))
        
        try:
            price = float(price)
        except ValueError:
            flash('Please enter a valid price.', 'error')
            item = conn.execute('SELECT * FROM menu_items WHERE id = ?', (item_id,)).fetchone()
            conn.close()
            return render_template('admin_edit.html', item=dict(item))
        
        # Handle file upload
        if 'image_file' in request.files:
            file = request.files['image_file']
            if file and file.filename != '' and allowed_file(file.filename):
                # Create upload directory if it doesn't exist
                os.makedirs(UPLOAD_FOLDER, exist_ok=True)
                
                # Generate secure filename
                filename = secure_filename(file.filename)
                # Add timestamp to make filename unique
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                name_part = secure_filename(name).replace(' ', '_')
                file_ext = filename.rsplit('.', 1)[1].lower()
                unique_filename = f"{name_part}_{timestamp}.{file_ext}"
                
                filepath = os.path.join(UPLOAD_FOLDER, unique_filename)
                file.save(filepath)
                image_url = url_for('static', filename=f'images/menu/{unique_filename}')
        
        # Update database
        conn.execute('''
            UPDATE menu_items 
            SET name = ?, description = ?, price = ?, category = ?, image_url = ?
            WHERE id = ?
        ''', (name, description, price, category, image_url, item_id))
        conn.commit()
        conn.close()
        
        flash(f'Menu item "{name}" has been updated successfully!', 'success')
        return redirect(url_for('admin_menu'))
    
    item = conn.execute('SELECT * FROM menu_items WHERE id = ?', (item_id,)).fetchone()
    conn.close()
    
    if not item:
        flash('Menu item not found.', 'error')
        return redirect(url_for('admin_menu'))
    
    return render_template('admin_edit.html', item=dict(item))

@app.route('/admin/delete/<int:item_id>', methods=['POST'])
@login_required
def admin_delete(item_id):
    """Admin route - deletes a menu item."""
    conn = get_db_connection()
    item = conn.execute('SELECT * FROM menu_items WHERE id = ?', (item_id,)).fetchone()
    
    if item:
        conn.execute('DELETE FROM menu_items WHERE id = ?', (item_id,))
        conn.commit()
        flash(f'Menu item "{item["name"]}" has been deleted successfully!', 'success')
    else:
        flash('Menu item not found.', 'error')
    
    conn.close()
    return redirect(url_for('admin_menu'))

@app.route('/admin/messages', methods=['GET'])
@login_required
def admin_messages():
    """Admin page to view contact messages."""
    sort_order = request.args.get('sort', 'desc')  # 'asc' or 'desc'
    filter_type = request.args.get('filter', 'active')  # 'active', 'archived', or 'all'
    order_by = 'ASC' if sort_order == 'asc' else 'DESC'
    
    conn = get_db_connection()
    
    # Build query based on filter
    if filter_type == 'active':
        query = f'SELECT * FROM contact_messages WHERE archived = 0 ORDER BY created_at {order_by}'
    elif filter_type == 'archived':
        query = f'SELECT * FROM contact_messages WHERE archived = 1 ORDER BY created_at {order_by}'
    else:  # 'all'
        query = f'SELECT * FROM contact_messages ORDER BY created_at {order_by}'
    
    rows = conn.execute(query).fetchall()
    conn.close()
    messages = [dict(row) for row in rows]
    return render_template('admin_messages.html', messages=messages, sort_order=sort_order, filter_type=filter_type)

@app.route('/admin/messages/archive/<int:message_id>', methods=['POST'])
@login_required
def admin_archive_message(message_id):
    """Admin route - archives a contact message."""
    conn = get_db_connection()
    message = conn.execute('SELECT * FROM contact_messages WHERE id = ?', (message_id,)).fetchone()
    
    if message:
        conn.execute('UPDATE contact_messages SET archived = 1 WHERE id = ?', (message_id,))
        conn.commit()
        flash(f'Message from {message["name"]} has been archived!', 'success')
    else:
        flash('Message not found.', 'error')
    
    conn.close()
    return redirect(request.referrer or url_for('admin_messages'))

@app.route('/admin/messages/unarchive/<int:message_id>', methods=['POST'])
@login_required
def admin_unarchive_message(message_id):
    """Admin route - unarchives a contact message."""
    conn = get_db_connection()
    message = conn.execute('SELECT * FROM contact_messages WHERE id = ?', (message_id,)).fetchone()
    
    if message:
        conn.execute('UPDATE contact_messages SET archived = 0 WHERE id = ?', (message_id,))
        conn.commit()
        flash(f'Message from {message["name"]} has been unarchived!', 'success')
    else:
        flash('Message not found.', 'error')
    
    conn.close()
    return redirect(request.referrer or url_for('admin_messages'))

@app.route('/admin/messages/delete/<int:message_id>', methods=['POST'])
@login_required
def admin_delete_message(message_id):
    """Admin route - deletes a contact message."""
    conn = get_db_connection()
    message = conn.execute('SELECT * FROM contact_messages WHERE id = ?', (message_id,)).fetchone()
    
    if message:
        conn.execute('DELETE FROM contact_messages WHERE id = ?', (message_id,))
        conn.commit()
        flash(f'Message from {message["name"]} has been deleted successfully!', 'success')
    else:
        flash('Message not found.', 'error')
    
    conn.close()
    return redirect(request.referrer or url_for('admin_messages'))

# Missing routes referenced in templates - add stubs to prevent errors
@app.route('/cart')
@app.route('/view_cart')
def view_cart():
    """Cart page - placeholder for future implementation."""
    flash('Cart functionality is coming soon!', 'info')
    return redirect(url_for('menu'))

@app.route('/customer/login', methods=['GET', 'POST'])
def customer_login():
    """Customer login page - redirects to admin login for now."""
    return redirect(url_for('login'))

@app.route('/customer/logout')
def customer_logout():
    """Customer logout - redirects to standard logout."""
    return redirect(url_for('logout'))

@app.route('/customer/profile')
def customer_profile():
    """Customer profile page - placeholder."""
    flash('Customer profile functionality is coming soon!', 'info')
    return redirect(url_for('index'))

@app.route('/customer/notifications')
def customer_notifications():
    """Customer notifications page - placeholder."""
    flash('Notifications functionality is coming soon!', 'info')
    return redirect(url_for('index'))

@app.route('/gift-cards')
@app.route('/gift_cards')
def gift_cards():
    """Gift cards page - placeholder."""
    flash('Gift cards functionality is coming soon!', 'info')
    return redirect(url_for('index'))

@app.route('/favorites')
@app.route('/view_favorites')
def view_favorites():
    """Favorites page - placeholder."""
    flash('Favorites functionality is coming soon!', 'info')
    return redirect(url_for('menu'))

@app.route('/loyalty')
@app.route('/loyalty_program')
def loyalty_program():
    """Loyalty program page - placeholder."""
    flash('Loyalty program functionality is coming soon!', 'info')
    return redirect(url_for('index'))

@app.route('/newsletter/subscribe', methods=['POST'])
def newsletter_subscribe():
    """Newsletter subscription - placeholder."""
    flash('Thank you for your interest! Newsletter functionality is coming soon.', 'info')
    return redirect(url_for('index'))

# Health check route for Render
@app.route('/health')
def health_check():
    """Health check endpoint for monitoring."""
    try:
        # Test database connection
        conn = get_db_connection()
        conn.execute('SELECT 1').fetchone()
        conn.close()
        return {'status': 'healthy', 'database': 'connected'}, 200
    except Exception as e:
        return {'status': 'unhealthy', 'error': str(e)}, 500

if __name__ == '__main__':
    try:
        init_database()
        port = int(os.environ.get('PORT', 5000))
        app.run(debug=False, host='0.0.0.0', port=port)
    except Exception as e:
        print(f"Error starting application: {str(e)}")
        raise

