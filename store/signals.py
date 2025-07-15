# store/signals.py
from django.db.models.signals import post_save
from django.contrib.auth.models import User
from django.dispatch import receiver
from .models import Profile

# Este decorador conecta a função create_user_profile ao sinal post_save do modelo User.
# Isso significa que toda vez que um objeto User for salvo (incluindo na criação),
# esta função será executada.
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        # Se um novo usuário foi criado, cria um perfil correspondente para ele.
        # O campo 'user' do Profile aponta para a instância do User recém-criada.
        Profile.objects.create(user=instance)

# Este decorador conecta a função save_user_profile ao sinal post_save do modelo User.
# Ele garante que o perfil do usuário seja salvo junto com o usuário.
@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    # Salva o perfil associado ao usuário.
    # Isso é útil caso haja alterações no perfil que precisem ser persistidas.
    instance.profile.save()
