# store/views.py

from django.shortcuts import render, get_object_or_404
from .models import Product, Category # Importa o modelo Category

# Função auxiliar para obter categorias raiz e seus filhos
def get_categories_tree():
    # Busca todas as categorias que não têm um pai (categorias de nível superior)
    root_categories = Category.objects.filter(parent__isnull=True).prefetch_related('children')
    return root_categories

# View para a página inicial da Jeci Store
def home_view(request):
    featured_products = Product.objects.filter(is_featured=True)[:4]
    categories = get_categories_tree() # Obtém a árvore de categorias
    context = {
        'featured_products': featured_products,
        'page_title': 'Bem-vindo à Jeci Store!',
        'categories': categories, # Passa as categorias para o template
    }
    return render(request, 'home.html', context)

# View para listar todos os produtos ou produtos por categoria
def product_list_view(request, category_slug=None): # Adiciona category_slug como parâmetro opcional
    products = Product.objects.all()
    current_category = None

    if category_slug:
        # Se um slug de categoria for fornecido, filtra os produtos por essa categoria
        current_category = get_object_or_404(Category, slug=category_slug)
        # Filtra por produtos da categoria atual OU de suas subcategorias
        # Isso garante que ao selecionar "Feminino", você veja todas as blusas, calças, etc.
        category_ids = [current_category.id]
        for child in current_category.children.all():
            category_ids.append(child.id)
            # Se você tiver mais níveis de subcategorias, precisaria de uma função recursiva aqui
            # para coletar todos os IDs de categorias descendentes.
            # Para 2 níveis (Pai -> Filho), isso é suficiente.
        products = products.filter(category__id__in=category_ids)

    categories = get_categories_tree() # Obtém a árvore de categorias para o menu
    context = {
        'products': products,
        'current_category': current_category, # Passa a categoria atual (se houver)
        'page_title': current_category.name if current_category else 'Nossos Produtos',
        'categories': categories, # Passa as categorias para o template
    }
    return render(request, 'product_list.html', context)

# View para exibir os detalhes de um produto específico
def product_detail_view(request, pk):
    product = get_object_or_404(Product, pk=pk)
    categories = get_categories_tree() # Obtém a árvore de categorias
    context = {
        'product': product,
        'page_title': product.name,
        'categories': categories, # Passa as categorias para o template
    }
    return render(request, 'product_detail.html', context)

# View para a página "Sobre Nós"
def about_view(request):
    categories = get_categories_tree() # Obtém a árvore de categorias
    context = {
        'page_title': 'Sobre a Jeci Store',
        'categories': categories, # Passa as categorias para o template
    }
    return render(request, 'about.html', context)

# View para a página de "Contato"
def contact_view(request):
    categories = get_categories_tree() # Obtém a árvore de categorias
    context = {
        'page_title': 'Fale Conosco',
        'categories': categories, # Passa as categorias para o template
    }
    return render(request, 'contact.html', context)

