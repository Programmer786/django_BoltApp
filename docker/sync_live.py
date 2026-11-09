"""
Keep the Docker copy (MySQL) in step with the live app's db.sqlite3.

Detect:  every SYNC_POLL_SECONDS, look at the live file's timestamp and size
         (plus its -journal / -wal files). Only a change triggers a sync, and
         syncs are at least SYNC_MIN_INTERVAL seconds apart.
Update:  take a read-only snapshot of the live file, bring it to this code's
         schema, apply the same length cleanup as the first import, then per
         table compare a cheap fingerprint (rows, highest id, latest
         timestamp). Changed tables (and every small table) are diffed row by
         row and only the differences are written: inserts, updates, deletes.

The live file is only ever READ (mounted read-only, opened with mode=ro).
The copy is a mirror: changes made directly in the copy's mirrored tables are
overwritten. The bot's own tables (wa_bot) and logins (sessions) are skipped.

Usage: python docker/sync_live.py            (run forever)
       python docker/sync_live.py --once     (one sync now, then exit)
"""
import json
import os
import sys
import tempfile
import time
import traceback
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cms_bolt.settings')

import django  # noqa: E402

django.setup()

from django.apps import apps  # noqa: E402
from django.core.management import call_command  # noqa: E402
from django.db import connections, transaction  # noqa: E402
from django.db.models import Count, Max  # noqa: E402

from bootstrap import snapshot  # noqa: E402
from fit_lengths import fit_lengths  # noqa: E402

LIVE_DB = os.path.join(os.getenv('LIVE_APP_DIR', '/live'), 'db.sqlite3')
SNAP = os.path.join(tempfile.gettempdir(), 'sync_live.sqlite3')
MARKER = os.getenv('IMPORT_MARKER', '/app/media/.bolt_import')
STATUS_FILE = os.getenv('SYNC_STATUS_FILE', '/app/media/.bolt_sync.json')
POLL = int(os.getenv('SYNC_POLL_SECONDS', '30'))
MIN_INTERVAL = int(os.getenv('SYNC_MIN_INTERVAL', '60'))
ALWAYS_DIFF_BELOW = 5000  # rows: small tables are always diffed in full
BATCH = 500

SKIP_TABLES = {'django_session', 'django_migrations'}
SKIP_APPS = {'wa_bot'}
TIME_FIELDS = ('updated_at', 'timestamp', 'action_time', 'sent_at', 'last_login', 'date_joined', 'created_at')


