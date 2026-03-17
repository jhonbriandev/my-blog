import factory
from django.utils.text import slugify
from  apps.users.models import User, ProfileUser

class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
    username = factory.Sequence(lambda n: f'user{n}')
    email = factory.Sequence(lambda n: f'user{n}@test.com')
    password = factory.PostGenerationMethodCall('set_password', 'testpass123')