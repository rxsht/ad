FROM python:3.11.5

# Установка рабочей директории
WORKDIR /app

# Устанавливаем зависимости системы и netcat для health checks
RUN apt-get update && apt-get install -y \
    postgresql-client \
    libpq-dev \
    gcc \
    g++ \
    make \
    netcat-traditional \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Установка Rust для сборки tokenizers
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

# Копируем файлы зависимостей
COPY requirements.txt /app/

# Установка Python зависимостей
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Копируем проект
COPY . /app/

# Исправляем окончания строк entrypoint и кладём его вне /app, чтобы bind-монтирование не перетёрло
RUN apt-get update && apt-get install -y dos2unix && \
    cp /app/entrypoint.sh /usr/local/bin/entrypoint.sh && \
    dos2unix /usr/local/bin/entrypoint.sh && \
    chmod +x /usr/local/bin/entrypoint.sh && \
    rm -rf /var/lib/apt/lists/*

# Создаём необходимые директории
RUN mkdir -p /app/Folder/media/pdf_files /app/Folder/media/txt_files /app/Folder/staticfiles

# Порт для приложения
EXPOSE 8000

# Entrypoint для инициализации (вне /app, чтобы не зависеть от монтирования кода)
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

# Команда по умолчанию
CMD ["gunicorn", "Folder.app.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--chdir", "/app/Folder"]


