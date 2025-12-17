# Production Deployment Checklist

Use this checklist before deploying to production.

## Pre-Deployment Security

- [ ] Generate and set a strong `SECRET_KEY` in `.env` file
- [ ] Change default admin password (username: admin, default password: admin123)
- [ ] Remove or secure any hardcoded credentials
- [ ] Set `FLASK_ENV=production` in `.env`
- [ ] Set `FLASK_DEBUG=False` in `.env`
- [ ] Configure email credentials in `.env`
- [ ] Verify `.env` file is in `.gitignore` and not committed

## Server Configuration

- [ ] Install all dependencies: `pip install -r requirements.txt`
- [ ] Set up virtual environment
- [ ] Configure Gunicorn or another WSGI server
- [ ] Set up Nginx reverse proxy
- [ ] Configure SSL certificate (HTTPS)
- [ ] Set up firewall rules
- [ ] Configure proper file permissions

## Database

- [ ] Initialize database: `python -c "from app import init_database; init_database()"`
- [ ] Set proper database file permissions
- [ ] Set up automated database backups
- [ ] Test database connection

## Application

- [ ] Test all major features:
  - [ ] Customer registration and login
  - [ ] Menu browsing and ordering
  - [ ] Admin login and dashboard
  - [ ] Order management
  - [ ] Inventory management
  - [ ] Email functionality (if enabled)
- [ ] Verify error pages work (404, 500, 403)
- [ ] Test file uploads
- [ ] Verify static files are served correctly

## Monitoring

- [ ] Set up application logging
- [ ] Configure log rotation
- [ ] Set up monitoring/alerting (optional)
- [ ] Test backup restoration process

## Post-Deployment

- [ ] Change default admin password
- [ ] Test all critical user flows
- [ ] Monitor error logs for first 24 hours
- [ ] Verify email notifications work
- [ ] Test on mobile devices
- [ ] Verify HTTPS is working
- [ ] Check performance under load

## Security Hardening

- [ ] Enable HTTPS only (redirect HTTP to HTTPS)
- [ ] Set secure cookie flags
- [ ] Configure CORS if needed
- [ ] Review and limit file upload sizes
- [ ] Set up rate limiting (if not already implemented)
- [ ] Regular security updates

## Backup Strategy

- [ ] Database backup script created
- [ ] Backup schedule configured (daily recommended)
- [ ] Backup retention policy set
- [ ] Test backup restoration
- [ ] Store backups off-server

## Documentation

- [ ] Update README with production URLs
- [ ] Document admin credentials (securely)
- [ ] Document deployment process
- [ ] Create runbook for common issues

---

**Important Notes:**

1. **Never commit `.env` file to version control**
2. **Always use HTTPS in production**
3. **Change default admin password immediately**
4. **Regular backups are essential**
5. **Monitor logs regularly for errors**

For detailed deployment instructions, see `DEPLOYMENT.md`.


