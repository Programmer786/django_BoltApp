"""
Helpers for the Docker entrypoint (run as: python docker/bootstrap.py <command>).

  wait-db       wait until MySQL accepts connections
  ensure-db     create the app database + user if missing (needs MYSQL_ROOT_PASSWORD)
  is-empty      print "yes" if the app database has no users yet, else "no"
  snapshot SRC DST
                consistent read-only copy of a live SQLite file (never writes SRC)
"""
import os
import shutil
import sqlite3
import sys
import time

import MySQLdb


def _connect(user, password, db=None):
    kwargs = dict(
        host=os.environ.get('DB_HOST', 'localhost'),
        port=int(os.environ.get('DB_PORT', '3306')),
        user=user, passwd=password, charset='utf8mb4',
    )
    if db:
        kwargs['db'] = db
    return MySQLdb.connect(**kwargs)


def wait_db():
    root_pw = os.environ.get('MYSQL_ROOT_PASSWORD')
    user, pw = ('root', root_pw) if root_pw else (os.environ['DB_USER'], os.environ['DB_PASSWORD'])
    for attempt in range(60):
        try:
            _connect(user, pw).close()
            print('MySQL is reachable.')
            return
        except MySQLdb.OperationalError as e:
            print(f'Waiting for MySQL ({attempt + 1}/60): {e}')
            time.sleep(2)
    sys.exit('MySQL did not become reachable.')


def ensure_db():
    root_pw = os.environ.get('MYSQL_ROOT_PASSWORD')
    if not root_pw:
        print('MYSQL_ROOT_PASSWORD not set; assuming database and user already exist.')
        return
    name, user, pw = os.environ['DB_NAME'], os.environ['DB_USER'], os.environ['DB_PASSWORD']
    conn = _connect('root', root_pw)
    cur = conn.cursor()
    cur.execute(f'CREATE DATABASE IF NOT EXISTS `{name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci')
    cur.execute("CREATE USER IF NOT EXISTS %s@'%%' IDENTIFIED BY %s", (user, pw))
    cur.execute("ALTER USER %s@'%%' IDENTIFIED BY %s", (user, pw))
    cur.execute(f"GRANT ALL PRIVILEGES ON `{name}`.* TO %s@'%%'", (user,))
    cur.execute('FLUSH PRIVILEGES')
    conn.commit()
    conn.close()
    print(f'Database `{name}` and user `{user}` are ready.')


def is_empty():
    conn = _connect(os.environ['DB_USER'], os.environ['DB_PASSWORD'], os.environ['DB_NAME'])
    cur = conn.cursor()
    cur.execute('SELECT COUNT(*) FROM auth_user')
    print('yes' if cur.fetchone()[0] == 0 else 'no')
    conn.close()


def snapshot(src, dst):
    # mode=ro: opened read-only, so the live file can never be modified.
    target = sqlite3.connect(dst)
    try:
        source = sqlite3.connect(f'file:{src}?mode=ro', uri=True)
        source.backup(target)
    except sqlite3.Error as e:
        # e.g. WAL mode needs a writable -shm file, impossible on a :ro mount.
        # Fall back to a plain file copy (still only reads the live file).
        print(f'Read-only open failed ({e}); copying the file instead.')
        target.close()
        shutil.copyfile(src, dst)
        target = sqlite3.connect(dst)
        source = None
    # A duplicate whatsapp 0006 migration was removed from the code; if this
    # database recorded the removed name, point it at the identical survivor
    # (in the copy only) so migrate doesn't try to create the table twice.
    target.execute(
        "UPDATE django_migrations SET name = '0006_contactcategory_whatsappcontact_category' "
        "WHERE app = 'whatsapp' AND name = '0006_contact_categories'"
    )
    target.commit()
    target.close()
    if source is not None:
        source.close()
    print(f'Snapshot of {src} written to {dst}.')


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'wait-db':
        wait_db()
    elif cmd == 'ensure-db':
        ensure_db()
    elif cmd == 'is-empty':
        is_empty()
    elif cmd == 'snapshot':
        snapshot(sys.argv[2], sys.argv[3])
    else:
        sys.exit(f'Unknown command: {cmd}')
