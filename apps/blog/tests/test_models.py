import pytest
from django.utils.text import slugify
from apps.blog.models import Category, Post, Commentary     
from apps.blog.tests.factories import CategoryFactory, PostFactory, CommentaryFactory
from apps.users.tests.factories import UserFactory
from django.core.exceptions import ValidationError

""" MUY IMPORTANTE EN ESTOS TEST:

- USAMOS assert PARA VERIFICAR QUE ALGO FUNCIONA CORRECTAMENTE
  (afirmamos que el resultado debe ser verdadero)

- USAMOS pytest.raises(Exception) PARA VERIFICAR QUE ALGO FALLA CORRECTAMENTE
  (afirmamos que el sistema debe rechazar datos inválidos)
"""

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

@pytest.mark.django_db
class TestPost:
     # ── CREACIÓN ──────────────────────────────────────────────

    def test_create_post(self):
        """Verifica que un post se crea correctamente"""
        post = PostFactory()
        # pk no None significa que se guardó correctamente en BD
        assert post.pk is not None
        # El estado por defecto en la factory es 'published'
        assert post.status == 'published'

    def test_post_requires_author(self):
        """Verifica que un post sin autor no se puede crear"""
        with pytest.raises(Exception):
            # author=None viola el ForeignKey obligatorio hacia User
            PostFactory(author=None)

    # ── SLUG ──────────────────────────────────────────────────

    def test_slug_is_generated_automatically(self):
        """Verifica que el slug se genera automáticamente desde el título"""
        # Creamos el post sin slug para forzar que el método save() lo genere
        post = PostFactory(title='Mi Post De Prueba', slug='')
        # save() llama a slugify(self.title) si slug está vacío
        assert post.slug == slugify('Mi Post De Prueba')
        # resultado esperado: 'mi-post-de-prueba'

    def test_slug_is_unique(self):
        """Verifica que no se pueden crear dos posts con el mismo slug"""
        PostFactory(slug='slug-repetido')
        with pytest.raises(Exception):
            # unique=True en slug lanza excepción al repetir
            PostFactory(slug='slug-repetido')

    def test_slug_is_not_overwritten_if_exists(self):
        """Verifica que el slug no se sobreescribe si ya existe"""
        post = PostFactory(slug='mi-slug-personalizado')
        post.title = 'Nuevo Título Diferente'
        post.save()
        # save() solo genera slug si está vacío, no debe sobreescribir uno existente
        assert post.slug == 'mi-slug-personalizado'

    # ── PUBLISHED AT ──────────────────────────────────────────

    def test_published_at_is_set_when_published(self):
        """Verifica que published_at se asigna al publicar"""
        # Creamos en borrador para que published_at sea None
        post = PostFactory(status='drafts', published_at=None)
        assert post.published_at is None
        # Cambiamos a publicado y guardamos
        post.status = 'published'
        post.save()
        # save() asigna timezone.now() cuando status='published' y published_at es None
        assert post.published_at is not None

    def test_published_at_is_not_overwritten(self):
        """Verifica que published_at no se sobreescribe si ya tiene valor"""
        post = PostFactory(status='published')
        original_date = post.published_at
        # Guardamos de nuevo sin cambiar estado
        post.save()
        # published_at debe mantenerse igual, no actualizarse
        assert post.published_at == original_date

    # ── IS PUBLISHED / IS DRAFT ───────────────────────────────

    def test_is_published_returns_true(self):
        """Verifica que is_published() retorna True para posts publicados"""
        post = PostFactory(status='published')
        assert post.is_published() is True

    def test_is_published_returns_false_for_draft(self):
        """Verifica que is_published() retorna False para borradores"""
        post = PostFactory(status='drafts')
        assert post.is_published() is False

    def test_is_draft_returns_true(self):
        """Verifica que is_draft() retorna True para borradores"""
        post = PostFactory(status='drafts')
        assert post.is_draft() is True

    # ── INCREASE VIEWS ────────────────────────────────────────

    def test_increase_views_increments_count(self):
        """Verifica que increase_views() incrementa el contador en 1"""
        post = PostFactory()
        initial_views = post.count_views
        post.increase_views()
        # refresh_from_db() dentro del método trae el valor actualizado de la BD
        assert post.count_views == initial_views + 1

    def test_increase_views_multiple_times(self):
        """Verifica que increase_views() acumula correctamente"""
        post = PostFactory()
        post.increase_views()
        post.increase_views()
        post.increase_views()
        assert post.count_views == 3

    # ── CAN BE EDITED / DELETED ───────────────────────────────

    def test_can_be_edited_by_author(self):
        """Verifica que el autor puede editar su propio post"""
        post = PostFactory()
        # post.author es el User creado por SubFactory(UserFactory)
        assert post.can_be_edited_by(post.author) is True

    def test_can_be_edited_by_admin(self):
        """Verifica que un admin puede editar cualquier post"""
        post = PostFactory()
        admin = UserFactory()
        # Asignamos rol admin al perfil del usuario
        admin.profile.rol = 'admin'
        admin.profile.save()
        assert post.can_be_edited_by(admin) is True

    def test_cannot_be_edited_by_other_user(self):
        """Verifica que otro usuario no puede editar el post"""
        post = PostFactory()
        # Creamos un usuario diferente al autor
        other_user = UserFactory()
        assert post.can_be_edited_by(other_user) is False

    def test_cannot_be_edited_by_anonymous(self):
        """Verifica que un usuario no autenticado no puede editar"""
        post = PostFactory()
        # None simula un usuario no autenticado
        assert post.can_be_edited_by(None) is False

    def test_can_be_deleted_by_author(self):
        """Verifica que el autor puede eliminar su propio post"""
        post = PostFactory()
        # can_be_deleted_by() reutiliza can_be_edited_by()
        assert post.can_be_deleted_by(post.author) is True

    # ── MANAGER ───────────────────────────────────────────────

    def test_manager_published_returns_only_published(self):
        """Verifica que el manager retorna solo posts publicados"""
        PostFactory(status='published')
        PostFactory(status='published')
        PostFactory(status='drafts')
        # Post.objects usa PostManager que tiene el método published()
        assert Post.objects.published().count() == 2

    def test_manager_popular_returns_max_10(self):
        """Verifica que popular() retorna máximo 10 posts"""
        # Creamos 12 posts publicados
        for _ in range(12):
            PostFactory(status='published')
        assert Post.objects.popular().count() <= 10

    def test_manager_recently_returns_max_10(self):
        """Verifica que recently() retorna máximo 10 posts"""
        for _ in range(12):
            PostFactory(status='published')
        assert Post.objects.recently().count() <= 10

