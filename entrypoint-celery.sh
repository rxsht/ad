#!/bin/bash
# Entrypoint для Celery worker контейнера

set -e

echo "==> Waiting for Redis..."
while ! nc -z redis 6379; do
  sleep 0.5
done
echo "==> Redis is ready!"

echo "==> Waiting for database..."
while ! nc -z db 5432; do
  sleep 0.5
done
echo "==> Database is ready!"

echo "==> Starting Celery worker..."
exec "$@"

