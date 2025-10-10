from django.shortcuts import redirect, render, get_object_or_404
from django.db.models import Q
from documents.models import Document, Status
from documents.forms import DocumentForm
from django.views.generic import View
from django.contrib.auth.decorators import login_required
from django.contrib import auth, messages


from django.http import HttpResponse, HttpResponseRedirect 
from django.urls import reverse,reverse_lazy
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from django.http import JsonResponse
from documents.utils import q_search
from documents.utils import q_search_by_fio
from django.core.paginator import Paginator

# Импорт Celery задачи
from documents.tasks import process_document_plagiarism

def download_file(request, document_id):
    document = Document.objects.get(id=document_id)
    
    # Обрабатываем случай, когда result может быть None
    result_value = document.result if document.result is not None else 0
    result_float = float(result_value) if result_value is not None else 0.0
    result_int = int(result_float)
    
    context = {
        'document': document,
        'result': result_int,
        'similarity': 100 - result_int,
        'doc_similarity': round(100 - result_float, 2) if result_value is not None else 100,  
    }
    return render(request, 'documents/file.html', context)

@login_required
def change_status(request, document_id):
    document = Document.objects.get(id=document_id)
    # На защите
    document.status = Status.objects.get(pk=1)
    document.last_status_changed_by = request.user
    document.save()
    return redirect('documents:results') 

@login_required
def change_statusa(request, document_id):
    document = Document.objects.get(id=document_id)
    # Зачтен
    document.status = Status.objects.get(pk=3) 
    document.last_status_changed_by = request.user
    document.save()
    return redirect('documents:results')

@login_required
def change_statusb(request, document_id):
    document = Document.objects.get(id=document_id)
    # Не зачтен
    document.status = Status.objects.get(pk=4)
    document.last_status_changed_by = request.user
    document.save()
    return redirect('documents:results')   

@login_required
def cabinet(request):
    query = request.GET.get('q', None)
    is_searching = bool(query)
    
    if request.method == 'POST':
        form = DocumentForm(request.POST, request.FILES)
        if form.is_valid():
            document = form.save(commit=False)
            document.user = request.user
            document.processing_status = 'queue'
            document.save()
            
            # Пробуем отправить в Celery, если недоступен - fallback на синхронную обработку
            try:
                process_document_plagiarism.delay(document.id)
                messages.success(request, f'Документ "{document.name}" загружен и отправлен на проверку')
            except Exception as e:
                # Если Celery/Redis недоступен - обрабатываем синхронно СРАЗУ
                try:
                    from documents.processing import process_document_sync
                    # Обрабатываем документ синхронно (занимает 30-60 сек)
                    result = process_document_sync(document.id)
                    
                    if result.get('status') == 'success':
                        messages.success(request, f'Документ "{document.name}" обработан успешно. Оригинальность: {result.get("originality", "N/A")}%')
                    else:
                        messages.warning(request, f'Документ загружен, но обработка завершилась с предупреждением')
                except Exception as sync_error:
                    messages.error(request, f'Ошибка обработки: {str(sync_error)}')
            
            return HttpResponseRedirect(reverse('documents:cabinet'))
    else:
        form = DocumentForm()
    if request.user.is_staff or request.user.is_superuser:
        # Админы и преподаватели видят все документы
        base_qs = Document.objects.all()
    else:
        # Обычные пользователи (студенты) видят только свои документы
        base_qs = Document.objects.filter(user=request.user)

    if query:
        # Создаём Q объект для поиска по имени документа
        keywords = query.split()
        q_objects = Q()
        for token in keywords:
            q_objects |= Q(name__icontains=token)
        documents = base_qs.filter(q_objects)
    else:
        documents = base_qs

    
    page_number = request.GET.get('page', 1)
    paginator = Paginator(documents, 10)  
    current_page_documents = paginator.get_page(page_number)

    context = {
        'form': form,
        'documents': current_page_documents,
        'query': query,
        'paginator': paginator,
        'is_searching': is_searching,
    }
    
    return render(request, 'documents/cab.html', context)


@login_required
def results(request):
    query = request.GET.get('q', '')  
    is_searching = bool(query) 
    # Показываем только документы отправленные на защиту (status_id=1)
    documents = Document.objects.filter(status_id=1)

    if query:
        documents = q_search_by_fio(query).filter(status_id=1)

    page_number = request.GET.get('page', 1)
    paginator = Paginator(documents, 10) 

    try:
        current_page_documents = paginator.page(page_number)
    except PageNotAnInteger:
        current_page_documents = paginator.page(1) 
    except EmptyPage:
        current_page_documents = paginator.page(paginator.num_pages)  
    context = {
        'documents': current_page_documents,
        'query': query, 
        'paginator': paginator,
        'is_searching': is_searching, 
    }

    return render(request, 'documents/results-cab.html', context)

@login_required
def logout_view(request):
    messages.success(request, f"{request.user.username}, Вы вышли из аккаунта")
    auth.logout(request)
    return render(request, 'users/main.html')


@login_required
def document_status(request, document_id):
    """
    API endpoint для получения статуса обработки документа
    Используется для AJAX-опроса прогресса
    """
    try:
        # Проверяем права доступа
        if request.user.is_staff or request.user.is_superuser:
            doc = get_object_or_404(Document, id=document_id)
        else:
            doc = get_object_or_404(Document, id=document_id, user=request.user)
        
        response_data = {
            'document_id': doc.id,
            'document_name': doc.name,
            'processing_status': doc.processing_status,
            'status_id': doc.status.id,
            'status_name': doc.status.name,
            'result': float(doc.result) if doc.result else None,
            'processing_started_at': doc.processing_started_at.isoformat() if doc.processing_started_at else None,
            'processing_completed_at': doc.processing_completed_at.isoformat() if doc.processing_completed_at else None,
            'processing_error': doc.processing_error,
            'detailed_analysis': doc.detailed_analysis
        }
        
        return JsonResponse(response_data)
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=404)
