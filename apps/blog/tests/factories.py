import factory
from django.utils.text import slugify
from apps.blog.models import Category, Post, Commentary
from apps.users.tests.factories import UserFactory


class CategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Category
    """En resumen: Sequence para unique = True, 
        Faker para el resto de datos que seran falsos pero parecen realistas
        y valores fijos cuando hay validaciones estrictas como en Commentary
    """   
    name = factory.Sequence(lambda n: f'Category {n}')
    # Sequence genera nombres únicos automáticamente:
    # primer objeto  → 'Categoria 0'
    # segundo objeto → 'Categoria 1'
    # Esto evita errores de unique=True en el campo name
    slug = factory.LazyAttribute(lambda o: slugify(o.name))

class PostFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Post
    title = factory.Sequence(lambda n: f'Post {n}')
    author = factory.SubFactory(UserFactory)
    category = factory.SubFactory(CategoryFactory)
    status = 'published'
    slug = factory.Sequence(lambda n: f'post-{n}')  # único por Sequence


class CommentaryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Commentary
    post = factory.SubFactory(PostFactory) # SUB FACTORY ES PARA LLAVES FORANEAS
    author = factory.SubFactory(UserFactory)
    content = factory.Faker('paragraph')
    aprobated = True

#factory.Faker('word')       # "table"
#factory.Faker('sentence')   # "The quick brown fox jumps."
#factory.Faker('paragraph')  # "Several sentences together forming a paragraph..."
#factory.Faker('text')       # texto largo e impredecible en tamaño
    
