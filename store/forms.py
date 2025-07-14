# store/forms.py

from django import forms

class ContactForm(forms.Form):
    name = forms.CharField(
        max_length=100, 
        label="Seu Nome",
        widget=forms.TextInput(attrs={'class': 'shadow-sm appearance-none border border-stone-300 rounded-lg w-full py-3 px-4 text-gray-700 leading-tight focus:outline-none focus:ring-2 focus:ring-pink-500 focus:border-transparent transition duration-200', 'placeholder': 'Seu nome completo'})
    )
    email = forms.EmailField(
        label="Seu E-mail",
        widget=forms.EmailInput(attrs={'class': 'shadow-sm appearance-none border border-stone-300 rounded-lg w-full py-3 px-4 text-gray-700 leading-tight focus:outline-none focus:ring-2 focus:ring-pink-500 focus:border-transparent transition duration-200', 'placeholder': 'seu.email@exemplo.com'})
    )
    message = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 6, 'class': 'shadow-sm appearance-none border border-stone-300 rounded-lg w-full py-3 px-4 text-gray-700 leading-tight focus:outline-none focus:ring-2 focus:ring-pink-500 focus:border-transparent transition duration-200', 'placeholder': 'Escreva sua mensagem aqui...'}),
        label="Sua Mensagem"
    )
