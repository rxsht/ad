from django.urls import path
from django.contrib.auth import views as auth_views
from documents import views
from documents import batch_views


app_name = 'documents'

urlpatterns = [
    # Основные представления
    path('cabinet/search/', views.cabinet, name='cabinet/search'),
    path('cabinet/', views.cabinet, name='cabinet'),
    path('results/', views.results, name='results'),
    path('results/search/', views.results, name='results/search'),
    path('change-status/<int:document_id>/', views.change_status, name='change_status'),
    path('change-statusa/<int:document_id>/', views.change_statusa, name='change_statusa'),
    path('change-statusb/<int:document_id>/', views.change_statusb, name='change_statusb'),
    path('send-to-defense/<int:document_id>/', views.send_to_defense, name='send_to_defense'),
    path('cancel-from-defense/<int:document_id>/', views.cancel_from_defense, name='cancel_from_defense'),
    path('download-file/<int:document_id>/', views.download_file, name='download_file'),

    # QR-коды
    path('qr/report/<int:document_id>/', views.qr_report, name='qr_report'),
    path('qr/original/<int:document_id>/', views.qr_original, name='qr_original'),

    # API для статуса обработки
    path('status/<int:document_id>/', views.document_status, name='document_status'),

    # Массовые операции
    path('batch/upload/', batch_views.batch_upload_view, name='batch_upload'),
    path('batch/process/', batch_views.batch_process_view, name='batch_process'),
    path('batch/status/<int:batch_id>/', batch_views.batch_status_view, name='batch_status'),
    path('batch/list/', batch_views.batch_list_view, name='batch_list'),
    path('batch/optimize/', batch_views.optimize_database_view, name='optimize_database'),
    path('batch/similarity/search/', batch_views.similarity_search_view, name='similarity_search'),
    path('batch/originality/calculate/', batch_views.bulk_originality_calculation_view, name='bulk_originality'),
]
