from django.contrib import admin
from django.urls import include, path
from users import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.main, name='main'), 
    path('logout/', views.logout_view, name='logout'),
    path('documents/', include('documents.urls', namespace="documents")),
    path('users/', include('users.urls', namespace = "users")),
]

if settings.DEBUG:
    urlpatterns += [path("__debug__/", include("debug_toolbar.urls"))]
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