def log(*a):
    print(datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S'), *a, flush=True)


def models_to_sync():
    return [m for m in apps.get_models(include_auto_created=True)
            if m._meta.db_table not in SKIP_TABLES and not m._meta.proxy
            and m._meta.app_label not in SKIP_APPS]


def file_signature():
    sig = []
    for suffix in ('', '-journal', '-wal'):
        try:
            st = os.stat(LIVE_DB + suffix)
            sig.append((suffix, st.st_mtime_ns, st.st_size))
        except FileNotFoundError:
            pass
    return tuple(sig)


def fingerprint(model, alias):
    names = {f.attname for f in model._meta.concrete_fields}
    aggs = {'n': Count('pk'), 'max_pk': Max('pk')}
    for t in TIME_FIELDS:
        if t in names:
            aggs[f'max_{t}'] = Max(t)
    return model._base_manager.using(alias).aggregate(**aggs)


def load_rows(model, alias):
    fields = model._meta.concrete_fields
    names = [f.attname for f in fields]
    pk_i = names.index(model._meta.pk.attname)
    return {r[pk_i]: r for r in model._base_manager.using(alias).values_list(*names).iterator(chunk_size=2000)}


def apply_diff(model, cur, dst):
    """Make the copy's table equal to the snapshot's. Returns (ins, upd, dele)."""
    fields = model._meta.concrete_fields
    qn = dst.ops.quote_name
    table, pk_col = qn(model._meta.db_table), qn(model._meta.pk.column)
    pk_field = model._meta.pk

    live = load_rows(model, 'live')
    copy = load_rows(model, 'default')
    inserts = [pk for pk in live if pk not in copy]
    updates = [pk for pk, row in live.items() if pk in copy and copy[pk] != row]
    deletes = [pk for pk in copy if pk not in live]

    def prep_pk(pk):
        return pk_field.get_db_prep_value(pk, connection=dst)

    # Updated rows are replaced (delete + insert): simple and exact.
    gone = deletes + updates
    for i in range(0, len(gone), BATCH):
        chunk = gone[i:i + BATCH]
        cur.execute(f'DELETE FROM {table} WHERE {pk_col} IN ({", ".join(["%s"] * len(chunk))})',
                    [prep_pk(pk) for pk in chunk])

    cols = ', '.join(qn(f.column) for f in fields)
    sql = f'INSERT INTO {table} ({cols}) VALUES ({", ".join(["%s"] * len(fields))})'
    rows = [live[pk] for pk in inserts + updates]
    for i in range(0, len(rows), BATCH):
        cur.executemany(sql, [[f.get_db_prep_save(v, connection=dst) for f, v in zip(fields, row)]
                              for row in rows[i:i + BATCH]])
    return len(inserts), len(updates), len(deletes)


def write_status(**data):
    data['at'] = datetime.now(timezone.utc).isoformat()
    try:
        with open(STATUS_FILE, 'w') as f:
            json.dump(data, f)
    except OSError as e:
        log('could not write status file:', e)


def sync_once():
    started = time.monotonic()
    # Syncs can be hours apart when the live app is quiet, long enough for MySQL
    # to drop an idle connection. Django only recycles connections around web
    # requests, so without this a dead one would fail every retry forever.
    connections['default'].close()
    snapshot(LIVE_DB, SNAP)
    cfg = dict(connections.settings['default'])
    cfg.update(ENGINE='django.db.backends.sqlite3', NAME=SNAP, USER='', PASSWORD='', HOST='', PORT='',
               OPTIONS={}, CONN_MAX_AGE=0)
    connections.settings['live'] = cfg
    if 'live' in connections:
        connections['live'].close()
    try:
        call_command('migrate', database='live', verbosity=0, interactive=False)
        fit_lengths('live', verbose=False)

        dst = connections['default']
        changes, checked, skipped = {}, 0, 0
        with transaction.atomic(using='default'):
            with dst.cursor() as cur:
                cur.execute('SET FOREIGN_KEY_CHECKS=0')
                for model in models_to_sync():
                    fp_live = fingerprint(model, 'live')
                    if fp_live['n'] >= ALWAYS_DIFF_BELOW and fp_live == fingerprint(model, 'default'):
                        skipped += 1
                        continue
                    checked += 1
                    ins, upd, dele = apply_diff(model, cur, dst)
                    if ins or upd or dele:
                        changes[model._meta.label] = {'inserted': ins, 'updated': upd, 'deleted': dele}
                cur.execute('SET FOREIGN_KEY_CHECKS=1')
    finally:
        connections['live'].close()
        connections['default'].close()  # don't sit on an idle connection until the next sync
        try:
            os.remove(SNAP)
        except OSError:
            pass

    secs = round(time.monotonic() - started, 1)
    total = sum(sum(c.values()) for c in changes.values())
    if changes:
        log(f'synced {total} change(s) in {secs}s:',
            '; '.join(f'{k} +{v["inserted"]} ~{v["updated"]} -{v["deleted"]}' for k, v in changes.items()))
    else:
        log(f'checked, copy already up to date ({secs}s; {checked} table(s) diffed, {skipped} unchanged)')
    write_status(ok=True, seconds=secs, changes=changes, total_changes=total,
                 poll_seconds=POLL, min_interval=MIN_INTERVAL)
    return changes


def wait_for_first_import():
    while not os.path.exists(MARKER):
        log('waiting for the first import to finish...')
        time.sleep(15)


def main():
    if '--once' in sys.argv:
        sync_once()
        return
    wait_for_first_import()
    log(f'watching {LIVE_DB} (every {POLL}s, at most one sync per {MIN_INTERVAL}s)')
    last_sig, last_sync = None, 0.0
    while True:
        try:
            sig = file_signature()
            if sig and sig != last_sig and time.monotonic() - last_sync >= MIN_INTERVAL:
                time.sleep(3)  # let an in-progress write finish
                if file_signature() == sig:
                    sync_once()
                    last_sig, last_sync = sig, time.monotonic()
        except Exception as e:  # never die: report and retry next round
            log('sync failed:', e)
            traceback.print_exc()
            write_status(ok=False, error=str(e)[:500], poll_seconds=POLL, min_interval=MIN_INTERVAL)
            last_sync = time.monotonic()
        time.sleep(POLL)


if __name__ == '__main__':
    main()
