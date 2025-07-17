# store/signals.py
from django.db.models.signals import post_save
from django.contrib.auth import get_user_model
from django.dispatch import receiver
from .models import Profile

# Obtém o modelo de usuário ativo do Django. É uma boa prática usar get_user_model()
# em vez de importar User diretamente de django.contrib.auth.models,
# pois permite que você use um modelo de usuário personalizado no futuro.
User = get_user_model()

# Este decorador conecta a função create_and_save_user_profile ao sinal post_save do modelo User.
# Isso significa que toda vez que um objeto User for salvo (incluindo na criação),
# esta função será executada.
@receiver(post_save, sender=User)
def create_and_save_user_profile(sender, instance, created, **kwargs):
    """
    Cria um objeto Profile para um novo usuário ou salva o perfil existente
    quando um objeto User é salvo.
    """
    if created:
        # Se um novo usuário foi criado, cria um perfil correspondente para ele.
        # O campo 'user' do Profile aponta para a instância do User recém-criada.
        Profile.objects.create(user=instance)
    else:
        # Se o usuário não foi recém-criado, tenta salvar o perfil associado.
        # Isso é útil caso haja alterações no perfil que precisem ser persistidas
        # e que não sejam diretamente acionadas por um save no Profile.
        # Adiciona um try-except para lidar com casos onde o perfil pode não existir ainda
        # (embora o 'created' acima deva garantir isso para novos usuários).
        try:
            instance.profile.save()
        except Profile.DoesNotExist:
            # Isso pode acontecer se o sinal for disparado para um usuário
            # que por algum motivo não tem um perfil (ex: migrações antigas ou dados inconsistentes).
            # Para robustez, podemos criar um perfil aqui também, ou apenas logar o erro.
            # Neste caso, vamos criar para garantir a consistência.
            Profile.objects.create(user=instance)
            print(f"AVISO: Perfil para o usuário {instance.username} não encontrado, um novo foi criado.")

