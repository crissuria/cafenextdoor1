"""
Cafe Next Door - Flask Web Application
A simple web system for showcasing menu, managing items, and contact information.
"""

from flask import Flask, render_template, request, redirect, url_for, flash, session, make_response
from flask_mail import Mail, Message
import sqlite3
import os
import secrets
import csv
import io
from datetime import datetime, timedelta
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv is optional

app = Flask(__name__)

# Secret key from environment variable (required for production)
app.secret_key = os.environ.get('SECRET_KEY')
if not app.secret_key:
    # Generate a temporary key for development (NOT for production!)
    app.secret_key = secrets.token_hex(32)
    if os.environ.get('FLASK_ENV') == 'production':
        raise ValueError("SECRET_KEY environment variable must be set in production!")

# Email configuration - all from environment variables
# Gmail SMTP configuration (default for production)
# For local development with ProtonMail Bridge, override these in .env
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'True').lower() in ['true', '1', 'yes']
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', '')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', '')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', os.environ.get('MAIL_USERNAME', ''))
app.config['CAFE_EMAIL'] = os.environ.get('CAFE_EMAIL', 'cafenextdoor@protonmail.com')

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
        
        conn = sqlite3.connect(DATABASE_PATH, timeout=10.0)
        cursor = conn.cursor()
    except Exception as e:
        print(f"Error creating database directory or connection: {str(e)}")
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
            is_available INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create users table for admin authentication
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'admin',
            full_name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create promotions/discounts table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS promotions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            description TEXT,
            discount_type TEXT NOT NULL,
            discount_value REAL NOT NULL,
            min_order_amount REAL DEFAULT 0,
            max_uses INTEGER DEFAULT NULL,
            used_count INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            start_date TEXT,
            end_date TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create reviews table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            menu_item_id INTEGER NOT NULL,
            order_id INTEGER,
            rating INTEGER NOT NULL CHECK(rating >= 1 AND rating <= 5),
            comment TEXT,
            is_approved INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES customers (id),
            FOREIGN KEY (menu_item_id) REFERENCES menu_items (id),
            FOREIGN KEY (order_id) REFERENCES orders (id)
        )
    ''')
    
    # Create loyalty_points table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS loyalty_points (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            points INTEGER DEFAULT 0,
            total_earned INTEGER DEFAULT 0,
            total_redeemed INTEGER DEFAULT 0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES customers (id),
            UNIQUE(customer_id)
        )
    ''')
    
    # Create loyalty_transactions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS loyalty_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            points INTEGER NOT NULL,
            transaction_type TEXT NOT NULL,
            description TEXT,
            order_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES customers (id),
            FOREIGN KEY (order_id) REFERENCES orders (id)
        )
    ''')
    
    # Create email_verifications table (replacing phone_verifications)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS email_verifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            email TEXT NOT NULL,
            verification_code TEXT NOT NULL,
            is_verified INTEGER DEFAULT 0,
            expires_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES customers (id)
        )
    ''')
    
    # Keep phone_verifications for backward compatibility (will be deprecated)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS phone_verifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            phone TEXT NOT NULL,
            verification_code TEXT NOT NULL,
            is_verified INTEGER DEFAULT 0,
            expires_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES customers (id)
        )
    ''')
    
    # Create blacklist table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS blacklist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER,
            email TEXT,
            phone TEXT,
            reason TEXT,
            no_show_count INTEGER DEFAULT 0,
            cancelled_count INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES customers (id)
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
    
    # Create customers table for customer accounts
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            phone TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create favorites table for wishlists
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS favorites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            menu_item_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES customers (id),
            FOREIGN KEY (menu_item_id) REFERENCES menu_items (id),
            UNIQUE(customer_id, menu_item_id)
        )
    ''')
    
    # Create newsletter_subscribers table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS newsletter_subscribers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            name TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create orders table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            status TEXT DEFAULT 'pending',
            total_amount REAL NOT NULL,
            pickup_time TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES customers (id)
        )
    ''')
    
    # Create order_items table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            menu_item_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 1,
            price REAL NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orders (id),
            FOREIGN KEY (menu_item_id) REFERENCES menu_items (id)
        )
    ''')
    
    # Add archived column if it doesn't exist (for existing databases)
    try:
        cursor.execute('ALTER TABLE contact_messages ADD COLUMN archived INTEGER DEFAULT 0')
    except sqlite3.OperationalError:
        pass  # Column already exists
    try:
        cursor.execute('ALTER TABLE contact_messages ADD COLUMN replied INTEGER DEFAULT 0')
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    # Add ip_address column if it doesn't exist (for existing databases)
    try:
        cursor.execute('ALTER TABLE contact_messages ADD COLUMN ip_address TEXT')
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    # Add name column to newsletter_subscribers if it doesn't exist (for existing databases)
    try:
        cursor.execute('ALTER TABLE newsletter_subscribers ADD COLUMN name TEXT')
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    # Add role column to users table if it doesn't exist
    try:
        cursor.execute('ALTER TABLE users ADD COLUMN role TEXT DEFAULT "admin"')
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    # Add full_name column to users table if it doesn't exist
    try:
        cursor.execute('ALTER TABLE users ADD COLUMN full_name TEXT')
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    # Add is_available column to menu_items if it doesn't exist
    try:
        cursor.execute('ALTER TABLE menu_items ADD COLUMN is_available INTEGER DEFAULT 1')
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    # Add discount columns to orders table if they don't exist
    try:
        cursor.execute('ALTER TABLE orders ADD COLUMN discount_amount REAL DEFAULT 0')
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute('ALTER TABLE orders ADD COLUMN promo_code TEXT')
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute('ALTER TABLE orders ADD COLUMN payment_method TEXT')
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute('ALTER TABLE orders ADD COLUMN payment_verified INTEGER DEFAULT 0')
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute('ALTER TABLE orders ADD COLUMN payment_proof TEXT')
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute('ALTER TABLE orders ADD COLUMN confirmation_called INTEGER DEFAULT 0')
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute('ALTER TABLE customers ADD COLUMN phone_verified INTEGER DEFAULT 0')
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute('ALTER TABLE customers ADD COLUMN no_show_count INTEGER DEFAULT 0')
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute('ALTER TABLE customers ADD COLUMN cancelled_count INTEGER DEFAULT 0')
    except sqlite3.OperationalError:
        pass
    
    # Create password_reset_tokens table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS password_reset_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            token TEXT UNIQUE NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            used INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES customers (id)
        )
    ''')
    
    # Create notifications table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            order_id INTEGER,
            type TEXT NOT NULL,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            is_read INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES customers (id),
            FOREIGN KEY (order_id) REFERENCES orders (id)
        )
    ''')
    
    # Add notification preferences to customers table
    try:
        cursor.execute('ALTER TABLE customers ADD COLUMN email_notifications INTEGER DEFAULT 1')
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute('ALTER TABLE customers ADD COLUMN sms_notifications INTEGER DEFAULT 1')
    except sqlite3.OperationalError:
        pass
    
    # Create gift_cards table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS gift_cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            customer_id INTEGER,
            amount REAL NOT NULL,
            balance REAL NOT NULL,
            is_active INTEGER DEFAULT 1,
            expires_at TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES customers (id)
        )
    ''')
    
    # Create gift_card_transactions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS gift_card_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            gift_card_id INTEGER NOT NULL,
            transaction_type TEXT NOT NULL,
            amount REAL NOT NULL,
            order_id INTEGER,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (gift_card_id) REFERENCES gift_cards (id),
            FOREIGN KEY (order_id) REFERENCES orders (id)
        )
    ''')
    
    # Create vouchers table (separate from promotions)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS vouchers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            customer_id INTEGER,
            discount_type TEXT NOT NULL,
            discount_value REAL NOT NULL,
            min_order_amount REAL DEFAULT 0,
            is_used INTEGER DEFAULT 0,
            expires_at TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES customers (id)
        )
    ''')
    
    # Create ingredients/inventory table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ingredients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            unit TEXT NOT NULL,
            current_stock REAL DEFAULT 0,
            min_stock REAL DEFAULT 0,
            cost_per_unit REAL DEFAULT 0,
            supplier TEXT,
            category TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create menu_item_ingredients table (many-to-many)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS menu_item_ingredients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            menu_item_id INTEGER NOT NULL,
            ingredient_id INTEGER NOT NULL,
            quantity_required REAL NOT NULL,
            FOREIGN KEY (menu_item_id) REFERENCES menu_items (id) ON DELETE CASCADE,
            FOREIGN KEY (ingredient_id) REFERENCES ingredients (id) ON DELETE CASCADE,
            UNIQUE(menu_item_id, ingredient_id)
        )
    ''')
    
    # Create inventory_transactions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS inventory_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ingredient_id INTEGER NOT NULL,
            transaction_type TEXT NOT NULL,
            quantity REAL NOT NULL,
            order_id INTEGER,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (ingredient_id) REFERENCES ingredients (id),
            FOREIGN KEY (order_id) REFERENCES orders (id)
        )
    ''')
    
    # Check if database is empty and seed it, or update with new items
    try:
        cursor.execute('SELECT COUNT(*) FROM menu_items')
        count = cursor.fetchone()[0]
        
        if count == 0:
            # Database is empty, seed it
            seed_database(cursor)
            conn.commit()
            print("Database seeded with menu items")
        else:
            # Database has items, update existing items and add new ones
            try:
                # First, update prices/descriptions of existing items
                updated_count = update_existing_menu_items(cursor)
                if updated_count > 0:
                    print(f"Updated {updated_count} existing menu items")
                
                # Then, add any new items that don't exist
                added_count = update_menu_with_new_items(cursor)
                if added_count > 0:
                    print(f"Added {added_count} new menu items to existing database")
                
                if updated_count > 0 or added_count > 0:
                    conn.commit()
            except Exception as update_error:
                print(f"Warning: Error updating menu items: {str(update_error)}")
    except Exception as e:
        print(f"Warning: Error checking/seeding menu_items: {str(e)}")
        # Try to seed anyway
        try:
            seed_database(cursor)
            conn.commit()
        except:
            pass
    
    # Seed ingredients if empty
    try:
        cursor.execute('SELECT COUNT(*) FROM ingredients')
        ingredient_count = cursor.fetchone()[0]
        
        if ingredient_count == 0:
            seed_ingredients(cursor)
            conn.commit()
    except Exception as e:
        print(f"Warning: Error checking/seeding ingredients: {str(e)}")
        # Try to seed anyway
        try:
            seed_ingredients(cursor)
            conn.commit()
        except:
            pass
    
    # Create default admin user if it doesn't exist
    cursor.execute('SELECT COUNT(*) FROM users')
    user_count = cursor.fetchone()[0]
    
    if user_count == 0:
        # Default admin credentials: username='admin', password='admin123'
        # ⚠️ SECURITY WARNING: Change this password immediately in production!
        # Use the admin panel to change the password after first login.
        if os.environ.get('FLASK_ENV') == 'production':
            print("⚠️  WARNING: Creating default admin user with password 'admin123'")
            print("⚠️  SECURITY RISK: Change this password immediately after first login!")
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
        # Hot Drinks
        ('Espresso', 'Strong and bold Italian coffee', 105, 'Hot Drinks', 'https://images.unsplash.com/photo-1510591509098-f4fdc6d0ff04?w=800&h=600&fit=crop'),
        ('Cappuccino', 'Espresso with steamed milk and foam', 160, 'Hot Drinks', 'https://images.unsplash.com/photo-1572442388796-11668a67e53d?w=800&h=600&fit=crop'),
        ('Latte', 'Smooth espresso with steamed milk', 165, 'Hot Drinks', 'https://images.unsplash.com/photo-1461023058943-07fcbe16d735?w=800&h=600&fit=crop'),
        ('Americano', 'Espresso with hot water', 110, 'Hot Drinks', 'https://images.unsplash.com/photo-1509042239860-f550ce710b93?w=800&h=600&fit=crop'),
        ('Macchiato', 'Espresso with a dollop of foamed milk', 140, 'Hot Drinks', 'https://images.unsplash.com/photo-1517487881594-2787fef5ebf7?w=800&h=600&fit=crop'),
        ('Mocha', 'Espresso with chocolate and steamed milk', 175, 'Hot Drinks', 'https://images.unsplash.com/photo-1572490122747-3968b75cc699?w=800&h=600&fit=crop'),
        ('Flat White', 'Double espresso with microfoam milk', 170, 'Hot Drinks', 'https://images.unsplash.com/photo-1555507036-ab1f4038808a?w=800&h=600&fit=crop'),
        ('Cortado', 'Espresso with equal parts warm milk', 145, 'Hot Drinks', 'https://images.unsplash.com/photo-1607958996333-41aef7caefaa?w=800&h=600&fit=crop'),
        ('Caffe Breve', 'Espresso with half-and-half cream', 180, 'Hot Drinks', 'https://images.unsplash.com/photo-1578985545062-69928b1d9587?w=800&h=600&fit=crop'),
        ('Hot Chocolate', 'Rich and creamy chocolate drink', 135, 'Hot Drinks', 'https://images.unsplash.com/photo-1606313564200-e75d5e30476c?w=800&h=600&fit=crop'),
        ('Chai Latte', 'Spiced tea with steamed milk', 160, 'Hot Drinks', 'https://images.unsplash.com/photo-1544787219-7f47ccb76574?w=800&h=600&fit=crop'),
        ('Matcha Latte', 'Japanese green tea with steamed milk', 170, 'Hot Drinks', 'https://images.unsplash.com/photo-1517487881594-2787fef5ebf7?w=800&h=600&fit=crop'),
        ('Caramel Macchiato', 'Vanilla syrup, espresso, caramel drizzle', 190, 'Hot Drinks', 'https://images.unsplash.com/photo-1555507036-ab1f4038808a?w=800&h=600&fit=crop'),
        ('Vanilla Latte', 'Espresso with vanilla syrup and steamed milk', 170, 'Hot Drinks', 'https://images.unsplash.com/photo-1607958996333-41aef7caefaa?w=800&h=600&fit=crop'),
        ('Hazelnut Latte', 'Espresso with hazelnut syrup and milk', 170, 'Hot Drinks', 'https://images.unsplash.com/photo-1578985545062-69928b1d9587?w=800&h=600&fit=crop'),
        
        # Cold Drinks
        ('Iced Coffee', 'Cold brewed coffee over ice', 135, 'Cold Drinks', 'https://images.unsplash.com/photo-1517487881594-2787fef5ebf7?w=800&h=600&fit=crop'),
        ('Frappuccino', 'Blended coffee with ice and cream', 195, 'Cold Drinks', 'https://images.unsplash.com/photo-1572490122747-3968b75cc699?w=800&h=600&fit=crop'),
        ('Iced Latte', 'Espresso with cold milk over ice', 165, 'Cold Drinks', 'https://images.unsplash.com/photo-1461023058943-07fcbe16d735?w=800&h=600&fit=crop'),
        ('Cold Brew', 'Smooth, slow-steeped cold coffee', 150, 'Cold Drinks', 'https://images.unsplash.com/photo-1509042239860-f550ce710b93?w=800&h=600&fit=crop'),
        ('Iced Mocha', 'Espresso, chocolate, and cold milk over ice', 175, 'Cold Drinks', 'https://images.unsplash.com/photo-1510591509098-f4fdc6d0ff04?w=800&h=600&fit=crop'),
        ('Iced Caramel Macchiato', 'Vanilla, espresso, caramel, and ice', 190, 'Cold Drinks', 'https://images.unsplash.com/photo-1572442388796-11668a67e53d?w=800&h=600&fit=crop'),
        ('Iced Americano', 'Espresso with cold water over ice', 110, 'Cold Drinks', 'https://images.unsplash.com/photo-1461023058943-07fcbe16d735?w=800&h=600&fit=crop'),
        ('Nitro Cold Brew', 'Smooth, creamy cold brew on tap', 180, 'Cold Drinks', 'https://images.unsplash.com/photo-1509042239860-f550ce710b93?w=800&h=600&fit=crop'),
        ('Iced Matcha Latte', 'Japanese green tea with cold milk', 170, 'Cold Drinks', 'https://images.unsplash.com/photo-1517487881594-2787fef5ebf7?w=800&h=600&fit=crop'),
        ('Strawberry Smoothie', 'Fresh strawberries blended with yogurt', 150, 'Cold Drinks', 'https://images.unsplash.com/photo-1553530666-ba11a7da3888?w=800&h=600&fit=crop'),
        ('Mango Smoothie', 'Tropical mango blended to perfection', 150, 'Cold Drinks', 'https://images.unsplash.com/photo-1600271886742-f049cd451bba?w=800&h=600&fit=crop'),
        ('Iced Chai Latte', 'Spiced tea with cold milk over ice', 145, 'Cold Drinks', 'https://images.unsplash.com/photo-1607958996333-41aef7caefaa?w=800&h=600&fit=crop'),
        ('Lemonade', 'Freshly squeezed lemonade', 100, 'Cold Drinks', 'https://images.unsplash.com/photo-1523677011783-c91d1bbe2fdc?w=800&h=600&fit=crop'),
        ('Iced Tea', 'Refreshing iced tea', 100, 'Cold Drinks', 'https://images.unsplash.com/photo-1556679343-c7306c1976bc?w=800&h=600&fit=crop'),
        
        # Pastries
        ('Croissant', 'Buttery French pastry', 110, 'Pastries', 'https://images.unsplash.com/photo-1555507036-ab1f4038808a?w=800&h=600&fit=crop'),
        ('Blueberry Muffin', 'Fresh baked with blueberries', 130, 'Pastries', 'https://images.unsplash.com/photo-1607958996333-41aef7caefaa?w=800&h=600&fit=crop'),
        ('Chocolate Chip Muffin', 'Classic muffin with chocolate chips', 130, 'Pastries', 'https://images.unsplash.com/photo-1607958996333-41aef7caefaa?w=800&h=600&fit=crop'),
        ('Almond Croissant', 'Buttery croissant with almond filling', 150, 'Pastries', 'https://images.unsplash.com/photo-1524351199678-94160358e893?w=800&h=600&fit=crop'),
        ('Danish Pastry', 'Flaky pastry with fruit filling', 145, 'Pastries', 'https://images.unsplash.com/photo-1517487881594-2787fef5ebf7?w=800&h=600&fit=crop'),
        ('Cinnamon Roll', 'Sweet roll with cinnamon and glaze', 155, 'Pastries', 'https://images.unsplash.com/photo-1572490122747-3968b75cc699?w=800&h=600&fit=crop'),
        ('Bagel', 'Fresh New York style bagel', 105, 'Pastries', 'https://images.unsplash.com/photo-1586444248902-2f64eddc13df?w=800&h=600&fit=crop'),
        ('Scone', 'Traditional British scone with jam', 135, 'Pastries', 'https://images.unsplash.com/photo-1607958996333-41aef7caefaa?w=800&h=600&fit=crop'),
        ('Chocolate Croissant', 'Buttery croissant with chocolate', 150, 'Pastries', 'https://images.unsplash.com/photo-1578985545062-69928b1d9587?w=800&h=600&fit=crop'),
        ('Apple Turnover', 'Flaky pastry with apple filling', 150, 'Pastries', 'https://images.unsplash.com/photo-1524351199678-94160358e893?w=800&h=600&fit=crop'),
        ('Banana Bread', 'Moist homemade banana bread', 140, 'Pastries', 'https://images.unsplash.com/photo-1586444248902-2f64eddc13df?w=800&h=600&fit=crop'),
        ('Donut', 'Classic glazed donut', 100, 'Pastries', 'https://images.unsplash.com/photo-1572490122747-3968b75cc699?w=800&h=600&fit=crop'),
        
        # Desserts
        ('Chocolate Cake', 'Rich chocolate layer cake', 180, 'Desserts', 'https://images.unsplash.com/photo-1578985545062-69928b1d9587?w=800&h=600&fit=crop'),
        ('Cheesecake', 'Creamy New York style cheesecake', 195, 'Desserts', 'https://images.unsplash.com/photo-1524351199678-94160358e893?w=800&h=600&fit=crop'),
        ('Tiramisu', 'Classic Italian coffee-flavored dessert', 200, 'Desserts', 'https://images.unsplash.com/photo-1571877227200-a0d98ea607e9?w=800&h=600&fit=crop'),
        ('Brownie', 'Fudgy chocolate brownie', 120, 'Desserts', 'https://images.unsplash.com/photo-1606313564200-e75d5e30476c?w=800&h=600&fit=crop'),
        ('Chocolate Chip Cookie', 'Warm, gooey chocolate chip cookie', 100, 'Desserts', 'https://images.unsplash.com/photo-1555507036-ab1f4038808a?w=800&h=600&fit=crop'),
        ('Red Velvet Cake', 'Moist red velvet with cream cheese frosting', 190, 'Desserts', 'https://images.unsplash.com/photo-1607958996333-41aef7caefaa?w=800&h=600&fit=crop'),
        ('Carrot Cake', 'Spiced carrot cake with cream cheese', 170, 'Desserts', 'https://images.unsplash.com/photo-1578985545062-69928b1d9587?w=800&h=600&fit=crop'),
        ('Lemon Tart', 'Tangy lemon curd in buttery crust', 160, 'Desserts', 'https://images.unsplash.com/photo-1524351199678-94160358e893?w=800&h=600&fit=crop'),
        ('Chocolate Mousse', 'Light and airy chocolate mousse', 165, 'Desserts', 'https://images.unsplash.com/photo-1517487881594-2787fef5ebf7?w=800&h=600&fit=crop'),
        ('Ice Cream Sundae', 'Vanilla ice cream with toppings', 150, 'Desserts', 'https://images.unsplash.com/photo-1572490122747-3968b75cc699?w=800&h=600&fit=crop'),
        ('Apple Pie', 'Classic apple pie with flaky crust', 170, 'Desserts', 'https://images.unsplash.com/photo-1555507036-ab1f4038808a?w=800&h=600&fit=crop'),
        ('Pecan Pie', 'Rich pecan pie with caramel', 185, 'Desserts', 'https://images.unsplash.com/photo-1607958996333-41aef7caefaa?w=800&h=600&fit=crop'),
        ('Key Lime Pie', 'Tart and creamy key lime pie', 170, 'Desserts', 'https://images.unsplash.com/photo-1578985545062-69928b1d9587?w=800&h=600&fit=crop'),
        
        # Light Meals & Sandwiches
        ('Avocado Toast', 'Smashed avocado on sourdough', 175, 'Light Meals', 'https://images.unsplash.com/photo-1541519227356-08fa5d50c44d?w=800&h=600&fit=crop'),
        ('Grilled Cheese', 'Classic grilled cheese sandwich', 160, 'Light Meals', 'https://images.unsplash.com/photo-1528735602780-2552fd46c7af?w=800&h=600&fit=crop'),
        ('Turkey Sandwich', 'Sliced turkey with veggies', 190, 'Light Meals', 'https://images.unsplash.com/photo-1544025162-d76694265947?w=800&h=600&fit=crop'),
        ('Chicken Panini', 'Grilled chicken panini', 200, 'Light Meals', 'https://images.unsplash.com/photo-1555507036-ab1f4038808a?w=800&h=600&fit=crop'),
        ('Caprese Sandwich', 'Fresh mozzarella, tomato, and basil', 180, 'Light Meals', 'https://images.unsplash.com/photo-1607958996333-41aef7caefaa?w=800&h=600&fit=crop'),
        ('Quiche', 'Savory egg and cheese quiche', 170, 'Light Meals', 'https://images.unsplash.com/photo-1578985545062-69928b1d9587?w=800&h=600&fit=crop'),
        ('Caesar Salad', 'Fresh romaine with Caesar dressing', 185, 'Light Meals', 'https://images.unsplash.com/photo-1546793665-c74683f339c1?w=800&h=600&fit=crop'),
        ('Greek Salad', 'Mixed greens with feta and olives', 185, 'Light Meals', 'https://images.unsplash.com/photo-1540189549336-e6e99c3679fe?w=800&h=600&fit=crop'),
    ]
    
    cursor.executemany('''
        INSERT INTO menu_items (name, description, price, category, image_url)
        VALUES (?, ?, ?, ?, ?)
    ''', menu_items)

def update_existing_menu_items(cursor):
    """Update prices and descriptions of existing menu items to match seed data."""
    # Menu items data (same as seed_database)
    menu_items_dict = {
        # Hot Drinks
        'Espresso': ('Strong and bold Italian coffee', 105, 'Hot Drinks'),
        'Cappuccino': ('Espresso with steamed milk and foam', 160, 'Hot Drinks'),
        'Latte': ('Smooth espresso with steamed milk', 165, 'Hot Drinks'),
        'Americano': ('Espresso with hot water', 110, 'Hot Drinks'),
        'Macchiato': ('Espresso with a dollop of foamed milk', 140, 'Hot Drinks'),
        'Mocha': ('Espresso with chocolate and steamed milk', 175, 'Hot Drinks'),
        'Flat White': ('Double espresso with microfoam milk', 170, 'Hot Drinks'),
        'Cortado': ('Espresso with equal parts warm milk', 145, 'Hot Drinks'),
        'Caffe Breve': ('Espresso with half-and-half cream', 180, 'Hot Drinks'),
        'Hot Chocolate': ('Rich and creamy chocolate drink', 135, 'Hot Drinks'),
        'Chai Latte': ('Spiced tea with steamed milk', 160, 'Hot Drinks'),
        'Matcha Latte': ('Japanese green tea with steamed milk', 170, 'Hot Drinks'),
        'Caramel Macchiato': ('Vanilla syrup, espresso, caramel drizzle', 190, 'Hot Drinks'),
        'Vanilla Latte': ('Espresso with vanilla syrup and steamed milk', 170, 'Hot Drinks'),
        'Hazelnut Latte': ('Espresso with hazelnut syrup and milk', 170, 'Hot Drinks'),
        # Cold Drinks
        'Iced Coffee': ('Cold brewed coffee over ice', 135, 'Cold Drinks'),
        'Frappuccino': ('Blended coffee with ice and cream', 195, 'Cold Drinks'),
        'Iced Latte': ('Espresso with cold milk over ice', 165, 'Cold Drinks'),
        'Cold Brew': ('Smooth, slow-steeped cold coffee', 150, 'Cold Drinks'),
        'Iced Mocha': ('Espresso, chocolate, and cold milk over ice', 175, 'Cold Drinks'),
        'Iced Caramel Macchiato': ('Vanilla, espresso, caramel, and ice', 190, 'Cold Drinks'),
        'Iced Americano': ('Espresso with cold water over ice', 110, 'Cold Drinks'),
        'Nitro Cold Brew': ('Smooth, creamy cold brew on tap', 180, 'Cold Drinks'),
        'Iced Matcha Latte': ('Japanese green tea with cold milk', 170, 'Cold Drinks'),
        'Strawberry Smoothie': ('Fresh strawberries blended with yogurt', 150, 'Cold Drinks'),
        'Mango Smoothie': ('Tropical mango blended to perfection', 150, 'Cold Drinks'),
        'Iced Chai Latte': ('Spiced tea with cold milk over ice', 145, 'Cold Drinks'),
        'Lemonade': ('Freshly squeezed lemonade', 100, 'Cold Drinks'),
        'Iced Tea': ('Refreshing iced tea', 100, 'Cold Drinks'),
        # Pastries
        'Croissant': ('Buttery French pastry', 110, 'Pastries'),
        'Blueberry Muffin': ('Fresh baked with blueberries', 130, 'Pastries'),
        'Chocolate Chip Muffin': ('Classic muffin with chocolate chips', 130, 'Pastries'),
        'Almond Croissant': ('Buttery croissant with almond filling', 150, 'Pastries'),
        'Danish Pastry': ('Flaky pastry with fruit filling', 145, 'Pastries'),
        'Cinnamon Roll': ('Sweet roll with cinnamon and glaze', 155, 'Pastries'),
        'Bagel': ('Fresh New York style bagel', 105, 'Pastries'),
        'Scone': ('Traditional British scone with jam', 135, 'Pastries'),
        'Chocolate Croissant': ('Buttery croissant with chocolate', 150, 'Pastries'),
        'Apple Turnover': ('Flaky pastry with apple filling', 150, 'Pastries'),
        'Banana Bread': ('Moist homemade banana bread', 140, 'Pastries'),
        'Donut': ('Classic glazed donut', 100, 'Pastries'),
        # Desserts
        'Chocolate Cake': ('Rich chocolate layer cake', 180, 'Desserts'),
        'Cheesecake': ('Creamy New York style cheesecake', 195, 'Desserts'),
        'Tiramisu': ('Classic Italian coffee-flavored dessert', 200, 'Desserts'),
        'Brownie': ('Fudgy chocolate brownie', 120, 'Desserts'),
        'Chocolate Chip Cookie': ('Warm, gooey chocolate chip cookie', 100, 'Desserts'),
        'Red Velvet Cake': ('Moist red velvet with cream cheese frosting', 190, 'Desserts'),
        'Carrot Cake': ('Spiced carrot cake with cream cheese', 170, 'Desserts'),
        'Lemon Tart': ('Tangy lemon curd in buttery crust', 160, 'Desserts'),
        'Chocolate Mousse': ('Light and airy chocolate mousse', 165, 'Desserts'),
        'Ice Cream Sundae': ('Vanilla ice cream with toppings', 150, 'Desserts'),
        'Apple Pie': ('Classic apple pie with flaky crust', 170, 'Desserts'),
        'Pecan Pie': ('Rich pecan pie with caramel', 185, 'Desserts'),
        'Key Lime Pie': ('Tart and creamy key lime pie', 170, 'Desserts'),
        # Light Meals
        'Avocado Toast': ('Smashed avocado on sourdough', 175, 'Light Meals'),
        'Grilled Cheese': ('Classic grilled cheese sandwich', 160, 'Light Meals'),
        'Turkey Sandwich': ('Sliced turkey with veggies', 190, 'Light Meals'),
        'Chicken Panini': ('Grilled chicken panini', 200, 'Light Meals'),
        'Caprese Sandwich': ('Fresh mozzarella, tomato, and basil', 180, 'Light Meals'),
        'Quiche': ('Savory egg and cheese quiche', 170, 'Light Meals'),
        'Caesar Salad': ('Fresh romaine with Caesar dressing', 185, 'Light Meals'),
        'Greek Salad': ('Mixed greens with feta and olives', 185, 'Light Meals'),
    }
    
    updated_count = 0
    for name, (description, price, category) in menu_items_dict.items():
        cursor.execute('''
            UPDATE menu_items 
            SET description = ?, price = ?, category = ?
            WHERE name = ?
        ''', (description, price, category, name))
        if cursor.rowcount > 0:
            updated_count += 1
    
    return updated_count

def update_menu_with_new_items(cursor):
    """Add new menu items to existing database without duplicates."""
    # Get all menu items from seed_database (same as seed_database function)
    menu_items = [
        # Hot Drinks
        ('Espresso', 'Strong and bold Italian coffee', 105, 'Hot Drinks', 'https://images.unsplash.com/photo-1510591509098-f4fdc6d0ff04?w=800&h=600&fit=crop'),
        ('Cappuccino', 'Espresso with steamed milk and foam', 160, 'Hot Drinks', 'https://images.unsplash.com/photo-1572442388796-11668a67e53d?w=800&h=600&fit=crop'),
        ('Latte', 'Smooth espresso with steamed milk', 165, 'Hot Drinks', 'https://images.unsplash.com/photo-1461023058943-07fcbe16d735?w=800&h=600&fit=crop'),
        ('Americano', 'Espresso with hot water', 110, 'Hot Drinks', 'https://images.unsplash.com/photo-1509042239860-f550ce710b93?w=800&h=600&fit=crop'),
        ('Macchiato', 'Espresso with a dollop of foamed milk', 140, 'Hot Drinks', 'https://images.unsplash.com/photo-1517487881594-2787fef5ebf7?w=800&h=600&fit=crop'),
        ('Mocha', 'Espresso with chocolate and steamed milk', 175, 'Hot Drinks', 'https://images.unsplash.com/photo-1572490122747-3968b75cc699?w=800&h=600&fit=crop'),
        ('Flat White', 'Double espresso with microfoam milk', 170, 'Hot Drinks', 'https://images.unsplash.com/photo-1555507036-ab1f4038808a?w=800&h=600&fit=crop'),
        ('Cortado', 'Espresso with equal parts warm milk', 145, 'Hot Drinks', 'https://images.unsplash.com/photo-1607958996333-41aef7caefaa?w=800&h=600&fit=crop'),
        ('Caffe Breve', 'Espresso with half-and-half cream', 180, 'Hot Drinks', 'https://images.unsplash.com/photo-1578985545062-69928b1d9587?w=800&h=600&fit=crop'),
        ('Hot Chocolate', 'Rich and creamy chocolate drink', 135, 'Hot Drinks', 'https://images.unsplash.com/photo-1606313564200-e75d5e30476c?w=800&h=600&fit=crop'),
        ('Chai Latte', 'Spiced tea with steamed milk', 160, 'Hot Drinks', 'https://images.unsplash.com/photo-1544787219-7f47ccb76574?w=800&h=600&fit=crop'),
        ('Matcha Latte', 'Japanese green tea with steamed milk', 170, 'Hot Drinks', 'https://images.unsplash.com/photo-1517487881594-2787fef5ebf7?w=800&h=600&fit=crop'),
        ('Caramel Macchiato', 'Vanilla syrup, espresso, caramel drizzle', 190, 'Hot Drinks', 'https://images.unsplash.com/photo-1555507036-ab1f4038808a?w=800&h=600&fit=crop'),
        ('Vanilla Latte', 'Espresso with vanilla syrup and steamed milk', 170, 'Hot Drinks', 'https://images.unsplash.com/photo-1607958996333-41aef7caefaa?w=800&h=600&fit=crop'),
        ('Hazelnut Latte', 'Espresso with hazelnut syrup and milk', 170, 'Hot Drinks', 'https://images.unsplash.com/photo-1578985545062-69928b1d9587?w=800&h=600&fit=crop'),

        # Cold Drinks
        ('Iced Coffee', 'Cold brewed coffee over ice', 135, 'Cold Drinks', 'https://images.unsplash.com/photo-1517487881594-2787fef5ebf7?w=800&h=600&fit=crop'),
        ('Frappuccino', 'Blended coffee with ice and cream', 195, 'Cold Drinks', 'https://images.unsplash.com/photo-1572490122747-3968b75cc699?w=800&h=600&fit=crop'),
        ('Iced Latte', 'Espresso with cold milk over ice', 165, 'Cold Drinks', 'https://images.unsplash.com/photo-1461023058943-07fcbe16d735?w=800&h=600&fit=crop'),
        ('Cold Brew', 'Smooth, slow-steeped cold coffee', 150, 'Cold Drinks', 'https://images.unsplash.com/photo-1509042239860-f550ce710b93?w=800&h=600&fit=crop'),
        ('Iced Mocha', 'Espresso, chocolate, and cold milk over ice', 175, 'Cold Drinks', 'https://images.unsplash.com/photo-1510591509098-f4fdc6d0ff04?w=800&h=600&fit=crop'),
        ('Iced Caramel Macchiato', 'Vanilla, espresso, caramel, and ice', 190, 'Cold Drinks', 'https://images.unsplash.com/photo-1572442388796-11668a67e53d?w=800&h=600&fit=crop'),
        ('Iced Americano', 'Espresso with cold water over ice', 110, 'Cold Drinks', 'https://images.unsplash.com/photo-1461023058943-07fcbe16d735?w=800&h=600&fit=crop'),
        ('Nitro Cold Brew', 'Smooth, creamy cold brew on tap', 180, 'Cold Drinks', 'https://images.unsplash.com/photo-1509042239860-f550ce710b93?w=800&h=600&fit=crop'),
        ('Iced Matcha Latte', 'Japanese green tea with cold milk', 170, 'Cold Drinks', 'https://images.unsplash.com/photo-1517487881594-2787fef5ebf7?w=800&h=600&fit=crop'),
        ('Strawberry Smoothie', 'Fresh strawberries blended with yogurt', 150, 'Cold Drinks', 'https://images.unsplash.com/photo-1553530666-ba11a7da3888?w=800&h=600&fit=crop'),
        ('Mango Smoothie', 'Tropical mango blended to perfection', 150, 'Cold Drinks', 'https://images.unsplash.com/photo-1600271886742-f049cd451bba?w=800&h=600&fit=crop'),
        ('Iced Chai Latte', 'Spiced tea with cold milk over ice', 145, 'Cold Drinks', 'https://images.unsplash.com/photo-1607958996333-41aef7caefaa?w=800&h=600&fit=crop'),
        ('Lemonade', 'Freshly squeezed lemonade', 100, 'Cold Drinks', 'https://images.unsplash.com/photo-1523677011783-c91d1bbe2fdc?w=800&h=600&fit=crop'),
        ('Iced Tea', 'Refreshing iced tea', 100, 'Cold Drinks', 'https://images.unsplash.com/photo-1556679343-c7306c1976bc?w=800&h=600&fit=crop'),

        # Pastries
        ('Croissant', 'Buttery French pastry', 110, 'Pastries', 'https://images.unsplash.com/photo-1555507036-ab1f4038808a?w=800&h=600&fit=crop'),
        ('Blueberry Muffin', 'Fresh baked with blueberries', 130, 'Pastries', 'https://images.unsplash.com/photo-1607958996333-41aef7caefaa?w=800&h=600&fit=crop'),
        ('Chocolate Chip Muffin', 'Classic muffin with chocolate chips', 130, 'Pastries', 'https://images.unsplash.com/photo-1607958996333-41aef7caefaa?w=800&h=600&fit=crop'),
        ('Almond Croissant', 'Buttery croissant with almond filling', 150, 'Pastries', 'https://images.unsplash.com/photo-1524351199678-94160358e893?w=800&h=600&fit=crop'),
        ('Danish Pastry', 'Flaky pastry with fruit filling', 145, 'Pastries', 'https://images.unsplash.com/photo-1517487881594-2787fef5ebf7?w=800&h=600&fit=crop'),
        ('Cinnamon Roll', 'Sweet roll with cinnamon and glaze', 155, 'Pastries', 'https://images.unsplash.com/photo-1572490122747-3968b75cc699?w=800&h=600&fit=crop'),
        ('Bagel', 'Fresh New York style bagel', 105, 'Pastries', 'https://images.unsplash.com/photo-1586444248902-2f64eddc13df?w=800&h=600&fit=crop'),
        ('Scone', 'Traditional British scone with jam', 135, 'Pastries', 'https://images.unsplash.com/photo-1607958996333-41aef7caefaa?w=800&h=600&fit=crop'),
        ('Chocolate Croissant', 'Buttery croissant with chocolate', 150, 'Pastries', 'https://images.unsplash.com/photo-1578985545062-69928b1d9587?w=800&h=600&fit=crop'),
        ('Apple Turnover', 'Flaky pastry with apple filling', 150, 'Pastries', 'https://images.unsplash.com/photo-1524351199678-94160358e893?w=800&h=600&fit=crop'),
        ('Banana Bread', 'Moist homemade banana bread', 140, 'Pastries', 'https://images.unsplash.com/photo-1586444248902-2f64eddc13df?w=800&h=600&fit=crop'),
        ('Donut', 'Classic glazed donut', 100, 'Pastries', 'https://images.unsplash.com/photo-1572490122747-3968b75cc699?w=800&h=600&fit=crop'),

        # Desserts
        ('Chocolate Cake', 'Rich chocolate layer cake', 180, 'Desserts', 'https://images.unsplash.com/photo-1578985545062-69928b1d9587?w=800&h=600&fit=crop'),
        ('Cheesecake', 'Creamy New York style cheesecake', 195, 'Desserts', 'https://images.unsplash.com/photo-1524351199678-94160358e893?w=800&h=600&fit=crop'),
        ('Tiramisu', 'Classic Italian coffee-flavored dessert', 200, 'Desserts', 'https://images.unsplash.com/photo-1571877227200-a0d98ea607e9?w=800&h=600&fit=crop'),
        ('Brownie', 'Fudgy chocolate brownie', 120, 'Desserts', 'https://images.unsplash.com/photo-1606313564200-e75d5e30476c?w=800&h=600&fit=crop'),
        ('Chocolate Chip Cookie', 'Warm, gooey chocolate chip cookie', 100, 'Desserts', 'https://images.unsplash.com/photo-1555507036-ab1f4038808a?w=800&h=600&fit=crop'),
        ('Red Velvet Cake', 'Moist red velvet with cream cheese frosting', 190, 'Desserts', 'https://images.unsplash.com/photo-1607958996333-41aef7caefaa?w=800&h=600&fit=crop'),
        ('Carrot Cake', 'Spiced carrot cake with cream cheese', 170, 'Desserts', 'https://images.unsplash.com/photo-1578985545062-69928b1d9587?w=800&h=600&fit=crop'),
        ('Lemon Tart', 'Tangy lemon curd in buttery crust', 160, 'Desserts', 'https://images.unsplash.com/photo-1524351199678-94160358e893?w=800&h=600&fit=crop'),
        ('Chocolate Mousse', 'Light and airy chocolate mousse', 165, 'Desserts', 'https://images.unsplash.com/photo-1517487881594-2787fef5ebf7?w=800&h=600&fit=crop'),
        ('Ice Cream Sundae', 'Vanilla ice cream with toppings', 150, 'Desserts', 'https://images.unsplash.com/photo-1572490122747-3968b75cc699?w=800&h=600&fit=crop'),
        ('Apple Pie', 'Classic apple pie with flaky crust', 170, 'Desserts', 'https://images.unsplash.com/photo-1555507036-ab1f4038808a?w=800&h=600&fit=crop'),
        ('Pecan Pie', 'Rich pecan pie with caramel', 185, 'Desserts', 'https://images.unsplash.com/photo-1607958996333-41aef7caefaa?w=800&h=600&fit=crop'),
        ('Key Lime Pie', 'Tart and creamy key lime pie', 170, 'Desserts', 'https://images.unsplash.com/photo-1578985545062-69928b1d9587?w=800&h=600&fit=crop'),

        # Light Meals & Sandwiches
        ('Avocado Toast', 'Smashed avocado on sourdough', 175, 'Light Meals', 'https://images.unsplash.com/photo-1541519227356-08fa5d50c44d?w=800&h=600&fit=crop'),
        ('Grilled Cheese', 'Classic grilled cheese sandwich', 160, 'Light Meals', 'https://images.unsplash.com/photo-1528735602780-2552fd46c7af?w=800&h=600&fit=crop'),
        ('Turkey Sandwich', 'Sliced turkey with veggies', 190, 'Light Meals', 'https://images.unsplash.com/photo-1544025162-d76694265947?w=800&h=600&fit=crop'),
        ('Chicken Panini', 'Grilled chicken panini', 200, 'Light Meals', 'https://images.unsplash.com/photo-1555507036-ab1f4038808a?w=800&h=600&fit=crop'),
        ('Caprese Sandwich', 'Fresh mozzarella, tomato, and basil', 180, 'Light Meals', 'https://images.unsplash.com/photo-1607958996333-41aef7caefaa?w=800&h=600&fit=crop'),
        ('Quiche', 'Savory egg and cheese quiche', 170, 'Light Meals', 'https://images.unsplash.com/photo-1578985545062-69928b1d9587?w=800&h=600&fit=crop'),
        ('Caesar Salad', 'Fresh romaine with Caesar dressing', 185, 'Light Meals', 'https://images.unsplash.com/photo-1546793665-c74683f339c1?w=800&h=600&fit=crop'),
        ('Greek Salad', 'Mixed greens with feta and olives', 185, 'Light Meals', 'https://images.unsplash.com/photo-1540189549336-e6e99c3679fe?w=800&h=600&fit=crop'),
    ]
    
    # Get existing menu item names
    existing_items = cursor.execute('SELECT name FROM menu_items').fetchall()
    existing_names = {row[0] for row in existing_items}
    
    # Filter out items that already exist
    new_items = [item for item in menu_items if item[0] not in existing_names]
    
    if new_items:
        cursor.executemany('''
            INSERT INTO menu_items (name, description, price, category, image_url)
            VALUES (?, ?, ?, ?, ?)
        ''', new_items)
        return len(new_items)
    return 0

def seed_ingredients(cursor):
    """Seed the database with common cafe ingredients."""
    # Common cafe ingredients with initial stock
    ingredients = [
        # Coffee & Beverages
        ('Coffee Beans', 'kg', 50.0, 10.0, 500.0, 'Local Supplier', 'Beverages'),
        ('Milk', 'liter', 30.0, 5.0, 80.0, 'Dairy Supplier', 'Beverages'),
        ('Sugar', 'kg', 20.0, 5.0, 60.0, 'Local Supplier', 'Beverages'),
        ('Cream', 'liter', 15.0, 3.0, 120.0, 'Dairy Supplier', 'Beverages'),
        ('Ice', 'kg', 100.0, 20.0, 20.0, 'Ice Supplier', 'Beverages'),
        ('Water', 'liter', 200.0, 50.0, 5.0, 'Water Supplier', 'Beverages'),
        ('Chocolate Syrup', 'liter', 10.0, 2.0, 150.0, 'Beverage Supplier', 'Beverages'),
        ('Vanilla Syrup', 'liter', 10.0, 2.0, 150.0, 'Beverage Supplier', 'Beverages'),
        ('Caramel Syrup', 'liter', 8.0, 2.0, 150.0, 'Beverage Supplier', 'Beverages'),
        
        # Pastries & Desserts
        ('Flour', 'kg', 25.0, 5.0, 50.0, 'Baking Supplier', 'Baking'),
        ('Butter', 'kg', 15.0, 3.0, 200.0, 'Dairy Supplier', 'Baking'),
        ('Eggs', 'dozen', 20.0, 5.0, 80.0, 'Poultry Supplier', 'Baking'),
        ('Sugar (Baking)', 'kg', 20.0, 5.0, 60.0, 'Local Supplier', 'Baking'),
        ('Chocolate Chips', 'kg', 10.0, 2.0, 300.0, 'Baking Supplier', 'Baking'),
        ('Blueberries', 'kg', 5.0, 1.0, 400.0, 'Fruit Supplier', 'Baking'),
        ('Cream Cheese', 'kg', 8.0, 2.0, 250.0, 'Dairy Supplier', 'Baking'),
        ('Vanilla Extract', 'liter', 2.0, 0.5, 500.0, 'Baking Supplier', 'Baking'),
        ('Cocoa Powder', 'kg', 5.0, 1.0, 350.0, 'Baking Supplier', 'Baking'),
        
        # Toppings & Extras
        ('Whipped Cream', 'can', 30.0, 10.0, 100.0, 'Dairy Supplier', 'Toppings'),
        ('Cinnamon', 'kg', 2.0, 0.5, 400.0, 'Spice Supplier', 'Toppings'),
        ('Nutmeg', 'kg', 1.0, 0.25, 500.0, 'Spice Supplier', 'Toppings'),
        ('Caramel Sauce', 'liter', 5.0, 1.0, 200.0, 'Beverage Supplier', 'Toppings'),
        ('Chocolate Sauce', 'liter', 5.0, 1.0, 200.0, 'Beverage Supplier', 'Toppings'),
        
        # Tea & Specialty Beverages
        ('Chai Tea', 'gram', 20.0, 5.0, 150.0, 'Tea Supplier', 'Beverages'),
        ('Matcha Powder', 'gram', 15.0, 3.0, 500.0, 'Tea Supplier', 'Beverages'),
        ('Tea Leaves', 'gram', 25.0, 5.0, 100.0, 'Tea Supplier', 'Beverages'),
        ('Hazelnut Syrup', 'liter', 8.0, 2.0, 150.0, 'Beverage Supplier', 'Beverages'),
        
        # Fruits
        ('Strawberries', 'kg', 10.0, 2.0, 300.0, 'Fruit Supplier', 'Beverages'),
        ('Mango', 'kg', 8.0, 2.0, 250.0, 'Fruit Supplier', 'Beverages'),
        ('Lemons', 'kg', 12.0, 3.0, 200.0, 'Fruit Supplier', 'Beverages'),
        ('Apples', 'kg', 15.0, 3.0, 150.0, 'Fruit Supplier', 'Baking'),
        ('Bananas', 'kg', 10.0, 2.0, 180.0, 'Fruit Supplier', 'Baking'),
        ('Carrots', 'kg', 8.0, 2.0, 120.0, 'Vegetable Supplier', 'Baking'),
        ('Cherries', 'kg', 5.0, 1.0, 400.0, 'Fruit Supplier', 'Toppings'),
        
        # Dairy & Specialty
        ('Yogurt', 'liter', 20.0, 5.0, 120.0, 'Dairy Supplier', 'Beverages'),
        ('Mascarpone', 'kg', 5.0, 1.0, 600.0, 'Dairy Supplier', 'Baking'),
        ('Vanilla Ice Cream', 'liter', 15.0, 3.0, 200.0, 'Dairy Supplier', 'Desserts'),
        
        # Baking Ingredients
        ('Yeast', 'gram', 30.0, 5.0, 80.0, 'Baking Supplier', 'Baking'),
        ('Salt', 'kg', 50.0, 10.0, 20.0, 'Local Supplier', 'Baking'),
        ('Almonds', 'kg', 8.0, 2.0, 350.0, 'Nut Supplier', 'Baking'),
        ('Pecans', 'kg', 6.0, 1.0, 450.0, 'Nut Supplier', 'Baking'),
        ('Graham Cracker Crumbs', 'kg', 10.0, 2.0, 180.0, 'Baking Supplier', 'Baking'),
        ('Ladyfingers', 'piece', 50.0, 10.0, 50.0, 'Baking Supplier', 'Baking'),
        ('Corn Syrup', 'liter', 8.0, 2.0, 120.0, 'Baking Supplier', 'Baking'),
        ('Lime Juice', 'liter', 10.0, 2.0, 200.0, 'Fruit Supplier', 'Baking'),
        ('Lime Zest', 'gram', 5.0, 1.0, 300.0, 'Fruit Supplier', 'Baking'),
        ('Fruit Jam', 'kg', 12.0, 3.0, 200.0, 'Baking Supplier', 'Baking'),
        
        # Sandwich Ingredients
        ('Bread', 'loaf', 20.0, 5.0, 60.0, 'Bakery Supplier', 'Light Meals'),
        ('Cheese', 'kg', 15.0, 3.0, 250.0, 'Dairy Supplier', 'Light Meals'),
        ('Mozzarella', 'kg', 12.0, 3.0, 280.0, 'Dairy Supplier', 'Light Meals'),
        ('Turkey', 'kg', 10.0, 2.0, 400.0, 'Meat Supplier', 'Light Meals'),
        ('Chicken', 'kg', 12.0, 3.0, 350.0, 'Meat Supplier', 'Light Meals'),
        ('Lettuce', 'kg', 15.0, 5.0, 80.0, 'Vegetable Supplier', 'Light Meals'),
        ('Romaine Lettuce', 'kg', 15.0, 5.0, 90.0, 'Vegetable Supplier', 'Light Meals'),
        ('Mixed Greens', 'kg', 12.0, 4.0, 100.0, 'Vegetable Supplier', 'Light Meals'),
        ('Tomato', 'kg', 20.0, 5.0, 120.0, 'Vegetable Supplier', 'Light Meals'),
        ('Cucumber', 'kg', 18.0, 5.0, 100.0, 'Vegetable Supplier', 'Light Meals'),
        ('Avocado', 'kg', 8.0, 2.0, 300.0, 'Fruit Supplier', 'Light Meals'),
        ('Basil', 'gram', 10.0, 2.0, 200.0, 'Herb Supplier', 'Light Meals'),
        ('Olives', 'kg', 8.0, 2.0, 250.0, 'Vegetable Supplier', 'Light Meals'),
        ('Feta Cheese', 'kg', 10.0, 2.0, 320.0, 'Dairy Supplier', 'Light Meals'),
        ('Parmesan', 'kg', 8.0, 2.0, 400.0, 'Dairy Supplier', 'Light Meals'),
        ('Mayonnaise', 'liter', 10.0, 2.0, 150.0, 'Condiment Supplier', 'Light Meals'),
        ('Caesar Dressing', 'liter', 8.0, 2.0, 180.0, 'Condiment Supplier', 'Light Meals'),
        ('Croutons', 'kg', 5.0, 1.0, 200.0, 'Bakery Supplier', 'Light Meals'),
        ('Olive Oil', 'liter', 12.0, 3.0, 200.0, 'Condiment Supplier', 'Light Meals'),
        ('Pepper', 'gram', 20.0, 5.0, 100.0, 'Spice Supplier', 'Light Meals'),
    ]
    
    cursor.executemany('''
        INSERT INTO ingredients (name, unit, current_stock, min_stock, cost_per_unit, supplier, category)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', ingredients)
    
    # Link ingredients to menu items (simplified - you can expand this)
    # Get menu items
    menu_items = cursor.execute('SELECT id, name, category FROM menu_items').fetchall()
    ingredients_list = cursor.execute('SELECT id, name FROM ingredients').fetchall()
    ingredients_dict = {name: id for id, name in ingredients_list}
    
    # Link common ingredients to items
    for menu_item in menu_items:
        item_id = menu_item[0]
        item_name = menu_item[1]
        item_category = menu_item[2]
        
        # Coffee drinks need coffee beans, milk, water
        if item_category in ['Hot Drinks', 'Cold Drinks']:
            if 'Coffee Beans' in ingredients_dict:
                cursor.execute('''
                    INSERT OR IGNORE INTO menu_item_ingredients (menu_item_id, ingredient_id, quantity_required)
                    VALUES (?, ?, ?)
                ''', (item_id, ingredients_dict['Coffee Beans'], 0.05))  # 50g per drink
            if 'Milk' in ingredients_dict and item_name not in ['Espresso', 'Americano']:
                cursor.execute('''
                    INSERT OR IGNORE INTO menu_item_ingredients (menu_item_id, ingredient_id, quantity_required)
                    VALUES (?, ?, ?)
                ''', (item_id, ingredients_dict['Milk'], 0.2))  # 200ml per drink
            if 'Water' in ingredients_dict:
                cursor.execute('''
                    INSERT OR IGNORE INTO menu_item_ingredients (menu_item_id, ingredient_id, quantity_required)
                    VALUES (?, ?, ?)
                ''', (item_id, ingredients_dict['Water'], 0.3))  # 300ml per drink
            if 'Ice' in ingredients_dict and item_category == 'Cold Drinks':
                cursor.execute('''
                    INSERT OR IGNORE INTO menu_item_ingredients (menu_item_id, ingredient_id, quantity_required)
                    VALUES (?, ?, ?)
                ''', (item_id, ingredients_dict['Ice'], 0.15))  # 150g ice
        
        # Pastries need flour, butter, eggs, sugar
        if item_category == 'Pastries':
            if 'Flour' in ingredients_dict:
                cursor.execute('''
                    INSERT OR IGNORE INTO menu_item_ingredients (menu_item_id, ingredient_id, quantity_required)
                    VALUES (?, ?, ?)
                ''', (item_id, ingredients_dict['Flour'], 0.1))  # 100g flour
            if 'Butter' in ingredients_dict:
                cursor.execute('''
                    INSERT OR IGNORE INTO menu_item_ingredients (menu_item_id, ingredient_id, quantity_required)
                    VALUES (?, ?, ?)
                ''', (item_id, ingredients_dict['Butter'], 0.05))  # 50g butter
            if 'Eggs' in ingredients_dict:
                cursor.execute('''
                    INSERT OR IGNORE INTO menu_item_ingredients (menu_item_id, ingredient_id, quantity_required)
                    VALUES (?, ?, ?)
                ''', (item_id, ingredients_dict['Eggs'], 0.5))  # 0.5 eggs
            if 'Sugar (Baking)' in ingredients_dict:
                cursor.execute('''
                    INSERT OR IGNORE INTO menu_item_ingredients (menu_item_id, ingredient_id, quantity_required)
                    VALUES (?, ?, ?)
                ''', (item_id, ingredients_dict['Sugar (Baking)'], 0.03))  # 30g sugar
        
        # Desserts need similar ingredients
        if item_category == 'Desserts':
            if 'Flour' in ingredients_dict:
                cursor.execute('''
                    INSERT OR IGNORE INTO menu_item_ingredients (menu_item_id, ingredient_id, quantity_required)
                    VALUES (?, ?, ?)
                ''', (item_id, ingredients_dict['Flour'], 0.15))
            if 'Sugar (Baking)' in ingredients_dict:
                cursor.execute('''
                    INSERT OR IGNORE INTO menu_item_ingredients (menu_item_id, ingredient_id, quantity_required)
                    VALUES (?, ?, ?)
                ''', (item_id, ingredients_dict['Sugar (Baking)'], 0.05))
            if 'Eggs' in ingredients_dict:
                cursor.execute('''
                    INSERT OR IGNORE INTO menu_item_ingredients (menu_item_id, ingredient_id, quantity_required)
                    VALUES (?, ?, ?)
                ''', (item_id, ingredients_dict['Eggs'], 1.0))
            if 'Chocolate Chips' in ingredients_dict and 'Chocolate' in item_name:
                cursor.execute('''
                    INSERT OR IGNORE INTO menu_item_ingredients (menu_item_id, ingredient_id, quantity_required)
                    VALUES (?, ?, ?)
                ''', (item_id, ingredients_dict['Chocolate Chips'], 0.1))
            if 'Cream Cheese' in ingredients_dict and 'Cheesecake' in item_name:
                cursor.execute('''
                    INSERT OR IGNORE INTO menu_item_ingredients (menu_item_id, ingredient_id, quantity_required)
                    VALUES (?, ?, ?)
                ''', (item_id, ingredients_dict['Cream Cheese'], 0.2))
            if 'Blueberries' in ingredients_dict and 'Blueberry' in item_name:
                cursor.execute('''
                    INSERT OR IGNORE INTO menu_item_ingredients (menu_item_id, ingredient_id, quantity_required)
                    VALUES (?, ?, ?)
                ''', (item_id, ingredients_dict['Blueberries'], 0.05))

