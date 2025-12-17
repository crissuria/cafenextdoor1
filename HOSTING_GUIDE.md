# Web Hosting Platform Upload Guide

This guide explains how to deploy Cafe Next Door to different types of web hosting platforms.

## Types of Web Hosting

### 1. Shared Hosting (cPanel, Plesk, etc.)
**Examples:** Bluehost, HostGator, SiteGround, GoDaddy

**Can you upload directly?** ✅ **YES, but with limitations**

**Requirements:**
- Python support (Python 3.8+)
- Flask support (may need to request from hosting provider)
- Database access (MySQL/PostgreSQL preferred over SQLite for shared hosting)
- SSH access (for some configurations)

**Steps:**
1. Upload all files via FTP/cPanel File Manager
2. Set up Python environment (if supported)
3. Configure database (may need to use MySQL instead of SQLite)
4. Set environment variables via hosting control panel
5. Point domain to your application

**Limitations:**
- May not support Gunicorn (might need to use mod_wsgi or hosting's Python handler)
- SQLite may have permission issues (use MySQL/PostgreSQL if available)
- Limited control over server configuration

---

### 2. VPS/Cloud Hosting (Full Control)
**Examples:** DigitalOcean, AWS EC2, Linode, Vultr, Azure

**Can you upload directly?** ✅ **YES - Full Control**

**Best Option:** Follow `DEPLOYMENT.md` guide
- Full server control
- Can use Gunicorn + Nginx
- Best performance and security

---

### 3. Platform-as-a-Service (PaaS)
**Examples:** Heroku, Railway, Render, PythonAnywhere, Fly.io

**Can you upload directly?** ✅ **YES - Easiest Option**

**Recommended for beginners!** These platforms handle most server setup automatically.

---

## Quick Deployment Options

### Option A: Railway (Easiest - Recommended)

1. **Sign up at** [railway.app](https://railway.app)

2. **Connect your repository** (GitHub/GitLab) or upload files

3. **Railway auto-detects Flask** and sets up everything

4. **Add environment variables:**
   - `SECRET_KEY` (generate one)
   - `FLASK_ENV=production`
   - `FLASK_DEBUG=False`
   - Email settings (if needed)

5. **Deploy!** Railway handles the rest

**Pros:**
- Free tier available
- Automatic HTTPS
- Easy database setup
- No server management

---

### Option B: Render (Also Easy)

1. **Sign up at** [render.com](https://render.com)

2. **Create new Web Service**

3. **Connect repository or upload files**

4. **Configure:**
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn wsgi:application`

5. **Add environment variables** (same as Railway)

6. **Deploy!**

**Pros:**
- Free tier available
- Automatic HTTPS
- PostgreSQL database option

---

### Option C: PythonAnywhere (Beginner-Friendly)

1. **Sign up at** [pythonanywhere.com](https://www.pythonanywhere.com)

2. **Upload files via Files tab**

3. **Create Web App:**
   - Choose Flask
   - Point to your `app.py`

4. **Configure WSGI file:**
   ```python
   import sys
   path = '/home/yourusername/cafenextdoor'
   if path not in sys.path:
       sys.path.append(path)
   
   from wsgi import application
   ```

5. **Set environment variables** in Files → `.env`

6. **Reload web app**

**Pros:**
- Free tier available
- Beginner-friendly interface
- Good for learning

---

### Option D: Traditional Shared Hosting (cPanel)

**If your hosting supports Python/Flask:**

1. **Upload all files** via FTP or cPanel File Manager to:
   ```
   public_html/
   ├── app.py
   ├── wsgi.py
   ├── requirements.txt
   ├── .env
   ├── templates/
   ├── static/
   └── database/
   ```

2. **Create `.env` file** with your configuration

3. **Set up Python environment** (if hosting provides it)

4. **Configure database:**
   - May need to switch from SQLite to MySQL
   - Update database connection in `app.py` if needed

5. **Point domain** to your application

**Important Notes:**
- Check with your hosting provider if they support Flask
- May need to use hosting's Python handler instead of Gunicorn
- SQLite may have permission issues - use MySQL if available

---

## Files to Upload

### Required Files:
```
✅ app.py
✅ wsgi.py
✅ requirements.txt
✅ .env (create from env.example, don't upload example)
✅ .gitignore
✅ templates/ (entire folder)
✅ static/ (entire folder)
✅ database/ (folder - will be created if doesn't exist)
```

### Optional Files (for reference):
```
📄 README.md
📄 DEPLOYMENT.md
📄 PRODUCTION_CHECKLIST.md
📄 DOCUMENTATION.md
```

### DO NOT Upload:
```
❌ .env (if it contains real credentials - create on server)
❌ __pycache__/
❌ *.pyc files
❌ venv/ (virtual environment)
❌ .git/ (if using Git)
```

---

## Pre-Upload Checklist

Before uploading to any hosting platform:

- [ ] Create `.env` file with production values
- [ ] Generate secure `SECRET_KEY`
- [ ] Set `FLASK_ENV=production`
- [ ] Set `FLASK_DEBUG=False`
- [ ] Configure email settings (if using email)
- [ ] Test locally first
- [ ] Review `PRODUCTION_CHECKLIST.md`

---

## Platform-Specific Notes

### Heroku
- Requires `Procfile`: `web: gunicorn wsgi:application`
- May need `runtime.txt` with Python version
- Uses PostgreSQL (free addon available)

### Railway
- Auto-detects Flask
- Can use SQLite or PostgreSQL
- Free tier: 500 hours/month

### Render
- Free tier: spins down after inactivity
- PostgreSQL available
- Automatic HTTPS

### PythonAnywhere
- Free tier: limited to one web app
- Must reload after code changes
- Good for testing

### Shared Hosting (cPanel)
- May need to request Python/Flask support
- Check for mod_wsgi or Python handler
- May need to use MySQL instead of SQLite

---

## After Uploading

1. **Set environment variables** on hosting platform
2. **Install dependencies:** Most platforms do this automatically, but check
3. **Initialize database:** May need to run once via SSH or hosting console
4. **Test the application:** Visit your domain
5. **Change admin password:** Log in and update immediately

---

## Troubleshooting

### "Module not found" errors
- Check that `requirements.txt` is uploaded
- Verify dependencies are installed on hosting platform

### Database errors
- Check file permissions for `database/` folder
- Consider switching to MySQL/PostgreSQL for shared hosting

### 500 Internal Server Error
- Check hosting error logs
- Verify environment variables are set
- Check file permissions

### Static files not loading
- Verify `static/` folder is uploaded
- Check hosting static file configuration
- Clear browser cache

---

## Recommendation

**For easiest deployment:** Use **Railway** or **Render**
- Free tiers available
- Automatic setup
- HTTPS included
- No server management needed

**For learning/control:** Use **VPS** (DigitalOcean, etc.)
- Follow `DEPLOYMENT.md`
- Full control
- Best performance

**For traditional hosting:** Check with your provider first
- May need special configuration
- May require MySQL instead of SQLite

---

## Quick Start Commands

### Generate Secret Key:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### Test Locally Before Upload:
```bash
# Set environment variables
export SECRET_KEY="your-generated-key"
export FLASK_ENV=production
export FLASK_DEBUG=False

# Run
python app.py
```

---

For detailed server setup, see `DEPLOYMENT.md`.
For security checklist, see `PRODUCTION_CHECKLIST.md`.

