# 🔴 REDIS: Полное руководство для проекта

## 📋 ЧТО ТАКОЕ REDIS

Redis (Remote Dictionary Server) — сверхбыстрая база данных в оперативной памяти.

**Скорость:**
- PostgreSQL (диск): ~1-10 ms
- Redis (RAM): ~0.001-0.1 ms ⚡ (в 100-1000 раз быстрее!)

---

## 🎯 ПРИМЕНЕНИЕ В ПРОЕКТЕ

### 1. Celery Message Broker (очередь задач)
Позволяет обрабатывать документы асинхронно в фоне.

### 2. Кэширование
- Векторы текстов (1-5 сек → 0.001 сек)
- Результаты анализа

### 3. Координация
- Статусы обработки документов
- Прогресс выполнения задач

---

## 📥 УСТАНОВКА

### Вариант 1: Docker (РЕКОМЕНДУЕТСЯ)

```powershell
# Запустить Redis контейнер
docker run -d -p 6379:6379 --name redis redis:alpine

# Проверить
docker ps | findstr redis

# Подключиться
docker exec -it redis redis-cli
> ping
PONG
```

**Плюсы:**
- ✅ Просто
- ✅ Изолировано
- ✅ Легко удалить

---

### Вариант 2: Memurai (Redis для Windows)

1. Скачать: https://www.memurai.com/get-memurai
2. Установить как Windows Service
3. Запустится автоматически

**Плюсы:**
- ✅ Нативный для Windows
- ✅ Работает как служба
- ✅ GUI для управления

---

### Вариант 3: WSL2 + Redis

```bash
# В WSL2 Ubuntu
sudo apt update
sudo apt install redis-server
sudo service redis-server start
```

---

## ✅ ПРОВЕРКА ПОДКЛЮЧЕНИЯ

### PowerShell:
```powershell
# Через Docker
docker exec -it redis redis-cli ping

# Через Memurai
"C:\Program Files\Memurai\memurai-cli.exe" ping
```

### Python:
```python
import redis

r = redis.Redis(host='localhost', port=6379, decode_responses=True)
r.ping()  # True
```

---

## 🔧 НАСТРОЙКА ПРОЕКТА

### 1. Обновить requirements.txt
```
redis==5.0.1
celery==5.3.4
```

### 2. Настроить .env (уже сделано)
```env
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

### 3. Запустить Celery Worker
```powershell
cd Folder
celery -A app worker --loglevel=info --pool=solo
```

---

## 🚀 ИСПОЛЬЗОВАНИЕ

### Пример: кэширование

```python
import redis

r = redis.Redis(decode_responses=True)

# Сохранить
r.set('user:123:name', 'Иван', ex=3600)  # TTL 1 час

# Получить
name = r.get('user:123:name')  # 'Иван'

# Удалить
r.delete('user:123:name')
```

### Пример: счётчики

```python
# Атомарное увеличение
r.incr('page:views')  # 1
r.incr('page:views')  # 2

# Получить значение
views = r.get('page:views')  # '2'
```

### Пример: списки (очереди)

```python
# Добавить в очередь
r.lpush('tasks', 'task1')
r.lpush('tasks', 'task2')

# Извлечь (FIFO)
task = r.rpop('tasks')  # 'task1'
```

---

## 📊 МОНИТОРИНГ

### Redis CLI:

```bash
redis-cli

# Просмотр всех ключей
KEYS *

# Информация о сервере
INFO

# Количество ключей
DBSIZE

# Мониторинг команд в реальном времени
MONITOR
```

### Flower (для Celery):

```powershell
cd Folder
celery -A app flower --port=5555
```

Откройте: http://localhost:5555

---

## 🧹 ОЧИСТКА

### Удалить все данные:
```bash
redis-cli FLUSHALL
```

### Удалить по паттерну:
```bash
redis-cli --scan --pattern "celery*" | xargs redis-cli DEL
```

---

## 🐛 РЕШЕНИЕ ПРОБЛЕМ

### Redis не запускается

**Docker:**
```powershell
docker logs redis
docker restart redis
```

**Memurai:**
```powershell
# Проверить службу
Get-Service Memurai
```

### Celery не видит Redis

```python
# Проверить подключение
python
>>> import redis
>>> r = redis.Redis()
>>> r.ping()
True
```

### Порт 6379 занят

```powershell
# Узнать что использует порт
netstat -ano | findstr :6379
```

---

## 💾 ПЕРСИСТЕНТНОСТЬ

Redis хранит данные в RAM, но может сохранять на диск:

### RDB (snapshot):
```bash
# В redis.conf
save 900 1      # Сохранить если 1+ изменение за 15 мин
save 300 10     # Сохранить если 10+ изменений за 5 мин
```

### AOF (append-only file):
```bash
appendonly yes
appendfsync everysec
```

**Для Celery очередей:** персистентность не критична (задачи можно пересоздать).

---

## 📈 ПРОИЗВОДИТЕЛЬНОСТЬ

### Текущий проект:

**БЕЗ Redis:**
- Отклик: 30-60 сек
- Параллелизм: 1 документ
- Кэш: нет

**С Redis:**
- Отклик: <1 сек ⚡
- Параллелизм: 4-8 документов
- Кэш: 1000x ускорение

---

## 🎓 КОМАНДЫ REDIS

### Строки:
```bash
SET key value [EX seconds]
GET key
DEL key
INCR key
```

### Списки:
```bash
LPUSH key value
RPUSH key value
LPOP key
RPOP key
LRANGE key 0 -1
```

### Хэши:
```bash
HSET user:123 name "Иван"
HGET user:123 name
HGETALL user:123
```

### Sets:
```bash
SADD tags "python" "redis"
SMEMBERS tags
```

### Sorted Sets:
```bash
ZADD leaderboard 100 "user1"
ZRANGE leaderboard 0 -1 WITHSCORES
```

---

## 🔒 БЕЗОПАСНОСТЬ

### Production:

```bash
# redis.conf
bind 127.0.0.1              # Только localhost
requirepass your_password   # Пароль
maxmemory 256mb             # Лимит памяти
maxmemory-policy allkeys-lru # Политика вытеснения
```

### В проекте:
```env
CELERY_BROKER_URL=redis://:password@localhost:6379/0
```

---

## 📚 ДОПОЛНИТЕЛЬНО

### Документация:
- https://redis.io/docs/
- https://docs.celeryq.dev/

### GUI клиенты:
- RedisInsight (официальный)
- Another Redis Desktop Manager
- Medis (Mac)

---

## ✅ ЧЕКЛИСТ ПРОВЕРКИ

- [ ] Redis установлен и запущен
- [ ] `redis-cli ping` возвращает `PONG`
- [ ] Python подключается: `redis.Redis().ping()`
- [ ] Celery worker запущен
- [ ] Flower работает на :5555
- [ ] Django загрузка документа < 1 сек

Готово! 🎉
