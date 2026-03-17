import pytest
from django.utils.text import slugify
from apps.blog.tests.factories import CategoryFactory , PostFactory


@pytest.mark.django_db
class TestCategory:

    # CREATE CATEGORY
    def test_create_category(self):
        """Verifica que una caategoria se crea correctamente"""
        category = CategoryFactory()
        # Importamos CategoryFactory y creamos un objeto
        # Se probara si la llave primaria de category ingresa como no None y el active ingresa como true
        # Si no es asi entonces el test fallara.
        assert category.pk is not None
        assert category.active is True
        # Con false fallara el test
        # assert category.active is False
    
    def test_create_category_without_icon(self):
        """Verifica que el icono es opcional"""
        # Si el campo icono ingresa con el valor vacio el assert lo igualara a vacio y sera aprobado
        # Pero si ingresa con algun dato, se alertara del error, el test no pasara
        category = CategoryFactory(icon='')
        # En este caso no pasaria el test 
        # category = CategoryFactory(icon='novacio')
        assert category.icon == ''
    
    def test_category_name_is_unique(self):
        """Verifica que el nombre de la categoria sea unico"""
        CategoryFactory(name='Python')
        # Hereda de factories el name y lo inserta como Python
        with pytest.raises(Exception):
            # Inserta un nombre en el mismo campo, si es el mismo emite la alerta
            CategoryFactory(name='Python')
            # Si el nombre no es igual el test fallara
            # CategoryFactory(name='Pythoan')

    # GET POST PUBLISHED
    def test_get_posts_published_counts_only_published(self):
        """Verifica que solo cuenta posts publicados"""
        category = CategoryFactory()
        PostFactory(category=category, status='published')
        PostFactory(category=category, status='published')
        PostFactory(category=category, status='drafts')
        # get_posts_published es metodo de Category, aca se usa como objeto
        assert category.get_posts_published() == 2

    def test_get_posts_published_returns_zero_if_none(self):
        """Verifica que retorna 0 si no hay posts publicados"""
        category = CategoryFactory()
        assert category.get_posts_published() == 0