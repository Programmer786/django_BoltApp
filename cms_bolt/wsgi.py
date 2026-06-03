"""
WSGI config for cms_bolt project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/wsgi/
"""

import os

# ✅ Limit thread usage for numerical libraries to prevent resource exhaustion
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cms_bolt.settings')

from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()