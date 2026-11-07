"""
Compare the Docker copy (MySQL, the default DB) with the live SQLite database,
record by record and field by field, and print a report.

Usage: python docker/compare_dbs.py /path/to/live/db.sqlite3 [import-marker]

The live file is never opened for writing: a read-only snapshot is taken to a
temp file first (bootstrap.snapshot) and only that copy is used.

Every difference is classified:
  * changed in LIVE after the copy was taken   -> expected (normal app use)
  * changed in the COPY after it was taken     -> expected (e.g. test logins)
  * anything else                               -> REAL MISMATCH
"""
import os
import sys
import tempfile
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cms_bolt.settings')

import django  # noqa: E402

django.setup()

from django.apps import apps  # noqa: E402
from django.core.management import call_command  # noqa: E402
from django.db import connections, models  # noqa: E402

from bootstrap import snapshot  # noqa: E402

LIVE_SRC = sys.argv[1]
MARKER = sys.argv[2] if len(sys.argv) > 2 else '/app/media/.bolt_import'
SNAP = os.path.join(tempfile.gettempdir(), 'compare_live.sqlite3')
SKIP = {'sessions.Session'}
SKIP_APPS = {'wa_bot'}  # bot tables exist only in the copy
CREATED_FIELDS = ('created_at', 'timestamp', 'date_joined', 'sent_at', 'action_time')
CHANGED_FIELDS = ('updated_at', 'last_login')
MAX_SHOWN = 5

try:
    with open(MARKER) as f:
        import_time = datetime.fromisoformat(f.read().split()[1]).replace(tzinfo=timezone.utc)
except (OSError, IndexError, ValueError):
    import_time = None

snapshot(LIVE_SRC, SNAP)
taken_at = datetime.now(timezone.utc)

cfg = dict(connections.settings['default'])
cfg.update(ENGINE='django.db.backends.sqlite3', NAME=SNAP, USER='', PASSWORD='', HOST='', PORT='',
           OPTIONS={}, CONN_MAX_AGE=0)
connections.settings['live'] = cfg
# Same schema as the copy (only the temp snapshot is migrated; no data changes).
call_command('migrate', database='live', verbosity=0, interactive=False)


def after_import(value):
    return bool(import_time and value and value > import_time)


def load(model, alias):
    fields = model._meta.concrete_fields
    names = [f.attname for f in fields]
    pk_i = names.index(model._meta.pk.attname)
    data = {r[pk_i]: r for r in model._base_manager.using(alias).values_list(*names)}
    return fields, names, data


def same_value(field, a, b):
    if a == b:
        return True
    # "No file" is stored as NULL in SQLite and '' after an export/import.
    if isinstance(field, models.FileField) and not a and not b:
        return True
    return False


def whitespace_cleanup(field, a, b):
    """fit_lengths collapsed whitespace in an over-long value during import."""
    return (isinstance(a, str) and isinstance(b, str) and getattr(field, 'max_length', None)
            and len(a) > field.max_length and ' '.join(a.split()) == b)


def first(row, names, candidates):
    for n in candidates:
        if n in names and row[names.index(n)]:
            return row[names.index(n)]
    return None


print('=' * 86)
print('DATABASE COMPARISON   live SQLite (/var/www/django_project)   vs   Docker copy (MySQL)')
print(f'Copy imported from a snapshot taken: {import_time:%Y-%m-%d %H:%M:%S} UTC' if import_time
      else 'Copy import time unknown (no marker) - cannot separate later changes')
print(f'Live database read now:              {taken_at:%Y-%m-%d %H:%M:%S} UTC')
print('=' * 86)
print(f'{"table":34} {"live":>7} {"copy":>7} {"identical":>9}  notes')

real_total = 0
details = []
for model in sorted(apps.get_models(include_auto_created=True), key=lambda m: m._meta.label):
    label = model._meta.label
    if label in SKIP or model._meta.app_label in SKIP_APPS:
        continue
    fields, names, live = load(model, 'live')
    _, _, copy = load(model, 'default')

    identical = cleaned = 0
    live_new = live_edit = copy_new = copy_edit = 0
    real = []
    for pk, lrow in live.items():
        crow = copy.get(pk)
        if crow is None:
            if after_import(first(lrow, names, CREATED_FIELDS)):
                live_new += 1
            else:
                real.append((pk, 'in live but missing from copy', None))
            continue
        diffs = [f for f, a, b in zip(fields, lrow, crow) if not same_value(f, a, b)]
        cleaned_here = [f for f in diffs
                        if whitespace_cleanup(f, lrow[names.index(f.attname)], crow[names.index(f.attname)])]
        if cleaned_here and len(cleaned_here) == len(diffs):
            cleaned += 1
            details.append(f'  {label} #{pk} .{cleaned_here[0].attname}: extra whitespace removed on import '
                           f'({len(lrow[names.index(cleaned_here[0].attname)])} -> '
                           f'{len(crow[names.index(cleaned_here[0].attname)])} chars) - expected')
        elif not diffs:
            identical += 1
        elif after_import(first(lrow, names, CHANGED_FIELDS)):
            live_edit += 1
        elif after_import(first(crow, names, CHANGED_FIELDS)):
            copy_edit += 1
        else:
            real.append((pk, 'different', [(f.attname, lrow[names.index(f.attname)], crow[names.index(f.attname)]) for f in diffs]))
    for pk, crow in copy.items():
        if pk not in live:
            if after_import(first(crow, names, CREATED_FIELDS)):
                copy_new += 1
            else:
                real.append((pk, 'in copy but not in live (deleted in live after the copy?)', None))

    notes = []
    if cleaned:
        notes.append(f'{cleaned} whitespace-cleaned on import (expected)')
    if live_new:
        notes.append(f'{live_new} new in live since copy')
    if live_edit:
        notes.append(f'{live_edit} edited in live since copy')
    if copy_new:
        notes.append(f'{copy_new} new in copy since import')
    if copy_edit:
        notes.append(f'{copy_edit} edited in copy since import')
    if real:
        notes.append(f'{len(real)} REAL MISMATCH')
    real_total += len(real)
    print(f'{label:34} {len(live):>7} {len(copy):>7} {identical:>9}  {"; ".join(notes) or "all identical"}')

    for pk, kind, diffs in real[:MAX_SHOWN]:
        if not diffs:
            details.append(f'  {label} #{pk}: {kind}')
        for name, a, b in diffs or []:
            details.append(f'  {label} #{pk} .{name}: live={str(a)[:50]!r}  copy={str(b)[:50]!r}')

print('-' * 86)
if details:
    print('Details (first few per table):')
    print('\n'.join(details))
print('RESULT: ' + ('every record that existed when the copy was taken is IDENTICAL (field by field).'
                    if real_total == 0 else f'{real_total} REAL MISMATCH(ES) - see above.'))
print('=' * 86)
connections['live'].close()
try:
    os.remove(SNAP)
except OSError:
    pass
