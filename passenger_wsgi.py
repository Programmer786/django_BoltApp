import sys
import os

# ✅ Fix: Limit thread usage BEFORE any NumPy/scientific libraries load
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

from django.core.wsgi import get_wsgi_application
from werkzeug.middleware.shared_data import SharedDataMiddleware

# Get the base directory of your project
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Add base directory to a Python path
sys.path.insert(0, BASE_DIR)

# Automatically detect Django project name (folder with settings.py)
for item in os.listdir(BASE_DIR):
    if os.path.isdir(os.path.join(BASE_DIR, item)) and os.path.isfile(os.path.join(BASE_DIR, item, 'settings.py')):
        PROJECT_NAME = item
        break
else:
    raise Exception("Django project folder with settings.py not found!")

# Set the settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', f'{PROJECT_NAME}.settings')

# Get WSGI application
application = get_wsgi_application()

# Serve static and media files via SharedDataMiddleware
application = SharedDataMiddleware(application, {
    '/media': os.path.join(BASE_DIR, 'media'),
    '/static': os.path.join(BASE_DIR, 'staticfiles'),
})
