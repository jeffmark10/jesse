# store/views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, Http404 # Importa Http404 para erros
from django.contrib.auth.forms import UserCreationForm # Para registro de usuário
from django.contrib.auth.decorators import login_required # Para proteger views
from django.contrib import messages # Para mensagens de feedback
from django.db.models import Q # Para funcionalidade de busca
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger # Para paginação

from .models import Product, Category, Cart, CartItem, Profile # Importa os novos modelos de carrinho e Profile
from .forms import ContactForm, ProductForm # Importa o formulário de contato e ProductForm

# --- Funções Auxiliares ---

def get_descendant_category_ids(category):
    """
    Retorna uma lista de IDs da categoria fornecida e de todas as suas subcategorias
    em qualquer nível de profundidade.
    """
    category_ids = [category.id]
    for child in category.children.all():
        category_ids.extend(get_descendant_category_ids(child)) # Chamada recursiva
    return category_ids

def get_categories_tree():
    """
    Busca todas as categorias de nível superior e pré-carrega seus filhos
    para construir a árvore de categorias no menu.
    """
    root_categories = Category.objects.filter(parent__isnull=True).prefetch_related('children')
    return root_categories

def get_or_create_cart(request):
    """
    Obtém o carrinho do usuário logado ou da sessão.
    Cria um novo carrinho se não existir.
    """
    if request.user.is_authenticated:
        # Tenta obter o carrinho do usuário logado
        cart, created = Cart.objects.get_or_create(user=request.user)
        # Se houver um session_key e o carrinho foi criado agora, tenta migrar itens da sessão
        if created and request.session.session_key:
            session_cart = Cart.objects.filter(session_key=request.session.session_key).first()
            if session_cart:
                for item in session_cart.items.all():
                    # Tenta adicionar o item ao carrinho do usuário
                    user_cart_item, item_created = CartItem.objects.get_or_create(
                        cart=cart,
                        product=item.product,
                        defaults={'quantity': item.quantity}
                    )
                    if not item_created:
                        user_cart_item.quantity += item.quantity
                        user_cart_item.save()
                session_cart.delete() # Remove o carrinho da sessão após a migração
                if 'cart_id' in request.session: # Garante que a chave exista antes de tentar deletar
                    del request.session['cart_id'] # Limpa a session_key do carrinho antigo
        return cart
    else:
        # Para usuários não logados, usa a session_key
        if not request.session.session_key:
            request.session.save() # Garante que uma session_key exista
        cart_id = request.session.get('cart_id')
        if cart_id:
            try:
                cart = Cart.objects.get(id=cart_id)
            except Cart.DoesNotExist:
                cart = Cart.objects.create(session_key=request.session.session_key)
                request.session['cart_id'] = cart.id
        else:
            cart = Cart.objects.create(session_key=request.session.session_key)
            request.session['cart_id'] = cart.id
        return cart

# NOVO DECORADOR: Garante que apenas vendedores possam acessar a view
def seller_required(function):
    def wrap(request, *args, **kwargs):
        # Primeiro, verifica se o usuário está logado (reutiliza a lógica de login_required)
        if not request.user.is_authenticated:
            messages.error(request, "Você precisa estar logado para acessar esta área.")
            return redirect('login') # Redireciona para a página de login

        # Tenta obter o perfil do usuário
        try:
            profile = request.user.profile
        except Profile.DoesNotExist:
            # Se o perfil não existe, cria um novo perfil e define como não-vendedor
            profile = Profile.objects.create(user=request.user, is_seller=False)
            messages.warning(request, "Seu perfil foi criado. Você não tem permissão de vendedor.")
            return redirect('store:user_profile') # Redireciona para o perfil

        # Verifica se o usuário é um vendedor
        if not profile.is_seller:
            messages.warning(request, "Você não tem permissão para acessar esta área. Contate a administração se deseja se tornar um vendedor.")
            return redirect('store:user_profile') # Redireciona para o perfil se não for vendedor

        return function(request, *args, **kwargs)
    return wrap


