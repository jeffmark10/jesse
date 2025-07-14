# jecistore_project/urls.py

from django.contrib import admin
from django.urls import path, include
from store.views import home_view
from django.conf import settings # Importe settings
from django.conf.urls.static import static # Importe static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home_view, name='home'), 
    path('store/', include('store.urls')), 
]

# Apenas para servir arquivos de mídia durante o desenvolvimento
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)