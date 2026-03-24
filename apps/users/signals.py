from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import ProfileUser

@receiver(post_save, sender= User)
def create_profile_user(sender, instance, created, **kwargs):
    """Crear perfil automáticamente cuando se crea un usuario"""
    if created:
        ProfileUser.objects.create(user=instance)
