#!/bin/sh
# Docker entrypoint for the Bolt copy.
#
# LIVE_APP_DIR is the original app's folder, mounted READ-ONLY. It is only
# ever read from: the database is snapshotted with SQLite's read-only mode
# and media files are copied out. Nothing is written back.
set -e

python docker/bootstrap.py wait-db
python docker/bootstrap.py ensure-db
python manage.py migrate --noinput

LIVE_DB="$LIVE_APP_DIR/db.sqlite3"
if [ "$(python docker/bootstrap.py is-empty)" = "yes" ]; then
    if [ -n "$LIVE_APP_DIR" ] && [ -f "$LIVE_DB" ]; then
        echo "MySQL database is empty - importing a copy of $LIVE_DB"
        python docker/bootstrap.py snapshot "$LIVE_DB" /tmp/live.sqlite3
        # Bring the snapshot up to this code's schema (only the /tmp copy changes).
        DB_ENGINE=sqlite SQLITE_PATH=/tmp/live.sqlite3 python manage.py migrate --noinput
        DB_ENGINE=sqlite SQLITE_PATH=/tmp/live.sqlite3 python docker/fit_lengths.py
        DB_ENGINE=sqlite SQLITE_PATH=/tmp/live.sqlite3 python manage.py dumpdata \
            --natural-foreign --natural-primary \
            -e contenttypes -e auth.permission -e sessions \
            -o /tmp/live.json
        python manage.py loaddata /tmp/live.json
        rm -f /tmp/live.sqlite3 /tmp/live.json
        echo "Import finished."
    else
        echo "WARNING: no live database found at '$LIVE_DB' - starting with an empty database."
    fi
else
    echo "MySQL database already has data - skipping import."
fi

if [ -n "$LIVE_APP_DIR" ] && [ -d "$LIVE_APP_DIR/media" ]; then
    # -n: never overwrite files already in the Docker media volume.
    cp -rn "$LIVE_APP_DIR/media/." /app/media/ 2>/dev/null || true
    echo "Media files synced from $LIVE_APP_DIR/media."
fi

exec gunicorn cms_bolt.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers "${GUNICORN_WORKERS:-2}" \
    --timeout 120 \
    --access-logfile -
