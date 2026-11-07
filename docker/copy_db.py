"""
Copy every table from the SQLite snapshot into MySQL exactly: same IDs, same
values, full-precision timestamps, whitespace untouched.

Usage: python docker/copy_db.py /tmp/live.sqlite3

Why not dumpdata/loaddata: the JSON format cuts timestamps to milliseconds
and the XML format alters whitespace (e.g. a trailing tab), and both re-create
records through model saves. Here rows are read with the ORM from the snapshot
and written with plain INSERTs, converted by each field's own DB converter.

Only the default (MySQL) database is written. The snapshot is only read.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cms_bolt.settings')

import django  # noqa: E402

django.setup()

from django.apps import apps  # noqa: E402
from django.db import connections, transaction  # noqa: E402

SRC = sys.argv[1]
BATCH = 1000
SKIP_TABLES = {'django_session', 'django_migrations'}

cfg = dict(connections.settings['default'])
cfg.update(ENGINE='django.db.backends.sqlite3', NAME=SRC, USER='', PASSWORD='', HOST='', PORT='',
           OPTIONS={}, CONN_MAX_AGE=0)
connections.settings['live'] = cfg

dst = connections['default']
assert dst.vendor == 'mysql', 'copy_db writes MySQL only'
qn = dst.ops.quote_name

# wa_bot exists only in the copy (bot settings + conversation log): keep it.
SKIP_APPS = {'wa_bot'}
models_to_copy = [m for m in apps.get_models(include_auto_created=True)
                  if m._meta.db_table not in SKIP_TABLES and not m._meta.proxy
                  and m._meta.app_label not in SKIP_APPS]

total = 0
with transaction.atomic(using='default'):
    with dst.cursor() as cur:
        cur.execute('SET FOREIGN_KEY_CHECKS=0')
        for model in models_to_copy:
            cur.execute(f'DELETE FROM {qn(model._meta.db_table)}')

        for model in models_to_copy:
            fields = model._meta.concrete_fields
            cols = ', '.join(qn(f.column) for f in fields)
            marks = ', '.join(['%s'] * len(fields))
            sql = f'INSERT INTO {qn(model._meta.db_table)} ({cols}) VALUES ({marks})'
            rows = model._base_manager.using('live').values_list(*[f.attname for f in fields])
            batch, n = [], 0
            for row in rows.iterator(chunk_size=BATCH):
                batch.append([f.get_db_prep_save(v, connection=dst) for f, v in zip(fields, row)])
                if len(batch) >= BATCH:
                    cur.executemany(sql, batch)
                    n += len(batch)
                    batch = []
            if batch:
                cur.executemany(sql, batch)
                n += len(batch)
            total += n
            if n:
                print(f'  {model._meta.label}: {n}')
        cur.execute('SET FOREIGN_KEY_CHECKS=1')

connections['live'].close()
print(f'copy_db: {total} rows copied exactly.')