@pytest.mark.django_db
class TestCommentary:

    # ── CREACIÓN ──────────────────────────────────────────────

    def test_create_commentary(self):
        """Verifica que un comentario se crea correctamente"""
        
        # Crea un comentario con datos válidos usando la Factory
        # (Factory se encarga de rellenar los campos requeridos automáticamente)
        commentary = CommentaryFactory()
        
        # Verifica que el comentario fue guardado en la base de datos
        # pk (primary key) es el ID que la BD asigna al guardar un registro
        # Si pk es None, significa que nunca se guardó
        assert commentary.pk is not None
        
        # Verifica que el comentario fue aprobado por defecto
        # Según la lógica del modelo, todo comentario nuevo debe estar aprobado
        assert commentary.aprobated is True


    def test_commentary_requires_post(self):
        """Verifica que un comentario sin post no se puede crear"""
        
        # Se espera que el sistema lance un error (Exception)
        # si se intenta crear un comentario sin asociarlo a un post
        # Un comentario sin post no tiene sentido en la aplicación
        with pytest.raises(Exception):
            # Intentamos crear el comentario con post=None (vacío)
            # Esto DEBE fallar, si no falla el test se marca como fallido
            CommentaryFactory(post=None)


    def test_commentary_requires_author(self):
        """Verifica que un comentario sin autor no se puede crear"""
        
        # Se espera que el sistema lance un error (Exception)
        # si se intenta crear un comentario sin un autor asignado
        # Todo comentario debe pertenecer a alguien
        with pytest.raises(Exception):
            # Intentamos crear el comentario con author=None (vacío)
            # Esto DEBE fallar, si no falla el test se marca como fallido
            CommentaryFactory(author=None)

    # ── CLEAN / VALIDACIONES ──────────────────────────────────

    def test_commentary_min_length(self):
        """Verifica que el comentario debe tener al menos 5 caracteres"""
        with pytest.raises(ValidationError):
            # 'Hi' tiene solo 2 chars, clean() debe lanzar ValidationError
            commentary = CommentaryFactory.build(content='Hi')
            # build() crea el objeto sin guardarlo, full_clean() valida manualmente
            commentary.full_clean()

    def test_commentary_max_length(self):
        """Verifica que el comentario no puede exceder 1000 caracteres"""
        with pytest.raises(ValidationError):
            commentary = CommentaryFactory.build(content='a' * 1001)
            commentary.full_clean()

    def test_commentary_only_spaces_is_invalid(self):
        """Verifica que un comentario con solo espacios no es válido"""
        with pytest.raises(ValidationError):
            # strip() elimina espacios, quedaría vacío y menor a 5 chars
            commentary = CommentaryFactory.build(content='     ')
            commentary.full_clean()

    def test_commentary_not_allowed_if_post_has_no_permission(self):
        """Verifica que no se puede comentar si el post no lo permite"""
        # commentaries_permission=False deshabilita comentarios en el post
        post = PostFactory(commentaries_permission=False)
        with pytest.raises(ValidationError):
            commentary = CommentaryFactory.build(post=post)
            commentary.full_clean()

    def test_commentary_not_allowed_on_archived_post(self):
        """Verifica que no se puede comentar en un post archivado"""
        post = PostFactory(status='archived')
        with pytest.raises(ValidationError):
            commentary = CommentaryFactory.build(post=post)
            commentary.full_clean()

    # ── CONTADOR DE COMENTARIOS ───────────────────────────────

    def test_count_commentaries_updates_on_save(self):
        """Verifica que el contador del post se actualiza al crear comentario"""
        post = PostFactory()
        # Al guardar el comentario, save() llama update_count_commentaries()
        CommentaryFactory(post=post, aprobated=True)
        post.refresh_from_db()  # recarga el post para ver el valor actualizado
        assert post.count_commentaries == 1

    def test_count_only_aprobated_commentaries(self):
        """Verifica que el contador solo cuenta comentarios aprobados"""
        post = PostFactory()
        CommentaryFactory(post=post, aprobated=True)
        CommentaryFactory(post=post, aprobated=True)
        CommentaryFactory(post=post, aprobated=False)  # este NO cuenta
        post.refresh_from_db()
        assert post.count_commentaries == 2

    # ── CAN BE EDITED / ELIMINATED ────────────────────────────

    def test_can_be_edited_by_author(self):
        """Verifica que el autor del comentario puede editarlo"""
        commentary = CommentaryFactory()
        assert commentary.can_be_edited_by(commentary.author) is True

    def test_can_be_edited_by_post_author(self):
        """Verifica que el autor del post puede editar cualquier comentario"""
        commentary = CommentaryFactory()
        # El autor del post tiene permisos sobre todos sus comentarios
        assert commentary.can_be_edited_by(commentary.post.author) is True

    def test_cannot_be_edited_by_other_user(self):
        """Verifica que otro usuario no puede editar el comentario"""
        commentary = CommentaryFactory()
        other_user = UserFactory()
        assert commentary.can_be_edited_by(other_user) is False

    def test_cannot_be_edited_by_anonymous(self):
        """Verifica que un anónimo no puede editar el comentario"""
        commentary = CommentaryFactory()
        assert commentary.can_be_edited_by(None) is False

    # ── RESPUESTAS ────────────────────────────────────────────

    def test_commentary_can_be_a_response(self):
        """Verifica que un comentario puede responder a otro"""
        parent = CommentaryFactory()
        # response_to apunta al comentario padre (autorreferencia)
        response = CommentaryFactory(post=parent.post, response_to=parent)
        assert response.response_to == parent

    def test_get_response_returns_only_aprobated(self):
        """Verifica que get_response() retorna solo respuestas aprobadas"""
        parent = CommentaryFactory()
        CommentaryFactory(post=parent.post, response_to=parent, aprobated=True)
        CommentaryFactory(post=parent.post, response_to=parent, aprobated=False)
        # responses es el related_name de response_to
        responses = parent.get_response()
        assert responses.count() == 1

    # ── __STR__ ───────────────────────────────────────────────

    def test_str_truncates_long_content(self):
        """Verifica que __str__ trunca contenido mayor a 50 caracteres"""
        commentary = CommentaryFactory(content='a' * 60)
        # __str__ agrega '...' si el contenido supera 50 chars
        assert '...' in str(commentary)

    def test_str_shows_full_content_if_short(self):
        """Verifica que __str__ muestra todo el contenido si es menor a 50 chars"""
        commentary = CommentaryFactory(content='Comentario corto')
        assert '...' not in str(commentary)