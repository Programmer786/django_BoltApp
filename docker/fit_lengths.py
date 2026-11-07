"""
Make every CharField value fit its max_length before copying to MySQL.

SQLite never enforced max_length, MySQL (strict mode) rejects longer values.
Runs ONLY against the /tmp snapshot of the live database (SQLITE_PATH), so
the live file is never touched. Each fixed record is printed so nothing is
changed silently: whitespace is collapsed first (lossless in practice), and
truncation is the last resort.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cms_bolt.settings')

import django  # noqa: E402

django.setup()

from django.apps import apps  # noqa: E402
from django.db import connection, models  # noqa: E402
from django.db.models.functions import Length  # noqa: E402

assert connection.vendor == 'sqlite', 'fit_lengths must only run against the SQLite snapshot'

fixed = 0
for model in apps.get_models():
    for field in model._meta.concrete_fields:
        if not (isinstance(field, models.CharField) and field.max_length):
            continue
        over = model._base_manager.annotate(_len=Length(field.name)).filter(_len__gt=field.max_length)
        for obj in over:
            value = getattr(obj, field.attname)
            new = re.sub(r'\s+', ' ', value).strip()
            how = 'whitespace collapsed'
            if len(new) > field.max_length:
                new = new[:field.max_length]
                how = 'TRUNCATED'
            model._base_manager.filter(pk=obj.pk).update(**{field.attname: new})
            fixed += 1
            print(f'  {model._meta.label} {obj.pk} .{field.name}: {len(value)} -> {len(new)} chars ({how})')

print(f'fit_lengths: {fixed} value(s) adjusted.')
