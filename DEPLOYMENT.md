# Cafe Next Door - Production Deployment Guide

This guide will help you deploy the Cafe Next Door application to a production server.

## Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- A web server (Nginx recommended)
- A WSGI server (Gunicorn recommended)
- Domain name (optional but recommended)
- SSL certificate (for HTTPS)

## Step 1: Server Setup

### Install Python and Dependencies

```bash
# Update system packages
sudo apt update
sudo apt upgrade -y

# Install Python and pip
sudo apt install python3 python3-pip python3-venv -y

# Install Nginx
sudo apt install nginx -y
```

## Step 2: Application Setup

### Clone/Upload Your Application

```bash
# Create application directory
sudo mkdir -p /var/www/cafenextdoor
sudo chown $USER:$USER /var/www/cafenextdoor

# Upload your application files to /var/www/cafenextdoor
# Or clone from your repository
```

### Create Virtual Environment

```bash
cd /var/www/cafenextdoor
python3 -venv venv
source venv/bin/activate
```

### Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

## Step 3: Environment Configuration

### Create .env File

```bash
# Copy the example file
cp env.example .env

# Edit .env with your production values
nano .env
```

### Required Environment Variables

```env
# Generate a secure secret key:
# python -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY=your-generated-secret-key-here

FLASK_ENV=production
FLASK_DEBUG=False

# Email Configuration
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
MAIL_DEFAULT_SENDER=your-email@gmail.com
CAFE_EMAIL=your-cafe-email@gmail.com

# Server Configuration
HOST=127.0.0.1
PORT=5000
```

### Generate Secret Key

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Copy the output and use it as your `SECRET_KEY` in the `.env` file.

## Step 4: Database Setup

### Initialize Database

```bash
# Activate virtual environment
source venv/bin/activate

# Run the application once to initialize database
python3 -c "from app import init_database; init_database()"
```

### Set Proper Permissions

```bash
sudo chown -R $USER:$USER /var/www/cafenextdoor/database
chmod 755 /var/www/cafenextdoor/database
```

## Step 5: Configure Gunicorn

### Create Gunicorn Service File

```bash
sudo nano /etc/systemd/system/cafenextdoor.service
```

Add the following content:

```ini
[Unit]
Description=Cafe Next Door Gunicorn daemon
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/cafenextdoor
Environment="PATH=/var/www/cafenextdoor/venv/bin"
ExecStart=/var/www/cafenextdoor/venv/bin/gunicorn --workers 3 --bind 127.0.0.1:5000 wsgi:application

[Install]
WantedBy=multi-user.target
```

### Start and Enable Service

```bash
sudo systemctl daemon-reload
sudo systemctl start cafenextdoor
sudo systemctl enable cafenextdoor
sudo systemctl status cafenextdoor
```

## Step 6: Configure Nginx

### Create Nginx Configuration

```bash
sudo nano /etc/nginx/sites-available/cafenextdoor
```

Add the following configuration:

```nginx
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;

    # Redirect HTTP to HTTPS (uncomment after SSL setup)
    # return 301 https://$server_name$request_uri;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static {
        alias /var/www/cafenextdoor/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    client_max_body_size 16M;
}
```

### Enable Site and Test

```bash
# Create symbolic link
sudo ln -s /etc/nginx/sites-available/cafenextdoor /etc/nginx/sites-enabled/

# Test Nginx configuration
sudo nginx -t

# Restart Nginx
sudo systemctl restart nginx
```

## Step 7: SSL Certificate (Let's Encrypt)

### Install Certbot

```bash
sudo apt install certbot python3-certbot-nginx -y
```

### Obtain SSL Certificate

```bash
sudo certbot --nginx -d your-domain.com -d www.your-domain.com
```

### Auto-renewal

Certbot automatically sets up auto-renewal. Test it:

```bash
sudo certbot renew --dry-run
```

## Step 8: Security Checklist

- [ ] Change default admin password (if using default credentials)
- [ ] Set strong SECRET_KEY in .env
- [ ] Configure firewall (UFW)
- [ ] Enable HTTPS only
- [ ] Set proper file permissions
- [ ] Regular backups of database
- [ ] Monitor logs regularly

### Firewall Configuration

```bash
sudo ufw allow 'Nginx Full'
sudo ufw allow ssh
sudo ufw enable
```

### File Permissions

```bash
# Set proper ownership
sudo chown -R www-data:www-data /var/www/cafenextdoor

# Set directory permissions
find /var/www/cafenextdoor -type d -exec chmod 755 {} \;

# Set file permissions
find /var/www/cafenextdoor -type f -exec chmod 644 {} \;

# Make scripts executable
chmod +x /var/www/cafenextdoor/venv/bin/gunicorn
```

## Step 9: Database Backups

### Create Backup Script

```bash
nano /var/www/cafenextdoor/backup.sh
```

```bash
#!/bin/bash
BACKUP_DIR="/var/backups/cafenextdoor"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR
cp /var/www/cafenextdoor/database/cafe.db $BACKUP_DIR/cafe_$DATE.db
# Keep only last 30 days of backups
find $BACKUP_DIR -name "cafe_*.db" -mtime +30 -delete
```

### Make Executable and Schedule

```bash
chmod +x /var/www/cafenextdoor/backup.sh

# Add to crontab (daily at 2 AM)
crontab -e
# Add: 0 2 * * * /var/www/cafenextdoor/backup.sh
```

## Step 10: Monitoring and Logs

### View Application Logs

```bash
sudo journalctl -u cafenextdoor -f
```

### View Nginx Logs

```bash
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

## Troubleshooting

### Application Not Starting

1. Check Gunicorn service status: `sudo systemctl status cafenextdoor`
2. Check logs: `sudo journalctl -u cafenextdoor -n 50`
3. Verify .env file exists and has correct values
4. Check database permissions

### 502 Bad Gateway

1. Verify Gunicorn is running: `sudo systemctl status cafenextdoor`
2. Check if port 5000 is accessible: `netstat -tulpn | grep 5000`
3. Review Nginx error logs

### Database Errors

1. Check database file permissions
2. Verify database directory exists
3. Check disk space: `df -h`

## Updating the Application

```bash
cd /var/www/cafenextdoor
source venv/bin/activate
git pull  # If using git
pip install -r requirements.txt
sudo systemctl restart cafenextdoor
```

## Additional Resources

- [Gunicorn Documentation](https://gunicorn.org/)
- [Nginx Documentation](https://nginx.org/en/docs/)
- [Let's Encrypt Documentation](https://letsencrypt.org/docs/)
- [Flask Deployment Guide](https://flask.palletsprojects.com/en/2.3.x/deploying/)

## Support

For issues or questions, refer to the main README.md or DOCUMENTATION.md files.