def get_db_connection():
    """Get a database connection."""
    # Ensure database directory exists
    os.makedirs(DATABASE_DIR, exist_ok=True)
    
    # Initialize database if it doesn't exist or tables are missing
    try:
        conn = sqlite3.connect(DATABASE_PATH, timeout=10.0)
        conn.row_factory = sqlite3.Row
        # Check if menu_items table exists
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='menu_items'")
        if not cursor.fetchone():
            # Database exists but tables don't - initialize
            conn.close()
            init_database()
            conn = sqlite3.connect(DATABASE_PATH, timeout=10.0)
            conn.row_factory = sqlite3.Row
        # Enable WAL mode for better concurrency
        try:
            conn.execute('PRAGMA journal_mode=WAL')
        except:
            pass  # WAL might not be supported in some environments
    except Exception as e:
        # If connection fails, try to initialize database
        print(f"Database connection error: {str(e)}")
        try:
            init_database()
            conn = sqlite3.connect(DATABASE_PATH, timeout=10.0)
            conn.row_factory = sqlite3.Row
        except Exception as init_error:
            print(f"Database initialization error: {str(init_error)}")
            raise
    
    return conn

def send_order_notification(customer_id, order_id, status, conn=None):
    """Send notification to customer about order status change."""
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True
    
    try:
        # Get customer info
        customer = conn.execute('SELECT * FROM customers WHERE id = ?', (customer_id,)).fetchone()
        if not customer:
            print(f"Customer {customer_id} not found for notification")
            if close_conn:
                conn.close()
            return
        
        # Get order info
        order = conn.execute('SELECT * FROM orders WHERE id = ?', (order_id,)).fetchone()
        if not order:
            print(f"Order {order_id} not found for notification")
            if close_conn:
                conn.close()
            return
        
        # Convert Row to dict for easier access
        order_dict = dict(order)
        customer_dict = dict(customer)
        
        # Define notification messages based on status
        pickup_time = order_dict.get('pickup_time') or 'TBD'
        status_messages = {
            'pending': {
                'title': 'Order Received!',
                'message': f'Thank you for your order! Order #{order_id} has been received and is being processed. Pickup time: {pickup_time}'
            },
            'confirmed': {
                'title': 'Order Confirmed!',
                'message': f'Your order #{order_id} has been confirmed and is being prepared. Pickup time: {pickup_time}'
            },
            'preparing': {
                'title': 'Order Being Prepared',
                'message': f'Your order #{order_id} is now being prepared. We\'ll notify you when it\'s ready!'
            },
            'ready': {
                'title': 'Order Ready for Pickup!',
                'message': f'Your order #{order_id} is ready for pickup! Please come to the cafe to collect your order.'
            },
            'completed': {
                'title': 'Order Completed',
                'message': f'Thank you! Your order #{order_id} has been completed. We hope you enjoyed your meal!'
            },
            'cancelled': {
                'title': 'Order Cancelled',
                'message': f'Your order #{order_id} has been cancelled. If you have any questions, please contact us.'
            }
        }
        
        if status not in status_messages:
            return
        
        notification = status_messages[status]
        
        # Create notification record
        conn.execute('''
            INSERT INTO notifications (customer_id, order_id, type, title, message)
            VALUES (?, ?, ?, ?, ?)
        ''', (customer_id, order_id, 'order_status', notification['title'], notification['message']))
        
        # Commit notification to database
        conn.commit()
        
        # Send email if enabled
        if customer_dict.get('email_notifications', 1):
            try:
                msg = Message(
                    subject=f'Order #{order_id} - {notification["title"]}',
                    recipients=[customer_dict['email']],
                    body=f'''Hello {customer_dict['first_name']},

{notification['message']}

Order Details:
- Order ID: #{order_id}
- Total: P{order_dict["total_amount"]:.2f}
- Pickup Time: {pickup_time}

Thank you for choosing Cafe Next Door!

Best regards,
Cafe Next Door Team'''
                )
                mail.send(msg)
                print(f"Email notification sent to {customer_dict['email']} for order #{order_id}")
            except Exception as e:
                print(f"Error sending email notification: {e}")
        
        # SMS notification (simulated - store in session for popup)
        if customer_dict.get('sms_notifications', 1) and customer_dict.get('phone'):
            # In production, integrate with SMS API here
            # For now, we'll just log it
            print(f"SMS notification would be sent to {customer_dict['phone']}: {notification['message']}")
        
        print(f"Notification created for order #{order_id}, status: {status}")
        
        if close_conn:
            conn.close()
            
    except Exception as e:
        print(f"Error sending notification: {e}")
        import traceback
        traceback.print_exc()
        if close_conn and conn:
            try:
                conn.rollback()
                conn.close()
            except:
                pass

