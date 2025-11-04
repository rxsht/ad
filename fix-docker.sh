#!/bin/bash
# Скрипт для исправления ошибки ContainerConfig в Docker Compose

echo "Останавливаем и удаляем все контейнеры..."
docker-compose down --remove-orphans

echo "Удаляем проблемные контейнеры вручную (если есть)..."
docker rm -f django_web flower_monitor celery_worker 2>/dev/null || true

echo "Удаляем старые образы проекта..."
docker images | grep forked-ad | awk '{print $3}' | xargs docker rmi -f 2>/dev/null || true

# Ищем образы по имени сервисов
docker images | grep -E '^(forked-ad|ad)' | awk '{print $3}' | xargs docker rmi -f 2>/dev/null || true

echo "Очищаем неиспользуемые образы..."
docker image prune -f

echo "Пересобираем образы с нуля..."
docker-compose build --no-cache

echo "Запускаем контейнеры..."
docker-compose up -d

echo "Готово! Проверьте статус:"
docker-compose ps

