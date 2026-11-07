"""
Compare the Docker copy (MySQL, the default DB) with the live SQLite database,
record by record and field by field, and print a report.

Usage: python docker/compare_dbs.py /path/to/live/db.sqlite3

The live file is never opened for writing: a read-only snapshot is taken to
/tmp first (bootstrap.snapshot) and only that copy is used.
"""
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cms_bolt.settings')

import django  # noqa: E402

django.setup()

from django.apps import apps  # noqa: E402
from django.core.management import call_command  # noqa: E402
from django.db import connections  # noqa: E402

LIVE_SRC = sys.argv[1]
SNAP = '/tmp/compare_live.sqlite3' if os.name != 'nt' else os.path.join(os.environ.get('TEMP', '.'), 'compare_live.sqlite3')
SKIP = {'contenttypes.ContentType', 'auth.Permission', 'sessions.Session'}
MAX_SHOWN = 5

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bootstrap import snapshot  # noqa: E402

snapshot(LIVE_SRC, SNAP)
taken_at = datetime.now(timezone.utc)

cfg = dict(connections.settings['default'])
cfg.update(ENGINE='django.db.backends.sqlite3', NAME=SNAP, USER='', PASSWORD='', HOST='', PORT='',
           OPTIONS={}, CONN_MAX_AGE=0)
connections.settings['live'] = cfg
# Same schema as the copy (only the /tmp snapshot is migrated; no data changes).
call_command('migrate', database='live', verbosity=0, interactive=False)


def norm(v):
    if isinstance(v, datetime):
        return v.astimezone(timezone.utc).replace(tzinfo=None) if v.tzinfo else v
    return v


def rows(model, alias):
    fields = [f.attname for f in model._meta.concrete_fields]
    data = {}
    for r in model._base_manager.using(alias).values_list(*fields):
        data[r[0] if fields[0] == model._meta.pk.attname else r[fields.index(model._meta.pk.attname)]] = r
    return fields, data


def ts(model, row, fields, name):
    return row[fields.index(name)] if name in fields else None


# When the copy was imported: the newest created/updated time inside the copy.
copy_cutoff = None
for m in apps.get_models():
    for name in ('created_at', 'updated_at', 'timestamp'):
        if name in [f.attname for f in m._meta.concrete_fields]:
            v = m._base_manager.using('default').order_by(f'-{name}').values_list(name, flat=True).first()
            if v and (copy_cutoff is None or v > copy_cutoff):
                copy_cutoff = v

print('=' * 78)
print('DATABASE COMPARISON  live SQLite  vs  Docker copy (MySQL)')
print(f'Live snapshot taken: {taken_at:%Y-%m-%d %H:%M:%S} UTC')
print(f'Newest timestamp in copy: {copy_cutoff:%Y-%m-%d %H:%M:%S} UTC' if copy_cutoff else '')
print('=' * 78)
print(f'{"table":42} {"live":>8} {"copy":>8} {"same":>8}  differences')

total_unexplained = 0
details = []
for model in sorted(apps.get_models(), key=lambda m: m._meta.label):
    label = model._meta.label
    if label in SKIP:
        continue
    fields, live = rows(model, 'live')
    _, copy = rows(model, 'default')
    same = 0
    new_after, edited_after, only_copy, mismatched = [], [], [], []
    for pk, lrow in live.items():
        crow = copy.get(pk)
        if crow is None:
            when = ts(model, lrow, fields, 'created_at') or ts(model, lrow, fields, 'timestamp')
            new_after.append((pk, when))
            continue
        diffs = [f for f, a, b in zip(fields, lrow, crow) if norm(a) != norm(b)]
        if not diffs:
            same += 1
            continue
        upd = ts(model, lrow, fields, 'updated_at')
        if upd and copy_cutoff and upd > copy_cutoff:
            edited_after.append((pk, upd, diffs))
        else:
            mismatched.append((pk, diffs, lrow, crow))
    only_copy = [pk for pk in copy if pk not in live]

    # Records added after the copy are expected only if they really are newer.
    unexplained_new = [x for x in new_after if not (x[1] and copy_cutoff and x[1] > copy_cutoff)]
    notes = []
    if new_after:
        notes.append(f'{len(new_after)} added in live after copy')
    if edited_after:
        notes.append(f'{len(edited_after)} edited in live after copy')
    if mismatched:
        notes.append(f'{len(mismatched)} DIFFERENT')
    if only_copy:
        notes.append(f'{len(only_copy)} ONLY IN COPY')
    if unexplained_new:
        notes.append(f'{len(unexplained_new)} MISSING FROM COPY')
    total_unexplained += len(mismatched) + len(only_copy) + len(unexplained_new)
    print(f'{label:42} {len(live):>8} {len(copy):>8} {same:>8}  {"; ".join(notes) or "identical"}')

    for pk, diffs, lrow, crow in mismatched[:MAX_SHOWN]:
        for f in diffs:
            a, b = lrow[fields.index(f)], crow[fields.index(f)]
            details.append(f'  {label} {pk} .{f}: live={str(a)[:60]!r} ({len(str(a))} chars)  copy={str(b)[:60]!r} ({len(str(b))} chars)')
    for pk in only_copy[:MAX_SHOWN]:
        details.append(f'  {label} {pk}: only in copy (deleted in live after copy?)')
    for pk, when in unexplained_new[:MAX_SHOWN]:
        details.append(f'  {label} {pk}: in live but not in copy (created {when})')

print('-' * 78)
if details:
    print('Details (first few per table):')
    print('\n'.join(details))
print(f'RESULT: {"all records from copy time are identical" if total_unexplained == 0 else f"{total_unexplained} unexpected difference(s) - see details"}')
print('=' * 78)
connections['live'].close()
try:
    os.remove(SNAP)
except OSError:
    pass
