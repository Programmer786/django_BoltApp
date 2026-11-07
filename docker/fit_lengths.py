"""
Make every CharField value fit its max_length before copying to MySQL.

SQLite never enforced max_length, MySQL (strict mode) rejects longer values.
Runs ONLY against a temp snapshot of the live database, so the live file is
never touched. Each fixed record is printed so nothing is changed silently:
whitespace is collapsed first (lossless in practice), and truncation is the
last resort.

As a script: SQLITE_PATH=/tmp/x.sqlite3 DB_ENGINE=sqlite python docker/fit_lengths.py
As a function: fit_lengths(alias) on any SQLite connection alias (used by sync_live).
"""
import os
import re
import sys


def fit_lengths(alias='default', verbose=True):
    from django.apps import apps
    from django.db import connections, models
    from django.db.models.functions import Length

    assert connections[alias].vendor == 'sqlite', 'fit_lengths must only run against the SQLite snapshot'
    fixed = 0
    for model in apps.get_models():
        for field in model._meta.concrete_fields:
            if not (isinstance(field, models.CharField) and field.max_length):
                continue
            qs = model._base_manager.using(alias)
            over = qs.annotate(_len=Length(field.name)).filter(_len__gt=field.max_length)
            for obj in over:
                value = getattr(obj, field.attname)
                new = re.sub(r'\s+', ' ', value).strip()
                how = 'whitespace collapsed'
                if len(new) > field.max_length:
                    new = new[:field.max_length]
                    how = 'TRUNCATED'
                qs.filter(pk=obj.pk).update(**{field.attname: new})
                fixed += 1
                if verbose:
                    print(f'  {model._meta.label} {obj.pk} .{field.name}: {len(value)} -> {len(new)} chars ({how})')
    return fixed


if __name__ == '__main__':
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cms_bolt.settings')
    import django

    django.setup()
    print(f'fit_lengths: {fit_lengths()} value(s) adjusted.')
