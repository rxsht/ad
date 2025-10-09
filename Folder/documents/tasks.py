"""
Celery-задачи для асинхронной обработки документов
"""

import os
from celery import shared_task
from django.utils import timezone
from django.conf import settings

from documents.models import Document, Status
from documents import text_clining, vector
from documents.detectors import AdvancedPlagiarismDetector


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_document_plagiarism(self, document_id):
    """
    Асинхронная обработка документа: извлечение текста, векторизация, анализ плагиата
    
    Args:
        document_id: ID документа в базе данных
        
    Returns:
        Dict с результатами обработки
    """
    try:
        # Получаем документ
        doc = Document.objects.get(id=document_id)
        
        # Обновляем статус на "обрабатывается"
        doc.processing_status = 'processing'
        doc.processing_started_at = timezone.now()
        doc.save(update_fields=['processing_status', 'processing_started_at'])
        
        # Шаг 1: Извлечение текста из PDF
        try:
            pdf_path = doc.data.path if os.path.isabs(doc.data.path) else os.path.join("media", doc.data.path)
            text_content = text_clining.clean_text_from_pdf(pdf_path)
            txt_filename = f"{doc.name}.txt"
            txt_file_path = os.path.join("media", "txt_files", txt_filename)
            
            # Создаём директорию если её нет
            os.makedirs(os.path.dirname(txt_file_path), exist_ok=True)
            
            with open(txt_file_path, "w", encoding='utf-8') as text_file:
                text_file.write(text_content)
                
            doc.txt_file = f"txt_files/{txt_filename}"
            doc.save(update_fields=['txt_file'])
            
        except Exception as e:
            raise Exception(f"Ошибка при извлечении текста из PDF: {str(e)}")
        
        # Шаг 2: Векторизация текста
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
        
        # Шаг 3: Детальный анализ плагиата с использованием AdvancedPlagiarismDetector
        try:
            detector = AdvancedPlagiarismDetector()
            analysis_result = detector.detect_plagiarism(document_id)
            
            if analysis_result['status'] == 'success':
                # Сохраняем результаты (статус НЕ меняем - он изменится при "Отправить на проверку")
                doc.result = analysis_result['originality']
                doc.detailed_analysis = analysis_result
                doc.processing_status = 'completed'
                doc.processing_completed_at = timezone.now()
                doc.processing_error = None
                
                doc.save(update_fields=[
                    'result', 
                    'detailed_analysis', 
                    'processing_status', 
                    'processing_completed_at',
                    'processing_error'
                ])
                
                return {
                    'status': 'success',
                    'document_id': document_id,
                    'originality': float(doc.result),
                    'message': analysis_result['message']
                }
            else:
                # Анализ вернул ошибку или предупреждение
                error_msg = analysis_result.get('message', 'Неизвестная ошибка анализа')
                raise Exception(error_msg)
                
        except Exception as e:
            raise Exception(f"Ошибка при анализе плагиата: {str(e)}")
            
    except Exception as exc:
        # Обрабатываем ошибку
        try:
            doc = Document.objects.get(id=document_id)
            doc.processing_status = 'failed'
            doc.processing_error = str(exc)
            doc.processing_completed_at = timezone.now()
            doc.save(update_fields=['processing_status', 'processing_error', 'processing_completed_at'])
        except Exception:
            pass
        
        # Пробуем повторить задачу
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=60)
        else:
            return {
                'status': 'failed',
                'document_id': document_id,
                'error': str(exc)
            }


@shared_task
def reprocess_document(document_id):
    """
    Пересчитать оригинальность для существующего документа
    
    Args:
        document_id: ID документа
    """
    return process_document_plagiarism.delay(document_id)


@shared_task
def batch_process_documents(document_ids):
    """
    Пакетная обработка документов
    
    Args:
        document_ids: Список ID документов
        
    Returns:
        List с результатами обработки
    """
    results = []
    for doc_id in document_ids:
        task = process_document_plagiarism.delay(doc_id)
        results.append({
            'document_id': doc_id,
            'task_id': task.id
        })
    return results
