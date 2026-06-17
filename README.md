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

## 15. WhatsApp Web (Selenium) Setup on VPS

The app can send WhatsApp messages two ways:

- **Twilio API** — cloud-based, needs a Twilio account (configured in `.env`).
- **WhatsApp Web (Local)** — uses headless Chrome + Selenium to drive `web.whatsapp.com`. Free, no Twilio needed. Setup steps below.

### How it works

The VPS has **no GUI**, so Chrome runs **headless** (invisible, in memory). When you click **Scan QR** in the app, Chrome loads WhatsApp Web, the QR code is captured as a **screenshot → base64**, and shown inside the Django modal. You scan it with your phone — no VPS display required. Once scanned, the login session is saved in `/tmp/wa_session`, so you don't need to scan again unless the session expires.

### Step 1 — Install Google Chrome

```bash
wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" | sudo tee /etc/apt/sources.list.d/google-chrome.list
sudo apt-get update && sudo apt-get install -y google-chrome-stable

# Verify — note the version number (e.g. 149.0.7827.155)
google-chrome --version
```

### Step 2 — Install matching ChromeDriver

ChromeDriver **must match** the installed Chrome version. This downloads the exact match automatically:

```bash
CHROME_VER=$(google-chrome --version | grep -oP '[\d]+\.[\d]+\.[\d]+\.[\d]+')
wget -q "https://storage.googleapis.com/chrome-for-testing-public/${CHROME_VER}/linux64/chromedriver-linux64.zip" -O /tmp/cd.zip \
  && unzip -q /tmp/cd.zip -d /tmp/ \
  && sudo mv /tmp/chromedriver-linux64/chromedriver /usr/local/bin/chromedriver \
  && sudo chmod +x /usr/local/bin/chromedriver \
  && chromedriver --version
```

> Re-run this step every time Chrome auto-updates to a new major version, or the driver/Chrome versions will mismatch and Chrome will fail to start.

### Step 3 — Install Chrome system libraries

These shared libraries are required or Chrome exits immediately:

```bash
sudo apt-get install -y libglib2.0-0t64 libnss3 libnspr4 libdbus-1-3 \
  libatk1.0-0t64 libatk-bridge2.0-0t64 libcups2t64 libdrm2 libxkbcommon0 \
  libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1 \
  libasound2t64 fonts-liberation libpangocairo-1.0-0
```

### Step 4 — Install Python packages

```bash
cd /var/www/django_project && source venv/bin/activate
pip install selenium webdriver-manager
```

### Step 5 — Configure Gunicorn: 1 worker + threads (CRITICAL)

Chrome can only run **one instance per profile**. Multiple gunicorn workers would each launch Chrome on the same profile and conflict. Use **one worker with multiple threads** instead — one shared Chrome, the threads keep the site responsive. Also raise the timeout, since launching Chrome + loading WhatsApp Web takes ~30s.

```bash
sudo nano /etc/systemd/system/gunicorn.service
```

The `ExecStart` block must be:

```ini
ExecStart=/var/www/django_project/venv/bin/gunicorn \
    --workers 1 \
    --threads 4 \
    --timeout 120 \
    --bind unix:/var/www/django_project/gunicorn.sock \
    --access-logfile /var/log/gunicorn/access.log \
    --error-logfile /var/log/gunicorn/error.log \
    cms_bolt.wsgi:application
```

Then reload:

```bash
sudo systemctl daemon-reload && sudo systemctl restart gunicorn
```

### Step 6 — Connect

In the app: **Send Message → Send Via: WhatsApp Web (Local) → Check Status → Scan QR**. Scan the QR with your phone (**WhatsApp → Linked Devices → Link a Device**). Once it shows **Connected**, you can send messages.

### Key gotchas (already handled in `whatsapp/selenium_sender.py`)

| Symptom | Cause | Fix in code |
| --- | --- | --- |
| `Permission denied: '/var/www/.wdm'` | gunicorn user `www-data` can't write to `/var/www` | Driver cache pinned to `/tmp/wa_drivers`; profile in `/tmp/wa_session` |
| `Chrome instance exited` / `crashpad: --database is required` | `www-data`'s `HOME=/var/www` is not writable; Chrome's crash reporter fails | Code sets `os.environ['HOME'] = '/tmp'` on Linux |
| `session not created` version mismatch | ChromeDriver ≠ Chrome version | Step 2 installs the exact matching driver to `/usr/local/bin/chromedriver` |
| Worker `SIGTERM` / `SyntaxError: Unexpected token '<'` | Request took longer than gunicorn's 30s default timeout (returns HTML 500, not JSON) | `--timeout 120` in Step 5 |
| QR works once then fails | Multiple workers fighting over one Chrome profile | `--workers 1 --threads 4` (Step 5) + re-entrant lock in code |

### Troubleshooting

```bash
# View the real Python error behind a 500 / "Unexpected token '<'"
tail -30 /var/log/gunicorn/error.log

# Test Chrome works standalone (should print page HTML)
google-chrome --headless=new --no-sandbox --disable-setuid-sandbox \
  --disable-dev-shm-usage --no-zygote --dump-dom https://example.com 2>/dev/null | head -3

# Test the WhatsApp status function as the gunicorn user (www-data)
sudo -u www-data /var/www/django_project/venv/bin/python3 -c "
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE','cms_bolt.settings')
os.chdir('/var/www/django_project')
django.setup()
from whatsapp.selenium_sender import get_status
r = get_status()
print('logged_in:', r['logged_in'], '| has_qr:', bool(r['qr_image']), '| error:', r['error'])
"

# Clear stuck Chrome processes / locked profile
pkill -9 chrome; pkill -9 chromedriver; rm -rf /tmp/wa_session/Singleton*
sudo systemctl restart gunicorn
```
