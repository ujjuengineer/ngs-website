# Narasimha Global Service & Solution Pvt. Ltd. — Website

## Local Development
```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```
Open http://127.0.0.1:8000

## Deploy FREE on Railway.app (Recommended)
1. Push this folder to a GitHub repo
2. Go to https://railway.app → New Project → Deploy from GitHub
3. Select your repo
4. Add environment variables:
   - SECRET_KEY = (any long random string)
   - DEBUG = False
5. Railway auto-detects Django and deploys!

## Connect Your Hostinger Domain
After Railway gives you a URL (e.g. ngs.up.railway.app):
1. Go to Hostinger DNS Manager
2. Add a CNAME record:
   - Type: CNAME
   - Name: @ (or www)
   - Value: your-railway-url.up.railway.app
3. In Railway → Settings → Domains → Add Custom Domain → enter your domain
4. Update ALLOWED_HOSTS in settings.py to include your domain

## Alternative: Deploy on Render.com (also free)
1. Push to GitHub
2. Go to https://render.com → New Web Service
3. Connect your GitHub repo
4. It reads render.yaml automatically

## Admin Panel
Visit /admin with your superuser credentials to view contact messages.

## Email Setup (Optional)
Set these env vars to receive contact form emails:
- EMAIL_HOST_USER = your Gmail address
- EMAIL_HOST_PASSWORD = Gmail App Password (not regular password)
- CONTACT_EMAIL = where to receive messages