# --- Views Principais ---

def home_view(request):
    featured_products = Product.objects.filter(is_featured=True, stock__gt=0)[:4] # Apenas produtos em estoque
    categories = get_categories_tree() # Obtém a árvore de categorias
    context = {
        'featured_products': featured_products,
        'page_title': 'Bem-vindo à Jeci Store!',
        'categories': categories, # Passa as categorias para o template
    }
    return render(request, 'home.html', context)

def product_list_view(request, category_slug=None):
    products = Product.objects.filter(stock__gt=0) # Começa filtrando apenas produtos em estoque
    current_category = None
    search_query = request.GET.get('q') # Obtém o parâmetro de busca 'q'
    min_price = request.GET.get('min_price') # Novo: filtro de preço mínimo
    max_price = request.GET.get('max_price') # Novo: filtro de preço máximo
    sort_by = request.GET.get('sort_by', 'name') # Novo: ordenação, padrão por nome

    if category_slug:
        current_category = get_object_or_404(Category, slug=category_slug)
        category_ids_to_filter = get_descendant_category_ids(current_category)
        products = products.filter(category__id__in=category_ids_to_filter)
    
    if search_query:
        # Filtra produtos pelo nome ou descrição que contenham a query de busca
        products = products.filter(
            Q(name__icontains=search_query) | Q(description__icontains=search_query)
        ).distinct()
        
        # Adiciona uma mensagem se não houver resultados para a busca
        if not products.exists():
            messages.info(request, f"Nenhum produto encontrado para '{search_query}'.")

    # Aplica filtros de preço
    if min_price:
        try:
            min_price = float(min_price)
            products = products.filter(price__gte=min_price)
        except ValueError:
            messages.error(request, "Valor mínimo de preço inválido.")
    
    if max_price:
        try:
            max_price = float(max_price)
            products = products.filter(price__lte=max_price)
        except ValueError:
            messages.error(request, "Valor máximo de preço inválido.")

    # Aplica ordenação
    if sort_by == 'price_asc':
        products = products.order_by('price')
    elif sort_by == 'price_desc':
        products = products.order_by('-price')
    elif sort_by == 'name_desc':
        products = products.order_by('-name')
    else: # 'name_asc' ou qualquer outro valor padrão
        products = products.order_by('name')

    # Paginação
    paginator = Paginator(products, 8) # 8 produtos por página
    page_number = request.GET.get('page')
    try:
        products = paginator.page(page_number)
    except PageNotAnInteger:
        # Se o número da página não é um inteiro, entrega a primeira página.
        products = paginator.page(1)
    except EmptyPage:
        # Se a página está fora do intervalo (ex. 9999), entrega a última página de resultados.
        products = paginator.page(paginator.num_pages)

    categories = get_categories_tree()
    context = {
        'products': products,
        'current_category': current_category,
        'page_title': current_category.name if current_category else 'Nossos Produtos',
        'categories': categories,
        'search_query': search_query, # Passa a query de busca para o template
        'min_price': min_price, # Passa o filtro de preço mínimo
        'max_price': max_price, # Passa o filtro de preço máximo
        'sort_by': sort_by, # Passa o tipo de ordenação
    }
    return render(request, 'product_list.html', context)

def product_detail_view(request, pk):
    product = get_object_or_404(Product, pk=pk)
    categories = get_categories_tree()
    context = {
        'product': product,
        'page_title': product.name,
        'categories': categories,
    }
    return render(request, 'product_detail.html', context)

def about_view(request):
    categories = get_categories_tree()
    context = {
        'page_title': 'Sobre a Jeci Store',
        'categories': categories,
    }
    return render(request, 'about.html', context)

