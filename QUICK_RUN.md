# ⚡ БЫСТРЫЙ ЗАПУСК

## 🚀 Запустить ВСЁ одним кликом

### Способ 1: BAT-файл (Windows)

**Двойной клик на:**
```
start_all.bat
```

Автоматически запустит:
- ✅ Redis (Docker)
- ✅ Django сервер (http://localhost:8000)
- ✅ Celery Worker (фоновая обработка)

### Способ 2: Docker Compose (Production)

```powershell
docker compose up -d
```

Запустит:
- ✅ PostgreSQL
- ✅ Redis
- ✅ Django
- ✅ Celery
- ✅ Flower (мониторинг)

---

## 🛑 Остановить ВСЁ

### BAT-файл:
```
stop_all.bat
```

### Docker Compose:
```powershell
docker compose down
```

---

## 📝 Отдельные команды

### Запустить только Django:
```powershell
cd Folder
python manage.py runserver
```

### Запустить только Celery:
```
start_celery.bat
```
или
```powershell
cd Folder
celery -A app worker --loglevel=info --pool=solo
```

### Запустить только Redis:
```powershell
docker start redis
```

---

## 🎯 Что выбрать?

| Задача | Команда |
|--------|---------|
| **Разработка (всё сразу)** | `start_all.bat` |
| **Только Django (без async)** | `python manage.py runserver` |
| **Production (сервер)** | `docker compose up -d` |
| **Остановить всё** | `stop_all.bat` |

---

## ✅ Проверка что всё работает

### 1. Django:
```
http://localhost:8000
```
Должна открыться главная страница ✅

### 2. Redis:
```powershell
docker exec -it redis redis-cli ping
# Ответ: PONG ✅
```

### 3. Celery:
```powershell
celery -A app inspect active
# Покажет список задач ✅
```

---

## 🎉 Готово!

Теперь запуск проекта - **один клик**! 🚀
