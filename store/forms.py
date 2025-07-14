# store/forms.py

from django import forms
# Importa o modelo Product para ser usado no ModelForm.
# Certifique-se de que Product esteja disponível no seu models.py.
from .models import Product 

# Formulário de Contato
# Este formulário é para que os usuários possam enviar mensagens.
class ContactForm(forms.Form):
    # Campo para o nome do remetente.
    name = forms.CharField(
        max_length=100, 
        label="Seu Nome",
        widget=forms.TextInput(attrs={
            'class': 'shadow-sm appearance-none border border-stone-300 rounded-lg w-full py-3 px-4 text-gray-700 leading-tight focus:outline-none focus:ring-2 focus:ring-pink-500 focus:border-transparent transition duration-200', 
            'placeholder': 'Seu nome completo'
        })
    )
    # Campo para o e-mail do remetente.
    email = forms.EmailField(
        label="Seu E-mail",
        widget=forms.EmailInput(attrs={
            'class': 'shadow-sm appearance-none border border-stone-300 rounded-lg w-full py-3 px-4 text-gray-700 leading-tight focus:outline-none focus:ring-2 focus:ring-pink-500 focus:border-transparent transition duration-200', 
            'placeholder': 'seu.email@exemplo.com'
        })
    )
    # Campo para a mensagem. Usa um Textarea para múltiplas linhas.
    message = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 6, 
            'class': 'shadow-sm appearance-none border border-stone-300 rounded-lg w-full py-3 px-4 text-gray-700 leading-tight focus:outline-none focus:ring-2 focus:ring-pink-500 focus:border-transparent transition duration-200', 
            'placeholder': 'Escreva sua mensagem aqui...'
        }),
        label="Sua Mensagem"
    )

# NOVO FORMULÁRIO: ProductForm
# Este formulário é baseado no modelo Product e será usado por vendedores para adicionar/editar produtos.
class ProductForm(forms.ModelForm):
    class Meta:
        # Define o modelo base para este formulário.
        model = Product
        # Campos que o vendedor poderá preencher.
        # 'seller' NÃO está incluído aqui, pois será preenchido automaticamente pela view (ou admin).
        fields = ['name', 'description', 'price', 'image', 'category', 'stock', 'is_featured']
        
        # Personalização dos widgets para aplicar classes Tailwind CSS.
        # Isso ajuda a estilizar os campos do formulário para corresponder ao design do seu site.
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'shadow-sm appearance-none border border-stone-300 rounded-lg w-full py-3 px-4 text-gray-700 leading-tight focus:outline-none focus:ring-2 focus:ring-pink-500 focus:border-transparent transition duration-200', 
                'placeholder': 'Nome do Produto'
            }),
            'description': forms.Textarea(attrs={
                'class': 'shadow-sm appearance-none border border-stone-300 rounded-lg w-full py-3 px-4 text-gray-700 leading-tight focus:outline-none focus:ring-2 focus:ring-pink-500 focus:border-transparent transition duration-200', 
                'rows': 6, 
                'placeholder': 'Descrição detalhada do produto'
            }),
            'price': forms.NumberInput(attrs={
                'class': 'shadow-sm appearance-none border border-stone-300 rounded-lg w-full py-3 px-4 text-gray-700 leading-tight focus:outline-none focus:ring-2 focus:ring-pink-500 focus:border-transparent transition duration-200', 
                'step': '0.01', # Permite valores decimais com duas casas.
                'min': '0'     # Garante que o preço não seja negativo.
            }),
            'stock': forms.NumberInput(attrs={
                'class': 'shadow-sm appearance-none border border-stone-300 rounded-lg w-full py-3 px-4 text-gray-700 leading-tight focus:outline-none focus:ring-2 focus:ring-pink-500 focus:border-transparent transition duration-200', 
                'min': '0'     # Garante que o estoque não seja negativo.
            }),
            'category': forms.Select(attrs={
                'class': 'shadow-sm appearance-none border border-stone-300 rounded-lg w-full py-3 px-4 text-gray-700 leading-tight focus:outline-none focus:ring-2 focus:ring-pink-500 focus:border-transparent transition duration-200'
            }),
            'image': forms.ClearableFileInput(attrs={
                'class': 'shadow-sm appearance-none border border-stone-300 rounded-lg w-full py-3 px-4 text-gray-700 leading-tight focus:outline-none focus:ring-2 focus:ring-pink-500 focus:border-transparent transition duration-200'
            }),
            'is_featured': forms.CheckboxInput(attrs={
                'class': 'form-checkbox h-5 w-5 text-pink-600 ml-2' # Ajuste de estilo para checkbox.
            }) 
        }
        # Rótulos amigáveis para os campos do formulário, exibidos para o usuário.
        labels = {
            'name': "Nome do Produto",
            'description': "Descrição",
            'price': "Preço (R$)",
            'image': "Imagem do Produto",
            'category': "Categoria",
            'stock': "Estoque",
            'is_featured': "Destacar na Página Inicial?"
        }
