"""
WSGI entry point for production deployment.
Use with Gunicorn, uWSGI, or other WSGI servers.
"""
import os
import sys
from app import app, init_database

# Initialize database on startup
try:
    init_database()
    print("Database initialized successfully on startup")
except Exception as e:
    print(f"WARNING: Error initializing database on startup: {str(e)}", file=sys.stderr)
    print("Database will be initialized on first use", file=sys.stderr)
    # Don't raise - let the app start and handle errors gracefully
    # The database will be initialized on first use if needed via get_db_connection()

# This is the application object that WSGI servers will use
application = app

if __name__ == "__main__":
    # For testing purposes only
    # In production, use: gunicorn wsgi:application
    port = int(os.environ.get('PORT', 5000))
    application.run(host='0.0.0.0', port=port, debug=False)


