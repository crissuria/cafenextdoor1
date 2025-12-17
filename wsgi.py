"""
WSGI entry point for production deployment.
Use with Gunicorn, uWSGI, or other WSGI servers.
"""
import os
from app import app, init_database

# Initialize database on startup
init_database()

# This is the application object that WSGI servers will use
application = app

if __name__ == "__main__":
    # For testing purposes only
    # In production, use: gunicorn wsgi:application
    application.run()

