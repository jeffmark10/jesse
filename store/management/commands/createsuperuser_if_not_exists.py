import os
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model

class Command(BaseCommand):
    help = 'Cria um superutilizador Django se este não existir, usando variáveis de ambiente.'

    def handle(self, *args, **options):
        User = get_user_model()

        # Obter credenciais do superutilizador a partir de variáveis de ambiente
        # É CRUCIAL que estas variáveis sejam definidas no Render.
        username = os.environ.get('DJANGO_SUPERUSER_USERNAME')
        email = os.environ.get('DJANGO_SUPERUSER_EMAIL')
        password = os.environ.get('DJANGO_SUPERUSER_PASSWORD')

        if not all([username, email, password]):
            raise CommandError(
                "As variáveis de ambiente DJANGO_SUPERUSER_USERNAME, "
                "DJANGO_SUPERUSER_EMAIL e DJANGO_SUPERUSER_PASSWORD devem ser definidas."
            )

        if not User.objects.filter(username=username).exists():
            self.stdout.write(self.style.SUCCESS(f"A criar superutilizador '{username}'..."))
            try:
                User.objects.create_superuser(username, email, password)
                self.stdout.write(self.style.SUCCESS('Superutilizador criado com sucesso!'))
            except Exception as e:
                raise CommandError(f"Erro ao criar superutilizador: {e}")
        else:
            self.stdout.write(self.style.SUCCESS(f"Superutilizador '{username}' já existe. Ignorando a criação."))

