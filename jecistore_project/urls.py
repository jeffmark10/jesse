# jecistore_project/urls.py

from django.contrib import admin
from django.urls import path, include
from store.views import home_view
from django.conf import settings # Importe settings
from django.conf.urls.static import static # Importe static

# Importa os manipuladores de erro personalizados
from store.views import custom_404_view, custom_500_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home_view, name='home'), 
    path('store/', include('store.urls')), 
    path('accounts/', include('django.contrib.auth.urls')), # URLs de autenticação do Django (login, logout, etc.)
]

# Apenas para servir arquivos de mídia e estáticos durante o desenvolvimento
# Em produção, um servidor web como Nginx ou Apache deve ser configurado para servir esses arquivos.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT) # Adicionado para estáticos

# Manipuladores de erro personalizados (não precisam de if settings.DEBUG)
handler404 = custom_404_view
handler500 = custom_500_view