@app.route('/')
def index():
    """Home page route."""
    try:
        return render_template('index.html')
    except Exception as e:
        print(f"Error in index route: {str(e)}")
        import traceback
        traceback.print_exc()
        return render_template('error.html', error_code=500, error_message='Error loading home page.'), 500

@app.route('/about')
def about():
    """About Us page route."""
    try:
        # Get gallery images
        gallery_path = os.path.join('static', 'images', 'gallery')
        gallery_images = []
        if os.path.exists(gallery_path):
            for filename in sorted(os.listdir(gallery_path)):
                if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.webp', '.gif')):
                    gallery_images.append({
                        'filename': filename,
                        'url': url_for('static', filename=f'images/gallery/{filename}')
                    })
        
        return render_template('about.html', gallery_images=gallery_images)
    except Exception as e:
        print(f"Error in about route: {str(e)}")
        return render_template('error.html', error_code=500, error_message='Error loading about page.'), 500

@app.route('/menu')
def menu():
    """Menu page route - displays all menu items with search and filter."""
    conn = None
    try:
        # Ensure database is initialized
        try:
            init_database()
        except Exception as init_error:
            print(f"Warning: Database initialization check failed: {str(init_error)}")
        
        search_query = request.args.get('search', '').strip()
        category_filter = request.args.get('category', '')
        price_sort = request.args.get('price', '')  # 'low' or 'high'
        
        conn = get_db_connection()
        
        # Check if is_available column exists, if not, show all items
        try:
            cursor = conn.cursor()
            cursor.execute('PRAGMA table_info(menu_items)')
            columns = [row[1] for row in cursor.fetchall()]
            has_is_available = 'is_available' in columns
        except:
            has_is_available = False
        
        # Build query based on filters - show ALL items including sold-out ones
        query = 'SELECT * FROM menu_items WHERE 1=1'
        params = []
        
        if search_query:
            query += ' AND (name LIKE ? OR description LIKE ?)'
            params.extend([f'%{search_query}%', f'%{search_query}%'])
        
        if category_filter:
            query += ' AND category = ?'
            params.append(category_filter)
        
        # Order by
        if price_sort == 'low':
            query += ' ORDER BY price ASC'
        elif price_sort == 'high':
            query += ' ORDER BY price DESC'
        else:
            query += ' ORDER BY category, name'
        
        rows = conn.execute(query, params).fetchall()
        items = [dict(row) for row in rows]
        
        # Get all categories for filter dropdown
        try:
            all_categories_rows = conn.execute('SELECT DISTINCT category FROM menu_items ORDER BY category').fetchall()
            all_categories = [row['category'] for row in all_categories_rows]
        except:
            all_categories = []
        
        # Get customer favorites if logged in
        favorites = []
        if 'customer_id' in session:
            try:
                fav_rows = conn.execute('SELECT menu_item_id FROM favorites WHERE customer_id = ?', 
                                        (session['customer_id'],)).fetchall()
                favorites = [row['menu_item_id'] for row in fav_rows]
            except:
                favorites = []
        
        # Get ratings for each item
        for item in items:
            try:
                rating_data = conn.execute('''
                    SELECT AVG(rating) as avg_rating, COUNT(*) as review_count
                    FROM reviews WHERE menu_item_id = ? AND is_approved = 1
                ''', (item['id'],)).fetchone()
                item['avg_rating'] = rating_data['avg_rating'] or 0 if rating_data else 0
                item['review_count'] = rating_data['review_count'] or 0 if rating_data else 0
            except:
                item['avg_rating'] = 0
                item['review_count'] = 0
        
        if conn:
            conn.close()
        
        # Group items by category (show all items that are marked as available)
        categories = {}
        for item in items:
            category = item.get('category', 'Uncategorized')
            if category not in categories:
                categories[category] = []
            categories[category].append(item)
        
        return render_template('menu.html', categories=categories, all_categories=all_categories,
                              search_query=search_query, category_filter=category_filter,
                              price_sort=price_sort, favorites=favorites)
    except Exception as e:
        print(f"Error in menu route: {str(e)}")
        import traceback
        traceback.print_exc()
        if conn:
            try:
                conn.close()
            except:
                pass
        flash('Error loading menu. Please try again.', 'error')
        return render_template('menu.html', categories={}, all_categories=[],
                              search_query=search_query or '', category_filter=category_filter or '', 
                              price_sort=price_sort or '', favorites=[])

def get_client_ip():
    """Get the client's IP address."""
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    return request.remote_addr

def generate_verification_code():
    """Generate a 6-digit verification code."""
    import random
    return str(random.randint(100000, 999999))

def check_blacklist(customer_id=None, email=None, phone=None):
    """Check if customer is blacklisted."""
    conn = get_db_connection()
    query = 'SELECT * FROM blacklist WHERE is_active = 1 AND ('
    params = []
    conditions = []
    
    if customer_id:
        conditions.append('customer_id = ?')
        params.append(customer_id)
    if email:
        conditions.append('email = ?')
        params.append(email)
    if phone:
        conditions.append('phone = ?')
        params.append(phone)
    
    if not conditions:
        conn.close()
        return None
    
    query += ' OR '.join(conditions) + ')'
    result = conn.execute(query, params).fetchone()
    conn.close()
    return dict(result) if result else None

def is_phone_verified(customer_id):
    """Check if customer's phone is verified (deprecated - use is_email_verified)."""
    conn = get_db_connection()
    customer = conn.execute('SELECT phone_verified FROM customers WHERE id = ?', (customer_id,)).fetchone()
    conn.close()
    return customer and customer['phone_verified'] == 1