def contact_view(request):
    categories = get_categories_tree()
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            # Aqui você processaria o formulário, por exemplo, enviando um e-mail
            # (necessitaria de configurações de e-mail no settings.py)
            name = form.cleaned_data['name']
            email = form.cleaned_data['email']
            message = form.cleaned_data['message']
            
            # Exemplo de como você enviaria um e-mail:
            # from django.core.mail import send_mail
            # send_mail(
            #     f'Mensagem de Contato da Jeci Store de {name}',
            #     message,
            #     email, # De
            #     ['seu_email@exemplo.com'], # Para
            #     fail_silently=False,
            # )
            
            messages.success(request, 'Sua mensagem foi enviada com sucesso! Em breve entraremos em contato.')
            return redirect('store:contact') # Redireciona para evitar reenvio do formulário
        else:
            messages.error(request, 'Por favor, corrija os erros no formulário.')
    else:
        form = ContactForm() # Formulário vazio para requisições GET

    context = {
        'page_title': 'Fale Conosco',
        'categories': categories,
        'form': form, # Passa o formulário para o template
    }
    return render(request, 'contact.html', context)

# --- Views de Carrinho de Compras ---

def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    cart = get_or_create_cart(request)
    quantity = int(request.POST.get('quantity', 1)) # Pega a quantidade do POST, padrão 1

    if quantity <= 0:
        messages.error(request, "A quantidade deve ser um número positivo.")
        return redirect('store:product_detail', pk=product_id)

    # Verifica se há estoque suficiente
    if product.stock < quantity:
        messages.error(request, f"Desculpe, só temos {product.stock} unidades de '{product.name}' em estoque.")
        return redirect('store:product_detail', pk=product_id)

    cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product, defaults={'quantity': quantity})
    if not created:
        # Verifica se a nova quantidade excede o estoque
        if cart_item.quantity + quantity > product.stock:
            messages.error(request, f"Não é possível adicionar mais. Você já tem {cart_item.quantity} unidades de '{product.name}' no carrinho e só temos {product.stock} em estoque.")
            return redirect('store:product_detail', pk=product_id)
        cart_item.quantity += quantity
        cart_item.save()
    
    messages.success(request, f"{quantity}x {product.name} adicionado ao carrinho!")
    return redirect('store:product_detail', pk=product_id) # Redireciona para a página do produto

def view_cart(request):
    cart = get_or_create_cart(request)
    categories = get_categories_tree()
    context = {
        'cart': cart,
        'page_title': 'Seu Carrinho',
        'categories': categories,
    }
    return render(request, 'cart.html', context)

def update_cart_item(request, item_id):
    cart_item = get_object_or_404(CartItem, id=item_id)
    cart = get_or_create_cart(request)

    # Garante que o item pertence ao carrinho correto (segurança)
    if cart_item.cart != cart:
        messages.error(request, "Você não tem permissão para modificar este item do carrinho.")
        return redirect('store:view_cart')

    if request.method == 'POST':
        try:
            new_quantity = int(request.POST.get('quantity'))
            
            if new_quantity <= 0:
                cart_item.delete()
                messages.info(request, f"Item '{cart_item.product.name}' removido do carrinho.")
            else:
                # Verifica se a nova quantidade excede o estoque
                if new_quantity > cart_item.product.stock:
                    messages.error(request, f"Não é possível atualizar para {new_quantity} unidades. Só temos {cart_item.product.stock} de '{cart_item.product.name}' em estoque.")
                    return redirect('store:view_cart')

                cart_item.quantity = new_quantity
                cart_item.save()
                messages.success(request, f"Quantidade de '{cart_item.product.name}' atualizada para {new_quantity}.")
        except (ValueError, TypeError):
            messages.error(request, "Quantidade inválida.")
    return redirect('store:view_cart')

def remove_from_cart(request, item_id):
    cart_item = get_object_or_404(CartItem, id=item_id)
    cart = get_or_create_cart(request)

    # Garante que o item pertence ao carrinho correto (segurança)
    if cart_item.cart != cart:
        messages.error(request, "Você não tem permissão para remover este item do carrinho.")
        return redirect('store:view_cart')

    product_name = cart_item.product.name
    cart_item.delete()
    messages.info(request, f"'{product_name}' removido do carrinho.")
    return redirect('store:view_cart')

