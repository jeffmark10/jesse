# store/urls.py

from django.urls import path
from . import views

app_name = 'store'

urlpatterns = [
    # A rota para a página inicial é mapeada no urls.py principal do projeto
    # path('', views.home_view, name='home'), 
    
    # Rota para a lista de todos os produtos
    path('produtos/', views.product_list_view, name='product_list'),
    
    # NOVA ROTA: Rota para listar produtos por categoria
    path('produtos/categoria/<slug:category_slug>/', views.product_list_view, name='product_list_by_category'),
    
    # Rota para os detalhes de um produto específico
    path('produtos/<int:pk>/', views.product_detail_view, name='product_detail'),
    
    # Rota para a página "Sobre Nós"
    path('sobre/', views.about_view, name='about'),
    
    # Rota para a página de "Contato"
    path('contato/', views.contact_view, name='contact'),
]

