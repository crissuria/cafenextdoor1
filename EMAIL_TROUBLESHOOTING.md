# Email Verification Troubleshooting Guide

## Issue: Email verification not working

If verification emails are not being sent, follow these steps:

## Step 1: Check Render Environment Variables

Go to your Render dashboard → Your Service → Environment

**Required Variables:**
```
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-gmail-app-password
MAIL_DEFAULT_SENDER=your-email@gmail.com
```

⚠️ **Important:** 
- `MAIL_PASSWORD` must be a Gmail App Password, NOT your regular Gmail password
- `MAIL_USERNAME` should be your full Gmail address
- `MAIL_DEFAULT_SENDER` should match `MAIL_USERNAME`

## Step 2: Get Gmail App Password

1. Go to [Google Account](https://myaccount.google.com/)
2. Click **Security** (left sidebar)
3. Enable **2-Step Verification** (if not already enabled)
4. Scroll down to **App passwords**
5. Click **App passwords**
6. Select **Mail** and your device
7. Click **Generate**
8. Copy the 16-character password (no spaces)
9. Paste it into Render's `MAIL_PASSWORD` environment variable

## Step 3: Check Render Logs

1. Go to Render dashboard → Your Service → **Logs**
2. Look for these messages:

**If email is configured correctly:**
```
Attempting to send verification email to user@example.com
Using sender: your-email@gmail.com
SMTP server: smtp.gmail.com:587
✓ Verification email sent successfully to user@example.com
  Verification code: 123456
```

**If email is NOT configured:**
```
EMAIL ERROR: Email service is not configured...
MAIL_USERNAME is set: False
MAIL_PASSWORD is set: False
```

**If email fails to send:**
```
✗ EMAIL SEND FAILED: Error sending verification email: [error details]
```

## Step 4: Common Errors and Fixes

### Error: "Email service is not configured"
**Fix:** Set `MAIL_USERNAME` and `MAIL_PASSWORD` in Render environment variables

### Error: "Authentication failed" or "Invalid credentials"
**Fix:** 
- Make sure you're using a Gmail App Password, not your regular password
- Verify 2-Step Verification is enabled
- Check that `MAIL_USERNAME` is your full email address

### Error: "Connection refused" or "Connection timeout"
**Fix:**
- Verify `MAIL_SERVER=smtp.gmail.com`
- Verify `MAIL_PORT=587`
- Verify `MAIL_USE_TLS=True`

### Error: "Sender address rejected"
**Fix:**
- Make sure `MAIL_DEFAULT_SENDER` matches `MAIL_USERNAME`
- Use your full Gmail address for both

## Step 5: Test Email Configuration

After setting environment variables:

1. **Redeploy** your service in Render (or wait for auto-deploy)
2. Try registering a new account
3. Check Render logs for email sending attempts
4. Check your email inbox (and spam folder)

## Step 6: Debug Verification Code

If emails aren't sending but you need to verify an account:

1. Check Render logs for: `DEBUG: Verification code for [email]: [code]`
2. The verification code will be logged there
3. You can manually enter it on the verification page

## Alternative: Use SendGrid or Mailgun

If Gmail continues to have issues, consider using a professional email service:

### SendGrid Setup:
```
MAIL_SERVER=smtp.sendgrid.net
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=apikey
MAIL_PASSWORD=your-sendgrid-api-key
MAIL_DEFAULT_SENDER=your-verified-sender@domain.com
```

### Mailgun Setup:
```
MAIL_SERVER=smtp.mailgun.org
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-mailgun-username
MAIL_PASSWORD=your-mailgun-password
MAIL_DEFAULT_SENDER=noreply@yourdomain.com
```

## Quick Checklist

- [ ] `MAIL_USERNAME` is set in Render
- [ ] `MAIL_PASSWORD` is set in Render (Gmail App Password)
- [ ] `MAIL_DEFAULT_SENDER` matches `MAIL_USERNAME`
- [ ] `MAIL_SERVER=smtp.gmail.com`
- [ ] `MAIL_PORT=587`
- [ ] `MAIL_USE_TLS=True`
- [ ] Gmail 2-Step Verification is enabled
- [ ] Gmail App Password is generated
- [ ] Service has been redeployed after setting variables
- [ ] Checked Render logs for errors

## Still Not Working?

1. Check Render logs for specific error messages
2. Verify all environment variables are set correctly
3. Try generating a new Gmail App Password
4. Consider using SendGrid or Mailgun for better reliability
5. Check if your Gmail account has any restrictions

---

**Note:** On Render's free tier, the service may spin down after inactivity. The first request after spin-down may take longer, but email should still work once the service is running.
