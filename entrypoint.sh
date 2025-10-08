#!/bin/bash
# Entrypoint для Docker контейнера

set -e

echo "==> Waiting for database..."
while ! nc -z db 5432; do
  sleep 0.5
done
echo "==> Database is ready!"

echo "==> Running migrations..."
python Folder/manage.py migrate --noinput

echo "==> Collecting static files..."
python Folder/manage.py collectstatic --noinput --clear

echo "==> Creating cache directory..."
mkdir -p /app/Folder/media/txt_files

echo "==> Starting application..."
exec "$@"