# --- Views de Autenticação e Perfil (Básicas) ---

def signup_view(request):
    categories = get_categories_tree()
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # login(request, user) # Opcional: logar o usuário automaticamente após o registro
            messages.success(request, 'Sua conta foi criada com sucesso! Faça login para continuar.')
            return redirect('login') # Redireciona para a página de login
        else:
            messages.error(request, 'Por favor, corrija os erros no formulário de registro.')
    else:
        form = UserCreationForm()
    context = {
        'page_title': 'Registrar-se',
        'form': form,
        'categories': categories,
    }
    return render(request, 'registration/signup.html', context)

@login_required # Garante que apenas usuários logados podem acessar esta view
def user_profile_view(request):
    categories = get_categories_tree()
    context = {
        'page_title': f'Perfil de {request.user.username}',
        'categories': categories,
        # Adicione aqui informações adicionais do perfil do usuário, se houver
        # Ex: 'orders': Order.objects.filter(user=request.user)
    }
    return render(request, 'registration/user_profile.html', context) # Caminho corrigido

# --- Manipuladores de Erro Personalizados ---

def custom_404_view(request, exception):
    categories = get_categories_tree()
    context = {
        'page_title': 'Página Não Encontrada',
        'categories': categories,
    }
    return render(request, '404.html', context, status=404)

def custom_500_view(request):
    categories = get_categories_tree()
    context = {
        'page_title': 'Erro Interno do Servidor',
        'categories': categories,
    }
    return render(request, '500.html', context, status=500)


# --- NOVAS VIEWS PARA VENDEDORES ---

@seller_required # Protege a view para que só vendedores acessem
def add_product_view(request):
    categories = get_categories_tree()
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save(commit=False)
            product.seller = request.user
            product.save()
            messages.success(request, f"Produto '{product.name}' adicionado com sucesso!")
            return redirect('store:my_products')
        else:
            messages.error(request, "Por favor, corrija os erros no formulário.")
    else:
        form = ProductForm()
    
    context = {
        'page_title': 'Adicionar Novo Produto',
        'form': form,
        'categories': categories,
    }
    # CORREÇÃO AQUI: Caminho completo para o template
    return render(request, 'store/seller/seller_add_product.html', context)


@seller_required # Protege a view
def my_products_view(request):
    categories = get_categories_tree()
    products = Product.objects.filter(seller=request.user).order_by('-created_at')

    paginator = Paginator(products, 10)
    page_number = request.GET.get('page')
    try:
        products = paginator.page(page_number)
    except PageNotAnInteger:
        products = paginator.page(1)
    except EmptyPage:
        products = paginator.page(paginator.num_pages)
        
    context = {
        'page_title': 'Meus Produtos',
        'products': products,
        'categories': categories,
    }
    # CORREÇÃO AQUI: Caminho completo para o template
    return render(request, 'store/seller/seller_my_products.html', context)


@seller_required # Protege a view
def edit_product_view(request, pk):
    product = get_object_or_404(Product, pk=pk, seller=request.user)
    categories = get_categories_tree()
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, f"Produto '{product.name}' atualizado com sucesso!")
            return redirect('store:my_products')
        else:
            messages.error(request, "Por favor, corrija os erros no formulário.")
    else:
        form = ProductForm(instance=product)
    
    context = {
        'page_title': f'Editar Produto: {product.name}',
        'form': form,
        'product': product,
        'categories': categories,
    }
    # CORREÇÃO AQUI: Caminho completo para o template
    return render(request, 'store/seller/seller_edit_product.html', context)


@seller_required # Protege a view
def delete_product_view(request, pk):
    product = get_object_or_404(Product, pk=pk, seller=request.user)
    if request.method == 'POST':
        product_name = product.name
        product.delete()
        messages.info(request, f"Produto '{product_name}' excluído com sucesso.")
        return redirect('store:my_products')
    
    messages.error(request, "Método inválido para exclusão. Confirme a exclusão via POST.")
    return redirect('store:my_products')

