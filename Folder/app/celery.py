import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
app = Celery('app')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Настройка роутинга задач по очередям
app.conf.task_routes = {
    'documents.tasks.process_document_plagiarism': {'queue': 'plagiarism'},
    'documents.tasks.batch_process_documents': {'queue': 'batch'},
}

# Отслеживание начала выполнения задач
app.conf.task_track_started = True

# Игнорирование результатов для экономии памяти (опционально)
# app.conf.task_ignore_result = False

# Настройки для worker
app.conf.worker_prefetch_multiplier = 1  # Берём по одной задаче за раз
app.conf.worker_max_tasks_per_child = 50  # Рестарт worker после 50 задач (защита от утечек памяти)