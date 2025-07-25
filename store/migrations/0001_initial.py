# Generated by Django 5.2.4 on 2025-07-11 19:07

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Product',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200, verbose_name='Nome do Produto')),
                ('description', models.TextField(verbose_name='Descrição')),
                ('price', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Preço')),
                ('image_url', models.URLField(default='https://placehold.co/400x400/cccccc/ffffff?text=Jeci+Store+Produto', max_length=500, verbose_name='URL da Imagem')),
                ('is_featured', models.BooleanField(default=False, verbose_name='Destaque na Home')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Criado Em')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Atualizado Em')),
            ],
            options={
                'verbose_name_plural': 'Produtos',
                'ordering': ['name'],
            },
        ),
    ]
