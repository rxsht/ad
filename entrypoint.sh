#!/bin/bash
# Entrypoint для Docker контейнера

set -e

echo "==> Waiting for database..."
while ! nc -z db 5432; do
  sleep 0.5
done
echo "==> Database is ready!"

echo "==> Installing pgvector extension..."
# Парсим DATABASE_URL для получения учетных данных
if [ -n "$DATABASE_URL" ]; then
    DB_PARAMS=$(echo "$DATABASE_URL" | sed -e 's/postgres:\/\///' -e 's/@.*//')
    DB_USER=$(echo "$DB_PARAMS" | cut -d: -f1)
    DB_PASS=$(echo "$DB_PARAMS" | cut -d: -f2)
    DB_NAME=$(echo "$DATABASE_URL" | sed -e 's/.*\///')
    export PGPASSWORD=$DB_PASS
    psql -h db -U "$DB_USER" -d "$DB_NAME" -c "CREATE EXTENSION IF NOT EXISTS vector;" || echo "Warning: Failed to create pgvector extension (may already exist)"
else
    export PGPASSWORD=${POSTGRES_PASSWORD}
    psql -h db -U ${POSTGRES_USER} -d ${POSTGRES_DB} -c "CREATE EXTENSION IF NOT EXISTS vector;" || echo "Warning: Failed to create pgvector extension (may already exist)"
fi

echo "==> Running migrations..."
python Folder/manage.py migrate --noinput

echo "==> Creating superuser (admin123/admin123)..."
python Folder/manage.py shell << EOF
from django.contrib.auth import get_user_model
User = get_user_model()
try:
    if not User.objects.filter(username='admin123').exists():
        User.objects.create_superuser('admin123', '', 'admin123')
        print("✓ Superuser 'admin123' created successfully!")
    else:
        print("✓ Superuser 'admin123' already exists")
        # Обновляем пароль если пользователь уже существует
        user = User.objects.get(username='admin123')
        user.set_password('admin123')
        user.is_superuser = True
        user.is_staff = True
        user.save()
        print("✓ Password for 'admin123' updated to 'admin123'")
except Exception as e:
    print(f"Warning: Could not create/update superuser: {e}")
EOF

echo "==> Collecting static files..."
python Folder/manage.py collectstatic --noinput

echo "==> Creating cache directory..."
mkdir -p /app/Folder/media/txt_files
mkdir -p /app/Folder/media/documents

echo "==> Starting application..."
exec "$@"