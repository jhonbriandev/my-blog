import pytest
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth.models import User
from apps.users.models import ProfileUser
from apps.blog.models import Post, Category, Commentary

# ─────────────────────────────────────────────────────────────
# FIXTURES GLOBALES
# Los fixtures son datos de prueba reutilizables.
# Piénsalos como ingredientes que preparas antes de cocinar.
# Cada test puede pedirlos como parámetros y Django los crea
# frescos para cada test, evitando que un test "ensucie" otro.
# ─────────────────────────────────────────────────────────────

@pytest.fixture
def category(db):
    # active=True es necesario porque PostListView filtra
    # Category.objects.filter(active=True) en get_context_data()
    return Category.objects.create(
        name='Python',
        slug='python',
        active=True
    )

@pytest.fixture
def user(db):
    """
    Crea un usuario normal (sin rol especial).
    ProfileUser se crea automáticamente via signal al crear User.
    """
    user = User.objects.create_user(
        username='usuario_normal',
        password='pass1234',
        email='normal@test.com'
    )
    # .update() evita re-disparar signals al asignar el rol
    # Analogía: cambiar la etiqueta directamente en el almacén,
    # sin pasar por el proceso de recepción de nuevo.
    user.profile.__class__.objects.filter(pk=user.profile.pk).update(rol='user')
    user.profile.refresh_from_db()
    return user

@pytest.fixture
def admin_user(db):
    """
    Crea un usuario con rol de administrador.
    Los admins tienen auto-aprobación igual que los moderadores.
    """
    user = User.objects.create_user(
        username='administrador',
        password='pass1234',
        email='admin@test.com'
    )
    user.profile.__class__.objects.filter(pk=user.profile.pk).update(rol='admin')
    user.profile.refresh_from_db()
    return user
    
    # Modificamos el profile directamente desde la BD
    # usando update() en lugar de save() para evitar
    # que el signal save_profile_user se dispare y resetee el role

@pytest.fixture
def moderator_user(db):
    """
    Crea un usuario con rol de moderador.
    Los moderadores pueden aprobar comentarios automáticamente.
    """
    user = User.objects.create_user(
        username='moderador',
        password='pass1234',
        email='mod@test.com'
    )
    user.profile.__class__.objects.filter(pk=user.profile.pk).update(rol='mod')
    user.profile.refresh_from_db()
    return user

@pytest.fixture
def post_published(db, user, category):
    """
    Crea un post publicado con comentarios habilitados.
    Este es el escenario más común donde se espera que
    los comentarios funcionen normalmente.
    """
    # published_at es requerido para que Post.objects.published()
    # retorne este post — ese manager filtra status='published'
    return Post.objects.create(
        title='Test Post',
        slug='post-de-prueba',
        author=user,
        content='Contenido largo de prueba' * 10,
        category=category,
        status='published',
        published_at=timezone.now(),
        commentaries_permission=True, 
    )

@pytest.fixture
def approved_commentary(db, published_post, regular_user):
    """
    Crea un comentario aprobado de nivel 0 (sin padre).
    Sirve como base para probar las respuestas.
    
    Usamos Commentary.objects.create() con update() previo
    para saltar el full_clean() del modelo en el setUp,
    ya que queremos control directo sobre el estado.
    """
    # Creamos sin pasar por save() del modelo para evitar
    # que full_clean() interfiera con el fixture.
    # En tests de *vista* lo que importa es el estado inicial en BD.
    commentary = Commentary(
        post=published_post,
        author=regular_user,
        content='Comentario padre aprobado',
        aprobated=True,
    )
    # Llamamos super().save() saltando full_clean vía bulk=False no disponible,
    # así que usamos save directo — el clean() aquí pasará porque el post
    # tiene commentaries_permission=True
    commentary.save()
    return commentary
 
 
@pytest.fixture
def pending_commentary(db, published_post, regular_user):
    """
    Crea un comentario pendiente de aprobación (aprobated=False).
    Sirve para verificar que los usuarios no aprobados no son visibles.
    """
    commentary = Commentary(
        post=published_post,
        author=regular_user,
        content='Comentario pendiente de aprobacion',
        aprobated=False,
    )
    commentary.save()
    return commentary

