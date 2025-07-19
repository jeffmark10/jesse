# store/views.py

import logging 
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, JsonResponse # Importa JsonResponse para respostas AJAX
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm 
from django.contrib.auth.decorators import login_required, user_passes_test 
from django.contrib import messages 
from django.db.models import Q 
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger 
from urllib.parse import quote 
from django.conf import settings 
from django.contrib.auth import login 
from django.core.cache import cache # Importa o módulo de cache
from django.views.decorators.cache import cache_page # Importa o decorador de cache de página

from .models import Product, Category, Cart, CartItem, Profile 
from .forms import ContactForm, ProductForm, UserRegistrationForm, UserLoginForm 

# Configura o logger para este módulo
logger = logging.getLogger(__name__)

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
    para construir a árvore de categorias no menu. Usa cache para otimização.
    """
    # Tenta obter as categorias do cache
    categories = cache.get('root_categories_tree')
    if categories is None:
        # Se não estiver no cache, busca no banco de dados
        root_categories = Category.objects.filter(parent__isnull=True).prefetch_related('children')
        # Converte para lista para que o QuerySet seja avaliado e possa ser armazenado no cache
        categories = list(root_categories) 
        # Armazena no cache por 1 hora (3600 segundos)
        cache.set('root_categories_tree', categories, 3600)
        logger.debug("Árvore de categorias carregada do DB e cacheada.")
    else:
        logger.debug("Árvore de categorias carregada do cache.")
    return categories

def get_or_create_cart(request):
    """
    Obtém o carrinho do usuário logado ou da sessão.
    Cria um novo carrinho se não existir.
    Lida com a migração de itens de um carrinho de sessão para um carrinho de usuário.
    """
    session_key = request.session.session_key
    if not session_key:
        request.session.save() # Garante que uma session_key exista
        session_key = request.session.session_key # Pega a chave recém-criada
        logger.debug(f"Nova chave de sessão criada: {session_key}")

    if request.user.is_authenticated:
        # Tenta obter ou criar o carrinho para o usuário logado
        user_cart, user_cart_created = Cart.objects.get_or_create(user=request.user)
        if user_cart_created:
            logger.info(f"Carrinho criado para o usuário: {request.user.username}")

        # Se houver um cart_id na sessão, tenta migrar os itens do carrinho de sessão
        session_cart = None
        if 'cart_id' in request.session:
            try:
                # Busca o carrinho de sessão pela ID e pela session_key para maior segurança
                session_cart = Cart.objects.get(id=request.session['cart_id'], session_key=session_key)
                logger.debug(f"Carrinho de sessão encontrado para migração: {session_cart.id}")
            except Cart.DoesNotExist:
                logger.warning(f"Carrinho de sessão com ID {request.session['cart_id']} não encontrado ou chave de sessão inválida. Removendo da sessão.")
                del request.session['cart_id']
                session_cart = None

        if session_cart and session_cart != user_cart: # Garante que não é o mesmo carrinho
            logger.info(f"Iniciando migração de itens do carrinho de sessão ({session_cart.id}) para o carrinho do usuário ({user_cart.id}).")
            for item in session_cart.items.select_related('product').all(): # Otimiza a busca do produto
                user_cart_item, item_created = CartItem.objects.get_or_create(
                    cart=user_cart,
                    product=item.product,
                    defaults={'quantity': item.quantity}
                )
                if not item_created:
                    quantity_to_add = item.quantity
                    available_stock_for_addition = item.product.stock - user_cart_item.quantity
                    
                    if available_stock_for_addition > 0:
                        actual_added_quantity = min(quantity_to_add, available_stock_for_addition)
                        user_cart_item.quantity += actual_added_quantity
                        user_cart_item.save()
                        logger.debug(f"Item '{item.product.name}' atualizado no carrinho do usuário. Adicionado: {actual_added_quantity}.")
                        if actual_added_quantity < quantity_to_add:
                            messages.warning(request, f"Adicionado {actual_added_quantity} unidades de '{item.product.name}'. O restante ({quantity_to_add - actual_added_quantity}) não pôde ser migrado por limite de estoque.")
                            logger.warning(f"Estoque insuficiente para migrar todas as unidades de '{item.product.name}'.")
                    else:
                        messages.warning(request, f"Não foi possível migrar '{item.product.name}' para o seu carrinho devido ao limite de estoque.")
                        logger.warning(f"Não foi possível migrar '{item.product.name}' para o carrinho do usuário devido ao estoque zero ou insuficiente.")
                else:
                    logger.debug(f"Item '{item.product.name}' migrado para o carrinho do usuário com quantidade {item.quantity}.")
                
                item.delete() # Remove o item do carrinho da sessão após a tentativa de migração
            
            if session_cart.items.count() == 0:
                session_cart.delete()
                logger.info(f"Carrinho de sessão ({session_cart.id}) excluído após migração.")
            
            if 'cart_id' in request.session:
                del request.session['cart_id']
                logger.debug("cart_id removido da sessão após migração.")
        
        return user_cart
    else:
        # Para usuários não logados, usa ou cria um carrinho de sessão
        cart_id = request.session.get('cart_id')
        cart = None
        if cart_id:
            try:
                # Tenta buscar o carrinho pela ID e pela session_key para maior segurança
                cart = Cart.objects.get(id=cart_id, session_key=session_key)
                logger.debug(f"Carrinho de sessão existente encontrado: {cart.id}")
            except Cart.DoesNotExist:
                logger.warning(f"Carrinho de sessão com ID {cart_id} não encontrado ou chave de sessão inválida. Criando novo carrinho.")
                pass # O carrinho não existe ou a session_key não corresponde, cria um novo

        if not cart:
            cart = Cart.objects.create(session_key=session_key)
            request.session['cart_id'] = cart.id # Armazena a ID do novo carrinho na sessão
            logger.info(f"Novo carrinho de sessão criado: {cart.id}")
        
        return cart

# NOVO DECORADOR: Garante que apenas vendedores possam acessar a view
# Usa user_passes_test para melhor integração com o sistema de autenticação do Django
def is_seller_check(user):
    # Garante que o usuário está autenticado e tem um perfil de vendedor
    is_seller = user.is_authenticated and hasattr(user, 'profile') and user.profile.is_seller
    if not is_seller:
        logger.warning(f"Tentativa de acesso não autorizado à área de vendedor por usuário: {user.username if user.is_authenticated else 'Anônimo'}")
    return is_seller

# O decorador seller_required agora usa user_passes_test
seller_required = user_passes_test(is_seller_check, login_url='login')

# --- Helper para respostas AJAX de carrinho ---
def get_cart_data(cart):
    """
    Retorna os dados do carrinho formatados para uma resposta JSON.
    """
    cart_items_data = []
    for item in cart.items.select_related('product').all():
        cart_items_data.append({
            'id': item.id,
            'product_id': item.product.id,
            'product_name': item.product.name,
            'quantity': item.quantity,
            'price': float(item.product.price), # Converte Decimal para float para JSON
            'total_item_price': float(item.get_total_price()),
            'stock': item.product.stock,
            'image_url': item.product.get_optimized_image_url(width=50, height=50, crop='fill') if item.product.image else settings.STATIC_URL + 'favicon.png', # Fallback para imagem
            'tracking_code': item.product.tracking_code,
        })
    return {
        'cart_count': cart.items.count(),
        'cart_total_price': float(cart.get_total_price()),
        'cart_items': cart_items_data,
    }


# --- Views Principais ---

def home_view(request):
    featured_products_queryset = Product.objects.filter(is_featured=True, stock__gt=0).select_related('category', 'seller')[:4] 
    
    # Prepara os produtos com URLs de imagem otimizadas para o template
    featured_products_for_template = []
    for product in featured_products_queryset:
        product_data = {
            'pk': product.pk,
            'name': product.name,
            'price': product.price,
            'image': product.image, # Mantém o objeto CloudinaryField para o método
            'optimized_src': product.get_optimized_image_url(width=400, height=400, crop='fill'),
            'optimized_srcset': f"{product.get_optimized_image_url(width=200, height=200, crop='fill')} 200w, " \
                                f"{product.get_optimized_image_url(width=400, height=400, crop='fill')} 400w, " \
                                f"{product.get_optimized_image_url(width=600, height=600, crop='fill')} 600w",
            # Adicione outros campos necessários se o template os usar
            'category': product.category,
            'seller': product.seller,
            'stock': product.stock,
            'is_featured': product.is_featured,
            'created_at': product.created_at,
            'updated_at': product.updated_at,
            'tracking_code': product.tracking_code,
        }
        featured_products_for_template.append(product_data)

    categories = get_categories_tree() 
    context = {
        'featured_products': featured_products_for_template, # Passa a lista com as URLs pré-calculadas
        'page_title': 'Bem-vindo à Jeci Store!',
        'categories': categories, 
    }
    logger.debug("Página inicial renderizada.")
    return render(request, 'home.html', context)

def product_list_view(request, category_slug=None):
    products = Product.objects.filter(stock__gt=0).select_related('category', 'seller') 
    current_category = None
    search_query = request.GET.get('q') 
    min_price = request.GET.get('min_price') 
    max_price = request.GET.get('max_price') 
    sort_by = request.GET.get('sort_by', 'name') 

    if category_slug:
        current_category = get_object_or_404(Category, slug=category_slug)
        category_ids_to_filter = get_descendant_category_ids(current_category)
        products = products.filter(category__id__in=category_ids_to_filter)
        logger.debug(f"Filtrando produtos por categoria: {current_category.name}")
    
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) | Q(description__icontains=search_query)
        ).distinct()
        logger.debug(f"Aplicando busca por: '{search_query}'. Resultados: {products.count()}")
        # A mensagem para "nenhum produto encontrado" é agora tratada no template product_list.html
        # if not products.exists():
        #     messages.info(request, f"Nenhum produto encontrado para '{search_query}'.")

    if min_price:
        try:
            min_price = float(min_price)
            products = products.filter(price__gte=min_price)
            logger.debug(f"Filtrando por preço mínimo: R${min_price}")
        except ValueError:
            messages.error(request, "Valor mínimo de preço inválido.")
            logger.error(f"Valor mínimo de preço inválido: {min_price}")
    
    if max_price:
        try:
            max_price = float(max_price)
            products = products.filter(price__lte=max_price)
            logger.debug(f"Filtrando por preço máximo: R${max_price}")
        except ValueError:
            messages.error(request, "Valor máximo de preço inválido.")
            logger.error(f"Valor máximo de preço inválido: {max_price}")

    if sort_by == 'price_asc':
        products = products.order_by('price')
    elif sort_by == 'price_desc':
        products = products.order_by('-price')
    elif sort_by == 'name_desc':
        products = products.order_by('-name')
    elif sort_by == 'created_at': 
        products = products.order_by('-created_at')
    else: 
        products = products.order_by('name')
    logger.debug(f"Ordenando produtos por: {sort_by}")

    paginator = Paginator(products, 8) 
    page_number = request.GET.get('page')
    try:
        products = paginator.page(page_number)
        logger.debug(f"Página {products.number} de produtos carregada.")
    except PageNotAnInteger:
        products = paginator.page(1)
        logger.warning(f"Número de página inválido '{page_number}'. Redirecionando para a primeira página.")
    except EmptyPage:
        products = paginator.page(paginator.num_pages)
        logger.warning(f"Página '{page_number}' fora do intervalo. Redirecionando para a última página.")

    categories = get_categories_tree()
    context = {
        'products': products,
        'current_category': current_category,
        'page_title': current_category.name if current_category else 'Nossos Produtos',
        'categories': categories,
        'search_query': search_query, 
        'min_price': min_price, 
        'max_price': max_price, 
        'sort_by': sort_by, 
    }
    return render(request, 'product_list.html', context)

def product_detail_view(request, pk):
    product = get_object_or_404(Product.objects.select_related('category', 'seller'), pk=pk) 
    categories = get_categories_tree()
    context = {
        'product': product,
        'page_title': product.name,
        'categories': categories,
    }
    logger.debug(f"Detalhes do produto {product.name} (ID: {pk}) renderizados.")
    return render(request, 'product_detail.html', context)

@cache_page(60 * 15) # Cache por 15 minutos
def about_view(request):
    categories = get_categories_tree()
    context = {
        'page_title': 'Sobre a Jeci Store',
        'categories': categories,
    }
    logger.debug("Página 'Sobre Nós' renderizada.")
    return render(request, 'about.html', context)

@cache_page(60 * 15) # Cache por 15 minutos
def contact_view(request):
    categories = get_categories_tree()
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data['name']
            email = form.cleaned_data['email']
            message = form.cleaned_data['message']
            
            logger.info(f"Formulário de contato recebido de {name} ({email}). Mensagem: {message[:50]}...")
            
            messages.success(request, 'Sua mensagem foi enviada com sucesso! Em breve entraremos em contato.')
            return redirect('store:contact') 
        else:
            messages.error(request, 'Por favor, corrija os erros no formulário.')
            logger.error(f"Erros no formulário de contato: {form.errors}")
    else:
        form = ContactForm() 

    context = {
        'page_title': 'Fale Conosco',
        'categories': categories,
        'form': form, 
    }
    logger.debug("Página 'Fale Conosco' renderizada.")
    return render(request, 'contact.html', context)

# --- Views de Carrinho de Compras (com suporte AJAX) ---

def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    cart = get_or_create_cart(request)
    quantity = int(request.POST.get('quantity', 1)) 

    if quantity <= 0:
        messages.error(request, "A quantidade deve ser um número positivo.")
        logger.warning(f"Tentativa de adicionar quantidade inválida ({quantity}) para o produto ID: {product_id}")
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': 'A quantidade deve ser um número positivo.'}, status=400)
        return redirect('store:product_detail', pk=product_id)

    if product.stock < quantity:
        messages.error(request, f"Desculpe, só temos {product.stock} unidades de '{product.name}' em estoque.")
        logger.warning(f"Estoque insuficiente para adicionar {quantity} de '{product.name}' (ID: {product_id}). Estoque: {product.stock}")
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': f"Desculpe, só temos {product.stock} unidades de '{product.name}' em estoque."}, status=400)
        return redirect('store:product_detail', pk=product_id)

    cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product, defaults={'quantity': quantity})
    if not created:
        if cart_item.quantity + quantity > product.stock:
            messages.error(request, f"Não é possível adicionar mais. Você já tem {cart_item.quantity} unidades de '{product.name}' no carrinho e só temos {product.stock} em estoque.")
            logger.warning(f"Tentativa de exceder estoque para '{product.name}' (ID: {product_id}). Já no carrinho: {cart_item.quantity}, Tentativa: {quantity}, Estoque: {product.stock}")
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'message': f"Não é possível adicionar mais. Você já tem {cart_item.quantity} unidades de '{product.name}' no carrinho e só temos {product.stock} em estoque."}, status=400)
            return redirect('store:product_detail', pk=product_id)
        cart_item.quantity += quantity
        cart_item.save()
        logger.info(f"Quantidade de '{product.name}' (ID: {product_id}) atualizada no carrinho para {cart_item.quantity}.")
    else:
        logger.info(f"{quantity}x '{product.name}' (ID: {product_id}) adicionado ao carrinho.")
    
    messages.success(request, f"{quantity}x {product.name} adicionado ao carrinho!")
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'message': f"{quantity}x {product.name} adicionado ao carrinho!", **get_cart_data(cart)})
    return redirect('store:product_detail', pk=product_id) 

def view_cart(request):
    cart = get_or_create_cart(request)
    cart_items = cart.items.select_related('product').all() 
    categories = get_categories_tree()
    context = {
        'cart': cart,
        'cart_items': cart_items, 
        'page_title': 'Seu Carrinho',
        'categories': categories,
    }
    logger.debug(f"Carrinho (ID: {cart.id}) visualizado. Itens: {cart_items.count()}")
    return render(request, 'cart.html', context)

def update_cart_item(request, item_id):
    cart_item = get_object_or_404(CartItem.objects.select_related('product'), id=item_id) 
    cart = get_or_create_cart(request)

    if cart_item.cart != cart:
        messages.error(request, "Você não tem permissão para modificar este item do carrinho.")
        logger.warning(f"Tentativa de modificar item de carrinho não pertencente ao usuário/sessão. Item ID: {item_id}, Carrinho do usuário/sessão: {cart.id}")
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': 'Você não tem permissão para modificar este item do carrinho.'}, status=403)
        return redirect('store:view_cart')

    if request.method == 'POST':
        try:
            new_quantity = int(request.POST.get('quantity'))
            
            if new_quantity <= 0:
                product_name = cart_item.product.name
                cart_item.delete()
                messages.info(request, f"Item '{product_name}' removido do carrinho.")
                logger.info(f"Item '{product_name}' (ID: {item_id}) removido do carrinho. Nova quantidade: {new_quantity}")
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({'success': True, 'message': f"Item '{product_name}' removido do carrinho.", 'removed_item_id': item_id, **get_cart_data(cart)})
            else:
                if new_quantity > cart_item.product.stock:
                    messages.error(request, f"Não é possível atualizar para {new_quantity} unidades. Só temos {cart_item.product.stock} de '{cart_item.product.name}' em estoque.")
                    logger.warning(f"Tentativa de atualizar quantidade de '{cart_item.product.name}' (ID: {item_id}) para {new_quantity} excede estoque ({cart_item.product.stock}).")
                    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                        return JsonResponse({'success': False, 'message': f"Não é possível atualizar para {new_quantity} unidades. Só temos {cart_item.product.stock} de '{cart_item.product.name}' em estoque."}, status=400)
                    return redirect('store:view_cart')

                cart_item.quantity = new_quantity
                cart_item.save()
                messages.success(request, f"Quantidade de '{cart_item.product.name}' atualizada para {new_quantity}.")
                logger.info(f"Quantidade de '{cart_item.product.name}' (ID: {item_id}) atualizada para {new_quantity}.")
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({'success': True, 'message': f"Quantidade de '{cart_item.product.name}' atualizada para {new_quantity}.", 'updated_item_id': item_id, **get_cart_data(cart)})
        except (ValueError, TypeError):
            messages.error(request, "Quantidade inválida.")
            logger.error(f"Quantidade inválida recebida para item ID {item_id}: {request.POST.get('quantity')}")
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'message': 'Quantidade inválida.'}, status=400)
    
    return redirect('store:view_cart')

def remove_from_cart(request, item_id):
    cart_item = get_object_or_404(CartItem.objects.select_related('product'), id=item_id) 
    cart = get_or_create_cart(request)

    if cart_item.cart != cart:
        messages.error(request, "Você não tem permissão para remover este item do carrinho.")
        logger.warning(f"Tentativa de remover item de carrinho não pertencente ao usuário/sessão. Item ID: {item_id}, Carrinho do usuário/sessão: {cart.id}")
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': 'Você não tem permissão para remover este item do carrinho.'}, status=403)
        return redirect('store:view_cart')

    product_name = cart_item.product.name
    cart_item.delete()
    messages.info(request, f"'{product_name}' removido do carrinho.")
    logger.info(f"Item '{product_name}' (ID: {item_id}) removido do carrinho.")
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'message': f"'{product_name}' removido do carrinho.", 'removed_item_id': item_id, **get_cart_data(cart)})
    return redirect('store:view_cart')

# NOVO: View para finalizar a compra e gerar o link do WhatsApp
def checkout_whatsapp_view(request):
    cart = get_or_create_cart(request)
    
    if not cart.items.exists():
        messages.warning(request, "Seu carrinho está vazio. Adicione produtos antes de finalizar a compra.")
        logger.warning(f"Tentativa de finalizar compra com carrinho vazio para usuário/sessão: {request.user.username if request.user.is_authenticated else request.session.session_key}")
        return redirect('store:view_cart')

    whatsapp_number = settings.STORE_WHATSAPP_NUMBER 

    message_parts = [
        "Olá, gostaria de finalizar meu pedido na Jeci Store!",
        "Itens no carrinho:"
    ]
    tracking_codes = []

    for item in cart.items.select_related('product').all():
        message_parts.append(f"- {item.quantity}x {item.product.name} (R${item.product.price:.2f})")
        if item.product.tracking_code:
            tracking_codes.append(f"    Código de Rastreamento: {item.product.tracking_code}")
    
    if tracking_codes:
        message_parts.append("\nCódigos de Rastreamento dos Produtos (para referência):")
        message_parts.extend(tracking_codes)
    
    message_parts.append(f"\nValor Total: R${cart.get_total_price():.2f}")
    message_parts.append("\nPor favor, me ajude a prosseguir com o pagamento e envio.")

    full_message = "\n".join(message_parts)
    
    encoded_message = quote(full_message)
    
    whatsapp_url = f"https://wa.me/{whatsapp_number}?text={encoded_message}"
    
    logger.info(f"Link de checkout do WhatsApp gerado para o carrinho {cart.id}.")
    return redirect(whatsapp_url)


# --- Views de Autenticação e Perfil (Básicas) ---

def signup_view(request):
    categories = get_categories_tree()
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST) 
        if form.is_valid():
            user = form.save()
            login(request, user) 
            messages.success(request, 'Sua conta foi criada com sucesso! Você está logado(a).')
            logger.info(f"Novo usuário registrado e logado: {user.username}")
            return redirect('home') 
        else:
            messages.error(request, 'Por favor, corrija os erros no formulário de registro.')
            logger.error(f"Erros no formulário de registro: {form.errors}")
    else:
        form = UserRegistrationForm() 
    context = {
        'page_title': 'Registrar-se',
        'form': form,
        'categories': categories,
    }
    logger.debug("Página de registro renderizada.")
    return render(request, 'registration/signup.html', context)

def login_view(request):
    categories = get_categories_tree()
    if request.method == 'POST':
        form = UserLoginForm(request, data=request.POST) 
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f"Bem-vindo(a) de volta, {user.username}!")
            logger.info(f"Usuário logado: {user.username}")
            return redirect('home') 
        else:
            messages.error(request, "Nome de usuário ou senha inválidos.")
            logger.warning(f"Tentativa de login falhou para o usuário: {request.POST.get('username')}")
    else:
        form = UserLoginForm() 
    context = {
        'page_title': 'Entrar',
        'form': form,
        'categories': categories,
    }
    logger.debug("Página de login renderizada.")
    return render(request, 'registration/login.html', context)


@login_required 
def user_profile_view(request):
    categories = get_categories_tree()
    context = {
        'page_title': f'Perfil de {request.user.username}',
        'categories': categories,
    }
    logger.debug(f"Perfil do usuário {request.user.username} renderizado.")
    return render(request, 'registration/user_profile.html', context) 

# --- Manipuladores de Erro Personalizados ---

def custom_404_view(request, exception):
    categories = get_categories_tree()
    context = {
        'page_title': 'Página Não Encontrada',
        'categories': categories,
    }
    logger.warning(f"Página 404 acessada para URL: {request.path}")
    return render(request, '404.html', context, status=404)

def custom_500_view(request):
    categories = get_categories_tree()
    context = {
        'page_title': 'Erro Interno do Servidor',
        'categories': categories,
    }
    logger.error(f"Página 500 acessada. Request path: {request.path}")
    return render(request, '500.html', context, status=500)


# --- NOVAS VIEWS PARA VENDEDORES ---

@seller_required 
def add_product_view(request):
    categories = get_categories_tree()
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save(commit=False)
            product.seller = request.user
            product.save()
            messages.success(request, f"Produto '{product.name}' adicionado com sucesso!")
            logger.info(f"Produto '{product.name}' adicionado por {request.user.username}.")
            return redirect('store:my_products')
        else:
            messages.error(request, "Por favor, corrija os erros no formulário.")
            logger.error(f"Erro ao adicionar produto por {request.user.username}: {form.errors}")
    else:
        form = ProductForm()
    
    context = {
        'page_title': 'Adicionar Novo Produto',
        'form': form,
        'categories': categories,
    }
    logger.debug(f"Página 'Adicionar Novo Produto' renderizada para {request.user.username}.")
    return render(request, 'store/seller/seller_add_product.html', context)


@seller_required 
def my_products_view(request):
    categories_tree = get_categories_tree() 
    products = Product.objects.filter(seller=request.user).select_related('category', 'seller') 

    search_query = request.GET.get('q')
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    category_slug = request.GET.get('category_slug') 
    stock_status = request.GET.get('stock_status') 
    sort_by = request.GET.get('sort_by', '-created_at') 

    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) | 
            Q(description__icontains=search_query) |
            Q(tracking_code__icontains=search_query) 
        ).distinct()
        logger.debug(f"Busca aplicada aos produtos do vendedor: '{search_query}'.")

    current_category_filter = None
    if category_slug:
        try:
            current_category_filter = Category.objects.get(slug=category_slug)
            category_ids_to_filter = get_descendant_category_ids(current_category_filter)
            products = products.filter(category__id__in=category_ids_to_filter)
            logger.debug(f"Filtrando produtos do vendedor por categoria: {current_category_filter.name}")
        except Category.DoesNotExist:
            messages.error(request, "Categoria selecionada inválida.")
            logger.error(f"Tentativa de filtrar produtos do vendedor por categoria inválida: {category_slug}")

    if stock_status == 'in_stock':
        products = products.filter(stock__gt=0)
        logger.debug("Filtrando produtos do vendedor: Em Estoque.")
    elif stock_status == 'out_of_stock':
        products = products.filter(stock=0)
        logger.debug("Filtrando produtos do vendedor: Esgotado.")

    if min_price:
        try:
            min_price = float(min_price)
            products = products.filter(price__gte=min_price)
            logger.debug(f"Filtrando produtos do vendedor por preço mínimo: R${min_price}")
        except ValueError:
            messages.error(request, "Valor mínimo de preço inválido.")
            logger.error(f"Valor mínimo de preço inválido para produtos do vendedor: {min_price}")
    
    if max_price:
        try:
            max_price = float(max_price)
            products = products.filter(price__lte=max_price)
            logger.debug(f"Filtrando produtos do vendedor por preço máximo: R${max_price}")
        except ValueError:
            messages.error(request, "Valor máximo de preço inválido.")
            logger.error(f"Valor máximo de preço inválido para produtos do vendedor: {max_price}")

    if sort_by == 'price_asc':
        products = products.order_by('price')
    elif sort_by == 'price_desc':
        products = products.order_by('-price')
    elif sort_by == 'name_asc': 
        products = products.order_by('name')
    elif sort_by == 'name_desc':
        products = products.order_by('-name')
    elif sort_by == 'stock_asc': 
        products = products.order_by('stock')
    elif sort_by == 'stock_desc': 
        products = products.order_by('-stock')
    elif sort_by == 'created_at':
        products = products.order_by('created_at') 
    else: 
        products = products.order_by('-created_at')
    logger.debug(f"Ordenando produtos do vendedor por: {sort_by}")

    paginator = Paginator(products, 10)
    page_number = request.GET.get('page')
    try:
        products = paginator.page(page_number)
        logger.debug(f"Página {products.number} de produtos do vendedor {request.user.username} carregada.")
    except PageNotAnInteger:
        products = paginator.page(1)
        logger.warning(f"Número de página inválido '{page_number}' para produtos do vendedor. Redirecionando para a primeira página.")
    except EmptyPage:
        products = paginator.page(paginator.num_pages)
        logger.warning(f"Página '{page_number}' fora do intervalo para produtos do vendedor. Redirecionando para a última página.")
        
    context = {
        'page_title': 'Meus Produtos',
        'products': products,
        'categories': categories_tree, 
        'search_query': search_query,
        'min_price': min_price,
        'max_price': max_price,
        'current_category_filter': current_category_filter, 
        'stock_status': stock_status, 
        'sort_by': sort_by,
    }
    return render(request, 'store/seller/seller_my_products.html', context)


@seller_required 
def edit_product_view(request, pk):
    product = get_object_or_404(Product.objects.select_related('category', 'seller'), pk=pk, seller=request.user) 
    categories = get_categories_tree()
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, f"Produto '{product.name}' atualizado com sucesso!")
            logger.info(f"Produto '{product.name}' (ID: {product.pk}) atualizado por {request.user.username}.")
            return redirect('store:my_products')
        else:
            messages.error(request, "Por favor, corrija os erros no formulário.")
            logger.error(f"Erro ao editar produto '{product.name}' (ID: {product.pk}) por {request.user.username}: {form.errors}")
    else:
        form = ProductForm(instance=product)
    
    context = {
        'page_title': f'Editar Produto: {product.name}',
        'form': form,
        'product': product,
        'categories': categories,
    }
    logger.debug(f"Página 'Editar Produto' para '{product.name}' (ID: {product.pk}) renderizada para {request.user.username}.")
    return render(request, 'store/seller/seller_edit_product.html', context)


@seller_required 
def delete_product_view(request, pk):
    product = get_object_or_404(Product, pk=pk, seller=request.user)
    if request.method == 'POST':
        product_name = product.name
        product.delete()
        messages.info(request, f"Produto '{product_name}' excluído com sucesso.")
        logger.info(f"Produto '{product_name}' (ID: {pk}) excluído por {request.user.username}.")
        return redirect('store:my_products')
    
    messages.error(request, "Método inválido para exclusão. Confirme a exclusão via POST.")
    logger.warning(f"Tentativa de exclusão de produto (ID: {pk}) com método inválido por {request.user.username}.")
    return redirect('store:my_products')
