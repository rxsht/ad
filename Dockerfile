# Делаю по README.md версию
FROM python:3.11.5

# Установка рабочей директории
WORKDIR /app

# Зависимость для pgvector
RUN apt-get update && apt-get install -y postgresql-client libpq-dev gcc

# Обновляем pip
RUN pip install --upgrade pip

# Копируем файлы зависимостей
COPY requirements.txt /app/

# Установить зависимости с увеличенным таймаутом и retry
RUN pip install --no-cache-dir --timeout 1000 --retries 5 -r requirements.txt

# Скопировать файлы проекта в контейнер
COPY . /app/

# Создаем директории для статических файлов
RUN mkdir -p /app/Folder/staticfiles

# Собираем статические файлы
RUN python Folder/manage.py collectstatic --noinput --clear

# Порт для приложения
EXPOSE 8000

# Команда для запуска приложения
CMD ["gunicorn", "Folder.app.wsgi:application", "--bind", "0.0.0.0:8000", "--chdir", "/app/Folder"]
