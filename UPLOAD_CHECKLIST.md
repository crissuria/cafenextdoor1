# Quick Upload Checklist

Use this when uploading to any web hosting platform.

## Before Uploading

- [ ] Create `.env` file with your production settings
- [ ] Generate `SECRET_KEY`: `python -c "import secrets; print(secrets.token_hex(32))"`
- [ ] Set `FLASK_ENV=production` in `.env`
- [ ] Set `FLASK_DEBUG=False` in `.env`
- [ ] Configure email settings in `.env` (if using email)

## Files to Upload

### ✅ Upload These:
```
app.py
wsgi.py
requirements.txt
Procfile (for Heroku/Railway)
runtime.txt (optional, for Python version)
.env (create on server, don't upload if contains real secrets)
templates/ (entire folder)
static/ (entire folder)
.gitignore
```

### ⚠️ Create on Server:
```
.env (create from env.example with your values)
database/ (folder will be created automatically)
```

### ❌ Don't Upload:
```
__pycache__/
*.pyc
venv/
.git/
.env (if it has real credentials - create fresh on server)
database/*.db (will be created automatically)
```

## After Uploading

1. **Set Environment Variables** on hosting platform
2. **Install Dependencies** (usually automatic)
3. **Initialize Database** (run once via SSH or console)
4. **Test Application** - Visit your domain
5. **Change Admin Password** - Log in and update immediately

## Quick Test

After upload, test these URLs:
- `/` - Home page
- `/menu` - Menu page
- `/admin/login` - Admin login (change password!)

## Need Help?

- See `HOSTING_GUIDE.md` for platform-specific instructions
- See `DEPLOYMENT.md` for detailed server setup
- See `PRODUCTION_CHECKLIST.md` for security checklist























