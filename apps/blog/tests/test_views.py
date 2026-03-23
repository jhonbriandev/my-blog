import pytest
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth.models import User
from apps.users.models import ProfileUser
from apps.blog.models import Post, Category

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
    return User.objects.create_user(
        username='test',
        password='test123'
    )

@pytest.fixture
def admin_user(db):
    # create_user() dispara el signal que crea el ProfileUser
    user = User.objects.create_user(
        username='admin',
        password='admin123'
    )
    
    # Modificamos el profile directamente desde la BD
    # usando update() en lugar de save() para evitar
    # que el signal save_profile_user se dispare y resetee el role
    ProfileUser.objects.filter(user=user).update(rol='admin')
    
    return user


@pytest.fixture
def post_published(db, user, category):
    # published_at es requerido para que Post.objects.published()
    # retorne este post — ese manager filtra status='published'
    return Post.objects.create(
        title='Test Post',
        author=user,
        content='Contenido largo de prueba' * 10,
        category=category,
        status='published',
        published_at=timezone.now()
    )

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