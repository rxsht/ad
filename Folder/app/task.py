from celery import Celery
from documents.models import Document

app = Celery('tasks', broker='redis://localhost:6379/0')

@app.task
def check_originality():
    all_texts = Document.objects.filter(result='').exclude(txt_file=None)

    for text in all_texts:
        text.calculate_originality()