@pytest.fixture
def drafts_post(db, user, category):
    # published_at=None porque aún no ha sido aprobado por admin
    # Solo el autor y admin pueden verlo via get_object() en PostDetailView
    return Post.objects.create(
        title='Post Borrador',
        author=user,
        content='Contenido borrador' * 10,
        category=category,
        status='drafts'
    )


# ─────────────────────────────────────────────────────────────
@pytest.mark.django_db
class TestPostListView:
    """
    Tests para PostListView.
    Verifica que get_queryset() filtra, busca y ordena correctamente.
    URL: GET /blog/posts/
    """

    def test_list_posts_visible(self, client, post_published):
        """
        Post.objects.published() en get_queryset() debe retornar
        solo posts con status='published', verificamos que aparece
        en el contexto que recibe el template.
        """
        response = client.get(reverse('blog:posts_list'))
        
        assert response.status_code == 200
        assert post_published in response.context['posts']
    
    def test_drafts_no_visible(self, client, drafts_post):
        """
        get_queryset() usa Post.objects.published() que internamente
        filtra status='published', por lo tanto los borradores
        nunca deben llegar al template de la lista pública.
        """
        response = client.get(reverse('blog:posts_list'))
        
        assert not any(p.title == 'Post Borrador' for p in response.context['posts'])
    
    def test_search_by_title(self, client, post_published):
        """
        get_queryset() aplica Q(title__icontains=query) cuando
        recibe el parámetro GET ?q=, permitiendo búsqueda
        sin distinción de mayúsculas/minúsculas.
        """
        response = client.get(reverse('blog:posts_list'), {'q': 'Test'})
        
        assert response.status_code == 200
        assert post_published in response.context['posts']

    def test_search_without_results(self, client, post_published):
        """
        Cuando el filtro Q() no encuentra coincidencias,
        get_queryset() debe retornar queryset vacío
        sin lanzar ningún error.
        """
        response = client.get(reverse('blog:posts_list'), {'q': 'xyzxyzxyz'})
        
        assert response.status_code == 200
        assert len(response.context['posts']) == 0
    
    def test_filter_by_category(self, client, post_published):
        """
        get_queryset() filtra por category__slug cuando recibe
        el parámetro GET ?category=, usando la relación
        ForeignKey entre Post y Category.
        """
        response = client.get(reverse('blog:posts_list'), {'category': 'python'})
        
        assert post_published in response.context['posts']


# ─────────────────────────────────────────────────────────────
@pytest.mark.django_db
class TestPostDetailView:
    """
    Tests para PostDetailView.
    Verifica get_object() para control de acceso
    y get_context_data() para incremento de vistas.
    URL: GET /blog/<slug>/
    """

    def test_increase_views(self, client, post_published):
        """
        get_context_data() llama a post.increase_views() en cada visita.
        increase_views() usa F() para incrementar count_views directamente
        en BD, evitando condiciones de carrera con múltiples visitantes.
        """
        assert post_published.count_views == 0
        
        client.get(reverse('blog:posts_detail', kwargs={'slug': post_published.slug}))
        
        # refresh_from_db() es necesario para ver el valor actualizado
        # en BD, sin esto veríamos el valor viejo cargado en memoria
        post_published.refresh_from_db()
        assert post_published.count_views == 1
    
    def test_drafts_no_visible_anonimous(self, client, drafts_post):
        """
        get_object() lanza Http404 si el post es borrador
        y el usuario no está autenticado.
        Retorna 404 en lugar de 403 para no revelar
        que el post existe.
        """
        response = client.get(
            reverse('blog:posts_detail', kwargs={'slug': drafts_post.slug})
        )
        assert response.status_code == 404
    
    def test_drafts_visible_by_author(self, client, user, drafts_post):
        """
        get_object() permite el acceso si request.user == post.author,
        usando la relación ForeignKey author definida en el modelo Post.
        """
        client.login(username='test', password='test123')
        response = client.get(
            reverse('blog:posts_detail', kwargs={'slug': drafts_post.slug})
        )
        assert response.status_code == 200


