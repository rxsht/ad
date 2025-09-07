# Делаю по README.md версию
FROM python:3.11.5

# Установка рабочей директории
WORKDIR /app

# Зависимость для pgvector
RUN apt-get update && apt-get install -y postgresql-client libpq-dev gcc

# Копируем файлы зависимостей
COPY requirements.txt /app/

# Установить зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Скопировать файлы проекта в контейнер
COPY . /app/

RUN python Folder/manage.py collectstatic --noinput

# Порт для приложения
EXPOSE 8000

# Команда для запуска приложения
CMD ["gunicorn", "Folder.app.wsgi:application", "--bind", "0.0.0.0:8000", "--chdir", "/app/Folder"]
