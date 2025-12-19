# Cafe Next Door - Render Deployment Guide

This guide will help you deploy the Cafe Next Door application to Render.com.

## ✅ Pre-Deployment Checklist

- [x] All code changes committed to GitHub
- [x] `.env` file is in `.gitignore` (contains sensitive data)
- [x] `requirements.txt` includes all dependencies
- [x] `Procfile` is configured correctly
- [x] `runtime.txt` specifies Python version
- [x] `wsgi.py` is set up for production

## Step 1: Create Render Account

1. Go to [render.com](https://render.com)
2. Sign up or log in
3. Connect your GitHub account

## Step 2: Create New Web Service

1. Click **"New +"** → **"Web Service"**
2. Connect your GitHub repository: `crissuria/cafenextdoor`
3. Select the repository and branch (`main`)

## Step 3: Configure Build Settings

### Basic Settings:
- **Name**: `cafenextdoor` (or your preferred name)
- **Region**: Choose closest to your users
- **Branch**: `main`
- **Root Directory**: Leave empty (or `./` if needed)

### Build Command:
```bash
pip install -r requirements.txt
```

### Start Command:
```bash
gunicorn wsgi:application
```

## Step 4: Environment Variables

Add these environment variables in Render dashboard under **"Environment"**:

### Required Variables:

```env
SECRET_KEY=your-generated-secret-key-here
FLASK_ENV=production
FLASK_DEBUG=False
DATABASE_PATH=database/cafe.db
```

### Email Configuration (Choose ONE option):

#### Option 1: ProtonMail Bridge (NOT RECOMMENDED for Render)
⚠️ ProtonMail Bridge requires a local installation, which won't work on Render.

#### Option 2: Gmail SMTP (Recommended for Render)
```env
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-gmail-app-password
MAIL_DEFAULT_SENDER=your-email@gmail.com
CAFE_EMAIL=cafenextdoor@protonmail.com
```

**To get Gmail App Password:**
1. Go to Google Account → Security
2. Enable 2-Step Verification
3. Go to App Passwords
4. Generate password for "Mail"
5. Use that password (not your regular Gmail password)

#### Option 3: Other Email Services (SendGrid, Mailgun, etc.)
```env
MAIL_SERVER=smtp.sendgrid.net
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=apikey
MAIL_PASSWORD=your-sendgrid-api-key
MAIL_DEFAULT_SENDER=cafenextdoor@protonmail.com
CAFE_EMAIL=cafenextdoor@protonmail.com
```

### Generate Secret Key:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

## Step 5: Deploy

1. Click **"Create Web Service"**
2. Render will automatically:
   - Clone your repository
   - Install dependencies
   - Build your application
   - Start the service

## Step 6: Post-Deployment Setup

### Initialize Database

After first deployment, the database will be automatically initialized when the app starts (via `init_database()` in `wsgi.py`).

### Change Admin Password

1. Visit your deployed site: `https://your-app.onrender.com/admin/login`
2. Log in with default credentials (if applicable)
3. Change the admin password immediately

### Verify Email Configuration

1. Test email verification by registering a new account
2. Check if verification emails are being sent
3. Test newsletter subscription
4. Test contact form replies

## Step 7: Custom Domain (Optional)

1. Go to your service settings
2. Click **"Custom Domains"**
3. Add your domain
4. Follow DNS configuration instructions

## Troubleshooting

### Build Fails

- Check build logs in Render dashboard
- Verify `requirements.txt` has all dependencies
- Ensure Python version in `runtime.txt` is supported

### Application Crashes

- Check logs in Render dashboard
- Verify all environment variables are set
- Check database initialization

### Email Not Working

- Verify email environment variables are correct
- For Gmail: Use App Password, not regular password
- Check Render logs for email errors
- Consider using SendGrid or Mailgun for better reliability

### Database Issues

- Database is stored in `database/cafe.db` (ephemeral on free tier)
- Consider upgrading to paid plan for persistent storage
- Or use external database (PostgreSQL) for production

## Updating the Application

1. Push changes to GitHub:
   ```bash
   git add .
   git commit -m "Your update message"
   git push origin main
   ```

2. Render will automatically detect changes and redeploy

## Important Notes

⚠️ **Free Tier Limitations:**
- Service spins down after 15 minutes of inactivity
- Database is ephemeral (data may be lost)
- Limited build minutes per month

💡 **Recommendations:**
- Upgrade to paid plan for production use
- Use external database (PostgreSQL) for data persistence
- Set up monitoring and alerts
- Regular backups of database

## Support

For issues:
1. Check Render logs
2. Review application logs
3. Verify environment variables
4. Check database initialization

---

**Last Updated**: After email verification implementation
**Status**: ✅ Ready for deployment
