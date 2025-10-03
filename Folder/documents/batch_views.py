"""
Представления для массовых операций с документами
"""

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.db import transaction
from django.contrib import messages
import json
import logging

from documents.models import Document, DocumentBatch, DocumentProcessingQueue
from documents.vector_models import DocumentVector, DocumentSimilarity
from documents.forms import DocumentForm

logger = logging.getLogger(__name__)


@login_required
def batch_upload_view(request):
    """
    Представление для массовой загрузки документов
    """
    if request.method == 'POST':
        try:
            # Получаем данные из запроса
            files = request.FILES.getlist('files')
            batch_name = request.POST.get('batch_name', 'Batch Upload')
            
            if not files:
                return JsonResponse({'error': 'No files provided'}, status=400)
            
            # Создаем пакет
            batch = DocumentBatch.objects.create(
                name=batch_name,
                total_documents=len(files),
                created_by=request.user
            )
            
            # Обрабатываем файлы
            processed_docs = []
            for file in files:
                try:
                    document = Document.objects.create(
                        name=file.name,
                        data=file,
                        user=request.user,
                        status_id=1  # В очереди
                    )
                    processed_docs.append(document.id)
                    
                    # Добавляем в очередь обработки
                    DocumentProcessingQueue.objects.create(
                        document=document,
                        batch=batch,
                        priority=2
                    )
                    
                except Exception as e:
                    logger.error(f"Error processing file {file.name}: {e}")
                    batch.failed_documents += 1
            
            batch.processed_documents = len(processed_docs)
            batch.save()
            
            return JsonResponse({
                'success': True,
                'batch_id': batch.id,
                'processed_documents': len(processed_docs),
                'message': f'Successfully uploaded {len(processed_docs)} documents'
            })
            
        except Exception as e:
            logger.error(f"Batch upload error: {e}")
            return JsonResponse({'error': str(e)}, status=500)
    
    return render(request, 'documents/batch_upload.html')


@login_required
def batch_process_view(request):
    """
    Представление для обработки пакета документов
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            document_ids = data.get('document_ids', [])
            batch_name = data.get('batch_name', 'Manual Batch')
            
            if not document_ids:
                return JsonResponse({'error': 'No documents provided'}, status=400)
            
            # Создаем пакет
            batch = DocumentBatch.objects.create(
                name=batch_name,
                total_documents=len(document_ids),
                created_by=request.user
            )
            
            # Добавляем документы в очередь обработки
            for doc_id in document_ids:
                DocumentProcessingQueue.objects.create(
                    document_id=doc_id,
                    batch=batch,
                    priority=2
                )
            
            return JsonResponse({
                'success': True,
                'batch_id': batch.id,
                'status': batch.status,
                'message': f'Batch processing started for {len(document_ids)} documents'
            })
            
        except Exception as e:
            logger.error(f"Batch processing error: {e}")
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@login_required
def batch_status_view(request, batch_id):
    """
    Представление для получения статуса пакета
    """
    try:
        batch = DocumentBatch.objects.get(id=batch_id)
        
        return JsonResponse({
            'batch_id': batch.id,
            'name': batch.name,
            'status': batch.status,
            'total_documents': batch.total_documents,
            'processed_documents': batch.processed_documents,
            'failed_documents': batch.failed_documents,
            'created_at': batch.created_at.isoformat(),
            'started_at': batch.started_at.isoformat() if batch.started_at else None,
            'completed_at': batch.completed_at.isoformat() if batch.completed_at else None,
            'error_message': batch.error_message
        })
        
    except DocumentBatch.DoesNotExist:
        return JsonResponse({'error': 'Batch not found'}, status=404)
    except Exception as e:
        logger.error(f"Batch status error: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def batch_list_view(request):
    """
    Представление для списка пакетов
    """
    batches = DocumentBatch.objects.all().order_by('-created_at')
    
    # Пагинация
    page_number = request.GET.get('page', 1)
    paginator = Paginator(batches, 20)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'batches': page_obj,
        'paginator': paginator
    }
    
    return render(request, 'documents/batch_list.html', context)


@login_required
def optimize_database_view(request):
    """
    Представление для оптимизации базы данных
    """
    if request.method == 'POST':
        try:
            # Создаем индексы
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS vector_hnsw_idx ON document_vectors USING hnsw (vector vector_cosine_ops);")
                cursor.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS normalized_vector_gin_idx ON document_vectors USING gin (normalized_vector);")
                cursor.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS similarity_weighted_idx ON document_similarities (weighted_similarity DESC);")
            
            return JsonResponse({
                'success': True,
                'message': 'Database optimization completed'
            })
            
        except Exception as e:
            logger.error(f"Database optimization error: {e}")
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@login_required
def similarity_search_view(request):
    """
    Представление для поиска похожих документов
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            document_id = data.get('document_id')
            threshold = data.get('threshold', 0.7)
            limit = data.get('limit', 10)
            
            if not document_id:
                return JsonResponse({'error': 'Document ID required'}, status=400)
            
            # Получаем документ
            document = Document.objects.get(id=document_id)
            
            # Ищем похожие документы
            similarities = DocumentSimilarity.objects.filter(
                document1=document,
                weighted_similarity__gte=threshold
            ).order_by('-weighted_similarity')[:limit]
            
            results = []
            for similarity in similarities:
                results.append({
                    'document_id': similarity.document2.id,
                    'document_name': similarity.document2.name,
                    'similarity': similarity.weighted_similarity,
                    'cosine_similarity': similarity.cosine_similarity,
                    'is_paraphrasing': similarity.is_paraphrasing,
                    'confidence': similarity.confidence_score
                })
            
            return JsonResponse({
                'success': True,
                'results': results,
                'total_found': len(results)
            })
            
        except Document.DoesNotExist:
            return JsonResponse({'error': 'Document not found'}, status=404)
        except Exception as e:
            logger.error(f"Similarity search error: {e}")
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@login_required
def bulk_originality_calculation_view(request):
    """
    Представление для массового вычисления оригинальности
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            document_ids = data.get('document_ids', [])
            
            if not document_ids:
                return JsonResponse({'error': 'No documents provided'}, status=400)
            
            # Вычисляем оригинальность для каждого документа
            for doc_id in document_ids:
                try:
                    document = Document.objects.get(id=doc_id)
                    document.calculate_originality()
                except Exception as e:
                    logger.error(f"Error calculating originality for document {doc_id}: {e}")
            
            return JsonResponse({
                'success': True,
                'message': f'Originality calculated for {len(document_ids)} documents'
            })
            
        except Exception as e:
            logger.error(f"Bulk originality calculation error: {e}")
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)
