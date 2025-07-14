# store/admin.py

from django.contrib import admin
from .models import Product, Category # Importa o novo modelo Category

# Registra o modelo Category no painel de administração do Django
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    # Campos que serão exibidos na lista de categorias no admin
    list_display = ('name', 'parent', 'slug')
    # Campos pelos quais você pode pesquisar as categorias
    search_fields = ('name', 'slug')
    # Campos que serão preenchidos automaticamente
    prepopulated_fields = {'slug': ('name',)} # Preenche o slug automaticamente ao digitar o nome
    # Filtro para categorias pai
    list_filter = ('parent',)

# Registra o modelo Product no painel de administração do Django
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    # Campos que serão exibidos na lista de produtos no admin
    list_display = ('name', 'category', 'price', 'is_featured', 'created_at')
    # Campos pelos quais você pode filtrar os produtos
    list_filter = ('is_featured', 'category', 'created_at') # Adiciona filtro por categoria
    # Campos pelos quais você pode pesquisar os produtos
    search_fields = ('name', 'description')
    # prepopulated_fields = {'slug': ('name',)} # Se você tivesse um campo slug

