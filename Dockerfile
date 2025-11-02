# ============================================
# STAGE 1: Builder - компиляция зависимостей
# ============================================
FROM python:3.11-slim as builder

WORKDIR /build

# Установка только необходимых для компиляции пакетов
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    gcc \
    g++ \
    make \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Установка Rust минимальной версией (только для компиляции)
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --default-toolchain stable --profile minimal
ENV PATH="/root/.cargo/bin:${PATH}"

# Копируем requirements для установки зависимостей
COPY requirements.txt /build/

# Установка Python зависимостей в виртуальное окружение
# CPU-only версия PyTorch (экономит ~1GB!)
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir --user -r requirements.txt && \
    # Заменяем torch на CPU-only версию для экономии места
    pip install --no-cache-dir --user --upgrade --force-reinstall torch --index-url https://download.pytorch.org/whl/cpu || true

# Очистка ненужных файлов после установки
RUN find /root/.local -type d -name __pycache__ -exec rm -r {} + 2>/dev/null || true && \
    find /root/.local -type f -name "*.pyc" -delete && \
    find /root/.local -type f -name "*.pyo" -delete

# Предзагрузка модели HuggingFace (опционально, но ускоряет старт)
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('paraphrase-MiniLM-L6-v2')" || true

# ============================================
# STAGE 2: Runtime - минимальный финальный образ
# ============================================
FROM python:3.11-slim

WORKDIR /app

# Установка только runtime зависимостей (без компиляторов!)
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    libpq5 \
    netcat-traditional \
    dos2unix \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean \
    && rm -rf /tmp/* /var/tmp/*

# Копируем только скомпилированные пакеты из builder stage
COPY --from=builder /root/.local /root/.local

# Копируем предзагруженную модель HuggingFace (если нужно)
COPY --from=builder /root/.cache/huggingface /root/.cache/huggingface 2>/dev/null || true

# Убедимся что скрипты используют локальные пакеты
ENV PATH=/root/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Копируем только необходимые файлы проекта
COPY Folder/ /app/Folder/
COPY entrypoint.sh /usr/local/bin/entrypoint.sh

# Исправляем окончания строк и права
RUN dos2unix /usr/local/bin/entrypoint.sh && \
    chmod +x /usr/local/bin/entrypoint.sh && \
    mkdir -p /app/Folder/media/pdf_files /app/Folder/media/txt_files /app/Folder/staticfiles && \
    # Удаляем ненужные файлы из проекта
    find /app -type d -name __pycache__ -exec rm -r {} + 2>/dev/null || true && \
    find /app -type f -name "*.pyc" -delete && \
    find /app -type f -name "*.pyo" -delete

# Порт для приложения
EXPOSE 8000

# Entrypoint для инициализации (вне /app, чтобы не зависеть от монтирования кода)
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

# Команда по умолчанию
CMD ["gunicorn", "Folder.app.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--chdir", "/app/Folder"]


