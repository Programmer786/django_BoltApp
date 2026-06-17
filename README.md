# Full Django Deployment Guide on KVM Ubuntu 24.04 (IP-Based, No Domain)

## 1. Update System and Install Prerequisites

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install python3-pip python3.11-venv nginx unzip -y
```

---

## 2. Upload and Extract Your Django Project

```bash
scp cms_bolt.zip root@147.93.90.97:/root/

sudo unzip /root/cms_bolt.zip -d /var/www/

sudo mv /var/www/cms_bolt /var/www/django_project
```

---

## 3. Set Up Virtual Environment and Install Dependencies

```bash
cd /var/www/django_project

python3.11 -m venv venv

source venv/bin/activate

pip install --upgrade pip

pip install -r requirements.txt
```

---

## 4. Install Required Python Packages (If Missing)

```bash
pip install django
pip install python-dateutil
pip install openpyxl
pip install reportlab
pip install PyPDF2
pip install whitenoise
```

---

## 5. Update `settings.py`

```python
ALLOWED_HOSTS = ['147.93.90.97', 'localhost', '127.0.0.1']

STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
```

---

## 6. Apply Migrations and Collect Static Files

```bash
cd /var/www/django_project

source venv/bin/activate

python manage.py makemigrations

python manage.py migrate

python manage.py collectstatic
```

---

## 7. Test Application with Gunicorn

```bash
gunicorn --workers 3 --bind 0.0.0.0:8000 cms_bolt.wsgi:application
```

---

## 8. Create Gunicorn Systemd Service

Create the service file:

```bash
sudo nano /etc/systemd/system/gunicorn.service
```

Paste the following:

```ini
[Unit]
Description=gunicorn daemon for Django Project
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/django_project
Environment="PATH=/var/www/django_project/venv/bin"

ExecStart=/var/www/django_project/venv/bin/gunicorn \
    --workers 3 \
    --bind unix:/var/www/django_project/gunicorn.sock \
    cms_bolt.wsgi:application

[Install]
WantedBy=multi-user.target
```

---

## 9. Enable and Start Gunicorn

```bash
sudo systemctl daemon-reexec

sudo systemctl daemon-reload

sudo systemctl enable gunicorn

sudo systemctl start gunicorn

sudo systemctl restart gunicorn

sudo systemctl status gunicorn
```

---

## 10. Configure Nginx for IP-Based Access

Create the Nginx configuration:

```bash
sudo nano /etc/nginx/sites-available/django_project
```

Paste the following:

```nginx
server {
    listen 80;

    server_name 147.93.90.97;

    location /static/ {
        alias /var/www/django_project/staticfiles/;
    }

    location /media/ {
        alias /var/www/django_project/media/;
    }

    location = /favicon.ico {
        access_log off;
        log_not_found off;
    }

    location / {
        include proxy_params;
        proxy_pass http://unix:/var/www/django_project/gunicorn.sock;
    }
}
```

---

## 11. Enable Site and Restart Nginx

```bash
sudo rm /etc/nginx/sites-enabled/default

sudo ln -s /etc/nginx/sites-available/django_project \
/etc/nginx/sites-enabled/

sudo nginx -t

sudo systemctl restart nginx
```

---

## 12. Verify Everything is Running

Open:

```text
http://147.93.90.97
```

Check logs if needed:

```bash
sudo tail -n 50 /var/log/nginx/error.log

sudo journalctl -u gunicorn -n 50 --no-pager
```

### Components Used

- **Gunicorn** → Serves the Django application
- **Nginx** → Handles web traffic, SSL, and static files

---

## 13. If You Update or Change Your Django Project

### Restart Gunicorn

```bash
sudo systemctl restart gunicorn
```

### Check Gunicorn Status

```bash
sudo systemctl status gunicorn
```

---

## 14. When to Restart Nginx

Restart Nginx if you change:

- Nginx configuration files
- Domain settings
- Port settings
- SSL certificates

### Test Nginx Configuration

```bash
sudo nginx -t
```

### Restart Nginx

```bash
sudo systemctl restart nginx
```

---

## Reload Systemd and Restart Gunicorn

```bash
sudo systemctl daemon-reexec

sudo systemctl daemon-reload

sudo systemctl restart gunicorn
```

## Test Gunicorn manually

```bash
cd /var/www/django_project

source venv/bin/activate

gunicorn cms_bolt.wsgi:application
```

## Now push this to the VPS and run one command on the server to make the session folder writable:
```bash

# On your VPS — run this once
cd /var/www/django_project

# Create writable session + cache dirs for the current user (root)
mkdir -p .whatsapp_session ~/.cache/selenium ~/.wdm

# If Django runs as www-data instead of root, fix ownership
# chown -R www-data:www-data .whatsapp_session
Then click Retry in the modal. Here's what changed:

Attempt	Method	Cache location	Why
1st	Selenium built-in (selenium-manager)	~/.cache/selenium/	Root-writable, no extra packages
2nd	webdriver-manager with explicit path	~/.wdm/ (home dir)	Forces it away from /var/www/.wdm
Previous (broken)	webdriver-manager default	/var/www/.wdm	Process home was /var/www → Errno 13
The root cause was that Django's process had HOME=/var/www, so webdriver-manager tried to create .wdm there and got a permission error. The new code uses os.path.expanduser('~') only as a last resort fallback, and prefers Selenium's own built-in manager which writes to /root/.cache/selenium/ on your VPS.
```

## How it works on VPS now Whatsapp QR Code
```bash

Chrome starts silently in the background (no window, no display needed)
--headless=new (Chrome 112+) renders the page in memory
The QR code is captured as a screenshot → base64 and sent to your Django web interface
You scan the QR from the Django admin page on your phone — no VPS GUI required
WhatsApp bot detection is bypassed with --disable-blink-features=AutomationControlled + navigator.webdriver override
One-time VPS setup — run these on your server:


# Install Google Chrome on Ubuntu/Debian VPS
wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" | sudo tee /etc/apt/sources.list.d/google-chrome.list
sudo apt-get update && sudo apt-get install -y google-chrome-stable

# Verify
google-chrome --version

# Install Python packages (if not already)
pip install selenium webdriver-manager
After that, go to Send Message → WhatsApp Web (Local) → Check Status → Scan QR — the QR will appear in the Django modal and you scan it with your phone.
```
