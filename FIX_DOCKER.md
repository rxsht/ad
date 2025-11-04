# Исправление ошибки ContainerConfig в Docker Compose

## Проблема
Ошибка `KeyError: 'ContainerConfig'` возникает, когда Docker Compose пытается работать с поврежденными контейнерами или образами.

## Решение

Выполните следующие команды **на сервере Linux** (в директории с проектом):

### Вариант 1: Автоматический скрипт

```bash
# Сделайте скрипт исполняемым
chmod +x fix-docker.sh

# Запустите скрипт
./fix-docker.sh
```

### Вариант 2: Ручные команды

```bash
# 1. Остановите и удалите все контейнеры
docker-compose down --remove-orphans

# 2. Удалите проблемные контейнеры вручную (если есть)
docker rm -f django_web flower_monitor celery_worker 2>/dev/null || true

# 3. Удалите старые образы проекта
docker images | grep forked-ad | awk '{print $3}' | xargs docker rmi -f 2>/dev/null || true

# Или удалите все образы проекта явно:
docker rmi -f $(docker images -q --filter "reference=*forked-ad*") 2>/dev/null || true

# 4. Очистите неиспользуемые образы
docker image prune -f

# 5. Пересоберите образы с нуля
docker-compose build --no-cache

# 6. Запустите контейнеры
docker-compose up -d

# 7. Проверьте статус
docker-compose ps
```

### Если проблема сохраняется

```bash
# Полная очистка (⚠️ удалит все неиспользуемые контейнеры и образы)
docker system prune -a --volumes

# Затем пересоберите
docker-compose build --no-cache
docker-compose up -d
```

## Проверка

После выполнения команд проверьте логи:

```bash
# Логи веб-сервера
docker-compose logs web

# Логи всех сервисов
docker-compose logs
```

## Примечания

- Команды должны выполняться на сервере Linux, где запущен Docker
- Убедитесь, что вы находитесь в директории проекта (`~/ad` или где находится `docker-compose.yml`)
- Если у вас нет прав, используйте `sudo` перед командами docker