# ─────────────────────────────────────────────────────────────
@pytest.mark.django_db
class TestPostCreateView:
    """
    Tests para PostCreateView.
    Verifica que form_valid() asigna autor y estado
    correctamente según el rol del usuario.
    URL: GET/POST /blog/posts/create/
    """
    
    def test_create_post_require_login(self, client):
        """
        LoginRequiredMixin intercepta la request antes de
        llegar a la vista y redirige a login_url = 'users:login'
        si el usuario no está autenticado.
        """
        response = client.get(reverse('blog:posts_create'))
        
        assert response.status_code == 302
        assert 'next' in response.url
    
    def test_user_create_drafts(self, client, user, category):
        """
        form_valid() verifica profile.is_admin() antes de publicar.
        Si el usuario no es admin, fuerza status='drafts' sin importar
        lo que el usuario haya enviado en el formulario.
        """
        client.login(username='test', password='test123')
        
        data = {
            'title': 'Mi Nuevo Post',
            'content': 'Contenido de prueba' * 10,
            'category': category.id,
            'status': 'published',  # form_valid() ignorará esto
        }
        
        response = client.post(reverse('blog:posts_create'), data)
        
        assert response.status_code == 302
        
        post = Post.objects.get(title='Mi Nuevo Post')
        assert post.status == 'drafts'
        # author se asigna en form_valid() con post.author = request.user
        assert post.author == user
    
    def test_admin_create_post_published(self, client,admin_user, category):
        """
        form_valid() llama profile.is_admin() y si retorna True,
        asigna status='published' y published_at=timezone.now()
        automáticamente, saltándose el flujo de aprobación.
        """
        # Debug temporal: verificar que el profile tiene role='admin'
        # antes de hacer el request
        print(f"\nROLE EN TEST: {admin_user.profile.rol}")
        print(f"IS_ADMIN(): {admin_user.profile.is_admin()}")
        
        client.login(username='admin', password='admin123')
        
        data = {
            'title': 'Admin Post',
            'content': 'Contenido' * 20,
            'category': category.id,
            'status': 'drafts',
        }
        
        response = client.post(reverse('blog:posts_create'), data)
        
        post = Post.objects.get(title='Admin Post')
        
        # Debug temporal: ver qué status quedó guardado
        print(f"STATUS DEL POST: {post.status}")
        
        assert post.status == 'published'
        assert post.published_at is not None


# ─────────────────────────────────────────────────────────────
@pytest.mark.django_db
class TestPostUpdateView:
    """
    Tests para PostUpdateView.
    Verifica que get_queryset() filtra por autor
    para proteger posts ajenos.
    URL: GET/POST /blog/<slug>/update/
    """
    
    def test_edit_my_post(self, client, user, post_published, category):
        """
        get_queryset() en PostUpdateView filtra por author=request.user
        cuando no es admin, permitiendo que el autor
        edite solo sus propios posts.
        """
        client.login(username='test', password='test123')
        
        data = {
            'title': 'Título Actualizado',
            'content': 'Contenido nuevo' * 10,
            'category': post_published.category.id,
            'status': 'drafts',
        }
        
        client.post(
            reverse('blog:posts_update', kwargs={'slug': post_published.slug}),
            data
        )
        
        # refresh_from_db() recarga el objeto desde BD
        # para verificar que los cambios se guardaron
        post_published.refresh_from_db()
        assert post_published.title == 'Título Actualizado'
    
    def test_not_edit_strange_post(self, client, category):
        """
        get_queryset() filtra queryset por author=request.user,
        entonces si el post no pertenece al usuario logueado,
        get_object() no lo encuentra y retorna 404
        en lugar de 403, para no revelar que el post existe.
        """
        author = User.objects.create_user(username='propietario', password='pass')
        stranger = User.objects.create_user(username='intruso', password='pass')
        
        post = Post.objects.create(
            title='Post Ajeno',
            author=author,
            content='Contenido' * 10,
            category=category,
            status='drafts'
        )
        
        client.login(username='intruso', password='pass')
        response = client.get(
            reverse('blog:posts_update', kwargs={'slug': post.slug})
        )
        assert response.status_code == 404


