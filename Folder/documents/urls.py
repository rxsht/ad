from django.urls import path
from django.contrib.auth import views as auth_views
from documents import views


app_name = 'documents'

urlpatterns = [
    path('cabinet/search/', views.cabinet, name = 'cabinet/search'),
    path('cabinet/', views.cabinet, name = 'cabinet'),
    # path('cabinet/<int:page>/', views.cabinet, name = 'cabinet'),
    path ('results/', views.results, name= 'results' ),
    path ('results/search/', views.results, name= 'results/search' ),
    path('change-status/<int:document_id>/', views.change_status, name='change_status'),
    path('change-statusa/<int:document_id>/', views.change_statusa, name='change_statusa'),
    path('change-statusb/<int:document_id>/', views.change_statusb, name='change_statusb'),
    path('download-file/<int:document_id>/', views.download_file, name='download_file'),
]

