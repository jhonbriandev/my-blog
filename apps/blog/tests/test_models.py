import pytest
from django.utils.text import slugify
from apps.blog.models import Category  # ✅ import al inicio, no dentro del método
from apps.blog.tests.factories import CategoryFactory, PostFactory


@pytest.mark.django_db
class TestCategory:

    # ── CREATE CATEGORY ───────────────────────────────────────

    def test_create_category(self):
        """Verifica que una categoría se crea correctamente"""
        category = CategoryFactory()
        # CategoryFactory() genera automáticamente todos los campos del modelo
        # pk es la llave primaria, si no es None significa que se guardó en BD
        assert category.pk is not None
        # active=True es el valor por defecto definido en el modelo
        assert category.active is True

    def test_create_category_without_icon(self):
        """Verifica que el ícono es opcional"""
        # Sobreescribimos el campo icon con vacío para simular una categoría sin ícono
        # Los demás campos se generan normalmente por la factory
        category = CategoryFactory(icon='')
        # Verificamos que el campo se guardó vacío y no con algún valor por defecto
        assert category.icon == ''

    def test_category_name_is_unique(self):
        """Verifica que no se puedan crear dos categorías con el mismo nombre"""
        # Creamos la primera categoría con nombre 'Python'
        CategoryFactory(name='Python')
        # pytest.raises captura la excepción que Django lanza al violar unique=True
        # Si NO lanza excepción → test falla (significa que sí permitió el duplicado)
        # Si SÍ lanza excepción → test pasa (el modelo protege correctamente)
        with pytest.raises(Exception):
            CategoryFactory(name='Python')

    # ── __STR__ ───────────────────────────────────────────────

    def test_str_with_icon(self):
        """Verifica que __str__ retorna ícono + nombre cuando hay ícono"""
        category = CategoryFactory(name='Python', icon='🐍')
        # str(category) llama al método __str__ del modelo
        # Esperamos que retorne el ícono pegado al nombre sin espacio
        # porque así está definido: f"{self.icon}{self.name}"
        assert str(category) == '🐍Python'

    def test_str_without_icon(self):
        """Verifica que __str__ retorna solo nombre si no hay ícono"""
        category = CategoryFactory(name='Python', icon='')
        # Cuando icon está vacío, __str__ retorna solo self.name
        # Esto valida el condicional: if self.icon else self.name
        assert str(category) == 'Python'

    # ── GET POSTS PUBLISHED ───────────────────────────────────

    def test_get_posts_published_counts_only_published(self):
        """Verifica que solo cuenta posts publicados"""
        category = CategoryFactory()
        # Creamos 2 posts publicados y 1 borrador para la misma categoría
        # Pasamos category=category para que todos pertenezcan a la misma categoría
        # Si no lo hacemos, PostFactory crearía una categoría nueva por cada post
        PostFactory(category=category, status='published')
        PostFactory(category=category, status='published')
        PostFactory(category=category, status='drafts')  # este NO debe contarse
        # get_posts_published() es método de Category que filtra status='published'
        assert category.get_posts_published() == 2

    def test_get_posts_published_returns_zero_if_none(self):
        """Verifica que retorna 0 si no hay posts publicados"""
        # Creamos una categoría sin ningún post asociado
        # get_posts_published() debe retornar 0 y no lanzar error
        category = CategoryFactory()
        assert category.get_posts_published() == 0

    # ── ORDERING ──────────────────────────────────────────────

    def test_ordering_by_order_then_name(self):
        """Verifica que las categorías se ordenan por order y luego por name"""
        cat_b = CategoryFactory(name='B', order=1)
        cat_a = CategoryFactory(name='A', order=2)
        cat_c = CategoryFactory(name='C', order=1)

        # list() fuerza la ejecución del QuerySet y lo convierte en lista
        # Sin list(), Django evalúa la consulta de forma lazy (perezosa)
        # lo que puede dar resultados inesperados al acceder por índice
        categories = list(Category.objects.all())

        # order=1 va antes que order=2
        # Entre order=1, 'B' va antes que 'C' alfabéticamente
        assert categories[0] == cat_b  # order=1, name='B'
        assert categories[1] == cat_c  # order=1, name='C'
        assert categories[2] == cat_a  # order=2, siempre al final