# ─────────────────────────────────────────────────────────────
@pytest.mark.django_db
class TestPostDeleteView:
    """
    Tests para PostDeleteView.
    Verifica que on_delete=CASCADE del modelo elimina
    correctamente el post y sus comentarios relacionados.
    URL: POST /blog/<slug>/delete/
    """
    
    def test_delete_my_post(self, client, user, post_published):
        """
        DeleteView llama a post.delete() internamente.
        Como Commentary tiene on_delete=CASCADE apuntando a Post,
        todos los comentarios del post se eliminan también
        automáticamente por la BD.
        """
        client.login(username='test', password='test123')
        
        client.post(
            reverse('blog:posts_delete', kwargs={'slug': post_published.slug})
        )
        
        # El post ya no debe existir en BD
        assert not Post.objects.filter(id=post_published.id).exists()

@pytest.mark.django_db
class TestCommentaries:
    """Tests para comentarios
        De la vista  AddCommentaryView
        Ruta: POST /blog/<slug>/comentar/
        Nombre: blog:add_commentary
        Analogía: probamos la "ventanilla de comentarios" —
        quién puede usarla, qué pasa con cada tipo de usuario,
        y qué rechaza la ventanilla automáticamente.
    """

    
    
    @pytest.fixture
    def post_with_commentaries(self, user, category):
        from django.utils import timezone
        post = Post.objects.create(
            title='Post con Comentarios',
            slug='post-comentarios',
            author=user,
            content='Contenido' * 20,
            category=category,
            status='published',
            published_at=timezone.now()
        )
        
        # Comentario aprobado
        Commentary.objects.create(
            post=post,
            author=user,
            content='Comentario aprobado',
            aprobated=True
        )
        
        # Comentario pendiente
        Commentary.objects.create(
            post=post,
            author=user,
            content='Comentario pendiente',
            aprobated=False
        )
        
        return post
    
    def test_commentary_require_login(self, client, post):
        """Comentar sin login debe redirigir"""
        response = client.post(
            reverse('blog:add_commentary', kwargs={'slug': post.slug}),
            {'content': 'Comentario'}
        )
        
        assert response.status_code == 302
        assert 'login' in response.url
    
    def test_create_commentary_user(self, client, user, post):
        """Usuario crea comentario (pendiente)"""
        client.login(username='test', password='test123')
        
        response = client.post(
            reverse('blog:add_commentary', kwargs={'slug': post.slug}),
            {'content': 'Mi comentario de prueba'}
        )
        
        assert response.status_code == 302
        
        commentary = Commentary.objects.get(content='Mi comentario de prueba')
        assert commentary.aprobated == False  # Pendiente
    
    def test_create_commentary_admin(self, client, admin_user, post):
        """Admin crea comentario (auto-aprobado)"""
        client.login(username='admin', password='admin123')
        
        response = client.post(
            reverse('blog:add_comment', kwargs={'slug': post.slug}),
            {'content': 'Comentario del admin'}
        )
        
        commentary = Commentary.objects.get(content='Comentario del admin')
        assert commentary.aprobated == True  # Auto-aprobado
    
    def test_validation_short_content(self, client, user, post):
        """Comentario < 5 caracteres debe fallar"""
        client.login(username='test', password='test123')
        
        response = client.post(
            reverse('blog:add_commentary', kwargs={'slug': post.slug}),
            {'content': 'Hi'}
        )
        
        # No debe crear comentario
        assert not Commentary.objects.filter(content='Hi').exists()
    
    def test_commentaries_aprobated_visible(self, client, post_with_commentaries):
        """Solo comentarios aprobados deben verse"""
        response = client.get(
            reverse('blog:posts_detail', kwargs={'slug': post_with_commentaries.slug})
        )
        
        commentaries = response.context['commentaries']
        
        # Solo el aprobado
        assert commentaries.count() == 1
        assert commentaries.first().contenido == 'Comentario aprobado'
    
    def test_moderador_create_commentary_autoaprobated(self, client, moderator_user, published_post):
        """
        Un moderador crea un comentario y se aprueba automáticamente.
        
        Esto ocurre porque can_moderate es True para moderadores,
        y la vista asigna: commentary.aprobated = request.user.profile.can_moderate
        """
        client.force_login(moderator_user)
        url = reverse('blog:add_commentary', kwargs={'slug': published_post.slug})
        client.post(url, {'content': 'Comentario del moderador'})
 
        commentary = Commentary.objects.get(content='Comentario del moderador')
        # El moderador tiene can_moderate=True → auto-aprobado
        assert commentary.aprobated is True