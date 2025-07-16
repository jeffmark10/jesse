# store/views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, Http404 # Importa Http404 para erros
from django.contrib.auth.forms import UserCreationForm # Para registro de usuário
from django.contrib.auth.decorators import login_required, user_passes_test # Importa user_passes_test
from django.contrib import messages # Para mensagens de feedback
from django.db.models import Q # Para funcionalidade de busca
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger # Para paginação
from urllib.parse import quote # Importa quote para codificar URLs
from django.conf import settings # Importa settings para acessar variáveis de configuração

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
    Lida com a migração de itens de um carrinho de sessão para um carrinho de usuário.
    """
    session_key = request.session.session_key
    if not session_key:
        request.session.save() # Garante que uma session_key exista
        session_key = request.session.session_key # Pega a chave recém-criada

    if request.user.is_authenticated:
        # Tenta obter ou criar o carrinho para o usuário logado
        user_cart, user_cart_created = Cart.objects.get_or_create(user=request.user)

        # Se houver um cart_id na sessão, tenta migrar os itens do carrinho de sessão
        session_cart = None
        if 'cart_id' in request.session:
            try:
                # Busca o carrinho de sessão pela ID e pela session_key para maior segurança
                session_cart = Cart.objects.get(id=request.session['cart_id'], session_key=session_key)
            except Cart.DoesNotExist:
                # Se o carrinho de sessão não for encontrado, limpa a session_key inválida
                del request.session['cart_id']
                session_cart = None

        if session_cart and session_cart != user_cart: # Garante que não é o mesmo carrinho
            for item in session_cart.items.all():
                # Tenta adicionar o item ao carrinho do usuário
                user_cart_item, item_created = CartItem.objects.get_or_create(
                    cart=user_cart,
                    product=item.product,
                    defaults={'quantity': item.quantity}
                )
                if not item_created:
                    # Se o item já existe no carrinho do usuário, tenta atualizar a quantidade
                    # Calcula a quantidade que realmente pode ser adicionada/mantida
                    quantity_to_add = item.quantity
                    available_stock_for_addition = item.product.stock - user_cart_item.quantity
                    
                    if available_stock_for_addition > 0:
                        # Adiciona apenas o que é possível até o limite de estoque
                        actual_added_quantity = min(quantity_to_add, available_stock_for_addition)
                        user_cart_item.quantity += actual_added_quantity
                        user_cart_item.save()
                        if actual_added_quantity < quantity_to_add:
                            messages.warning(request, f"Adicionado {actual_added_quantity} unidades de '{item.product.name}'. O restante ({quantity_to_add - actual_added_quantity}) não pôde ser migrado por limite de estoque.")
                    else:
                        messages.warning(request, f"Não foi possível migrar '{item.product.name}' para o seu carrinho devido ao limite de estoque.")
                
                # Remove o item do carrinho da sessão após a tentativa de migração
                item.delete() 
            
            # Após migrar todos os itens, remove o carrinho de sessão (se estiver vazio)
            if session_cart.items.count() == 0:
                session_cart.delete()
            
            # Limpa a cart_id da sessão, pois agora o usuário tem um carrinho persistente
            if 'cart_id' in request.session:
                del request.session['cart_id']
        
        return user_cart
    else:
        # Para usuários não logados, usa ou cria um carrinho de sessão
        cart_id = request.session.get('cart_id')
        cart = None
        if cart_id:
            try:
                # Tenta buscar o carrinho pela ID e pela session_key para maior segurança
                cart = Cart.objects.get(id=cart_id, session_key=session_key)
            except Cart.DoesNotExist:
                pass # O carrinho não existe ou a session_key não corresponde, cria um novo

        if not cart:
            cart = Cart.objects.create(session_key=session_key)
            request.session['cart_id'] = cart.id # Armazena a ID do novo carrinho na sessão
        
        return cart

# NOVO DECORADOR: Garante que apenas vendedores possam acessar a view
# Usa user_passes_test para melhor integração com o sistema de autenticação do Django
def is_seller_check(user):
    # Garante que o usuário está autenticado e tem um perfil de vendedor
    return user.is_authenticated and hasattr(user, 'profile') and user.profile.is_seller

# O decorador seller_required agora usa user_passes_test
seller_required = user_passes_test(is_seller_check, login_url='login')


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
    elif sort_by == 'created_at': # Adicionado para ordenar por mais recentes
        products = products.order_by('-created_at')
    else: # 'name' ou qualquer outro valor padrão
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

# NOVO: View para finalizar a compra e gerar o link do WhatsApp
def checkout_whatsapp_view(request):
    cart = get_or_create_cart(request)
    
    if not cart.items.exists():
        messages.warning(request, "Seu carrinho está vazio. Adicione produtos antes de finalizar a compra.")
        return redirect('store:view_cart')

    # Número de WhatsApp da loja, agora vindo das configurações
    whatsapp_number = settings.STORE_WHATSAPP_NUMBER 

    message_parts = [
        "Olá, gostaria de finalizar meu pedido na Jeci Store!",
        "Itens no carrinho:"
    ]
    tracking_codes = []

    for item in cart.items.all():
        message_parts.append(f"- {item.quantity}x {item.product.name} (R${item.product.price:.2f})")
        if item.product.tracking_code:
            tracking_codes.append(f"    Código de Rastreamento: {item.product.tracking_code}")
    
    if tracking_codes:
        message_parts.append("\nCódigos de Rastreamento dos Produtos (para referência):")
        message_parts.extend(tracking_codes)
    
    message_parts.append(f"\nValor Total: R${cart.get_total_price():.2f}")
    message_parts.append("\nPor favor, me ajude a prosseguir com o pagamento e envio.")

    full_message = "\n".join(message_parts)
    
    # Codifica a mensagem para URL
    encoded_message = quote(full_message)
    
    whatsapp_url = f"https://wa.me/{whatsapp_number}?text={encoded_message}"
    
    # Opcional: Limpar o carrinho após "finalizar" (neste caso, iniciar a conversa)
    # cart.items.all().delete()
    # messages.success(request, "Seu pedido foi iniciado via WhatsApp. Em breve entraremos em contato!")

    return redirect(whatsapp_url)


# --- Views de Autenticação e Perfil (Básicas) ---

def signup_view(request):
    categories = get_categories_tree()
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # O sinal post_save em store.signals.py garantirá que um Profile seja criado para este usuário.
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