def is_email_verified(customer_id):
    """Check if customer's email is verified."""
    try:
        conn = get_db_connection()
        # Try to get email_verified column, if it doesn't exist, check all columns
        try:
            customer = conn.execute('SELECT email_verified FROM customers WHERE id = ?', (customer_id,)).fetchone()
        except sqlite3.OperationalError:
            # Column doesn't exist, get all columns and check
            customer = conn.execute('SELECT * FROM customers WHERE id = ?', (customer_id,)).fetchone()
        
        conn.close()
        
        if not customer:
            return False
        
        # Convert Row to dict if needed
        if not isinstance(customer, dict):
            customer = dict(customer)
        
        # Check if email_verified column exists and is set to 1
        email_verified = customer.get('email_verified', 0)
        return email_verified == 1
    except Exception as e:
        print(f"Error checking email verification: {str(e)}")
        # If there's an error, assume not verified to be safe
        return False

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
    try:
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
    except Exception as e:
        print(f"Error in contact route: {str(e)}")
        import traceback
        traceback.print_exc()
        flash('An error occurred. Please try again.', 'error')
        return render_template('contact.html')

# Authentication decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

# Role-based access decorators
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('admin_login'))
        if session.get('user_role') != 'admin':
            flash('Admin access required.', 'error')
            return redirect(url_for('admin_dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def manager_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('admin_login'))
        if session.get('user_role') not in ['admin', 'manager']:
            flash('Manager access required.', 'error')
            return redirect(url_for('admin_dashboard'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login route - redirects to admin login for backward compatibility."""
    return redirect(url_for('admin_login'))

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Admin/Staff login page route."""
    try:
        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')
            
            if not username or not password:
                flash('Please enter both username and password.', 'error')
                return render_template('login.html')
            
            # Try to ensure database is initialized (silently fail if already initialized)
            try:
                init_database()
            except Exception as init_error:
                # Silently continue - database is likely already initialized
                pass
            
            conn = None
            try:
                conn = get_db_connection()
                
                # Check if users table exists
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
                table_exists = cursor.fetchone()
                
                if not table_exists:
                    if conn:
                        conn.close()
                    flash('Database not properly initialized. Please contact the administrator.', 'error')
                    return render_template('login.html')
                
                user = conn.execute(
                    'SELECT * FROM users WHERE username = ?', (username,)
                ).fetchone()
                
                if conn:
                    conn.close()
                
                if not user:
                    print(f"Login attempt failed: User '{username}' not found")
                    flash('Invalid username or password.', 'error')
                    return render_template('login.html')
                
                # Convert Row to dict for easier access
                user_dict = dict(user)
                
                # Check password
                password_valid = check_password_hash(user_dict['password_hash'], password)
                print(f"Login attempt for '{username}': Password valid = {password_valid}")
                
                if password_valid:
                    # Set session variables
                    session['user_id'] = user_dict['id']
                    session['username'] = user_dict['username']
                    session['user_role'] = user_dict.get('role') or 'admin'
                    session['user_full_name'] = user_dict.get('full_name')
                    display_name = user_dict.get('full_name') or username
                    
                    # Force session to be saved
                    session.permanent = True
                    
                    print(f"Login successful for '{username}' (ID: {user_dict['id']}, Role: {session['user_role']})")
                    print(f"Session after login: user_id={session.get('user_id')}, username={session.get('username')}, role={session.get('user_role')}")
                    
                    flash(f'Welcome back, {display_name}!', 'success')
                    return redirect(url_for('admin_dashboard'))
                else:
                    print(f"Login attempt failed: Invalid password for '{username}'")
                    flash('Invalid username or password.', 'error')
                    return render_template('login.html')
                    
            except sqlite3.Error as db_error:
                if conn:
                    try:
                        conn.close()
                    except:
                        pass
                print(f"Database error in admin_login: {str(db_error)}")
                import traceback
                traceback.print_exc()
                flash('Database error occurred. Please try again or contact support.', 'error')
                return render_template('login.html')
            except Exception as db_ex:
                if conn:
                    try:
                        conn.close()
                    except:
                        pass
                print(f"Error accessing database in admin_login: {str(db_ex)}")
                import traceback
                traceback.print_exc()
                flash('An error occurred while accessing the database. Please try again.', 'error')
                return render_template('login.html')
        
        return render_template('login.html')
    except Exception as e:
        print(f"Unexpected error in admin_login route: {str(e)}")
        import traceback
        traceback.print_exc()
        flash('An unexpected error occurred. Please try again.', 'error')
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

@app.route('/admin/update-menu', methods=['GET', 'POST'])
@manager_required
def admin_update_menu():
    """Admin route to add new menu items from seed data."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        added_count = update_menu_with_new_items(cursor)
        conn.commit()
        conn.close()
        
        if added_count > 0:
            flash(f'Successfully added {added_count} new menu items!', 'success')
        else:
            flash('All menu items are already in the database.', 'info')
        return redirect(url_for('admin_menu'))
    except Exception as e:
        flash(f'Error updating menu: {str(e)}', 'error')
        return redirect(url_for('admin_menu'))

@app.route('/admin/add', methods=['GET', 'POST'])
@manager_required
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
            conn = get_db_connection()
            categories_rows = conn.execute('SELECT DISTINCT category FROM menu_items ORDER BY category').fetchall()
            all_categories = [row['category'] for row in categories_rows]
            ingredients = conn.execute('SELECT * FROM ingredients WHERE is_active = 1 ORDER BY name').fetchall()
            conn.close()
            return render_template('admin_add.html', all_categories=all_categories, ingredients=[dict(i) for i in ingredients])
        
        try:
            price = float(price)
        except ValueError:
            flash('Please enter a valid price.', 'error')
            conn = get_db_connection()
            categories_rows = conn.execute('SELECT DISTINCT category FROM menu_items ORDER BY category').fetchall()
            all_categories = [row['category'] for row in categories_rows]
            ingredients = conn.execute('SELECT * FROM ingredients WHERE is_active = 1 ORDER BY name').fetchall()
            conn.close()
            return render_template('admin_add.html', all_categories=all_categories, ingredients=[dict(i) for i in ingredients])
        
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
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO menu_items (name, description, price, category, image_url)
            VALUES (?, ?, ?, ?, ?)
        ''', (name, description, price, category, image_url))
        menu_item_id = cursor.lastrowid
        
        # Handle ingredient linking
        ingredient_ids = request.form.getlist('ingredient_ids')
        
        # Link ingredients if provided
        for ingredient_id in ingredient_ids:
            if ingredient_id:
                quantity_key = f'ingredient_{ingredient_id}_quantity'
                quantity = request.form.get(quantity_key, '').strip()
                if quantity:
                    try:
                        quantity_float = float(quantity)
                        if quantity_float > 0:
                            conn.execute('''
                                INSERT OR REPLACE INTO menu_item_ingredients 
                                (menu_item_id, ingredient_id, quantity_required)
                                VALUES (?, ?, ?)
                            ''', (menu_item_id, int(ingredient_id), quantity_float))
                    except (ValueError, TypeError):
                        pass  # Skip invalid entries
        
        conn.commit()
        conn.close()
        
        flash(f'Menu item "{name}" has been added successfully!', 'success')
        return redirect(url_for('admin_menu'))
    
    # Fetch all active ingredients for the form
    conn = get_db_connection()
    ingredients = conn.execute('''
        SELECT * FROM ingredients WHERE is_active = 1 ORDER BY name
    ''').fetchall()
    
    # Fetch all distinct categories from menu items
    categories_rows = conn.execute('SELECT DISTINCT category FROM menu_items ORDER BY category').fetchall()
    all_categories = [row['category'] for row in categories_rows]
    
    conn.close()
    
    return render_template('admin_add.html', ingredients=[dict(i) for i in ingredients], all_categories=all_categories)

@app.route('/admin/edit/<int:item_id>', methods=['GET', 'POST'])
@manager_required
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
            categories_rows = conn.execute('SELECT DISTINCT category FROM menu_items ORDER BY category').fetchall()
            all_categories = [row['category'] for row in categories_rows]
            conn.close()
            return render_template('admin_edit.html', item=dict(item), all_categories=all_categories)
        
        try:
            price = float(price)
        except ValueError:
            flash('Please enter a valid price.', 'error')
            item = conn.execute('SELECT * FROM menu_items WHERE id = ?', (item_id,)).fetchone()
            categories_rows = conn.execute('SELECT DISTINCT category FROM menu_items ORDER BY category').fetchall()
            all_categories = [row['category'] for row in categories_rows]
            conn.close()
            return render_template('admin_edit.html', item=dict(item), all_categories=all_categories)
        
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
        
        # Handle ingredient linking - remove all existing links first
        conn.execute('DELETE FROM menu_item_ingredients WHERE menu_item_id = ?', (item_id,))
        
        # Add new ingredient links
        ingredient_ids = request.form.getlist('ingredient_ids')
        
        for ingredient_id in ingredient_ids:
            if ingredient_id:
                quantity_key = f'ingredient_{ingredient_id}_quantity'
                quantity = request.form.get(quantity_key, '').strip()
                if quantity:
                    try:
                        quantity_float = float(quantity)
                        if quantity_float > 0:
                            conn.execute('''
                                INSERT INTO menu_item_ingredients 
                                (menu_item_id, ingredient_id, quantity_required)
                                VALUES (?, ?, ?)
                            ''', (item_id, int(ingredient_id), quantity_float))
                    except (ValueError, TypeError):
                        pass  # Skip invalid entries
        
        conn.commit()
        conn.close()
        
        flash(f'Menu item "{name}" has been updated successfully!', 'success')
        return redirect(url_for('admin_menu'))
    
    # Fetch menu item
    item = conn.execute('SELECT * FROM menu_items WHERE id = ?', (item_id,)).fetchone()
    
    if not item:
        conn.close()
        flash('Menu item not found.', 'error')
        return redirect(url_for('admin_menu'))
    
    # Fetch all active ingredients
    ingredients = conn.execute('''
        SELECT * FROM ingredients WHERE is_active = 1 ORDER BY name
    ''').fetchall()
    
    # Fetch currently linked ingredients
    linked_ingredients = conn.execute('''
        SELECT ingredient_id, quantity_required 
        FROM menu_item_ingredients 
        WHERE menu_item_id = ?
    ''', (item_id,)).fetchall()
    
    # Create a dict for easy lookup
    linked_dict = {row['ingredient_id']: row['quantity_required'] for row in linked_ingredients}
    
    # Fetch all distinct categories from menu items
    categories_rows = conn.execute('SELECT DISTINCT category FROM menu_items ORDER BY category').fetchall()
    all_categories = [row['category'] for row in categories_rows]
    
    conn.close()
    
    return render_template('admin_edit.html', 
                         item=dict(item),
                         ingredients=[dict(i) for i in ingredients],
                         linked_ingredients=linked_dict,
                         all_categories=all_categories)

@app.route('/admin/delete/<int:item_id>', methods=['POST'])
@manager_required
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

@app.route('/admin/toggle-availability/<int:item_id>', methods=['POST'])
@login_required
def admin_toggle_availability(item_id):
    """Toggle menu item availability (sold out / available)."""
    conn = get_db_connection()
    item = conn.execute('SELECT * FROM menu_items WHERE id = ?', (item_id,)).fetchone()
    
    if item:
        new_status = 0 if item['is_available'] else 1
        conn.execute('UPDATE menu_items SET is_available = ? WHERE id = ?', (new_status, item_id))
        conn.commit()
        status_text = 'available' if new_status else 'sold out'
        flash(f'"{item["name"]}" marked as {status_text}.', 'success')
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

@app.route('/admin/messages/reply/<int:message_id>', methods=['GET', 'POST'])
@login_required
def admin_reply_message(message_id):
    """Admin route - reply to a contact message via email."""
    conn = get_db_connection()
    message = conn.execute('SELECT * FROM contact_messages WHERE id = ?', (message_id,)).fetchone()
    
    if not message:
        conn.close()
        flash('Message not found.', 'error')
        return redirect(url_for('admin_messages'))
    
    if request.method == 'POST':
        reply_message = request.form.get('reply_message', '').strip()
        
        if not reply_message:
            flash('Please enter a reply message.', 'error')
            conn.close()
            return render_template('admin_reply_message.html', message=dict(message))
        
        # Send reply email
        if app.config['MAIL_PASSWORD']:
            try:
                subject = f'Re: Your message to Cafe Next Door'
                body = f'''
Dear {message['name']},

Thank you for contacting Cafe Next Door. We have received your message and are happy to respond.

Your original message:
{message['message']}

---
Our Reply:
{reply_message}

---
If you have any further questions, please don't hesitate to contact us again.

Best regards,
Cafe Next Door Team
{app.config.get('CAFE_EMAIL', 'cafenextdoor@protonmail.com')}
'''
                msg = Message(
                    subject=subject,
                    recipients=[message['email']],
                    body=body,
                    sender=app.config['MAIL_DEFAULT_SENDER'],
                    reply_to=app.config.get('CAFE_EMAIL', app.config['MAIL_DEFAULT_SENDER'])
                )
                mail.send(msg)
                print(f"Reply email sent to {message['email']}")
                
                # Mark message as replied
                conn.execute('UPDATE contact_messages SET replied = 1 WHERE id = ?', (message_id,))
                conn.commit()
                
                flash(f'Reply sent successfully to {message["name"]}!', 'success')
            except Exception as e:
                print(f"Error sending reply email: {str(e)}")
                flash('Error sending reply email. Please try again or use the mailto link.', 'error')
        else:
            flash('Email service is not configured. Please configure MAIL_PASSWORD to send replies.', 'error')
        
        conn.close()
        return redirect(url_for('admin_messages'))
    
    conn.close()
    return render_template('admin_reply_message.html', message=dict(message))

# Customer authentication decorator
def customer_login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'customer_id' not in session:
            flash('Please log in to continue.', 'error')
            return redirect(url_for('customer_login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/register', methods=['GET', 'POST'])
def customer_register():
    """Customer registration page."""
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        phone = request.form.get('phone', '').strip()
        
        # Validation
        if not email or not password or not first_name or not last_name or not phone:
            flash('Please fill in all required fields including phone number.', 'error')
            return render_template('customer_register.html')
        
        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template('customer_register.html')
        
        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'error')
            return render_template('customer_register.html')
        
        # Check if email already exists
        conn = get_db_connection()
        existing = conn.execute('SELECT id FROM customers WHERE email = ?', (email,)).fetchone()
        if existing:
            conn.close()
            flash('An account with this email already exists.', 'error')
            return render_template('customer_register.html')
        
        # Create account
        password_hash = generate_password_hash(password)
        conn.execute('''
            INSERT INTO customers (email, password_hash, first_name, last_name, phone, email_verified)
            VALUES (?, ?, ?, ?, ?, 0)
        ''', (email, password_hash, first_name, last_name, phone))
        conn.commit()
        conn.close()
        
        flash('Account created successfully! Please log in and verify your email address.', 'success')
        return redirect(url_for('customer_login'))
    
    return render_template('customer_register.html')

@app.route('/customer/login', methods=['GET', 'POST'])
def customer_login():
    """Customer login page."""
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        
        if not email or not password:
            flash('Please enter email and password.', 'error')
            return render_template('customer_login.html')
        
        conn = get_db_connection()
        customer = conn.execute('SELECT * FROM customers WHERE email = ?', (email,)).fetchone()
        conn.close()
        
        if customer and check_password_hash(customer['password_hash'], password):
            session['customer_id'] = customer['id']
            session['customer_name'] = customer['first_name']
            session['customer_email'] = customer['email']
            flash(f'Welcome back, {customer["first_name"]}!', 'success')
            
            # Redirect to cart if there are items, otherwise to menu
            if session.get('cart'):
                return redirect(url_for('checkout'))
            return redirect(url_for('menu'))
        else:
            flash('Invalid email or password.', 'error')
    
    return render_template('customer_login.html')

@app.route('/customer/logout')
def customer_logout():
    """Customer logout."""
    session.pop('customer_id', None)
    session.pop('customer_name', None)
    session.pop('customer_email', None)
    flash('You have been logged out.', 'success')
    return redirect(url_for('index'))

@app.route('/customer/profile/edit', methods=['GET', 'POST'])
@customer_login_required
def edit_profile():
    """Edit customer profile."""
    conn = get_db_connection()
    customer = conn.execute('SELECT * FROM customers WHERE id = ?', (session['customer_id'],)).fetchone()
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        
        if not first_name or not last_name:
            flash('First name and last name are required.', 'error')
            conn.close()
            return render_template('edit_profile.html', customer=dict(customer))
        
        if not email or '@' not in email:
            flash('Please enter a valid email address.', 'error')
            conn.close()
            return render_template('edit_profile.html', customer=dict(customer))
        
        if not phone:
            flash('Phone number is required.', 'error')
            conn.close()
            return render_template('edit_profile.html', customer=dict(customer))
        
        # If email changed, reset verification
        email_changed = email != customer['email']
        email_verified = 0 if email_changed else customer.get('email_verified', 0)

        conn.execute('''
            UPDATE customers SET email = ?, phone = ?, first_name = ?, last_name = ?, email_verified = ?
            WHERE id = ?
        ''', (email, phone, first_name, last_name, email_verified, session['customer_id']))
        conn.commit()
        conn.close()

        if email_changed:
            flash('Profile updated! Please verify your new email address.', 'success')
            return redirect(url_for('verify_email'))
        else:
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('customer_profile'))
    
    conn.close()
    return render_template('edit_profile.html', customer=dict(customer))

@app.route('/customer/profile')
@customer_login_required
def customer_profile():
    """Customer profile page."""
    conn = get_db_connection()
    customer = conn.execute('SELECT * FROM customers WHERE id = ?', (session['customer_id'],)).fetchone()
    orders = conn.execute('''
        SELECT * FROM orders WHERE customer_id = ? ORDER BY created_at DESC
    ''', (session['customer_id'],)).fetchall()
    
    # Get loyalty points (initialize if doesn't exist)
    points = conn.execute('SELECT * FROM loyalty_points WHERE customer_id = ?', 
                         (session['customer_id'],)).fetchone()
    
    if not points:
        # Initialize with 0 points
        conn.execute('INSERT INTO loyalty_points (customer_id, points, total_earned, total_redeemed) VALUES (?, 0, 0, 0)', 
                    (session['customer_id'],))
        conn.commit()
        points = conn.execute('SELECT * FROM loyalty_points WHERE customer_id = ?', 
                             (session['customer_id'],)).fetchone()
    
    conn.close()
    
    # Ensure points is a dict with all required fields
    loyalty_data = dict(points) if points else {'points': 0, 'total_earned': 0, 'total_redeemed': 0}
    if loyalty_data.get('points') is None:
        loyalty_data['points'] = 0
    
    return render_template('customer_profile.html', customer=dict(customer), 
                         orders=[dict(o) for o in orders], 
                         loyalty_points=loyalty_data)

# Notifications Routes
@app.route('/customer/notifications')
@customer_login_required
def customer_notifications():
    """Customer notifications page."""
    conn = get_db_connection()
    notifications = conn.execute('''
        SELECT * FROM notifications 
        WHERE customer_id = ? 
        ORDER BY created_at DESC
        LIMIT 50
    ''', (session['customer_id'],)).fetchall()
    
    unread_count = conn.execute('''
        SELECT COUNT(*) as count FROM notifications 
        WHERE customer_id = ? AND is_read = 0
    ''', (session['customer_id'],)).fetchone()['count']
    
    conn.close()
    return render_template('customer_notifications.html', 
                         notifications=[dict(n) for n in notifications],
                         unread_count=unread_count)

@app.route('/customer/notifications/<int:notification_id>/read', methods=['POST'])
@customer_login_required
def mark_notification_read(notification_id):
    """Mark notification as read."""
    conn = get_db_connection()
    conn.execute('''
        UPDATE notifications SET is_read = 1 
        WHERE id = ? AND customer_id = ?
    ''', (notification_id, session['customer_id']))
    conn.commit()
    conn.close()
    return '', 204

@app.route('/customer/notifications/mark-all-read', methods=['POST'])
@customer_login_required
def mark_all_notifications_read():
    """Mark all notifications as read."""
    conn = get_db_connection()
    conn.execute('''
        UPDATE notifications SET is_read = 1 
        WHERE customer_id = ? AND is_read = 0
    ''', (session['customer_id'],))
    conn.commit()
    conn.close()
    flash('All notifications marked as read.', 'success')
    return redirect(url_for('customer_notifications'))

# Gift Cards & Vouchers Routes
@app.route('/gift-cards')
@customer_login_required
def gift_cards():
    """View customer's gift cards."""
    conn = get_db_connection()
    gift_cards_list = conn.execute('''
        SELECT * FROM gift_cards 
        WHERE customer_id = ? AND is_active = 1
        ORDER BY created_at DESC
    ''', (session['customer_id'],)).fetchall()
    
    # Get transaction history for each gift card
    for gc in gift_cards_list:
        transactions = conn.execute('''
            SELECT * FROM gift_card_transactions 
            WHERE gift_card_id = ?
            ORDER BY created_at DESC
        ''', (gc['id'],)).fetchall()
        gc['transactions'] = [dict(t) for t in transactions]
    
    conn.close()
    return render_template('gift_cards.html', gift_cards=[dict(gc) for gc in gift_cards_list])

@app.route('/gift-cards/purchase', methods=['GET', 'POST'])
@customer_login_required
def purchase_gift_card():
    """Purchase a gift card."""
    if request.method == 'POST':
        amount = request.form.get('amount', type=float)
        recipient_email = request.form.get('recipient_email', '').strip().lower()
        recipient_name = request.form.get('recipient_name', '').strip()
        message = request.form.get('message', '').strip()
        
        if not amount or amount <= 0:
            flash('Please enter a valid amount.', 'error')
            return render_template('purchase_gift_card.html')
        
        if amount < 100:
            flash('Minimum gift card amount is P100.', 'error')
            return render_template('purchase_gift_card.html')
        
        # Generate unique gift card code
        import secrets
        code = secrets.token_urlsafe(12).upper()[:12]
        
        # Check if code already exists
        conn = get_db_connection()
        while conn.execute('SELECT id FROM gift_cards WHERE code = ?', (code,)).fetchone():
            code = secrets.token_urlsafe(12).upper()[:12]
        
        # If recipient email provided, find customer
        recipient_id = None
        if recipient_email:
            recipient = conn.execute('SELECT id FROM customers WHERE email = ?', (recipient_email,)).fetchone()
            if recipient:
                recipient_id = recipient['id']
        
        # Create gift card
        expires_at = (datetime.now() + timedelta(days=365)).strftime('%Y-%m-%d')
        conn.execute('''
            INSERT INTO gift_cards (code, customer_id, amount, balance, expires_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (code, recipient_id or session['customer_id'], amount, amount, expires_at))
        
        gift_card_id = conn.lastrowid
        
        # Record transaction
        conn.execute('''
            INSERT INTO gift_card_transactions (gift_card_id, transaction_type, amount, description)
            VALUES (?, 'purchase', ?, ?)
        ''', (gift_card_id, amount, f'Gift card purchased - Code: {code}'))
        
        conn.commit()
        conn.close()
        
        flash(f'Gift card purchased successfully! Code: {code}', 'success')
        return redirect(url_for('gift_cards'))
    
    return render_template('purchase_gift_card.html')

@app.route('/gift-cards/redeem', methods=['POST'])
@customer_login_required
def redeem_gift_card():
    """Redeem a gift card code."""
    code = request.form.get('code', '').strip().upper()
    
    if not code:
        flash('Please enter a gift card code.', 'error')
        return redirect(url_for('gift_cards'))
    
    conn = get_db_connection()
    gift_card = conn.execute('''
        SELECT * FROM gift_cards 
        WHERE code = ? AND is_active = 1
    ''', (code,)).fetchone()
    
    if not gift_card:
        conn.close()
        flash('Invalid or inactive gift card code.', 'error')
        return redirect(url_for('gift_cards'))
    
    # Check if expired
    if gift_card['expires_at']:
        expires_at = datetime.strptime(gift_card['expires_at'], '%Y-%m-%d')
        if datetime.now() > expires_at:
            conn.close()
            flash('This gift card has expired.', 'error')
            return redirect(url_for('gift_cards'))
    
    # Check if already assigned to another customer
    if gift_card['customer_id'] and gift_card['customer_id'] != session['customer_id']:
        conn.close()
        flash('This gift card belongs to another customer.', 'error')
        return redirect(url_for('gift_cards'))
    
    # Assign to current customer if not assigned
    if not gift_card['customer_id']:
        conn.execute('UPDATE gift_cards SET customer_id = ? WHERE id = ?', 
                    (session['customer_id'], gift_card['id']))
        conn.commit()
    
    conn.close()
    flash(f'Gift card redeemed! Balance: P{gift_card["balance"]:.2f}', 'success')
    return redirect(url_for('gift_cards'))

# Shopping Cart Routes
@app.route('/cart')
@app.route('/view_cart')
def view_cart():
    """View shopping cart."""
    cart = session.get('cart', [])
    cart_items = []
    total = 0
    
    if cart:
        conn = get_db_connection()
        for item in cart:
            menu_item = conn.execute('SELECT * FROM menu_items WHERE id = ?', (item['id'],)).fetchone()
            if menu_item:
                cart_item = dict(menu_item)
                cart_item['quantity'] = item['quantity']
                cart_item['subtotal'] = menu_item['price'] * item['quantity']
                cart_items.append(cart_item)
                total += cart_item['subtotal']
        conn.close()
    
    return render_template('cart.html', cart_items=cart_items, total=total)

@app.route('/cart/add/<int:item_id>', methods=['POST'])
def add_to_cart(item_id):
    """Add item to cart."""
    try:
        quantity = int(request.form.get('quantity', 1))
    except (ValueError, TypeError):
        quantity = 1

    conn = get_db_connection()
    item = conn.execute('SELECT * FROM menu_items WHERE id = ?', (item_id,)).fetchone()
    conn.close()

    if not item:
        flash('Item not found.', 'error')
        return redirect(url_for('menu'))
    
    # Convert Row to dict for easier access
    item_dict = dict(item)
    
    # Check if item is available (not sold out)
    if item_dict.get('is_available', 1) == 0:
        flash(f'{item_dict["name"]} is currently sold out.', 'error')
        return redirect(request.referrer or url_for('menu'))

    cart = session.get('cart', [])

    # Check if item already in cart
    for cart_item in cart:
        if cart_item['id'] == item_id:
            cart_item['quantity'] += quantity
            break
    else:
        cart.append({'id': item_id, 'quantity': quantity})

    session['cart'] = cart
    session.permanent = True  # Ensure session persists
    flash(f'{item_dict["name"]} added to cart!', 'success')

    # Return to previous page or menu
    return redirect(request.referrer or url_for('menu'))

@app.route('/cart/update/<int:item_id>', methods=['POST'])
def update_cart(item_id):
    """Update cart item quantity."""
    quantity = int(request.form.get('quantity', 1))
    cart = session.get('cart', [])
    
    if quantity <= 0:
        cart = [item for item in cart if item['id'] != item_id]
    else:
        for item in cart:
            if item['id'] == item_id:
                item['quantity'] = quantity
                break
    
    session['cart'] = cart
    flash('Cart updated.', 'success')
    return redirect(url_for('view_cart'))

@app.route('/cart/remove/<int:item_id>', methods=['POST'])
def remove_from_cart(item_id):
    """Remove item from cart."""
    cart = session.get('cart', [])
    cart = [item for item in cart if item['id'] != item_id]
    session['cart'] = cart
    flash('Item removed from cart.', 'success')
    return redirect(url_for('view_cart'))

@app.route('/cart/clear', methods=['POST'])
def clear_cart():
    """Clear entire cart."""
    session['cart'] = []
    flash('Cart cleared.', 'success')
    return redirect(url_for('view_cart'))

# Checkout and Order Routes
@app.route('/checkout', methods=['GET', 'POST'])
@customer_login_required
def checkout():
    """Checkout page."""
    cart = session.get('cart', [])
    
    if not cart:
        flash('Your cart is empty.', 'error')
        return redirect(url_for('menu'))
    
    conn = get_db_connection()
    customer = conn.execute('SELECT * FROM customers WHERE id = ?', (session['customer_id'],)).fetchone()
    
    if not customer:
        conn.close()
        flash('Customer not found. Please log in again.', 'error')
        return redirect(url_for('customer_login'))
    
    # Convert Row to dict if needed
    if not isinstance(customer, dict):
        customer = dict(customer)
    
    # Check if customer is blacklisted
    try:
        blacklist_check = check_blacklist(customer_id=session['customer_id'], email=customer.get('email', ''), phone=customer.get('phone', ''))
        if blacklist_check:
            conn.close()
            flash('Your account has been restricted. Please contact customer service.', 'error')
            return redirect(url_for('customer_profile'))
    except Exception as e:
        print(f"Error checking blacklist: {str(e)}")
        # Continue if blacklist check fails
    
    # Check email verification
    try:
        if not is_email_verified(session['customer_id']):
            conn.close()
            flash('Please verify your email address before placing an order.', 'error')
            return redirect(url_for('verify_email'))
    except Exception as e:
        print(f"Error checking email verification: {str(e)}")
        # If verification check fails, allow checkout but log the error
        # You might want to change this to block checkout if verification is critical
    
    # Get cart items with details
    cart_items = []
    total = 0
    
    try:
        for item in cart:
            menu_item = conn.execute('SELECT * FROM menu_items WHERE id = ?', (item.get('id'),)).fetchone()
            if menu_item:
                # Convert Row to dict if needed
                if not isinstance(menu_item, dict):
                    menu_item = dict(menu_item)
                
                cart_item = menu_item.copy()
                cart_item['quantity'] = item.get('quantity', 1)
                cart_item['subtotal'] = float(menu_item.get('price', 0)) * cart_item['quantity']
                cart_items.append(cart_item)
                total += cart_item['subtotal']
    except Exception as e:
        print(f"Error processing cart items: {str(e)}")
        import traceback
        print(traceback.format_exc())
        conn.close()
        flash('Error loading cart items. Please try again.', 'error')
        return redirect(url_for('view_cart'))
    
    # Get customer's gift cards
    gift_cards = conn.execute('''
        SELECT * FROM gift_cards 
        WHERE customer_id = ? AND is_active = 1 AND balance > 0
        AND (expires_at IS NULL OR expires_at >= DATE('now'))
        ORDER BY balance DESC
    ''', (session['customer_id'],)).fetchall()
    
    if request.method == 'POST':
        pickup_time = request.form.get('pickup_time', '')
        payment_method = request.form.get('payment_method', '').strip()
        payment_proof = request.form.get('payment_proof', '').strip()
        notes = request.form.get('notes', '').strip()
        gift_card_id = request.form.get('gift_card_id', type=int)
        use_gift_card = request.form.get('use_gift_card') == 'on'
        
        if not pickup_time:
            flash('Please select a pickup time.', 'error')
            conn.close()
            return render_template('checkout.html', cart_items=cart_items, total=total, customer=customer, gift_cards=gift_cards)
        
        if not payment_method and not use_gift_card:
            flash('Please select a payment method.', 'error')
            conn.close()
            return render_template('checkout.html', cart_items=cart_items, total=total, customer=customer, gift_cards=gift_cards)
        
        # Require payment proof for non-cash payments (if not using gift card)
        if payment_method and payment_method != 'Cash' and not payment_proof and not use_gift_card:
            flash('Please provide proof of payment (transaction ID, screenshot, etc.).', 'error')
            conn.close()
            return render_template('checkout.html', cart_items=cart_items, total=total, customer=customer, gift_cards=gift_cards)
        
        # Calculate discount if promo code applied
        discount_amount = 0
        promo_code = session.get('promo_code')
        if promo_code:
            if session.get('promo_discount_type') == 'percentage':
                discount_amount = total * session.get('promo_discount_value', 0) / 100
            else:
                discount_amount = session.get('promo_discount_value', 0)
            discount_amount = min(discount_amount, total)  # Can't discount more than total
            
            # Update promo usage count
            conn.execute('UPDATE promotions SET used_count = used_count + 1 WHERE code = ?', (promo_code,))
        
        final_total = total - discount_amount
        
        # Handle gift card payment
        gift_card_used = None
        gift_card_amount = 0
        if use_gift_card and gift_card_id:
            gift_card = conn.execute('SELECT * FROM gift_cards WHERE id = ? AND customer_id = ? AND is_active = 1', 
                                    (gift_card_id, session['customer_id'])).fetchone()
            if gift_card:
                gift_card_used = gift_card
                gift_card_amount = min(gift_card['balance'], final_total)
                final_total -= gift_card_amount
                
                # Update gift card balance
                new_balance = gift_card['balance'] - gift_card_amount
                conn.execute('UPDATE gift_cards SET balance = ? WHERE id = ?', (new_balance, gift_card_id))
                
                # Record transaction
                conn.execute('''
                    INSERT INTO gift_card_transactions (gift_card_id, transaction_type, amount, description)
                    VALUES (?, 'redeemed', ?, ?)
                ''', (gift_card_id, gift_card_amount, f'Used for order payment'))
        
        # If gift card doesn't cover full amount, require another payment method
        if final_total > 0:
            if not payment_method:
                flash('Gift card balance is insufficient. Please select an additional payment method.', 'error')
                conn.close()
                return render_template('checkout.html', cart_items=cart_items, total=total, customer=customer, gift_cards=gift_cards)
            # Require payment proof for non-cash payments
            if payment_method != 'Cash' and not payment_proof:
                flash('Please provide proof of payment (transaction ID, screenshot, etc.).', 'error')
                conn.close()
                return render_template('checkout.html', cart_items=cart_items, total=total, customer=customer, gift_cards=gift_cards)
        elif final_total == 0 and gift_card_amount > 0:
            # Fully paid with gift card - no additional payment needed
            payment_method = 'Gift Card'
            payment_proof = None
        
        # Create order (pending payment verification)
        # If fully paid with gift card, auto-verify. Otherwise, verify based on payment method
        if final_total == 0 and gift_card_amount > 0:
            payment_verified = 1  # Fully paid with gift card
            payment_method = 'Gift Card'
        elif gift_card_amount > 0 and final_total > 0:
            payment_method = f'Gift Card + {payment_method}'
            payment_verified = 1 if payment_method.endswith('Cash') else 0
        else:
            payment_verified = 1 if payment_method == 'Cash' else 0  # Cash is auto-verified
        
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO orders (customer_id, total_amount, discount_amount, promo_code, pickup_time, payment_method, payment_proof, payment_verified, notes, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')
        ''', (session['customer_id'], total - discount_amount, discount_amount, promo_code, pickup_time, payment_method, payment_proof, payment_verified, notes))
        order_id = cursor.lastrowid
        
        # Add order items and deduct inventory
        for cart_item in cart_items:
            cursor.execute('''
                INSERT INTO order_items (order_id, menu_item_id, quantity, price)
                VALUES (?, ?, ?, ?)
            ''', (order_id, cart_item['id'], cart_item['quantity'], cart_item['price']))
            
            # Deduct ingredients from inventory
            required_ingredients = conn.execute('''
                SELECT ingredient_id, quantity_required
                FROM menu_item_ingredients
                WHERE menu_item_id = ?
            ''', (cart_item['id'],)).fetchall()
            
            for ing in required_ingredients:
                quantity_needed = ing['quantity_required'] * cart_item['quantity']
                ingredient_id = ing['ingredient_id']
                
                # Update stock
                conn.execute('''
                    UPDATE ingredients 
                    SET current_stock = current_stock - ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (quantity_needed, ingredient_id))
                
                # Record transaction
                conn.execute('''
                    INSERT INTO inventory_transactions (ingredient_id, transaction_type, quantity, order_id, notes)
                    VALUES (?, 'usage', ?, ?, ?)
                ''', (ingredient_id, quantity_needed, order_id, f'Used for order #{order_id}'))
        
        conn.commit()
        
        # Send order confirmation notification
        send_order_notification(session['customer_id'], order_id, 'pending', conn)
        
        conn.close()
        
        # Clear cart and promo code
        session['cart'] = []
        session.pop('promo_code', None)
        session.pop('promo_discount_type', None)
        session.pop('promo_discount_value', None)
        session.pop('promo_min_order', None)
        
        flash(f'Order #{order_id} placed successfully! Pickup at {pickup_time}.', 'success')
        return redirect(url_for('order_confirmation', order_id=order_id))
    
    conn.close()
    return render_template('checkout.html', cart_items=cart_items, total=total, customer=customer, gift_cards=gift_cards)

@app.route('/order/<int:order_id>')
@customer_login_required
def order_confirmation(order_id):
    """Order confirmation page."""
    conn = get_db_connection()
    order = conn.execute('SELECT * FROM orders WHERE id = ? AND customer_id = ?', 
                         (order_id, session['customer_id'])).fetchone()
    
    if not order:
        conn.close()
        flash('Order not found.', 'error')
        return redirect(url_for('customer_profile'))
    
    order_items = conn.execute('''
        SELECT oi.*, mi.name, mi.image_url 
        FROM order_items oi 
        JOIN menu_items mi ON oi.menu_item_id = mi.id 
        WHERE oi.order_id = ?
    ''', (order_id,)).fetchall()
    conn.close()
    
    return render_template('order_confirmation.html', order=dict(order), items=[dict(i) for i in order_items])

# Admin Order Management
@app.route('/admin/orders')
@login_required
def admin_orders():
    """Admin page to view and manage orders."""
    status_filter = request.args.get('status', 'all')
    search_query = request.args.get('search', '').strip()
    
    conn = get_db_connection()
    
    # Build query based on filters
    query = '''
        SELECT o.*, c.first_name, c.last_name, c.email, c.phone
        FROM orders o
        JOIN customers c ON o.customer_id = c.id
        WHERE 1=1
    '''
    params = []
    
    # Add status filter
    if status_filter != 'all':
        query += ' AND o.status = ?'
        params.append(status_filter)
    
    # Add search filter
    if search_query:
        query += ' AND (o.id LIKE ? OR c.first_name LIKE ? OR c.last_name LIKE ? OR c.email LIKE ? OR c.phone LIKE ?)'
        search_pattern = f'%{search_query}%'
        params.extend([search_pattern, search_pattern, search_pattern, search_pattern, search_pattern])
    
    query += ' ORDER BY o.created_at DESC'
    
    orders = conn.execute(query, params).fetchall()
    
    conn.close()
    return render_template('admin_orders.html', orders=[dict(o) for o in orders], status_filter=status_filter, search_query=search_query)

@app.route('/admin/customers')
@login_required
def admin_customers():
    """Admin page to view all customers."""
    search_query = request.args.get('search', '').strip()
    
    conn = get_db_connection()
    
    # Build query based on search
    query = '''
        SELECT c.*, 
               COUNT(o.id) as total_orders,
               COALESCE(SUM(CASE WHEN o.status = 'completed' THEN o.total_amount ELSE 0 END), 0) as total_spent
        FROM customers c
        LEFT JOIN orders o ON c.id = o.customer_id
        WHERE 1=1
    '''
    params = []
    
    # Add search filter
    if search_query:
        query += ' AND (c.first_name LIKE ? OR c.last_name LIKE ? OR c.email LIKE ? OR c.phone LIKE ?)'
        search_pattern = f'%{search_query}%'
        params.extend([search_pattern, search_pattern, search_pattern, search_pattern])
    
    query += ' GROUP BY c.id ORDER BY c.created_at DESC'
    
    customers = conn.execute(query, params).fetchall()
    customers_list = [dict(c) for c in customers]
    
    # Calculate summary statistics
    total_customers = len(customers_list)
    total_orders = sum(c.get('total_orders', 0) or 0 for c in customers_list)
    total_revenue = sum(float(c.get('total_spent', 0) or 0) for c in customers_list)
    
    conn.close()
    return render_template('admin_customers.html', 
                         customers=customers_list, 
                         search_query=search_query,
                         total_customers=total_customers,
                         total_orders=total_orders,
                         total_revenue=total_revenue)

@app.route('/admin/orders/<int:order_id>')
@login_required
def admin_order_detail(order_id):
    """Admin page to view order details."""
    conn = get_db_connection()
    order = conn.execute('''
        SELECT o.*, c.first_name, c.last_name, c.email, c.phone
        FROM orders o
        JOIN customers c ON o.customer_id = c.id
        WHERE o.id = ?
    ''', (order_id,)).fetchone()
    
    if not order:
        conn.close()
        flash('Order not found.', 'error')
        return redirect(url_for('admin_orders'))
    
    items = conn.execute('''
        SELECT oi.*, mi.name, mi.image_url 
        FROM order_items oi 
        JOIN menu_items mi ON oi.menu_item_id = mi.id 
        WHERE oi.order_id = ?
    ''', (order_id,)).fetchall()
    conn.close()
    
    return render_template('admin_order_detail.html', order=dict(order), items=[dict(i) for i in items])

@app.route('/admin/orders/<int:order_id>/verify-payment', methods=['POST'])
@login_required
def admin_verify_payment(order_id):
    """Admin route to verify payment."""
    conn = get_db_connection()
    order = conn.execute('SELECT * FROM orders WHERE id = ?', (order_id,)).fetchone()
    
    if not order:
        conn.close()
        flash('Order not found.', 'error')
        return redirect(url_for('admin_orders'))
    
    conn.execute('UPDATE orders SET payment_verified = 1 WHERE id = ?', (order_id,))
    conn.commit()
    conn.close()
    
    flash('Payment verified successfully.', 'success')
    return redirect(url_for('admin_order_detail', order_id=order_id))

@app.route('/admin/orders/<int:order_id>/confirm-call', methods=['POST'])
@login_required
def admin_confirm_call(order_id):
    """Admin route to mark confirmation call as made."""
    conn = get_db_connection()
    order = conn.execute('SELECT * FROM orders WHERE id = ?', (order_id,)).fetchone()
    
    if not order:
        conn.close()
        flash('Order not found.', 'error')
        return redirect(url_for('admin_orders'))
    
    conn.execute('UPDATE orders SET confirmation_called = 1 WHERE id = ?', (order_id,))
    conn.commit()
    conn.close()
    
    flash('Confirmation call marked as completed.', 'success')
    return redirect(url_for('admin_order_detail', order_id=order_id))

@app.route('/admin/orders/<int:order_id>/mark-no-show', methods=['POST'])
@login_required
def admin_mark_no_show(order_id):
    """Admin route to mark order as no-show."""
    conn = get_db_connection()
    order = conn.execute('SELECT * FROM orders WHERE id = ?', (order_id,)).fetchone()
    
    if not order:
        conn.close()
        flash('Order not found.', 'error')
        return redirect(url_for('admin_orders'))
    
    # Update customer no-show count
    conn.execute('''
        UPDATE customers SET no_show_count = no_show_count + 1 
        WHERE id = ?
    ''', (order['customer_id'],))
    
    customer = conn.execute('SELECT * FROM customers WHERE id = ?', (order['customer_id'],)).fetchone()
    
    # Auto-blacklist after 3 no-shows
    if customer['no_show_count'] >= 3:
        # Check if already blacklisted
        existing = conn.execute('SELECT * FROM blacklist WHERE customer_id = ?', (order['customer_id'],)).fetchone()
        if not existing:
            conn.execute('''
                INSERT INTO blacklist (customer_id, email, phone, reason, no_show_count)
                VALUES (?, ?, ?, ?, ?)
            ''', (order['customer_id'], customer['email'], customer['phone'], 
                  'Multiple no-shows (3+)', customer['no_show_count']))
            flash(f'Customer blacklisted due to {customer["no_show_count"]} no-shows.', 'error')
    
    # Update order status
    conn.execute('UPDATE orders SET status = ? WHERE id = ?', ('cancelled', order_id))
    conn.commit()
    conn.close()
    
    flash('Order marked as no-show. Customer no-show count updated.', 'success')
    return redirect(url_for('admin_order_detail', order_id=order_id))

@app.route('/admin/blacklist')
@admin_required
def admin_blacklist():
    """Admin page to view blacklisted customers."""
    conn = get_db_connection()
    blacklisted = conn.execute('''
        SELECT b.*, c.first_name, c.last_name, c.email, c.phone
        FROM blacklist b
        LEFT JOIN customers c ON b.customer_id = c.id
        WHERE b.is_active = 1
        ORDER BY b.created_at DESC
    ''').fetchall()
    conn.close()
    return render_template('admin_blacklist.html', blacklisted=[dict(b) for b in blacklisted])

@app.route('/admin/blacklist/remove/<int:blacklist_id>', methods=['POST'])
@admin_required
def admin_remove_blacklist(blacklist_id):
    """Remove customer from blacklist."""
    conn = get_db_connection()
    conn.execute('UPDATE blacklist SET is_active = 0 WHERE id = ?', (blacklist_id,))
    conn.commit()
    conn.close()
    flash('Customer removed from blacklist.', 'success')
    return redirect(url_for('admin_blacklist'))

@app.route('/admin/orders/<int:order_id>/status', methods=['POST'])
@login_required
def admin_update_order_status(order_id):
    """Admin route to update order status."""
    new_status = request.form.get('status')
    valid_statuses = ['pending', 'confirmed', 'preparing', 'ready', 'completed', 'cancelled']
    
    if new_status not in valid_statuses:
        flash('Invalid status.', 'error')
        return redirect(url_for('admin_order_detail', order_id=order_id))
    
    conn = None
    try:
        conn = get_db_connection()
        
        # Get current order status to check if we need to award points
        current_order = conn.execute('SELECT customer_id, total_amount, status, payment_method, payment_verified FROM orders WHERE id = ?', (order_id,)).fetchone()
        if not current_order:
            flash('Order not found.', 'error')
            if conn:
                conn.close()
            return redirect(url_for('admin_orders'))
        
        # Check payment verification for non-cash payments when confirming
        if new_status in ['confirmed', 'preparing', 'ready'] and current_order['payment_method'] and current_order['payment_method'] != 'Cash':
            if not current_order['payment_verified']:
                flash('Payment must be verified before confirming this order.', 'error')
                if conn:
                    conn.close()
                return redirect(url_for('admin_order_detail', order_id=order_id))
        
        # Update order status
        conn.execute('''
            UPDATE orders SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?
        ''', (new_status, order_id))
        
        # Award loyalty points when order is completed (only if it wasn't already completed)
        if new_status == 'completed' and current_order['status'] != 'completed':
            points_earned = int(current_order['total_amount'])
            customer_id = current_order['customer_id']
            
            # Check if points were already awarded for this order
            existing_transaction = conn.execute('''
                SELECT id FROM loyalty_transactions WHERE order_id = ? AND transaction_type = 'earned'
            ''', (order_id,)).fetchone()
            
            if not existing_transaction:
                # Update or create loyalty points
                existing = conn.execute('SELECT * FROM loyalty_points WHERE customer_id = ?', (customer_id,)).fetchone()
                if existing:
                    conn.execute('''
                        UPDATE loyalty_points 
                        SET points = points + ?, total_earned = total_earned + ?, updated_at = CURRENT_TIMESTAMP
                        WHERE customer_id = ?
                    ''', (points_earned, points_earned, customer_id))
                else:
                    conn.execute('''
                        INSERT INTO loyalty_points (customer_id, points, total_earned)
                        VALUES (?, ?, ?)
                    ''', (customer_id, points_earned, points_earned))
                
                # Record transaction
                conn.execute('''
                    INSERT INTO loyalty_transactions (customer_id, points, transaction_type, description, order_id)
                    VALUES (?, ?, 'earned', ?, ?)
                ''', (customer_id, points_earned, f'Points earned from order #{order_id}', order_id))
        
        # Track cancellations
        if new_status == 'cancelled' and current_order['status'] != 'cancelled':
            conn.execute('''
                UPDATE customers SET cancelled_count = cancelled_count + 1 
                WHERE id = ?
            ''', (current_order['customer_id'],))
            
            customer = conn.execute('SELECT * FROM customers WHERE id = ?', (current_order['customer_id'],)).fetchone()
            
            # Auto-blacklist after 5 cancellations
            if customer['cancelled_count'] >= 5:
                existing = conn.execute('SELECT * FROM blacklist WHERE customer_id = ?', (current_order['customer_id'],)).fetchone()
                if not existing:
                    conn.execute('''
                        INSERT INTO blacklist (customer_id, email, phone, reason, cancelled_count)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (current_order['customer_id'], customer['email'], customer['phone'], 
                          'Multiple cancellations (5+)', customer['cancelled_count']))
        
        conn.commit()
        
        # Send notification to customer if status changed
        if new_status != current_order['status']:
            print(f"Status changed from {current_order['status']} to {new_status} for order #{order_id}")
            try:
                send_order_notification(current_order['customer_id'], order_id, new_status, conn)
            except Exception as e:
                print(f"Error in send_order_notification: {e}")
                import traceback
                traceback.print_exc()
        
        flash(f'Order #{order_id} status updated to {new_status}.', 'success')
    except sqlite3.OperationalError as e:
        if conn:
            conn.rollback()
        flash(f'Database error: {str(e)}. Please try again.', 'error')
        print(f"Database error: {e}")
    except Exception as e:
        if conn:
            conn.rollback()
        flash('An error occurred while updating the order status.', 'error')
        print(f"Error: {e}")
    finally:
        if conn:
            conn.close()
    
    return redirect(url_for('admin_order_detail', order_id=order_id))

# Reviews & Ratings Routes
@app.route('/review/<int:order_id>', methods=['GET', 'POST'])
@customer_login_required
def review_order(order_id):
    """Review order items."""
    conn = get_db_connection()
    order = conn.execute('SELECT * FROM orders WHERE id = ? AND customer_id = ?', 
                        (order_id, session['customer_id'])).fetchone()
    
    if not order:
        conn.close()
        flash('Order not found.', 'error')
        return redirect(url_for('customer_profile'))
    
    if request.method == 'POST':
        menu_item_id = request.form.get('menu_item_id')
        rating = int(request.form.get('rating', 0))
        comment = request.form.get('comment', '').strip()
        
        if not menu_item_id or rating < 1 or rating > 5:
            flash('Please provide a valid rating.', 'error')
            conn.close()
            return redirect(url_for('review_order', order_id=order_id))
        
        # Check if review already exists
        existing = conn.execute('''
            SELECT id FROM reviews WHERE customer_id = ? AND menu_item_id = ? AND order_id = ?
        ''', (session['customer_id'], menu_item_id, order_id)).fetchone()
        
        if existing:
            conn.execute('''
                UPDATE reviews SET rating = ?, comment = ? WHERE id = ?
            ''', (rating, comment, existing['id']))
            flash('Review updated!', 'success')
        else:
            conn.execute('''
                INSERT INTO reviews (customer_id, menu_item_id, order_id, rating, comment)
                VALUES (?, ?, ?, ?, ?)
            ''', (session['customer_id'], menu_item_id, order_id, rating, comment))
            flash('Thank you for your review!', 'success')
        
        conn.commit()
        conn.close()
        return redirect(url_for('review_order', order_id=order_id))
    
    # Get order items
    items = conn.execute('''
        SELECT oi.*, mi.name, mi.image_url, mi.id as menu_item_id,
               (SELECT rating FROM reviews WHERE customer_id = ? AND menu_item_id = mi.id AND order_id = ?) as user_rating,
               (SELECT comment FROM reviews WHERE customer_id = ? AND menu_item_id = mi.id AND order_id = ?) as user_comment
        FROM order_items oi
        JOIN menu_items mi ON oi.menu_item_id = mi.id
        WHERE oi.order_id = ?
    ''', (session['customer_id'], order_id, session['customer_id'], order_id, order_id)).fetchall()
    
    conn.close()
    return render_template('review_order.html', order=dict(order), items=[dict(i) for i in items])

@app.route('/menu/<int:item_id>/reviews')
def view_item_reviews(item_id):
    """View reviews for a menu item."""
    conn = get_db_connection()
    item = conn.execute('SELECT * FROM menu_items WHERE id = ?', (item_id,)).fetchone()
    
    if not item:
        conn.close()
        flash('Menu item not found.', 'error')
        return redirect(url_for('menu'))
    
    reviews = conn.execute('''
        SELECT r.*, c.first_name, c.last_name
        FROM reviews r
        JOIN customers c ON r.customer_id = c.id
        WHERE r.menu_item_id = ? AND r.is_approved = 1
        ORDER BY r.created_at DESC
    ''', (item_id,)).fetchall()
    
    # Calculate average rating
    avg_rating = conn.execute('''
        SELECT AVG(rating) as avg, COUNT(*) as count
        FROM reviews WHERE menu_item_id = ? AND is_approved = 1
    ''', (item_id,)).fetchone()
    
    conn.close()
    return render_template('item_reviews.html', item=dict(item), reviews=[dict(r) for r in reviews], 
                         avg_rating=avg_rating['avg'] or 0, review_count=avg_rating['count'] or 0)

# Loyalty Program Routes
@app.route('/loyalty')
@app.route('/loyalty_program')
@customer_login_required
def loyalty_program():
    """View loyalty points and history."""
    conn = get_db_connection()
    points = conn.execute('SELECT * FROM loyalty_points WHERE customer_id = ?', 
                         (session['customer_id'],)).fetchone()
    
    if not points:
        # Initialize with 0 points
        conn.execute('INSERT INTO loyalty_points (customer_id, points) VALUES (?, 0)', 
                    (session['customer_id'],))
        conn.commit()
        points = conn.execute('SELECT * FROM loyalty_points WHERE customer_id = ?', 
                            (session['customer_id'],)).fetchone()
    
    transactions = conn.execute('''
        SELECT * FROM loyalty_transactions 
        WHERE customer_id = ? 
        ORDER BY created_at DESC 
        LIMIT 20
    ''', (session['customer_id'],)).fetchall()
    
    conn.close()
    return render_template('loyalty.html', points=dict(points), transactions=[dict(t) for t in transactions])

# Password Reset Routes
# Email Verification Routes
@app.route('/verify-email', methods=['GET', 'POST'], endpoint='verify_email')
@customer_login_required
def verify_email():
    """Email verification page."""
    conn = get_db_connection()
    customer = conn.execute('SELECT * FROM customers WHERE id = ?', (session['customer_id'],)).fetchone()
    
    if not customer['email']:
        conn.close()
        flash('Email address not found. Please contact support.', 'error')
        return redirect(url_for('customer_profile'))
    
    # Check if email_verified column exists
    try:
        # Try to access email_verified column
        email_verified = customer.get('email_verified', 0) if customer else 0
        # If column doesn't exist, the get will return None, so convert to 0
        if email_verified is None:
            email_verified = 0
    except (KeyError, AttributeError, TypeError):
        # Column doesn't exist in database yet
        email_verified = 0
    
    if email_verified == 1:
        conn.close()
        flash('Your email is already verified.', 'success')
        return redirect(url_for('customer_profile'))
    
    if request.method == 'POST':
        try:
            code = request.form.get('verification_code', '').strip()
            
            if not code:
                flash('Please enter the verification code.', 'error')
                conn.close()
                return render_template('verify_email.html', customer=dict(customer))
            
            # Check verification code
            verification = conn.execute('''
                SELECT * FROM email_verifications 
                WHERE customer_id = ? AND verification_code = ? AND is_verified = 0
                ORDER BY created_at DESC LIMIT 1
            ''', (session['customer_id'], code)).fetchone()
            
            if verification:
                # Convert Row to dict if needed
                if not isinstance(verification, dict):
                    verification = dict(verification)
                
                # Check if code is expired (15 minutes)
                try:
                    if verification.get('expires_at'):
                        expires_at = datetime.strptime(verification['expires_at'], '%Y-%m-%d %H:%M:%S')
                        if datetime.now() > expires_at:
                            conn.close()
                            flash('Verification code has expired. Please request a new one.', 'error')
                            return render_template('verify_email.html', customer=dict(customer))
                except (ValueError, TypeError) as e:
                    print(f"Error parsing expiration date: {str(e)}")
                    # If we can't parse the date, assume it's valid and proceed
                
                # Mark as verified
                try:
                    conn.execute('UPDATE email_verifications SET is_verified = 1 WHERE id = ?', (verification['id'],))
                    
                    # Check if email_verified column exists, if not add it
                    try:
                        conn.execute('UPDATE customers SET email_verified = 1 WHERE id = ?', (session['customer_id'],))
                    except sqlite3.OperationalError as e:
                        # Column doesn't exist, add it
                        print(f"Adding email_verified column: {str(e)}")
                        conn.execute('ALTER TABLE customers ADD COLUMN email_verified INTEGER DEFAULT 0')
                        conn.execute('UPDATE customers SET email_verified = 1 WHERE id = ?', (session['customer_id'],))
                    
                    conn.commit()
                    conn.close()
                    
                    flash('Email address verified successfully!', 'success')
                    return redirect(url_for('customer_profile'))
                except Exception as e:
                    import traceback
                    print(f"Error updating verification status: {str(e)}")
                    print(traceback.format_exc())
                    conn.close()
                    flash(f'Error verifying email: {str(e)}. Please try again or contact support.', 'error')
                    return render_template('verify_email.html', customer=dict(customer))
            else:
                conn.close()
                flash('Invalid verification code. Please try again.', 'error')
                return render_template('verify_email.html', customer=dict(customer))
        except Exception as e:
            import traceback
            print(f"Error in verify_email POST: {str(e)}")
            print(traceback.format_exc())
            conn.close()
            flash(f'An error occurred: {str(e)}. Please try again.', 'error')
            return render_template('verify_email.html', customer=dict(customer))
    
    conn.close()
    return render_template('verify_email.html', customer=dict(customer))

@app.route('/send-verification-code', methods=['POST'])
@customer_login_required
def send_verification_code():
    """Send verification code to customer's email."""
    conn = get_db_connection()
    customer = conn.execute('SELECT * FROM customers WHERE id = ?', (session['customer_id'],)).fetchone()
    
    if not customer['email']:
        conn.close()
        flash('Email address not found. Please contact support.', 'error')
        return redirect(url_for('customer_profile'))
    
    # Generate code
    code = generate_verification_code()
    expires_at = (datetime.now() + timedelta(minutes=15)).strftime('%Y-%m-%d %H:%M:%S')
    
    # Save verification code
    conn.execute('''
        INSERT INTO email_verifications (customer_id, email, verification_code, expires_at)
        VALUES (?, ?, ?, ?)
    ''', (session['customer_id'], customer['email'], code, expires_at))
    conn.commit()
    
    # Send verification email via Flask-Mail
    if app.config.get('MAIL_PASSWORD') and app.config.get('MAIL_USERNAME'):
        try:
            subject = 'Email Verification Code - Cafe Next Door'
            body = f'''
Hello {customer['first_name']},

Thank you for registering with Cafe Next Door!

Your email verification code is: {code}

This code will expire in 15 minutes.

If you didn't request this code, please ignore this email.

Best regards,
Cafe Next Door Team
'''
            msg = Message(
                subject=subject,
                recipients=[customer['email']],
                body=body,
                sender=app.config.get('MAIL_DEFAULT_SENDER', app.config.get('MAIL_USERNAME', 'noreply@cafenextdoor.com'))
            )
            mail.send(msg)
            flash('Verification code has been sent to your email address!', 'success')
        except Exception as e:
            print(f"Error sending verification email: {str(e)}")
            flash(f'Error sending verification email: {str(e)}. Please try again later or contact support.', 'error')
    else:
        flash('Email service is not configured. Please set MAIL_USERNAME and MAIL_PASSWORD in your environment variables.', 'error')
    
    conn.close()
    return redirect(url_for('verify_email'))

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Request password reset."""
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        
        if not email:
            flash('Please enter your email address.', 'error')
            return render_template('forgot_password.html')
        
        conn = get_db_connection()
        customer = conn.execute('SELECT * FROM customers WHERE email = ?', (email,)).fetchone()
        
        if customer:
            # Generate secure token
            token = secrets.token_urlsafe(32)
            expires_at = (datetime.now() + timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S')
            
            # Invalidate any existing tokens for this customer
            conn.execute('UPDATE password_reset_tokens SET used = 1 WHERE customer_id = ? AND used = 0', (customer['id'],))
            
            # Store token
            conn.execute('''
                INSERT INTO password_reset_tokens (customer_id, token, expires_at)
                VALUES (?, ?, ?)
            ''', (customer['id'], token, expires_at))
            conn.commit()
            conn.close()
            
            # Generate reset link
            reset_link = url_for('reset_password', token=token, _external=True)

            # Send password reset email via Flask-Mail
            if app.config.get('MAIL_PASSWORD') and app.config.get('MAIL_USERNAME'):
                try:
                    subject = 'Password Reset Request - Cafe Next Door'
                    body = f'''
Hello {customer['first_name']},

You requested to reset your password for your Cafe Next Door account.

Click the link below to reset your password:
{reset_link}

This link will expire in 1 hour.

If you didn't request a password reset, please ignore this email. Your password will remain unchanged.

Best regards,
Cafe Next Door Team
'''
                    msg = Message(
                        subject=subject,
                        recipients=[email],
                        body=body,
                        sender=app.config.get('MAIL_DEFAULT_SENDER', app.config.get('MAIL_USERNAME', 'noreply@cafenextdoor.com'))
                    )
                    mail.send(msg)
                    print(f"Password reset email sent to {email}")
                except Exception as e:
                    print(f"Error sending password reset email: {str(e)}")
                    flash('Error sending password reset email. Please try again later or contact support.', 'error')
                    conn.close()
                    return render_template('forgot_password.html')
            
            conn.close()
            flash('If an account exists with that email, password reset instructions have been sent.', 'success')
            return redirect(url_for('customer_login'))
        else:
            # Don't reveal if email exists - still show success message
            conn.close()
            flash('If an account exists with that email, password reset instructions have been sent.', 'success')
            return redirect(url_for('customer_login'))
    
    return render_template('forgot_password.html')

@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Reset password with token."""
    conn = get_db_connection()
    
    # Find valid token
    reset_token = conn.execute('''
        SELECT pt.*, c.email 
        FROM password_reset_tokens pt
        JOIN customers c ON pt.customer_id = c.id
        WHERE pt.token = ? AND pt.used = 0 AND pt.expires_at > datetime('now')
    ''', (token,)).fetchone()
    
    if not reset_token:
        conn.close()
        flash('Invalid or expired reset link. Please request a new one.', 'error')
        return redirect(url_for('forgot_password'))
    
    if request.method == 'POST':
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if not password or not confirm_password:
            flash('Please fill in all fields.', 'error')
            conn.close()
            return render_template('reset_password.html', token=token)
        
        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            conn.close()
            return render_template('reset_password.html', token=token)
        
        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'error')
            conn.close()
            return render_template('reset_password.html', token=token)
        
        # Update password
        password_hash = generate_password_hash(password)
        conn.execute('UPDATE customers SET password_hash = ? WHERE id = ?', 
                    (password_hash, reset_token['customer_id']))
        
        # Mark token as used
        conn.execute('UPDATE password_reset_tokens SET used = 1 WHERE id = ?', (reset_token['id'],))
        conn.commit()
        conn.close()
        
        flash('Password reset successfully! You can now log in with your new password.', 'success')
        return redirect(url_for('customer_login'))
    
    conn.close()
    return render_template('reset_password.html', token=token)

# Favorites/Wishlist Routes
@app.route('/favorites/add/<int:item_id>', methods=['POST'])
@customer_login_required
def add_to_favorites(item_id):
    """Add item to favorites."""
    conn = get_db_connection()
    try:
        conn.execute('INSERT INTO favorites (customer_id, menu_item_id) VALUES (?, ?)',
                    (session['customer_id'], item_id))
        conn.commit()
        flash('Added to favorites!', 'success')
    except sqlite3.IntegrityError:
        flash('Already in favorites.', 'error')
    conn.close()
    return redirect(request.referrer or url_for('menu'))

@app.route('/favorites/remove/<int:item_id>', methods=['POST'])
@customer_login_required
def remove_from_favorites(item_id):
    """Remove item from favorites."""
    conn = get_db_connection()
    conn.execute('DELETE FROM favorites WHERE customer_id = ? AND menu_item_id = ?',
                (session['customer_id'], item_id))
    conn.commit()
    conn.close()
    flash('Removed from favorites.', 'success')
    return redirect(request.referrer or url_for('menu'))

@app.route('/favorites')
@customer_login_required
def view_favorites():
    """View favorites/wishlist."""
    conn = get_db_connection()
    rows = conn.execute('''
        SELECT mi.* FROM menu_items mi
        JOIN favorites f ON mi.id = f.menu_item_id
        WHERE f.customer_id = ?
        ORDER BY f.created_at DESC
    ''', (session['customer_id'],)).fetchall()
    conn.close()
    items = [dict(row) for row in rows]
    return render_template('favorites.html', items=items)

# Newsletter Routes
@app.route('/newsletter/subscribe', methods=['POST'])
def newsletter_subscribe():
    """Subscribe to newsletter."""
    email = request.form.get('email', '').strip().lower()
    name = request.form.get('name', '').strip()
    honeypot = request.form.get('website_url', '')  # Honeypot field
    
    # Honeypot check
    if honeypot:
        flash('Subscription failed.', 'error')
        return redirect(request.referrer or url_for('index'))
    
    # Validate email
    if not email or '@' not in email or '.' not in email.split('@')[-1]:
        flash('Please enter a valid email address.', 'error')
        return redirect(request.referrer or url_for('index'))
    
    # Block common disposable email domains
    disposable_domains = ['tempmail.com', 'throwaway.com', 'mailinator.com', 'guerrillamail.com', 
                          'fakeinbox.com', '10minutemail.com', 'trashmail.com']
    email_domain = email.split('@')[-1]
    if email_domain in disposable_domains:
        flash('Please use a valid email address.', 'error')
        return redirect(request.referrer or url_for('index'))
    
    # Rate limiting - check IP
    ip_address = get_client_ip()
    conn = get_db_connection()
    
    # Check for recent subscriptions from this IP (max 2 per minute)
    one_minute_ago = datetime.now() - timedelta(minutes=1)
    recent_subs = conn.execute('''
        SELECT COUNT(*) FROM newsletter_subscribers 
        WHERE created_at > ? AND id IN (
            SELECT MAX(id) FROM newsletter_subscribers GROUP BY email
        )
    ''', (one_minute_ago.strftime('%Y-%m-%d %H:%M:%S'),)).fetchone()[0]
    
    # Simple rate limit using session
    last_sub_time = session.get('last_newsletter_sub')
    if last_sub_time:
        time_diff = datetime.now() - datetime.fromisoformat(last_sub_time)
        if time_diff.total_seconds() < 10:
            conn.close()
            flash('Please wait a moment before subscribing again.', 'error')
            return redirect(request.referrer or url_for('index'))
    
    try:
        conn.execute('INSERT INTO newsletter_subscribers (email, name) VALUES (?, ?)', (email, name or None))
        conn.commit()
        session['last_newsletter_sub'] = datetime.now().isoformat()
        flash('Successfully subscribed to our newsletter!', 'success')
    except sqlite3.IntegrityError:
        flash('This email is already subscribed.', 'error')
    conn.close()
    return redirect(request.referrer or url_for('index'))

@app.route('/admin/newsletter')
@login_required
def admin_newsletter():
    """Admin page to view newsletter subscribers."""
    conn = get_db_connection()
    subscribers = conn.execute('SELECT * FROM newsletter_subscribers ORDER BY created_at DESC').fetchall()
    conn.close()
    return render_template('admin_newsletter.html', subscribers=[dict(s) for s in subscribers])

# Analytics Dashboard
@app.route('/admin/analytics')
@login_required
def admin_analytics():
    """Admin analytics dashboard with date filtering."""
    conn = get_db_connection()
    
    # Get date filter (default: all time)
    date_filter = request.args.get('period', 'all')
    start_date = None
    end_date = datetime.now().strftime('%Y-%m-%d')
    
    if date_filter == 'today':
        start_date = datetime.now().strftime('%Y-%m-%d')
    elif date_filter == 'week':
        start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    elif date_filter == 'month':
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    elif date_filter == 'year':
        start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
    elif date_filter == 'custom':
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date') or end_date
    
    # Build WHERE clause for date filtering
    date_where = ""
    date_params = []
    if start_date:
        date_where = "AND DATE(o.created_at) >= ? AND DATE(o.created_at) <= ?"
        date_params = [start_date, end_date]
    
    # Total revenue
    total_revenue_query = 'SELECT COALESCE(SUM(total_amount), 0) FROM orders WHERE status != "cancelled"'
    if start_date:
        total_revenue_query += ' AND DATE(created_at) >= ? AND DATE(created_at) <= ?'
    total_revenue = conn.execute(total_revenue_query, date_params if start_date else []).fetchone()[0]
    
    # Order counts by status
    order_stats_query = 'SELECT status, COUNT(*) as count FROM orders WHERE 1=1'
    if start_date:
        order_stats_query += ' AND DATE(created_at) >= ? AND DATE(created_at) <= ?'
    order_stats_query += ' GROUP BY status'
    order_stats = conn.execute(order_stats_query, date_params if start_date else []).fetchall()
    order_stats = {row['status']: row['count'] for row in order_stats}
    
    # Total orders
    total_orders_query = 'SELECT COUNT(*) FROM orders WHERE 1=1'
    if start_date:
        total_orders_query += ' AND DATE(created_at) >= ? AND DATE(created_at) <= ?'
    total_orders = conn.execute(total_orders_query, date_params if start_date else []).fetchone()[0]
    
    # Completed orders
    completed_orders_query = 'SELECT COUNT(*) FROM orders WHERE status = "completed"'
    if start_date:
        completed_orders_query += ' AND DATE(created_at) >= ? AND DATE(created_at) <= ?'
    completed_orders = conn.execute(completed_orders_query, date_params if start_date else []).fetchone()[0]
    
    # Average order value
    avg_order_value = total_revenue / completed_orders if completed_orders > 0 else 0
    
    # Total customers
    total_customers = conn.execute('SELECT COUNT(*) FROM customers').fetchone()[0]
    
    # New customers in period
    new_customers_query = 'SELECT COUNT(*) FROM customers WHERE 1=1'
    if start_date:
        new_customers_query += ' AND DATE(created_at) >= ? AND DATE(created_at) <= ?'
    new_customers = conn.execute(new_customers_query, date_params if start_date else []).fetchone()[0]
    
    # Total menu items
    total_menu_items = conn.execute('SELECT COUNT(*) FROM menu_items').fetchone()[0]
    
    # Newsletter subscribers
    total_subscribers = conn.execute('SELECT COUNT(*) FROM newsletter_subscribers WHERE is_active = 1').fetchone()[0]
    
    # Top selling items
    top_items_query = '''
        SELECT mi.name, SUM(oi.quantity) as total_sold, SUM(oi.quantity * oi.price) as revenue
        FROM order_items oi
        JOIN menu_items mi ON oi.menu_item_id = mi.id
        JOIN orders o ON oi.order_id = o.id
        WHERE o.status != 'cancelled'
    '''
    if start_date:
        top_items_query += ' AND DATE(o.created_at) >= ? AND DATE(o.created_at) <= ?'
    top_items_query += '''
        GROUP BY mi.id
        ORDER BY total_sold DESC
        LIMIT 10
    '''
    top_items = conn.execute(top_items_query, date_params if start_date else []).fetchall()
    
    # Recent orders (last 7 days or selected period)
    if date_filter == 'all' or date_filter == 'year':
        days_back = 30
    elif date_filter == 'month':
        days_back = 30
    else:
        days_back = 7
    
    period_start = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
    recent_orders_query = '''
        SELECT DATE(created_at) as date, COUNT(*) as count, SUM(total_amount) as revenue
        FROM orders WHERE created_at >= ? AND status != 'cancelled'
        GROUP BY DATE(created_at) ORDER BY date
    '''
    recent_orders = conn.execute(recent_orders_query, (period_start,)).fetchall()
    
    # Sales by category
    category_sales_query = '''
        SELECT mi.category, SUM(oi.quantity) as total_sold, SUM(oi.quantity * oi.price) as revenue
        FROM order_items oi
        JOIN menu_items mi ON oi.menu_item_id = mi.id
        JOIN orders o ON oi.order_id = o.id
        WHERE o.status != 'cancelled'
    '''
    if start_date:
        category_sales_query += ' AND DATE(o.created_at) >= ? AND DATE(o.created_at) <= ?'
    category_sales_query += '''
        GROUP BY mi.category
        ORDER BY revenue DESC
    '''
    category_sales = conn.execute(category_sales_query, date_params if start_date else []).fetchall()
    
    # Hourly sales pattern (for today or last 7 days)
    hourly_sales_query = '''
        SELECT strftime('%H', created_at) as hour, COUNT(*) as count, SUM(total_amount) as revenue
        FROM orders WHERE status != 'cancelled'
    '''
    if date_filter == 'today':
        hourly_sales_query += ' AND DATE(created_at) = DATE("now")'
    else:
        hourly_sales_query += ' AND created_at >= datetime("now", "-7 days")'
    hourly_sales_query += ' GROUP BY hour ORDER BY hour'
    hourly_sales = conn.execute(hourly_sales_query).fetchall()
    
    # Top customers by revenue
    top_customers_query = '''
        SELECT c.id, c.first_name, c.last_name, c.email, 
               COUNT(o.id) as order_count, SUM(o.total_amount) as total_spent
        FROM customers c
        JOIN orders o ON c.id = o.customer_id
        WHERE o.status != 'cancelled'
    '''
    if start_date:
        top_customers_query += ' AND DATE(o.created_at) >= ? AND DATE(o.created_at) <= ?'
    top_customers_query += '''
        GROUP BY c.id
        ORDER BY total_spent DESC
        LIMIT 10
    '''
    top_customers = conn.execute(top_customers_query, date_params if start_date else []).fetchall()
    
    # Revenue trend (monthly for year view, daily for shorter periods)
    if date_filter == 'year':
        # Monthly grouping for year view
        revenue_trend_query = '''
            SELECT strftime('%Y-%m', created_at) as period, 
                   COUNT(*) as count, COALESCE(SUM(total_amount), 0) as revenue
            FROM orders WHERE status != 'cancelled'
        '''
        if start_date:
            revenue_trend_query += ' AND DATE(created_at) >= ? AND DATE(created_at) <= ?'
        revenue_trend_query += ' GROUP BY period ORDER BY period'
        revenue_trend = conn.execute(revenue_trend_query, date_params if start_date else []).fetchall()
    else:
        # Daily grouping for shorter periods
        revenue_trend_query = '''
            SELECT DATE(created_at) as period, 
                   COUNT(*) as count, COALESCE(SUM(total_amount), 0) as revenue
            FROM orders WHERE status != 'cancelled'
        '''
        if start_date:
            revenue_trend_query += ' AND DATE(created_at) >= ? AND DATE(created_at) <= ?'
        else:
            # Default to last 30 days if no date filter
            revenue_trend_query += ' AND created_at >= datetime("now", "-30 days")'
        revenue_trend_query += ' GROUP BY period ORDER BY period'
        revenue_trend = conn.execute(revenue_trend_query, date_params if start_date else []).fetchall()
    
    conn.close()
    
    return render_template('admin_analytics.html', 
                          total_revenue=total_revenue,
                          order_stats=order_stats,
                          total_orders=total_orders,
                          completed_orders=completed_orders,
                          avg_order_value=avg_order_value,
                          total_customers=total_customers,
                          new_customers=new_customers,
                          total_menu_items=total_menu_items,
                          total_subscribers=total_subscribers,
                          top_items=[dict(i) for i in top_items],
                          recent_orders=[dict(o) for o in recent_orders],
                          category_sales=[dict(c) for c in category_sales],
                          hourly_sales=[dict(h) for h in hourly_sales],
                          top_customers=[dict(tc) for tc in top_customers],
                          revenue_trend=[dict(rt) for rt in revenue_trend],
                          date_filter=date_filter,
                          start_date=start_date,
                          end_date=end_date)

def get_analytics_data(date_filter='all', start_date=None, end_date=None):
    """Helper function to get analytics data for export."""
    if end_date is None:
        end_date = datetime.now().strftime('%Y-%m-%d')
    
    conn = get_db_connection()
    
    # Build date params
    date_params = []
    if start_date:
        date_params = [start_date, end_date]
    
    # Get all analytics data
    total_revenue_query = 'SELECT COALESCE(SUM(total_amount), 0) FROM orders WHERE status != "cancelled"'
    if start_date:
        total_revenue_query += ' AND DATE(created_at) >= ? AND DATE(created_at) <= ?'
    total_revenue = conn.execute(total_revenue_query, date_params if start_date else []).fetchone()[0]
    
    total_orders_query = 'SELECT COUNT(*) FROM orders WHERE 1=1'
    if start_date:
        total_orders_query += ' AND DATE(created_at) >= ? AND DATE(created_at) <= ?'
    total_orders = conn.execute(total_orders_query, date_params if start_date else []).fetchone()[0]
    
    completed_orders_query = 'SELECT COUNT(*) FROM orders WHERE status = "completed"'
    if start_date:
        completed_orders_query += ' AND DATE(created_at) >= ? AND DATE(created_at) <= ?'
    completed_orders = conn.execute(completed_orders_query, date_params if start_date else []).fetchone()[0]
    
    avg_order_value = total_revenue / completed_orders if completed_orders > 0 else 0
    
    # Top items
    top_items_query = '''
        SELECT mi.name, SUM(oi.quantity) as total_sold, SUM(oi.quantity * oi.price) as revenue
        FROM order_items oi
        JOIN menu_items mi ON oi.menu_item_id = mi.id
        JOIN orders o ON oi.order_id = o.id
        WHERE o.status != 'cancelled'
    '''
    if start_date:
        top_items_query += ' AND DATE(o.created_at) >= ? AND DATE(o.created_at) <= ?'
    top_items_query += '''
        GROUP BY mi.id
        ORDER BY total_sold DESC
        LIMIT 10
    '''
    top_items = conn.execute(top_items_query, date_params if start_date else []).fetchall()
    
    # Category sales
    category_sales_query = '''
        SELECT mi.category, SUM(oi.quantity) as total_sold, SUM(oi.quantity * oi.price) as revenue
        FROM order_items oi
        JOIN menu_items mi ON oi.menu_item_id = mi.id
        JOIN orders o ON oi.order_id = o.id
        WHERE o.status != 'cancelled'
    '''
    if start_date:
        category_sales_query += ' AND DATE(o.created_at) >= ? AND DATE(o.created_at) <= ?'
    category_sales_query += '''
        GROUP BY mi.category
        ORDER BY revenue DESC
    '''
    category_sales = conn.execute(category_sales_query, date_params if start_date else []).fetchall()
    
    # Top customers
    top_customers_query = '''
        SELECT c.id, c.first_name, c.last_name, c.email, 
               COUNT(o.id) as order_count, SUM(o.total_amount) as total_spent
        FROM customers c
        JOIN orders o ON c.id = o.customer_id
        WHERE o.status != 'cancelled'
    '''
    if start_date:
        top_customers_query += ' AND DATE(o.created_at) >= ? AND DATE(o.created_at) <= ?'
    top_customers_query += '''
        GROUP BY c.id
        ORDER BY total_spent DESC
        LIMIT 10
    '''
    top_customers = conn.execute(top_customers_query, date_params if start_date else []).fetchall()
    
    # Order stats
    order_stats_query = 'SELECT status, COUNT(*) as count FROM orders WHERE 1=1'
    if start_date:
        order_stats_query += ' AND DATE(created_at) >= ? AND DATE(created_at) <= ?'
    order_stats_query += ' GROUP BY status'
    order_stats = conn.execute(order_stats_query, date_params if start_date else []).fetchall()
    
    conn.close()
    
    return {
        'total_revenue': total_revenue,
        'total_orders': total_orders,
        'completed_orders': completed_orders,
        'avg_order_value': avg_order_value,
        'top_items': [dict(i) for i in top_items],
        'category_sales': [dict(c) for c in category_sales],
        'top_customers': [dict(tc) for tc in top_customers],
        'order_stats': {row['status']: row['count'] for row in order_stats},
        'date_filter': date_filter,
        'start_date': start_date,
        'end_date': end_date
    }

@app.route('/admin/analytics/export/csv')
@login_required
def export_analytics_csv():
    """Export analytics data to CSV."""
    date_filter = request.args.get('period', 'all')
    start_date = None
    end_date = datetime.now().strftime('%Y-%m-%d')
    
    if date_filter == 'today':
        start_date = datetime.now().strftime('%Y-%m-%d')
    elif date_filter == 'week':
        start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    elif date_filter == 'month':
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    elif date_filter == 'year':
        start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
    elif date_filter == 'custom':
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date') or end_date
    
    data = get_analytics_data(date_filter, start_date, end_date)
    
    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(['Cafe Next Door - Analytics Report'])
    writer.writerow([f'Period: {date_filter.title()}'])
    if start_date:
        writer.writerow([f'Date Range: {start_date} to {end_date}'])
    writer.writerow([f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'])
    writer.writerow([])
    
    # Summary Statistics
    writer.writerow(['SUMMARY STATISTICS'])
    writer.writerow(['Metric', 'Value'])
    writer.writerow(['Total Revenue', f"P{data['total_revenue']:.2f}"])
    writer.writerow(['Total Orders', data['total_orders']])
    writer.writerow(['Completed Orders', data['completed_orders']])
    writer.writerow(['Average Order Value', f"P{data['avg_order_value']:.2f}"])
    writer.writerow([])
    
    # Order Status Breakdown
    writer.writerow(['ORDER STATUS BREAKDOWN'])
    writer.writerow(['Status', 'Count'])
    for status, count in data['order_stats'].items():
        writer.writerow([status.title(), count])
    writer.writerow([])
    
    # Top Selling Items
    writer.writerow(['TOP SELLING ITEMS'])
    writer.writerow(['Rank', 'Item Name', 'Quantity Sold', 'Revenue (P)'])
    for idx, item in enumerate(data['top_items'], 1):
        writer.writerow([idx, item['name'], item['total_sold'], f"{item['revenue']:.2f}"])
    writer.writerow([])
    
    # Sales by Category
    writer.writerow(['SALES BY CATEGORY'])
    writer.writerow(['Category', 'Items Sold', 'Revenue (P)'])
    for cat in data['category_sales']:
        writer.writerow([cat['category'], cat['total_sold'], f"{cat['revenue']:.2f}"])
    writer.writerow([])
    
    # Top Customers
    writer.writerow(['TOP CUSTOMERS BY REVENUE'])
    writer.writerow(['Rank', 'Name', 'Email', 'Orders', 'Total Spent (P)'])
    for idx, customer in enumerate(data['top_customers'], 1):
        writer.writerow([
            idx,
            f"{customer['first_name']} {customer['last_name']}",
            customer['email'],
            customer['order_count'],
            f"{customer['total_spent']:.2f}"
        ])
    
    # Create response
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = f'attachment; filename=analytics_{date_filter}_{datetime.now().strftime("%Y%m%d")}.csv'
    
    return response

@app.route('/admin/analytics/export/pdf')
@login_required
def export_analytics_pdf():
    """Export analytics data to PDF."""
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.units import inch
    except ImportError:
        flash('PDF export requires reportlab library. Please install it: pip install reportlab', 'error')
        return redirect(url_for('admin_analytics'))
    
    date_filter = request.args.get('period', 'all')
    start_date = None
    end_date = datetime.now().strftime('%Y-%m-%d')
    
    if date_filter == 'today':
        start_date = datetime.now().strftime('%Y-%m-%d')
    elif date_filter == 'week':
        start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    elif date_filter == 'month':
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    elif date_filter == 'year':
        start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
    elif date_filter == 'custom':
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date') or end_date
    
    data = get_analytics_data(date_filter, start_date, end_date)
    
    # Create PDF in memory
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    story = []
    styles = getSampleStyleSheet()
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#2a1810'),
        spaceAfter=30,
    )
    story.append(Paragraph('Cafe Next Door - Analytics Report', title_style))
    story.append(Spacer(1, 0.2*inch))
    
    # Period info
    period_text = f"Period: {date_filter.title()}"
    if start_date:
        period_text += f" ({start_date} to {end_date})"
    story.append(Paragraph(period_text, styles['Normal']))
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
    story.append(Spacer(1, 0.3*inch))
    
    # Summary Statistics
    story.append(Paragraph('<b>SUMMARY STATISTICS</b>', styles['Heading2']))
    summary_data = [
        ['Metric', 'Value'],
        ['Total Revenue', f"P{data['total_revenue']:.2f}"],
        ['Total Orders', str(data['total_orders'])],
        ['Completed Orders', str(data['completed_orders'])],
        ['Average Order Value', f"P{data['avg_order_value']:.2f}"],
    ]
    summary_table = Table(summary_data)
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#8b4513')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 0.3*inch))
    
    # Top Selling Items
    story.append(Paragraph('<b>TOP SELLING ITEMS</b>', styles['Heading2']))
    items_data = [['Rank', 'Item Name', 'Quantity Sold', 'Revenue (P)']]
    for idx, item in enumerate(data['top_items'], 1):
        items_data.append([str(idx), item['name'], str(item['total_sold']), f"{item['revenue']:.2f}"])
    items_table = Table(items_data)
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#8b4513')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 0.3*inch))
    
    # Sales by Category
    story.append(Paragraph('<b>SALES BY CATEGORY</b>', styles['Heading2']))
    category_data = [['Category', 'Items Sold', 'Revenue (P)']]
    for cat in data['category_sales']:
        category_data.append([cat['category'], str(cat['total_sold']), f"{cat['revenue']:.2f}"])
    category_table = Table(category_data)
    category_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#8b4513')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    story.append(category_table)
    
    # Build PDF
    doc.build(story)
    buffer.seek(0)
    
    # Create response
    response = make_response(buffer.read())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=analytics_{date_filter}_{datetime.now().strftime("%Y%m%d")}.pdf'
    
    return response

# Inventory Management
@app.route('/admin/inventory')
@login_required
def admin_inventory():
    """Admin page to manage inventory."""
    conn = get_db_connection()
    
    # Get filter
    filter_type = request.args.get('filter', 'all')
    search_query = request.args.get('search', '').strip()
    
    # Build query
    query = 'SELECT * FROM ingredients WHERE 1=1'
    params = []
    
    if filter_type == 'low_stock':
        query += ' AND current_stock <= min_stock'
    elif filter_type == 'out_of_stock':
        query += ' AND current_stock <= 0'
    elif filter_type == 'active':
        query += ' AND is_active = 1'
    
    if search_query:
        query += ' AND name LIKE ?'
        params.append(f'%{search_query}%')
    
    query += ' ORDER BY name'
    
    ingredients = conn.execute(query, params).fetchall()
    
    # Get low stock count
    low_stock_count = conn.execute('SELECT COUNT(*) FROM ingredients WHERE current_stock <= min_stock AND is_active = 1').fetchone()[0]
    out_of_stock_count = conn.execute('SELECT COUNT(*) FROM ingredients WHERE current_stock <= 0 AND is_active = 1').fetchone()[0]
    
    conn.close()
    return render_template('admin_inventory.html', 
                         ingredients=[dict(i) for i in ingredients],
                         filter_type=filter_type,
                         search_query=search_query,
                         low_stock_count=low_stock_count,
                         out_of_stock_count=out_of_stock_count)

@app.route('/admin/inventory/add', methods=['GET', 'POST'])
@manager_required
def admin_add_ingredient():
    """Add new ingredient."""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        unit = request.form.get('unit', '').strip()
        current_stock = request.form.get('current_stock', type=float) or 0
        min_stock = request.form.get('min_stock', type=float) or 0
        cost_per_unit = request.form.get('cost_per_unit', type=float) or 0
        supplier = request.form.get('supplier', '').strip()
        category = request.form.get('category', '').strip()
        
        if not name or not unit:
            flash('Name and unit are required.', 'error')
            return render_template('admin_ingredient_form.html')
        
        conn = get_db_connection()
        try:
            conn.execute('''
                INSERT INTO ingredients (name, unit, current_stock, min_stock, cost_per_unit, supplier, category)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (name, unit, current_stock, min_stock, cost_per_unit, supplier, category))
            conn.commit()
            conn.close()
            flash('Ingredient added successfully!', 'success')
            return redirect(url_for('admin_inventory'))
        except sqlite3.IntegrityError:
            conn.close()
            flash('An ingredient with this name already exists.', 'error')
            return render_template('admin_ingredient_form.html')
    
    return render_template('admin_ingredient_form.html')

@app.route('/admin/inventory/<int:ingredient_id>/edit', methods=['GET', 'POST'])
@manager_required
def admin_edit_ingredient(ingredient_id):
    """Edit ingredient."""
    conn = get_db_connection()
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        unit = request.form.get('unit', '').strip()
        current_stock = request.form.get('current_stock', type=float) or 0
        min_stock = request.form.get('min_stock', type=float) or 0
        cost_per_unit = request.form.get('cost_per_unit', type=float) or 0
        supplier = request.form.get('supplier', '').strip()
        category = request.form.get('category', '').strip()
        is_active = 1 if request.form.get('is_active') == 'on' else 0
        
        if not name or not unit:
            flash('Name and unit are required.', 'error')
            ingredient = conn.execute('SELECT * FROM ingredients WHERE id = ?', (ingredient_id,)).fetchone()
            conn.close()
            return render_template('admin_ingredient_form.html', ingredient=dict(ingredient))
        
        try:
            conn.execute('''
                UPDATE ingredients 
                SET name = ?, unit = ?, current_stock = ?, min_stock = ?, cost_per_unit = ?, 
                    supplier = ?, category = ?, is_active = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (name, unit, current_stock, min_stock, cost_per_unit, supplier, category, is_active, ingredient_id))
            conn.commit()
            conn.close()
            flash('Ingredient updated successfully!', 'success')
            return redirect(url_for('admin_inventory'))
        except sqlite3.IntegrityError:
            conn.close()
            flash('An ingredient with this name already exists.', 'error')
            ingredient = conn.execute('SELECT * FROM ingredients WHERE id = ?', (ingredient_id,)).fetchone()
            return render_template('admin_ingredient_form.html', ingredient=dict(ingredient))
    
    ingredient = conn.execute('SELECT * FROM ingredients WHERE id = ?', (ingredient_id,)).fetchone()
    conn.close()
    
    if not ingredient:
        flash('Ingredient not found.', 'error')
        return redirect(url_for('admin_inventory'))
    
    return render_template('admin_ingredient_form.html', ingredient=dict(ingredient))

@app.route('/admin/inventory/<int:ingredient_id>/update-stock', methods=['POST'])
@manager_required
def admin_update_stock(ingredient_id):
    """Update ingredient stock."""
    adjustment = request.form.get('adjustment', type=float)
    notes = request.form.get('notes', '').strip()
    
    if adjustment is None:
        flash('Please enter an adjustment amount.', 'error')
        return redirect(url_for('admin_inventory'))
    
    conn = get_db_connection()
    ingredient = conn.execute('SELECT * FROM ingredients WHERE id = ?', (ingredient_id,)).fetchone()
    
    if not ingredient:
        conn.close()
        flash('Ingredient not found.', 'error')
        return redirect(url_for('admin_inventory'))
    
    new_stock = ingredient['current_stock'] + adjustment
    
    if new_stock < 0:
        conn.close()
        flash('Stock cannot be negative.', 'error')
        return redirect(url_for('admin_inventory'))
    
    # Update stock
    conn.execute('''
        UPDATE ingredients 
        SET current_stock = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    ''', (new_stock, ingredient_id))
    
    # Record transaction
    transaction_type = 'restock' if adjustment > 0 else 'usage'
    conn.execute('''
        INSERT INTO inventory_transactions (ingredient_id, transaction_type, quantity, notes)
        VALUES (?, ?, ?, ?)
    ''', (ingredient_id, transaction_type, abs(adjustment), notes or f'Stock {transaction_type}'))
    
    conn.commit()
    conn.close()
    
    flash(f'Stock updated successfully. New stock: {new_stock:.2f} {ingredient["unit"]}', 'success')
    return redirect(url_for('admin_inventory'))

@app.route('/admin/inventory/<int:ingredient_id>/delete', methods=['POST'])
@admin_required
def admin_delete_ingredient(ingredient_id):
    """Delete ingredient (admin only)."""
    conn = get_db_connection()
    conn.execute('UPDATE ingredients SET is_active = 0 WHERE id = ?', (ingredient_id,))
    conn.commit()
    conn.close()
    flash('Ingredient deactivated.', 'success')
    return redirect(url_for('admin_inventory'))

@app.route('/admin/inventory/<int:ingredient_id>')
@login_required
def admin_ingredient_detail(ingredient_id):
    """View ingredient details and transactions."""
    conn = get_db_connection()
    ingredient = conn.execute('SELECT * FROM ingredients WHERE id = ?', (ingredient_id,)).fetchone()
    
    if not ingredient:
        conn.close()
        flash('Ingredient not found.', 'error')
        return redirect(url_for('admin_inventory'))
    
    # Get transactions
    transactions = conn.execute('''
        SELECT * FROM inventory_transactions 
        WHERE ingredient_id = ?
        ORDER BY created_at DESC
        LIMIT 50
    ''', (ingredient_id,)).fetchall()
    
    # Get menu items using this ingredient
    menu_items = conn.execute('''
        SELECT mi.*, mii.quantity_required
        FROM menu_items mi
        JOIN menu_item_ingredients mii ON mi.id = mii.menu_item_id
        WHERE mii.ingredient_id = ?
    ''', (ingredient_id,)).fetchall()
    
    conn.close()
    return render_template('admin_ingredient_detail.html',
                         ingredient=dict(ingredient),
                         transactions=[dict(t) for t in transactions],
                         menu_items=[dict(mi) for mi in menu_items])

@app.route('/admin/inventory/export/csv')
@login_required
def export_inventory_csv():
    """Export inventory data to CSV."""
    filter_type = request.args.get('filter', 'all')
    search_query = request.args.get('search', '').strip()
    
    conn = get_db_connection()
    
    # Build query (same as admin_inventory)
    query = 'SELECT * FROM ingredients WHERE 1=1'
    params = []
    
    if filter_type == 'low_stock':
        query += ' AND current_stock <= min_stock'
    elif filter_type == 'out_of_stock':
        query += ' AND current_stock <= 0'
    elif filter_type == 'active':
        query += ' AND is_active = 1'
    
    if search_query:
        query += ' AND name LIKE ?'
        params.append(f'%{search_query}%')
    
    query += ' ORDER BY name'
    
    ingredients = conn.execute(query, params).fetchall()
    conn.close()
    
    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(['Cafe Next Door - Inventory Report'])
    writer.writerow([f'Filter: {filter_type.title()}'])
    if search_query:
        writer.writerow([f'Search: {search_query}'])
    writer.writerow([f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'])
    writer.writerow([])
    
    # Column headers
    writer.writerow(['ID', 'Name', 'Category', 'Current Stock', 'Min Stock', 'Unit', 'Cost/Unit', 'Supplier', 'Status'])
    
    # Write data
    for ing in ingredients:
        ing_dict = dict(ing)
        status = 'Out of Stock' if ing_dict['current_stock'] <= 0 else \
                 'Low Stock' if ing_dict['current_stock'] <= ing_dict['min_stock'] else \
                 'In Stock'
        if not ing_dict['is_active']:
            status = 'Inactive'
        
        writer.writerow([
            ing_dict['id'],
            ing_dict['name'],
            ing_dict['category'] or '-',
            f"{ing_dict['current_stock']:.2f}",
            f"{ing_dict['min_stock']:.2f}",
            ing_dict['unit'],
            f"P{ing_dict['cost_per_unit']:.2f}",
            ing_dict['supplier'] or '-',
            status
        ])
    
    # Create response
    output.seek(0)
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = f'attachment; filename=inventory_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    return response

@app.route('/admin/inventory/export/pdf')
@login_required
def export_inventory_pdf():
    """Export inventory data to PDF."""
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.units import inch
    except ImportError:
        flash('PDF export requires reportlab library. Please install it: pip install reportlab', 'error')
        return redirect(url_for('admin_inventory'))
    
    filter_type = request.args.get('filter', 'all')
    search_query = request.args.get('search', '').strip()
    
    conn = get_db_connection()
    
    # Build query (same as admin_inventory)
    query = 'SELECT * FROM ingredients WHERE 1=1'
    params = []
    
    if filter_type == 'low_stock':
        query += ' AND current_stock <= min_stock'
    elif filter_type == 'out_of_stock':
        query += ' AND current_stock <= 0'
    elif filter_type == 'active':
        query += ' AND is_active = 1'
    
    if search_query:
        query += ' AND name LIKE ?'
        params.append(f'%{search_query}%')
    
    query += ' ORDER BY name'
    
    ingredients = conn.execute(query, params).fetchall()
    conn.close()
    
    # Create PDF in memory
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    story = []
    styles = getSampleStyleSheet()
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#2a1810'),
        spaceAfter=30,
    )
    story.append(Paragraph('Cafe Next Door - Inventory Report', title_style))
    story.append(Spacer(1, 0.2*inch))
    
    # Filter info
    filter_text = f"Filter: {filter_type.title()}"
    if search_query:
        filter_text += f" | Search: {search_query}"
    story.append(Paragraph(filter_text, styles['Normal']))
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
    story.append(Spacer(1, 0.3*inch))
    
    # Table data
    data = [['ID', 'Name', 'Category', 'Stock', 'Min', 'Unit', 'Cost', 'Status']]
    
    for ing in ingredients:
        ing_dict = dict(ing)
        status = 'Out of Stock' if ing_dict['current_stock'] <= 0 else \
                 'Low Stock' if ing_dict['current_stock'] <= ing_dict['min_stock'] else \
                 'In Stock'
        if not ing_dict['is_active']:
            status = 'Inactive'
        
        data.append([
            str(ing_dict['id']),
            ing_dict['name'],
            ing_dict['category'] or '-',
            f"{ing_dict['current_stock']:.2f}",
            f"{ing_dict['min_stock']:.2f}",
            ing_dict['unit'],
            f"P{ing_dict['cost_per_unit']:.2f}",
            status
        ])
    
    # Create table
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#a67c52')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
    ]))
    
    story.append(table)
    
    # Build PDF
    doc.build(story)
    buffer.seek(0)
    
    # Create response
    response = make_response(buffer.getvalue())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=inventory_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
    return response

# Promotions Management
@app.route('/admin/promotions')
@login_required
def admin_promotions():
    """Admin page to manage promotions."""
    conn = get_db_connection()
    promotions = conn.execute('SELECT * FROM promotions ORDER BY created_at DESC').fetchall()
    conn.close()
    return render_template('admin_promotions.html', promotions=[dict(p) for p in promotions])

@app.route('/admin/promotions/add', methods=['GET', 'POST'])
@manager_required
def admin_add_promotion():
    """Add a new promotion."""
    if request.method == 'POST':
        code = request.form.get('code', '').strip().upper()
        description = request.form.get('description', '').strip()
        discount_type = request.form.get('discount_type')  # 'percentage' or 'fixed'
        discount_value = float(request.form.get('discount_value', 0))
        min_order = float(request.form.get('min_order_amount', 0))
        max_uses = request.form.get('max_uses')
        max_uses = int(max_uses) if max_uses else None
        start_date = request.form.get('start_date') or None
        end_date = request.form.get('end_date') or None
        
        if not code or not discount_type or discount_value <= 0:
            flash('Please fill in all required fields.', 'error')
            return render_template('admin_promotion_form.html', action='Add')
        
        conn = get_db_connection()
        try:
            conn.execute('''
                INSERT INTO promotions (code, description, discount_type, discount_value, min_order_amount, max_uses, start_date, end_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (code, description, discount_type, discount_value, min_order, max_uses, start_date, end_date))
            conn.commit()
            flash(f'Promotion "{code}" created successfully!', 'success')
        except sqlite3.IntegrityError:
            flash('A promotion with this code already exists.', 'error')
            conn.close()
            return render_template('admin_promotion_form.html', action='Add')
        conn.close()
        return redirect(url_for('admin_promotions'))
    
    return render_template('admin_promotion_form.html', action='Add')

@app.route('/admin/promotions/toggle/<int:promo_id>', methods=['POST'])
@manager_required
def admin_toggle_promotion(promo_id):
    """Toggle promotion active status."""
    conn = get_db_connection()
    promo = conn.execute('SELECT is_active FROM promotions WHERE id = ?', (promo_id,)).fetchone()
    if promo:
        new_status = 0 if promo['is_active'] else 1
        conn.execute('UPDATE promotions SET is_active = ? WHERE id = ?', (new_status, promo_id))
        conn.commit()
        flash('Promotion status updated.', 'success')
    conn.close()
    return redirect(url_for('admin_promotions'))

@app.route('/admin/promotions/delete/<int:promo_id>', methods=['POST'])
@manager_required
def admin_delete_promotion(promo_id):
    """Delete a promotion."""
    conn = get_db_connection()
    conn.execute('DELETE FROM promotions WHERE id = ?', (promo_id,))
    conn.commit()
    conn.close()
    flash('Promotion deleted.', 'success')
    return redirect(url_for('admin_promotions'))

# Apply promo code at checkout
@app.route('/apply-promo', methods=['POST'])
@customer_login_required
def apply_promo():
    """Apply a promo code."""
    code = request.form.get('promo_code', '').strip().upper()
    
    if not code:
        flash('Please enter a promo code.', 'error')
        return redirect(url_for('checkout'))
    
    conn = get_db_connection()
    promo = conn.execute('''
        SELECT * FROM promotions WHERE code = ? AND is_active = 1
    ''', (code,)).fetchone()
    
    if not promo:
        conn.close()
        flash('Invalid or expired promo code.', 'error')
        return redirect(url_for('checkout'))
    
    # Check dates
    today = datetime.now().strftime('%Y-%m-%d')
    if promo['start_date'] and promo['start_date'] > today:
        conn.close()
        flash(f'This promo code is not active yet. Valid from {promo["start_date"]}.', 'error')
        return redirect(url_for('checkout'))
    if promo['end_date'] and promo['end_date'] < today:
        conn.close()
        flash('This promo code has expired.', 'error')
        return redirect(url_for('checkout'))
    
    # Check max uses
    if promo['max_uses'] and promo['used_count'] >= promo['max_uses']:
        conn.close()
        flash('This promo code has reached its usage limit.', 'error')
        return redirect(url_for('checkout'))
    
    # Check minimum order amount
    cart = session.get('cart', [])
    cart_total = 0
    for item in cart:
        menu_item = conn.execute('SELECT price FROM menu_items WHERE id = ?', (item['id'],)).fetchone()
        if menu_item:
            cart_total += menu_item['price'] * item['quantity']
    
    if promo['min_order_amount'] and cart_total < promo['min_order_amount']:
        conn.close()
        flash(f'Minimum order of P{promo["min_order_amount"]:.2f} required for this promo code. Your cart: P{cart_total:.2f}', 'error')
        return redirect(url_for('checkout'))
    
    conn.close()
    session['promo_code'] = code
    session['promo_discount_type'] = promo['discount_type']
    session['promo_discount_value'] = promo['discount_value']
    session['promo_min_order'] = promo['min_order_amount']
    flash(f'Promo code "{code}" applied!', 'success')
    return redirect(url_for('checkout'))

@app.route('/remove-promo', methods=['POST'])
def remove_promo():
    """Remove applied promo code."""
    session.pop('promo_code', None)
    session.pop('promo_discount_type', None)
    session.pop('promo_discount_value', None)
    session.pop('promo_min_order', None)
    flash('Promo code removed.', 'success')
    return redirect(url_for('checkout'))

# Admin Users Management (Multiple Roles)
@app.route('/admin/users')
@admin_required
def admin_users():
    """Admin page to manage admin users."""
    conn = get_db_connection()
    users = conn.execute('SELECT id, username, role, full_name, created_at FROM users ORDER BY created_at DESC').fetchall()
    conn.close()
    return render_template('admin_users.html', users=[dict(u) for u in users])

@app.route('/admin/users/add', methods=['GET', 'POST'])
@admin_required
def admin_add_user():
    """Add a new admin user."""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        role = request.form.get('role', 'staff')
        full_name = request.form.get('full_name', '').strip()
        
        if not username or not password:
            flash('Please fill in all fields.', 'error')
            return render_template('admin_user_form.html', action='Add')
        
        conn = get_db_connection()
        try:
            password_hash = generate_password_hash(password)
            conn.execute('INSERT INTO users (username, password_hash, role, full_name) VALUES (?, ?, ?, ?)',
                        (username, password_hash, role, full_name or None))
            conn.commit()
            flash(f'User "{username}" created successfully!', 'success')
        except sqlite3.IntegrityError:
            flash('Username already exists.', 'error')
            conn.close()
            return render_template('admin_user_form.html', action='Add')
        conn.close()
        return redirect(url_for('admin_users'))
    
    return render_template('admin_user_form.html', action='Add')

@app.route('/admin/users/edit/<int:user_id>', methods=['GET', 'POST'])
@admin_required
def admin_edit_user(user_id):
    """Edit an admin user."""
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    
    if not user:
        conn.close()
        flash('User not found.', 'error')
        return redirect(url_for('admin_users'))
    
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        role = request.form.get('role', 'staff')
        new_password = request.form.get('password', '').strip()
        
        if new_password:
            password_hash = generate_password_hash(new_password)
            conn.execute('UPDATE users SET full_name = ?, role = ?, password_hash = ? WHERE id = ?',
                        (full_name or None, role, password_hash, user_id))
        else:
            conn.execute('UPDATE users SET full_name = ?, role = ? WHERE id = ?',
                        (full_name or None, role, user_id))
        
        conn.commit()
        conn.close()
        flash('User updated successfully!', 'success')
        return redirect(url_for('admin_users'))
    
    conn.close()
    return render_template('admin_user_form.html', action='Edit', user=dict(user))

@app.route('/admin/categories')
@manager_required
def admin_categories():
    """Admin page to manage menu categories."""
    conn = get_db_connection()
    
    # Get all distinct categories with item counts
    categories_data = conn.execute('''
        SELECT category, COUNT(*) as item_count
        FROM menu_items
        GROUP BY category
        ORDER BY category
    ''').fetchall()
    
    categories = [dict(row) for row in categories_data]
    
    conn.close()
    return render_template('admin_categories.html', categories=categories)

@app.route('/admin/categories/add', methods=['POST'])
@manager_required
def admin_add_category():
    """Add a new category."""
    category_name = request.form.get('category_name', '').strip()
    
    if not category_name:
        flash('Category name is required.', 'error')
        return redirect(url_for('admin_categories'))
    
    # Check if category already exists
    conn = get_db_connection()
    existing = conn.execute('SELECT COUNT(*) FROM menu_items WHERE category = ?', (category_name,)).fetchone()
    
    if existing[0] > 0:
        flash(f'Category "{category_name}" already exists.', 'error')
        conn.close()
        return redirect(url_for('admin_categories'))
    
    # Category will be created when a menu item uses it, so we just confirm
    conn.close()
    flash(f'Category "{category_name}" is ready to use. Add a menu item with this category to create it.', 'success')
    return redirect(url_for('admin_categories'))

@app.route('/admin/categories/delete/<category_name>', methods=['POST'])
@manager_required
def admin_delete_category(category_name):
    """Delete a category by renaming all items in it to 'Uncategorized'."""
    if not category_name:
        flash('Category name is required.', 'error')
        return redirect(url_for('admin_categories'))
    
    conn = get_db_connection()
    
    # Check how many items use this category
    item_count = conn.execute('SELECT COUNT(*) FROM menu_items WHERE category = ?', (category_name,)).fetchone()[0]
    
    if item_count == 0:
        flash('Category not found or already empty.', 'error')
        conn.close()
        return redirect(url_for('admin_categories'))
    
    # Update all items in this category to 'Uncategorized'
    conn.execute('UPDATE menu_items SET category = ? WHERE category = ?', ('Uncategorized', category_name))
    conn.commit()
    conn.close()
    
    flash(f'Category "{category_name}" deleted. {item_count} item(s) moved to "Uncategorized".', 'success')
    return redirect(url_for('admin_categories'))

@app.route('/admin/users/delete/<int:user_id>', methods=['POST'])
@admin_required
def admin_delete_user(user_id):
    """Delete an admin user."""
    if user_id == session.get('user_id'):
        flash('You cannot delete your own account.', 'error')
        return redirect(url_for('admin_users'))
    
    conn = get_db_connection()
    conn.execute('DELETE FROM users WHERE id = ?', (user_id,))
    conn.commit()
    conn.close()
    flash('User deleted.', 'success')
    return redirect(url_for('admin_users'))

# Error Handlers
@app.route('/debug/db-check')
def debug_db_check():
    """Debug route to check database state (remove in production)."""
    try:
        import os
        result = {
            'database_path': DATABASE_PATH,
            'database_dir': DATABASE_DIR,
            'database_dir_exists': os.path.exists(DATABASE_DIR),
            'database_file_exists': os.path.exists(DATABASE_PATH),
            'current_working_dir': os.getcwd(),
        }
        
        try:
            init_database()
            result['init_success'] = True
        except Exception as init_error:
            result['init_success'] = False
            result['init_error'] = str(init_error)
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Check all tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            result['tables'] = tables
            
            # Check if menu_items table exists
            menu_items_exists = 'menu_items' in tables
            result['menu_items_table_exists'] = menu_items_exists
            
            if menu_items_exists:
                cursor.execute('SELECT COUNT(*) FROM menu_items')
                menu_count = cursor.fetchone()[0]
                result['menu_items_count'] = menu_count
                
                # Try to fetch a few items
                try:
                    cursor.execute('SELECT id, name, price, category FROM menu_items LIMIT 5')
                    sample_items = cursor.fetchall()
                    result['sample_items'] = [dict(item) for item in sample_items]
                except Exception as e:
                    result['sample_items_error'] = str(e)
            
            # Check if users table exists
            users_table_exists = 'users' in tables
            result['users_table_exists'] = users_table_exists
            
            if users_table_exists:
                cursor.execute('SELECT COUNT(*) FROM users')
                user_count = cursor.fetchone()[0]
                result['users_count'] = user_count
                
                # Check admin user specifically
                cursor.execute("SELECT * FROM users WHERE username = 'admin'")
                admin_user = cursor.fetchone()
                result['admin_user_exists'] = admin_user is not None
                if admin_user:
                    result['admin_user'] = dict(admin_user)
            
            conn.close()
        except Exception as conn_error:
            result['connection_error'] = str(conn_error)
            import traceback
            result['connection_traceback'] = traceback.format_exc()
        
        import json
        return f"<h1>Database Check</h1><pre>{json.dumps(result, indent=2)}</pre>", 200
    except Exception as e:
        import traceback
        return f"<h1>Error</h1><pre>{str(e)}\n{traceback.format_exc()}</pre>", 500

@app.route('/debug/reseed-menu', methods=['GET', 'POST'])
def debug_reseed_menu():
    """Debug route to force re-seed menu items (remove in production)."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get current count before deletion
        cursor.execute('SELECT COUNT(*) FROM menu_items')
        old_count = cursor.fetchone()[0]
        
        # Delete all existing menu items (this will cascade delete related records)
        # First, delete from order_items to avoid foreign key issues
        try:
            cursor.execute('DELETE FROM order_items')
        except:
            pass
        
        try:
            cursor.execute('DELETE FROM menu_item_ingredients')
        except:
            pass
        
        try:
            cursor.execute('DELETE FROM favorites')
        except:
            pass
        
        try:
            cursor.execute('DELETE FROM reviews')
        except:
            pass
        
        # Now delete menu items
        cursor.execute('DELETE FROM menu_items')
        
        # Re-seed the database
        seed_database(cursor)
        conn.commit()
        
        # Count items
        cursor.execute('SELECT COUNT(*) FROM menu_items')
        new_count = cursor.fetchone()[0]
        
        conn.close()
        
        return f"<h1>Menu Re-seeded</h1><p>Successfully re-seeded menu.</p><p>Previous items: {old_count}</p><p>New items: {new_count}</p><p><a href='/menu'>View Menu</a> | <a href='/debug/db-check'>Check Database</a></p>", 200
    except Exception as e:
        import traceback
        return f"<h1>Error</h1><pre>{str(e)}\n{traceback.format_exc()}</pre>", 500

@app.route('/debug/reset-admin', methods=['GET', 'POST'])
def debug_reset_admin():
    """Debug route to reset/create admin user (remove in production)."""
    try:
        init_database()
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if admin user exists
        cursor.execute("SELECT * FROM users WHERE username = 'admin'")
        admin_user = cursor.fetchone()
        
        # Delete existing admin user if it exists
        if admin_user:
            cursor.execute("DELETE FROM users WHERE username = 'admin'")
        
        # Create new admin user
        default_password = generate_password_hash('admin123')
        cursor.execute('''
            INSERT INTO users (username, password_hash, role)
            VALUES (?, ?, ?)
        ''', ('admin', default_password, 'admin'))
        
        conn.commit()
        conn.close()
        
        return "<h1>Admin User Reset</h1><p>Admin user has been reset. Username: admin, Password: admin123</p><p><a href='/admin/login'>Go to Login</a></p>", 200
    except Exception as e:
        import traceback
        return f"<h1>Error</h1><pre>{str(e)}\n{traceback.format_exc()}</pre>", 500

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return render_template('error.html', error_code=404, error_message='Page not found'), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    import traceback
    if os.environ.get('FLASK_ENV') == 'production':
        # Log error but don't expose details to user
        print(f"Internal Server Error: {error}")
        print(traceback.format_exc())
        return render_template('error.html', error_code=500, error_message='An internal error occurred. Please try again later.'), 500
    else:
        # Show full error in development
        return f"<h1>Internal Server Error</h1><pre>{traceback.format_exc()}</pre>", 500

@app.errorhandler(403)
def forbidden(error):
    """Handle 403 errors."""
    return render_template('error.html', error_code=403, error_message='Access forbidden'), 403

@app.context_processor
def inject_notification_count():
    """Inject unread notification count into all templates."""
    if 'customer_id' in session:
        try:
            conn = get_db_connection()
            unread_count = conn.execute('''
                SELECT COUNT(*) as count FROM notifications 
                WHERE customer_id = ? AND is_read = 0
            ''', (session['customer_id'],)).fetchone()['count']
            conn.close()
            return {'unread_notification_count': unread_count}
        except:
            return {'unread_notification_count': 0}
    return {'unread_notification_count': 0}

if __name__ == '__main__':
    init_database()
    # Production settings
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() in ['true', '1', 'yes']
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 5000))
    
    # Never run in debug mode in production
    if os.environ.get('FLASK_ENV') == 'production':
        debug_mode = False
    
    app.run(debug=debug_mode, host=host, port=port)

