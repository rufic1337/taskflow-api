#!/bin/sh
set -e

python manage.py migrate --noinput
python manage.py collectstatic --noinput

if [ "$SEED_DEMO_DATA" = "true" ]; then
    python manage.py seed_demo_data
fi

exec "$@"
