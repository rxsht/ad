FROM python:3.11.5

# Установка рабочей директории
WORKDIR /app

# Устанавливаем зависимости системы и netcat для health checks
RUN apt-get update && apt-get install -y \
    postgresql-client \
    libpq-dev \
    gcc \
    netcat-traditional \
    && rm -rf /var/lib/apt/lists/*

# Копируем файлы зависимостей
COPY requirements.txt /app/

# Установка Python зависимостей
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Копируем проект
COPY . /app/

# Копируем и делаем исполняемым entrypoint
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Создаём необходимые директории
RUN mkdir -p /app/Folder/media/pdf_files /app/Folder/media/txt_files /app/Folder/staticfiles

# Порт для приложения
EXPOSE 8000

# Entrypoint для инициализации
ENTRYPOINT ["/app/entrypoint.sh"]

# Команда по умолчанию
CMD ["gunicorn", "Folder.app.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--chdir", "/app/Folder"]
