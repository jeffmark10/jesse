# store/models.py

from django.db import models
from django.utils.text import slugify

# Modelo para representar uma categoria de produto
class Category(models.Model):
    # Nome da categoria (ex: "Feminino", "Sandálias", "T-Shirts")
    name = models.CharField(max_length=100, unique=True, verbose_name="Nome da Categoria")
    
    # Slug para URLs amigáveis (ex: "feminino", "sandalias")
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    
    # Campo opcional para definir uma categoria pai, permitindo subcategorias
    parent = models.ForeignKey(
        'self', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='children',
        verbose_name="Categoria Pai"
    )

    class Meta:
        # Define o nome da tabela no plural para o Django Admin
        verbose_name_plural = "Categorias"
        # Ordena as categorias por nome
        ordering = ['name']

    def save(self, *args, **kwargs):
        # Gera o slug automaticamente se não for fornecido
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        # Representação em string do objeto Category
        full_path = [self.name]
        k = self.parent
        while k is not None:
            full_path.append(k.name)
            k = k.parent
        return ' -> '.join(full_path[::-1])

# Modelo para representar um produto na Jeci Store
class Product(models.Model):
    # Nome do produto (ex: "Sandália Verão", "T-Shirt Básica")
    name = models.CharField(max_length=200, verbose_name="Nome do Produto")
    
    # Descrição detalhada do produto
    description = models.TextField(verbose_name="Descrição")
    
    # Preço do produto. Usamos DecimalField para precisão monetária.
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Preço")
    
    # Campo para upload de imagem. As imagens serão salvas em 'products/' dentro de MEDIA_ROOT.
    image = models.ImageField(
        upload_to='products/', 
        blank=True, 
        null=True, 
        verbose_name="Imagem do Produto"
    )
    
    # Vincula o produto a uma categoria. Se a categoria for deletada, o produto permanece (SET_NULL).
    category = models.ForeignKey(
        Category, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='products',
        verbose_name="Categoria"
    )
    
    # Campo booleano para indicar se o produto deve ser exibido na página inicial
    is_featured = models.BooleanField(default=False, verbose_name="Destaque na Home")
    
    # Data e hora em que o produto foi criado
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado Em")
    
    # Data e hora da última atualização do produto
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Atualizado Em")

    class Meta:
        # Define o nome da tabela no plural para o Django Admin
        verbose_name_plural = "Produtos"
        # Ordena os produtos por nome por padrão
        ordering = ['name']

    def __str__(self):
        # Representação em string do objeto Product
        return self.name

