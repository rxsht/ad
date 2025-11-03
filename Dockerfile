# Multi-stage build для минимизации размера
FROM python:3.11-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /build/

# Установка PyTorch CPU версии сначала
RUN pip install --no-cache-dir --upgrade pip

RUN pip install --no-cache-dir --user torch==2.0.1+cpu torchvision==0.15.2+cpu --index-url https://download.pytorch.org/whl/cpu

# Установка остальных зависимостей, пропуская torch и torchvision
RUN pip install --no-cache-dir --user -r requirements.txt

# Чистка
RUN find /root/.local -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true && \
    find /root/.local -type f -name "*.pyc" -delete

FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client libpq5 netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# Копируем установленные пакеты
COPY --from=builder /root/.local /root/.local

ENV PATH=/root/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

COPY Folder/ /app/Folder/
COPY entrypoint.sh /usr/local/bin/entrypoint.sh

RUN chmod +x /usr/local/bin/entrypoint.sh && \
    mkdir -p /app/Folder/media/pdf_files /app/Folder/media/txt_files /app/Folder/staticfiles

EXPOSE 8000

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["gunicorn", "Folder.app.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--chdir", "/app/Folder"]
