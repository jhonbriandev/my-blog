import factory
from django.utils.text import slugify
from  apps.users.models import User, ProfileUser

# FACTORIES
"""
Un Factory es una clase que sabe cómo construir instancias de un modelo con datos por defecto.
El modelo define qué campos existen
El factory define qué valores usar
Definimos algunos campos porque:
Son obligatorios
Necesitamos controlar lógica
Queremos probar escenarios específicos
"""
# MUY IMPORTANTE 
"""Crear datos específicos para probar comportamiento"""
class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
        # Para evitar el warning
        # DeprecationWarning: UserFactory._after_postgeneration will stop saving the instance after postgeneration hooks in the next major release.
        skip_postgeneration_save = True  # ← esto elimina el warning
    username = factory.Sequence(lambda n: f'user{n}')
    email = factory.Sequence(lambda n: f'user{n}@test.com')
    password = factory.PostGenerationMethodCall('set_password', 'testpass123')