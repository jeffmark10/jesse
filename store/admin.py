# store/admin.py

from django.contrib import admin
from .models import Product, Category, Cart, CartItem # Importa os modelos de carrinho

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
    list_display = ('name', 'category', 'price', 'stock', 'is_featured', 'created_at') # Adicionado 'stock'
    # Campos pelos quais você pode filtrar os produtos
    list_filter = ('is_featured', 'category', 'created_at', 'stock') # Adicionado filtro por estoque
    # Campos pelos quais você pode pesquisar os produtos
    search_fields = ('name', 'description')
    # prepopulated_fields = {'slug': ('name',)} # Se você tivesse um campo slug

# Opcional: Registra os modelos de Carrinho e Item de Carrinho no admin
@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('user', 'session_key', 'created_at', 'updated_at', 'get_total_price_display')
    list_filter = ('created_at', 'updated_at', 'user')
    search_fields = ('user__username', 'session_key')
    readonly_fields = ('created_at', 'updated_at')

    def get_total_price_display(self, obj):
        return f"R$ {obj.get_total_price():.2f}"
    get_total_price_display.short_description = "Valor Total"


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ('cart', 'product', 'quantity', 'added_at', 'get_total_price_display')
    list_filter = ('added_at', 'product__category')
    search_fields = ('product__name', 'cart__user__username', 'cart__session_key')
    readonly_fields = ('added_at',)

    def get_total_price_display(self, obj):
        return f"R$ {obj.get_total_price():.2f}"
    get_total_price_display.short_description = "Total do Item"

