# store/models.py
from django.db import models
from django.utils.text import slugify
from django.contrib.auth.models import User # Importa o modelo User do Django

# NOVO MODELO: Profile (Perfil do Usuário)
# Este modelo estende o modelo User do Django, adicionando informações específicas
# para o perfil do usuário na sua aplicação, como se ele é um vendedor.
class Profile(models.Model):
    # Um relacionamento um-para-um com o modelo User do Django.
    # Se o usuário for excluído, o perfil também será excluído (CASCADE).
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name="Usuário")
    
    # Campo booleano para indicar se o usuário é um vendedor.
    # O valor padrão é False (não é vendedor).
    is_seller = models.BooleanField(default=False, verbose_name="É Vendedor")
    
    # Você pode adicionar outros campos aqui, como 'nome_da_loja', 'cnpj', etc.,
    # para armazenar informações adicionais do vendedor ou do cliente.
    # Exemplo: store_name = models.CharField(max_length=100, blank=True, null=True, verbose_name="Nome da Loja")

    class Meta:
        # Define o nome singular e plural para exibição no Django Admin.
        verbose_name = "Perfil"
        verbose_name_plural = "Perfis"

    def __str__(self):
        # Retorna uma representação em string do objeto Profile, útil para o Django Admin.
        return f"Perfil de {self.user.username}"

# Modelo para representar uma categoria de produto
# Permite organizar os produtos em categorias e subcategorias.
class Category(models.Model):
    # Nome da categoria (ex: "Feminino", "Sandálias", "T-Shirts"). Deve ser único.
    name = models.CharField(max_length=100, unique=True, verbose_name="Nome da Categoria")
    
    # Slug para URLs amigáveis (ex: "feminino", "sandalias"). Gerado automaticamente.
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    
    # Campo opcional para definir uma categoria pai, permitindo subcategorias.
    # 'self' referencia o próprio modelo Category.
    # Se a categoria pai for excluída, este campo será nulo (SET_NULL).
    parent = models.ForeignKey(
        'self', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='children', # Permite acessar subcategorias de uma categoria pai.
        verbose_name="Categoria Pai"
    )

    class Meta:
        # Define o nome da tabela no plural para o Django Admin.
        verbose_name_plural = "Categorias"
        # Ordena as categorias por nome por padrão.
        ordering = ['name']

    def save(self, *args, **kwargs):
        # Sobrescreve o método save para gerar o slug automaticamente se não for fornecido.
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        # Representação em string do objeto Category, mostrando o caminho completo da categoria.
        full_path = [self.name]
        k = self.parent
        while k is not None:
            full_path.append(k.name)
            k = k.parent
        return ' -> '.join(full_path[::-1])

# Modelo para representar um produto na Jeci Store
class Product(models.Model):
    # Nome do produto (ex: "Sandália Verão", "T-Shirt Básica").
    name = models.CharField(max_length=200, verbose_name="Nome do Produto")
    
    # Descrição detalhada do produto.
    description = models.TextField(verbose_name="Descrição")
    
    # Preço do produto. Usamos DecimalField para precisão monetária (10 dígitos no total, 2 casas decimais).
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Preço")
    
    # Campo para upload de imagem. As imagens serão salvas em 'products/' dentro de MEDIA_ROOT.
    # É opcional (blank=True, null=True).
    image = models.ImageField(
        upload_to='products/', 
        blank=True, 
        null=True, 
        verbose_name="Imagem do Produto"
    )
    
    # Vincula o produto a uma categoria.
    # Se a categoria for deletada, o produto permanece, mas o campo 'category' será nulo (SET_NULL).
    category = models.ForeignKey(
        Category, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='products', # Permite acessar produtos de uma categoria.
        verbose_name="Categoria"
    )
    
    # NOVO CAMPO: Vincula o produto a um vendedor (um usuário do Django).
    # Se o vendedor for excluído, os produtos dele não serão excluídos, apenas o campo 'seller' será nulo (SET_NULL).
    seller = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='products_listed', # Permite acessar os produtos listados por um usuário.
        verbose_name="Vendedor"
    )
    
    # Campo para controlar o estoque do produto. Valor padrão é 0.
    stock = models.PositiveIntegerField(default=0, verbose_name="Estoque")

    # Campo booleano para indicar se o produto deve ser exibido na página inicial como destaque.
    is_featured = models.BooleanField(default=False, verbose_name="Destaque na Home")
    
    # Data e hora em que o produto foi criado (definido automaticamente na criação).
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado Em")
    
    # Data e hora da última atualização do produto (atualizado automaticamente a cada salvamento).
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Atualizado Em")

    class Meta:
        # Define o nome da tabela no plural para o Django Admin.
        verbose_name_plural = "Produtos"
        # Ordena os produtos por nome por padrão.
        ordering = ['name']

    def __str__(self):
        # Representação em string do objeto Product.
        return self.name

# Modelo para representar um carrinho de compras
# Um carrinho pode ser associado a um usuário logado ou a uma sessão anônima.
class Cart(models.Model):
    # Relacionamento um-para-um com o modelo User. Opcional (null=True, blank=True) para carrinhos anônimos.
    # Se o usuário for excluído, o carrinho também será excluído (CASCADE).
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Usuário")
    
    # Chave de sessão para carrinhos anônimos. Deve ser única.
    session_key = models.CharField(max_length=40, null=True, blank=True, unique=True, verbose_name="Chave de Sessão")
    
    # Data e hora de criação do carrinho.
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado Em")
    
    # Data e hora da última atualização do carrinho.
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Atualizado Em")

    class Meta:
        verbose_name_plural = "Carrinhos"
        # Ordena os carrinhos pelos mais recentes.
        ordering = ['-created_at']

    def __str__(self):
        # Retorna uma representação em string, indicando se é um carrinho de usuário ou de sessão.
        if self.user:
            return f"Carrinho de {self.user.username}"
        return f"Carrinho de Sessão {self.session_key[:10]}..." # Mostra os primeiros 10 caracteres da chave.

    def get_total_price(self):
        # Calcula o preço total de todos os itens no carrinho.
        return sum(item.get_total_price() for item in self.items.all())

# Modelo para representar um item dentro do carrinho de compras
# Cada linha do carrinho representa um produto e sua quantidade.
class CartItem(models.Model):
    # Relacionamento com o modelo Cart. Se o carrinho for excluído, o item também será (CASCADE).
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items', verbose_name="Carrinho")
    
    # Relacionamento com o modelo Product. Se o produto for excluído, o item também será (CASCADE).
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name="Produto")
    
    # Quantidade do produto no carrinho. Valor padrão é 1.
    quantity = models.PositiveIntegerField(default=1, verbose_name="Quantidade")
    
    # Data e hora em que o item foi adicionado ao carrinho.
    added_at = models.DateTimeField(auto_now_add=True, verbose_name="Adicionado Em")

    class Meta:
        verbose_name_plural = "Itens do Carrinho"
        # Garante que um produto só pode aparecer uma vez em um determinado carrinho.
        unique_together = ('cart', 'product') 

    def __str__(self):
        # Representação em string do item do carrinho.
        return f"{self.quantity} x {self.product.name} no carrinho de {self.cart}"

    def get_total_price(self):
        # Calcula o preço total para este item específico (quantidade * preço do produto).
        return self.quantity * self.product.price
