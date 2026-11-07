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
# Bump IMPORT_VERSION when the import method changes: the copy is then
# re-imported once from a fresh snapshot. The marker lives in the media volume.
IMPORT_VERSION=3
MARKER=/app/media/.bolt_import
DONE_VERSION=$(cut -d' ' -f1 "$MARKER" 2>/dev/null || echo none)

NEED_IMPORT=no
if [ "$(python docker/bootstrap.py is-empty)" = "yes" ]; then
    NEED_IMPORT=yes
elif [ "$DONE_VERSION" != "$IMPORT_VERSION" ]; then
    echo "Import method changed ($DONE_VERSION -> $IMPORT_VERSION) - re-importing the copy."
    NEED_IMPORT=yes
fi

if [ "$NEED_IMPORT" = "yes" ]; then
    if [ -n "$LIVE_APP_DIR" ] && [ -f "$LIVE_DB" ]; then
        echo "Importing a copy of $LIVE_DB"
        IMPORT_TIME=$(date -u +%Y-%m-%dT%H:%M:%S)
        python docker/bootstrap.py snapshot "$LIVE_DB" /tmp/live.sqlite3
        # Bring the snapshot up to this code's schema (only the /tmp copy changes).
        DB_ENGINE=sqlite SQLITE_PATH=/tmp/live.sqlite3 python manage.py migrate --noinput
        DB_ENGINE=sqlite SQLITE_PATH=/tmp/live.sqlite3 python docker/fit_lengths.py
        # Table-by-table exact copy (same IDs, full timestamps, whitespace kept).
        python docker/copy_db.py /tmp/live.sqlite3
        rm -f /tmp/live.sqlite3
        echo "$IMPORT_VERSION $IMPORT_TIME" > "$MARKER"
        echo "Import finished (snapshot taken $IMPORT_TIME UTC)."
    else
        echo "WARNING: no live database found at '$LIVE_DB' - starting with an empty database."
    fi
else
    echo "Copy already imported (version $DONE_VERSION) - skipping import."
fi

if [ -n "$LIVE_APP_DIR" ] && [ -d "$LIVE_APP_DIR/media" ]; then
    # -n: never overwrite files already in the Docker media volume.
    cp -rn "$LIVE_APP_DIR/media/." /app/media/ 2>/dev/null || true
    echo "Media files synced from $LIVE_APP_DIR/media."
fi

if [ "${COMPARE_ON_START:-1}" = "1" ] && [ -f "$LIVE_DB" ]; then
    # Report only - a failure here must never stop the app from starting.
    python docker/compare_dbs.py "$LIVE_DB" || echo "Comparison could not run."
fi

exec gunicorn cms_bolt.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers "${GUNICORN_WORKERS:-2}" \
    --timeout 120 \
    --access-logfile -
