from django.urls import path
from users import views

app_name = 'users'

urlpatterns = [
    path('main/', views.main, name='main'),
    path('pers-cab/', views.pers_cab, name='pers-cab'),
    
]
