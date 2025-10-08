"""
Синхронная обработка документов (fallback когда Celery недоступен)
"""

import os
from django.utils import timezone

from documents.models import Document, Status
from documents import text_clining, vector
from documents.detectors import AdvancedPlagiarismDetector


def process_document_sync(document_id):
    """
    Синхронная обработка документа
    Используется как fallback когда Celery/Redis недоступен
    """
    try:
        doc = Document.objects.get(id=document_id)
        
        doc.processing_status = 'processing'
        doc.processing_started_at = timezone.now()
        doc.save(update_fields=['processing_status', 'processing_started_at'])
        
        # Шаг 1: Извлечение текста
        pdf_path = doc.data.path if os.path.isabs(doc.data.path) else os.path.join("media", doc.data.path)
        text_content = text_clining.clean_text_from_pdf(pdf_path)
        txt_filename = f"{doc.name}.txt"
        txt_file_path = os.path.join("media", "txt_files", txt_filename)
        
        os.makedirs(os.path.dirname(txt_file_path), exist_ok=True)
        
        with open(txt_file_path, "w", encoding='utf-8') as text_file:
            text_file.write(text_content)
            
        doc.txt_file = f"txt_files/{txt_filename}"
        doc.save(update_fields=['txt_file'])
        
        # Шаг 2: Векторизация
        try:
            vector_array = vector.process_text(txt_file_path)
            doc.set_vector_array(vector_array)
            doc.save(update_fields=['vector'])
        except Exception as e:
            print(f"Предупреждение: Ошибка при создании вектора: {e}")
            doc.vector = None
            doc.save(update_fields=['vector'])
        
        # Перезагружаем документ из БД чтобы обновить пути к файлам
        doc.refresh_from_db()
        
        # Шаг 3: Анализ плагиата
        detector = AdvancedPlagiarismDetector()
        analysis_result = detector.detect_plagiarism(document_id)
        
        if analysis_result['status'] == 'success':
            doc.result = analysis_result['originality']
            doc.detailed_analysis = analysis_result
            doc.processing_status = 'completed'
            doc.status = Status.objects.get(pk=2)
            doc.processing_completed_at = timezone.now()
            doc.processing_error = None
            
            doc.save(update_fields=[
                'result', 
                'detailed_analysis', 
                'processing_status', 
                'status', 
                'processing_completed_at',
                'processing_error'
            ])
            
            return {
                'status': 'success',
                'document_id': document_id,
                'originality': float(doc.result)
            }
        else:
            raise Exception(analysis_result.get('message', 'Ошибка анализа'))
            
    except Exception as e:
        try:
            doc = Document.objects.get(id=document_id)
            doc.processing_status = 'failed'
            doc.processing_error = str(e)
            doc.processing_completed_at = timezone.now()
            doc.save(update_fields=['processing_status', 'processing_error', 'processing_completed_at'])
        except Exception:
            pass
        
        raise e
