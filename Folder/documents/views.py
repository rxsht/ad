from django.shortcuts import redirect, render
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
    document.status = Status.objects.get(pk=3)
    document.last_status_changed_by = request.user
    document.save()
    return redirect('documents:results') 

@login_required
def change_statusa(request, document_id):
    document = Document.objects.get(id=document_id)
    document.status = Status.objects.get(pk=4) 
    document.last_status_changed_by = request.user
    document.save()
    return redirect('documents:results')

@login_required
def change_statusb(request, document_id):
    document = Document.objects.get(id=document_id)
    document.status = Status.objects.get(pk=5)
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
            document.save()
            return HttpResponseRedirect(reverse('documents:cabinet'))
    else:
        form = DocumentForm()
    if query:
        documents = q_search(query, request.user)  
    else:
        documents = Document.objects.filter(user=request.user)

    
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
    documents = Document.objects.filter(status_id=3)

    if query:
        documents = q_search_by_fio(query).filter(status_id=3)

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
