from django.http import Http404
from django.shortcuts import render, redirect,get_object_or_404
from django.views.generic import ListView,DeleteView,CreateView,UpdateView,DetailView
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.urls import reverse_lazy
from django.db.models import Q
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from .models import Post,Commentary,Category
from .forms import PostForm, ApprovePostForm, CommentaryForm, ApproveCommentaryForm

# ─────────────────────────────────────────────
# HELPER: envío de emails
# ─────────────────────────────────────────────
 
def _send_post_approved_email(post):
    """
    Envía email al autor cuando su post es APROBADO.
 
    Analogía: como cuando un editor llama al escritor para decirle
    "tu artículo saldrá mañana en el periódico".
 
    ¿Por qué una función aparte y no dentro de la vista?
    - Reutilizable: si en el futuro lo llamamos desde otro lado, no repetimos código.
    - Más limpia: la vista solo decide QUÉ hacer, esta función sabe CÓMO enviarlo.
    - Fácil de testear por separado.
    """
    subject = f'✅ Tu post "{post.title}" fue aprobado'
    message = (
        f'Hola {post.author.get_full_name() or post.author.username},\n\n'
        f'¡Buenas noticias! Tu post "{post.title}" ha sido aprobado y ya está publicado.\n\n'
        f'Puedes verlo en tu blog. ¡Gracias por tu contribución!\n\n'
        f'— El equipo del blog'
    )
    # send_mail(asunto, mensaje, remitente, [destinatarios], fail_silently=...)
    # fail_silently=True → si el email falla, NO lanza error en la app (el post igual se aprueba)
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [post.author.email],
        fail_silently=True,
    )
 
 
def _send_post_rejected_email(post, reason):
    """
    Envía email al autor cuando su post es RECHAZADO, incluyendo el motivo.
 
    Analogía: como cuando el editor te devuelve el artículo con notas
    explicando qué debes mejorar antes de publicarlo.
    """
    subject = f'ℹ️ Tu post "{post.title}" necesita cambios'
    message = (
        f'Hola {post.author.get_full_name() or post.author.username},\n\n'
        f'Tu post "{post.title}" fue revisado y necesita algunos cambios antes de publicarse.\n\n'
        f'Motivo:\n{reason}\n\n'
        f'Puedes editarlo y enviarlo de nuevo cuando esté listo.\n\n'
        f'— El equipo del blog'
    )
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [post.author.email],
        fail_silently=True,
    )

# Vista principal del blog
class IndexView(View):
    """
    Vista de INICIO (homepage).
    
    GET / o /blog/
    └─ Muestra homepage curada
    
    Diferente de PostListView porque:
    - Muestra posts destacados
    - Muestra categorías
    - Muestra últimos posts
    - Llamadas a acción
    """
    
    def get(self, request):
        """Renderizar homepage"""
        
        # Posts destacados (más vistos)
        featured_posts = Post.objects.published().order_popular()[:3] # Metodos de Postqueryset
        
        # Últimos posts publicados
        recently_posts = Post.objects.published().recently_order()[:6] # Metodos de Postqueryset
        
        # Todas las categorías
        categories = Category.objects.filter(active=True).order_by('order')
        
        # Estadísticas para hero section
        total_posts = Post.objects.published().count()
        total_users = User.objects.count()
        
        context = {
            'featured_posts': featured_posts,
            'recently_posts': recently_posts,
            'categories': categories,
            'total_posts': total_posts,
            'total_users': total_users,
        }
        
        return render(request, 'blog/index.html', context)

# VISTAS PARA LOS POST

# ListView es un ayudante que automáticamente toma una lista de objetos y la manda al template
class PostListView(ListView):
    """
    Vista de lista de posts.
    
    GET /blog/posts/ → Muestra lista de posts con filtros
    
    Características:
    - Mostrar solo posts publicados
    - Filtro por categoría
    - Búsqueda por titulo/contenido
    - Ordenamiento (reciente, popular)
    - Paginación (10 posts por página)
    """
    model = Post
    template_name = 'blog/posts_list.html'
    context_object_name = 'posts' # Variable en template
    paginate_by = 10 # Post por paginas

    def get_queryset(self):
        """
        Obtener posts para mostrar.
        
        ¿Por qué override get_queryset()?
        - Para filtrar según criterios
        - Para optimizar queries (select_related, prefetch_related)
        - Para ordenar de forma personalizada
        """
        # Iniciar con todos los posts publicados
        # Usaremos el metodo creado en models
        queryset = Post.objects.published().select_related('author','category')
        # publicados() = filter(estado='publicado')
        # select_related() = evitar N+1 queries

        # BUSQUEDA
        query = self.request.GET.get('q')
        if query:
            # Buscar en titulo O contenido O resumen
            queryset = queryset.filter(
                Q(title__icontains = query) | # icontains = case-insensitive
                Q(content__icontains = query) |
                Q(summary__icontains = query)
            )
        # FILTRO POR CATEGORIA
        category = self.request.GET.get('category')
        if category:
            queryset = queryset.filter(category__slug = category)

        # ORDENAMIENTO
        order = self.request.GET.get('order','-published_at')
        # Opciones válidas:
        # -fecha_publicacion (nuevo primero)
        # fecha_publicacion (viejo primero)
        # -vistas_count (más visto primero)
        # titulo (A-Z)
        valid_order = ['-published_at','-count_views','title']

        if order in valid_order:
            queryset = queryset.order_by(order)
        return queryset
    
    def get_context_data(self,**kwargs):
        """
        Agregar variables extra al template.
        
        ¿Por qué override?
        - Agregar lista de categorías
        - Agregar búsqueda realizada
        - Agregar posts relacionados/destacados
        """
        context = super().get_context_data(**kwargs)

        # Categorias para sidebar
        context['categories'] = Category.objects.filter(active = True)

        # Busqueda realizada(para mostrar "Resultados de : x")
        context['query'] = self.request.GET.get('q','')

        # Categoria seleccionada
        context['select_categories'] = self.request.GET.get('category','')

        # Posts mas vistos

        context['popular_posts'] = Post.objects.published().order_by('-count_views')[:5]

        return context

class PostDetailView(DetailView):
    """
    Vista de detalle de un post.
    
    GET /blog/<slug>/ → Muestra post completo + comentarios
    
    Características:
    - Solo posts publicados (o si eres autor/admin)
    - Incrementar contador de vistas
    - Mostrar comentarios aprobados
    - Mostrar respuestas a comentarios aprobados
    - Mostrar formulario de comentario
    - Mostrar posts relacionados
    """
    
    model = Post
    template_name = 'blog/posts_detail.html'
    context_object_name = 'post'
    slug_field = 'slug'  # Campo para lookup (URL)

    def get_queryset(self):
        """
        OPTIMIZACIÓN CLAVE:
        Trae author + profile + category en una sola query
        """
        return Post.objects.select_related(
            # Select_Related es un optimizador para llaves foraneas u One to one
            # Sirve para evirar escribir muchos queries y problema N + 1
            # Hara un JOIN en SQL y traera todo junto
            # Gracias a esto traemos el autor del post Y su perfil en la misma query
            # Y ademas cada post tiene una categoria entonces el la misma query trae esta informacion
            'author__profile',
                # usamos __ para navegar entre relaciones (author → profile)
                # y le indicamos a select_related qué relaciones debe incluir en el JOIN            
            'category'
        )
    
    def get_object(self, queryset=None):
        """
        Override para permitir ver borrador si eres autor.
        
        Por defecto, DetailView obtiene el objeto y lo renderiza.
        Aquí validamos que el post sea publicado (o seas el autor/admin).
        """
        obj = super().get_object(queryset)
        
        # Si es borrador, solo autor y admin lo ven
        if obj.status == 'drafts':
            if not self.request.user.is_authenticated:
                raise Http404('Post no encontrado')
            # is admin sin parentesis gracias al @property
            if self.request.user != obj.author and not self.request.user.profile.is_admin:
                raise Http404('Post no encontrado')
        
        return obj
    
    def get_context_data(self, **kwargs):
        """Agregar comentarios y formulario al contexto"""
        context = super().get_context_data(**kwargs)
        
        post = self.object
        
        # INCREMENTAR VISTAS
        post.increase_views()
        # atomic() = operación safe (evita race conditions)
        
        # En los templates Django NO podemos llamar métodos con argumentos
        # (ej: profile.can_edit_commentary(commentary) falla con error).
        # Solución: calculamos los permisos aquí en Python (donde SÍ podemos
        # pasar argumentos) y los enviamos listos al template como True/False.

        # COMENTARIOS APROBADOS
        # Traemos solo comentarios RAÍZ (sin padre) aprobados
        # Las respuestas las traemos anidadas dentro de cada comentario.
        # Analogía: traemos solo los hilos principales de un foro —
        # las respuestas de cada hilo vienen adjuntas.
        commentaries_raw = post.commentaries.filter(
            aprobated=True,
            response_to=None    # IMPORTANTE solo comentarios raíz
        ).select_related('author', 'author__profile')

        commentaries_with_permissions = []
 
        for commentary in commentaries_raw:
            can_edit = False
            can_delete = False
 
            # Solo calculamos permisos si hay un usuario autenticado
            if self.request.user.is_authenticated:
                profile = self.request.user.profile
                can_edit = profile.can_edit_commentary(commentary)
                can_delete = profile.can_delete_commentary(commentary)

            # Respuestas aprobadas de este comentario ────────
            # Usamos el método get_response() que ya tenemos en el modelo.
            # Lo convertimos a lista para poder iterar dos veces en el template.
            responses_raw = commentary.get_response()
            responses_with_permissions = []

            for response in responses_raw:
                res_can_edit = False
                res_can_delete = False

                if self.request.user.is_authenticated:
                    profile = self.request.user.profile
                    res_can_edit = profile.can_edit_commentary(response)
                    res_can_delete = profile.can_delete_commentary(response)

                responses_with_permissions.append({
                    'commentary': response,
                    'can_edit': res_can_edit,
                    'can_delete': res_can_delete,
                })
            commentaries_with_permissions.append({
                'commentary': commentary,
                'can_edit': can_edit,
                'can_delete': can_delete,
                'responses':  responses_with_permissions,
            })
 
        context['commentaries_with_permissions'] = commentaries_with_permissions
        
        # FORMULARIO DE COMENTARIO (si está logueado)
        if self.request.user.is_authenticated:
            context['form_commentary'] = CommentaryForm()
        
        # POSTS RELACIONADOS (misma categoría)
        context['relationed_posts'] = Post.objects.published().select_related(
            'author__profile'
        ).filter(
            category=post.category
        ).exclude(
            id=post.id
        )[:3]

        return context


class PostCreateView(LoginRequiredMixin, CreateView):
    """
    Vista para crear post.
    
    GET /blog/posts/crear/ → Mostrar form vacío
    POST /blog/posts/crear/ → Crear post
    
    CAMBIO IMPORTANTE (Flujo de aprobación):
    - Todos los posts se crean como BORRADOR
    - No importa si es usuario, moderador excepto admin
    - Solo ADMIN puede APROBAR posts después (cambiar a publicado)
    - Esto garantiza que todo contenido sea revisado
    """
    
    model = Post
    form_class = PostForm
    template_name = 'blog/posts_create.html'
    login_url = 'users:login'  # Redirigir aquí si no autenticado
    
    def get_form_kwargs(self):
        """
        Pasar argumentos extra al form.
        
        Por defecto, CreateView pasa:
        - data/files si POST
        - instance si edición
        
        Aquí podemos agregar kwargs personalizados.
        """
        kwargs = super().get_form_kwargs()
        
        # No mostrar todas las opciones de estado a usuarios regulares
        # Los usuarios solo pueden crear borradores
        
        return kwargs
    
    def form_valid(self, form):
        """
        Ejecutar si el form es válido.
        
        Aquí:
        - Establecer autor
        - Establecer estado = BORRADOR (siempre)
        - SIN fecha_publicacion (se asigna cuando admin aprueba)
        - Guardar en BD
        """
        
        post = form.save(commit=False)
        # commit=False = no guardar en BD aún
        
        # ESTABLECER AUTOR
        post.author = self.request.user
        # └─ request.user = usuario autenticado
        
        # LÓGICA DE ESTADO Y PUBLICACIÓN
        if self.request.user.profile.is_admin:
            # Admin: publicar automáticamente
            post.status = 'published'
            post.published_at = timezone.now()
        else:
            # Usuario regular: solo borrador
            post.status = 'drafts'
            # fecha_publicacion se establece cuando admin publique
        
        # GUARDAR EN BD
        post.save()
        # └─ Ahora tiene ID, puede tener comentarios, etc
        
        # MENSAJE DE ÉXITO
        messages.success(self.request, '✓ Post creado exitosamente')
        
        # REDIRIGIR AL POST CREADO
        return redirect('blog:posts_detail', slug=post.slug)
    
    def form_invalid(self, form):
        """Ejecutar si el form NO es válido"""
        messages.error(self.request, '❌ Error al crear post')
        return super().form_invalid(form)
    

class PostUpdateView(LoginRequiredMixin, UpdateView):
    """
    Vista para editar post.
    
    GET /blog/<slug>/editar/ → Mostrar form con datos
    POST /blog/<slug>/editar/ → Actualizar post
    
    Seguridad:
    - Usuario debe estar autenticado
    - Solo autor o admin pueden editar
    - Se valida en get_queryset()
    """
    
    model = Post
    form_class = PostForm
    template_name = 'blog/posts_update.html'
    slug_field = 'slug'
    login_url = 'users:login'
    
    def get_queryset(self):
        """
         SEGURIDAD CRÍTICA Y NUEVO PERMISO.
        
        CAMBIO: Moderador ahora puede editar posts ajenos
        ¿Por qué? Porque necesita poder MODERAR contenido
        
        Estructura de permisos:
        - USUARIO: Solo edita sus propios posts
        - MODERADOR: Edita CUALQUIER post (para moderar)
        - ADMIN: Edita CUALQUIER post
        
        Si usuario envía /blog/otro-post/editar/,
        queremos que vea 404 si no tiene permisos.
        
        get_queryset() filtra ANTES de get_object().
        """
        
        queryset = Post.objects.all()
        
        # Si NO es admin, filtrar solo sus posts
        # Usaremos el metodo que creamos en model User
        # Sin parentesis gracias al property
        if not self.request.user.profile.can_moderate:
            queryset = queryset.filter(author=self.request.user)

        # Si ES moderador/admin: ver todos (sin filtro adicional)
        return queryset
    
    def form_valid(self, form):
        """Actualizar post cuando form es válido"""
        
        # GUARDAR
        post = form.save()
        
        messages.success(self.request, '✓ Post actualizado')
        return redirect('blog:posts_detail', slug=post.slug)
    

class PostDeleteView(LoginRequiredMixin, DeleteView):
    """
    Vista para eliminar post.
    
    GET /blog/<slug>/eliminar/ → Mostrar confirmación
    POST /blog/<slug>/eliminar/ → Eliminar
    
    Permisos (según matriz):
    - USUARIO: Solo puede eliminar sus propios posts
    - MODERADOR: Puede eliminar CUALQUIER post (para moderar)
    - ADMIN: Puede eliminar CUALQUIER post
    """
    
    model = Post
    template_name = 'blog/posts_delete.html'
    success_url = reverse_lazy('blog:index')  # Redirigir aquí después
    slug_field = 'slug'
    login_url = 'users:login'
    
    def get_queryset(self):
        """Mismo filtro que UpdateView (moderador ve todos)"""
        queryset = Post.objects.all()

        # Si NO es moderador/admin, filtrar solo sus posts
        if not self.request.user.profile.can_moderate:
            queryset = queryset.filter(author=self.request.user)

        # Si ES moderador/admin: ver todos (sin filtro adicional
        return queryset
    
    def delete(self, request, *args, **kwargs):
        messages.success(self.request, '✓ Post eliminado')
        return super().delete(request, *args, **kwargs)

class ToggleArchivePostView(LoginRequiredMixin, View):
    """
    Archiva o desarchiva un post con un solo clic.
    POST /blog/<slug>/archive/

    Ahora delegamos la lógica de permisos al modelo (can_be_archived_by),
    manteniendo la vista limpia y sin repetir reglas de negocio.
    """
    login_url = 'users:login'

    def post(self, request, slug):
        # ── Bloque 1: Obtener el post ─────────────────────────────
        # get_object_or_404 devuelve el post o una página 404 automática
        post = get_object_or_404(Post, slug=slug)

        # ── Bloque 2: Verificar permiso usando el modelo ──────────
        # Ya no repetimos la lógica aquí, le preguntamos al post mismo
        if not post.can_be_archived_by(request.user):
            raise PermissionDenied('No tienes permiso para archivar este post')

        # ── Bloque 3: El interruptor ──────────────────────────────
        # archived → published  /  cualquier otro estado → archived
        if post.status == 'archived':
            post.status = 'published'
            msg = f'✅ "{post.title}" restaurado y publicado'
        else:
            post.status = 'archived'
            msg = f'📦 "{post.title}" archivado'

        # ── Bloque 4: Guardar solo el campo que cambió ────────────
        # update_fields evita tocar campos como updated_at innecesariamente
        post.save(update_fields=['status'])
        messages.success(request, msg)

        # ── Bloque 5: Redirigir según origen ─────────────────────
        # Si viene de my-posts, regresa ahí. Si no, al detalle del post.
        # request.META.get('HTTP_REFERER') = la URL desde donde vino el clic
        next_url = request.POST.get('next', '')
        if 'my-posts' in next_url:
            return redirect('blog:my_posts')
        return redirect('blog:posts_detail', slug=post.slug)


# VISTAS PRIVADAS PARA CADA USUARIO

class MyPostsView(LoginRequiredMixin, ListView):
    """
    Lista los posts del usuario logueado.
    GET /blog/my-posts/
    """
    model = Post
    template_name = 'blog/my_posts.html'   # template que crearemos
    context_object_name = 'posts'           # nombre de la variable en el template
    paginate_by = 10                        # 10 posts por página
    login_url = 'users:login'               # si no está logueado, va aquí

    def get_queryset(self):
        # request.user = el usuario que está navegando ahora mismo
        # .posts = accedemos via related_name='posts' en el modelo Post
        # .all() = todos sus posts (borradores Y publicados)
        # .order_by('-created_at') = más recientes primero
        # Es como filtrar un cajón de cartas y sacar solo las tuyas
        return Post.objects.filter(
            author=self.request.user
        ).order_by('-created_at')

    def get_context_data(self, **kwargs):
        # super() trae el contexto base (la lista de posts, paginación, etc)
        # Luego le agregamos contadores extra para mostrar en el template
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Contar por separado publicados y borradores
        # Útil para mostrar "3 publicados / 1 borrador" en el template
        context['published_count'] = Post.objects.filter(
            author=user,
            status='published'
        ).count()

        context['drafts_count'] = Post.objects.filter(
            author=user,
            status='drafts'
        ).count()

        context['archived_count'] = Post.objects.filter(
            author=user,
            status='archived'
        ).count()

        # ── IDs archivables ────────────────────────────────────────
        # Como los templates no pueden llamar métodos con argumentos,
        # calculamos aquí qué posts puede archivar este usuario
        # y pasamos solo los IDs al template.

        context['archivable_ids'] = {
            post.pk
            for post in context['posts']          # solo los de esta página
            if post.can_be_archived_by(user)
        }
        return context


class MyCommentariesView(LoginRequiredMixin, ListView):
    """
    Lista los comentarios del usuario logueado.
    GET /blog/my-commentaries/
    """
    model = Commentary
    template_name = 'blog/my_commentaries.html'
    context_object_name = 'commentaries'
    paginate_by = 10
    login_url = 'users:login'

    def get_queryset(self):
        # request.user.commentaries = accedemos via related_name='commentaries'
        # definido en Commentary.author
        # select_related('post') = trae el post relacionado en la misma
        # consulta, evitando hacer una query extra por cada comentario
        # (Si tenemos 10 comentarios, sin esto harías 11 consultas a la BD)
        return Commentary.objects.select_related('post').filter(author=self.request.user)

    # Enviamos variables extra al template, para obtener conteos de comentarios
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Contamos los comentarios del usuario logueado
        context['commentaries_count'] = self.get_queryset().count()
        return context
    
# VISTA PARA ADMIN

class PostsPendingView(LoginRequiredMixin, ListView):
    """
    Vista de DASHBOARD para ADMIN ver posts pendientes.
    
    GET /blog/dashboard/pendientes/
    
    SOLO ADMIN puede ver esto (es quien aprueba posts).
    
    Muestra:
    - Lista de posts en BORRADOR (pendientes de aprobación)
    - Información del autor
    - Fecha de creación
    - Botón para revisar cada post
    - Estadísticas (total pendientes, aprobados hoy)
    """
    model = Post
    template_name = 'blog/dashboard/posts_pending.html'
    context_object_name = 'posts'
    paginate_by = 20
    login_url = 'users:login'
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.profile.is_admin:
            raise PermissionDenied('Solo ADMIN puede ver posts pendientes')
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        # Solo filtra, sin validaciones de permisos
        return Post.objects.filter(status='drafts').select_related('author', 'category').order_by('created_at')
    
    def get_context_data(self, **kwargs):
        """
        Agregar estadísticas al contexto del dashboard.
        El campo  que usaremos es 'published_at'.
        Al rechazar un post, vuelve a 'drafts' (ver ApprovePostView).
        """
        
        context = super().get_context_data(**kwargs)
        
        context['total_posts'] = {
            # Posts esperando revisión (borradores)
            'pending': Post.objects.filter(
                status='drafts'
            ).count(),
            
            # Posts aprobados hoy
            # published_at__date extrae solo la fecha (sin hora) para comparar
            'today_approved': Post.objects.filter(
                status='published',
                published_at__date=timezone.now().date()
            ).count(),
            
            # Total de posts publicados (aprobados histórico)
            'total_published': Post.objects.filter(
                status='published'
            ).count(),
        }
        
        return context
    
class ApprovePostView(LoginRequiredMixin, View):
    """
    Vista para ADMIN REVISAR un post y APROBAR o RECHAZAR.
    
    GET /blog/post/<id>/aprobar/ → Mostrar post + formulario
    POST /blog/post/<id>/aprobar/ → Procesar decisión
    
    SOLO ADMIN (quien aprueba posts).
    
    Flujo:
    1. ADMIN ve post completo
    2. Revisa contenido, categoría, imagen, etc
    3. Decide: APROBAR o RECHAZAR
    4. Si aprueba:
       ├─ estado = 'published'
       ├─ aprobado_por = admin (quien aprobó)
       ├─ fecha_aprobacion = ahora
       ├─ fecha_publicacion = ahora
       └─ Post es VISIBLE para todos
    5. Si rechaza:
       ├─ estado = 'drafts'
       ├─ motivo_rechazo = feedback
       ├─ aprobado_por = admin
       ├─ fecha_aprobacion = ahora
       └─ Email a autor con motivo
    """

    login_url = 'users:login'
    template_name = 'blog/dashboard/approve_posts.html'

    def dispatch(self, request, *args, **kwargs):
        """Validaremos permisos antes de cualquier acción"""
        if not request.user.profile.is_admin:
            raise PermissionDenied('Solo ADMIN puede aprobar posts')
        return super().dispatch(request, *args, **kwargs)
    
    def get(self, request, post_id):
        """GET: Mostrar post + formulario de aprobación"""
        # Obtener post
        post = get_object_or_404(Post, id=post_id)

        # Validar que es ADMIN
        if not request.user.profile.is_admin:
            raise PermissionDenied('Solo ADMIN puede aprobar posts')
        # Validar que está en BORRADOR (no procesado)
        if post.status != 'drafts':
            messages.error(request, 'Este post ya fue procesado')
            return redirect('blog:posts_pending')
        
        # Mostrar formulario
        form = ApprovePostForm()
        
        context = {
            'post': post,
            'form': form,
        }
        
        return render(request, self.template_name, context)
    
    def post(self, request, post_id):
        """POST: Procesar decisión (aprobar o rechazar)"""
        
        post = get_object_or_404(Post, id=post_id)
        
        # Validar permisos
        if not request.user.profile.is_admin:
            raise PermissionDenied('Solo ADMIN puede aprobar')
        
        # Procesar formulario
        form = ApprovePostForm(request.POST)
        
        if form.is_valid():
            decision = form.cleaned_data['decision']
            
            if decision == 'approve':
                # APROBAR: Post pasa a PUBLICADO
                # status='published' = el único estado de "aprobado" que tenemos
                post.status = 'published'
                post.published_at = timezone.now()
                post.save(update_fields=['status', 'published_at'])
                _send_post_approved_email(post)  # LLamar al metodo que maneja los email
                messages.success(request, f'✅ Post "{post.title}" aprobado y publicado')
                
            
            elif decision == 'rejected':
                # RECHAZAR: Post pasa a RECHAZADO
                # La alternativa es volver a 'drafts' (borrador)
                # Así el autor puede editarlo y volver a enviarlo
                reason = form.cleaned_data['rejected_reason']
                
                post.status = 'drafts'
                post.published_at = None
                post.save(update_fields=['status', 'published_at'])
                _send_post_rejected_email(post, reason)   # LLamar al metodo que maneja los email
                messages.warning(request, f'Post "{post.title}" rechazado. Autor notificado')
                
            
            # Redirigir a dashboard de pendientes
            return redirect('blog:posts_pending')
        
        # Si form no es válido, re-renderizar con errores
        context = {'post': post, 'form': form}
        return render(request, self.template_name, context)
    
# VISTAS PARA LOS COMENTARIOS


class CommentaryPermissionMixin:
    """
    Mixin reutilizable para verificar permisos sobre comentarios.
    Usaremos un mismo acceso y sistema de seguridad para todos los views
    de comentarios. Si no existe el permiso obtienes
    un error 403 (Forbidden) en vez de un redirect raro.
    """

    def get_commentary_or_403(self, pk, action='edit'):
        """
        Obtenemos el comentario y verificamos permisos.
        - action='edit'   → solo el autor puede
        - action='delete' → autor, admin o moderador pueden
        """
        # Traemos el comentario. Si no existe → 404 automático
        commentary = get_object_or_404(Commentary, pk=pk)

        user_profile = self.request.user.profile

        if action == 'edit':
            # Usamos los metodos del user models
            has_permission = user_profile.can_edit_commentary(commentary)
        else:  # delete
            has_permission = user_profile.can_delete_commentary(commentary)

        # Si no tiene permiso → error 403 (Forbidden)
        # Analogía: intentar entrar a una habitación con llave equivocada
        if not has_permission:
            raise PermissionDenied

        return commentary
    
# VISTA PARA AGREGAR COMENTARIOS

class AddCommentaryView(LoginRequiredMixin,View):
    """
    Vista para agregar comentario.
    
    POST /blog/<slug>/comentar/ → Crear comentario
    
    Características:
    - Solo usuarios autenticados
    - Validar que el post permita comentarios
    - Si es admin, auto-aprobar
    - Si es usuario, requiere aprobación
    """
    login_url = 'users:login'

    def post(self,request,slug):
        """procesar nuevo comentario"""

        # Obtener el post
        post = get_object_or_404(Post, slug=slug)

        if not post.commentaries_permission:
            messages.error(request, 'Los comentarios están deshabilitados')
            return redirect('blog:posts_detail', slug=post.slug)
        # Procesar formulario
        form = CommentaryForm(request.POST)

        if form.is_valid():
            # Crear comentario
            commentary = form.save(commit = False)
            commentary.post = post
            commentary.author = request.user

            # Auto aprobar si es admin
            # is admin sin parentesis gracias al @property
            commentary.aprobated = request.user.profile.is_admin
            
            # Detectar si es una respuesta ──────────────────
            # El template enviará un campo oculto 'response_to' con el
            # id del comentario padre. Si no viene, es None (comentario normal).
            # Analogía: es como el "re:" en un email — si tiene referencia
            # es una respuesta, si no, es un mensaje nuevo.
            response_to_id = request.POST.get('response_to')

            if response_to_id:
                # Verificamos que el comentario padre exista y pertenezca
                # al mismo post — evita que alguien manipule el form
                # y responda a un comentario de otro post
                parent = get_object_or_404(
                    Commentary,
                    pk=response_to_id,
                    post=post          # ← seguridad: mismo post
                )

                # Solo se puede responder a comentarios de nivel 0
                # (sin padre). Esto garantiza 1 solo nivel de anidamiento.
                # Si el padre ya tiene response_to, rechazamos.
                if parent.response_to is not None:
                    messages.error(
                        request,
                        'No se puede responder a una respuesta'
                    )
                    return redirect('blog:posts_detail', slug=post.slug)

                commentary.response_to = parent

            # Guardar
            commentary.save()

            # Mensaje
            if commentary.aprobated:
                messages.success(request, '✓ Comentario publicado')
            else:
                messages.success(
                    request,'Tu comentario sera revisado pronto'
                )
        else:
            # Errores
            for field,errors in form.errors.items():
                for error in errors:
                    messages.error(request, error)

        # Redirigir al post
        return redirect('blog:posts_detail', slug=post.slug)

# VISTAS PARA APROBACION DE COMENTARIOS

class ApproveCommentaryView(LoginRequiredMixin,View):
    """
    Vista para que admin/moderador REVISE un comentario pendiente.

    Patrón idéntico a ApprovePostView:
    GET  /blog/comment/<id>/revisar/ → muestra el comentario + formulario
    POST /blog/comment/<id>/revisar/ → procesa la decisión

    Flujo:
    1. Moderador hace clic en 'Revisar' desde el dashboard
    2. Ve el comentario completo con contexto (autor, post, fecha)
    3. Decide: APROBAR o ELIMINAR
    4. Regresa al dashboard con mensaje de confirmación
    """

    login_url ='users:login'
    template_name = 'blog/dashboard/approve_commentaries.html'

    def dispatch(self, request, *args, **kwargs):
        """
        dispatch() se ejecuta ANTES que get() o post().
        Es la primera puerta de seguridad — igual que en ApprovePostView.
        """
        if not request.user.profile.can_moderate:
            raise PermissionDenied('Solo admin o moderador puede revisar comentarios')
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, commentary_id):
        """Muestra el comentario completo + formulario de decisión"""

        commentary = get_object_or_404(Commentary, id=commentary_id)

        # Solo tiene sentido revisar comentarios pendientes
        # Si ya fue aprobado, no hay nada que revisar
        if commentary.aprobated:
            messages.error(request, 'Este comentario ya fue aprobado')
            return redirect('blog:commentaries_pending')

        form = ApproveCommentaryForm()

        return render(request, self.template_name, {
            'commentary': commentary,
            'post': commentary.post,
            'form': form,
        })

    def post(self, request, commentary_id):
        """Procesa la decisión del moderador"""

        commentary = get_object_or_404(Commentary, id=commentary_id)
        form = ApproveCommentaryForm(request.POST)

        if form.is_valid():
            decision = form.cleaned_data['decision']

            if decision == 'approve':
                # APROBAR: el comentario se vuelve visible para todos
                commentary.aprobated = True
                commentary.save()
                messages.success(
                    request,
                    f'✓ Comentario de {commentary.get_name_author()} aprobado'
                )

            elif decision == 'delete':
                # ELIMINAR: borramos el comentario directamente
                # A diferencia de posts, no tiene sentido "devolver" un
                # comentario al autor para que lo corrija
                author_name = commentary.get_name_author()
                commentary.delete()
                messages.warning(
                    request,
                    f'Comentario de {author_name} eliminado'
                )

            return redirect('blog:commentaries_pending')

        # Si el form no es válido, re-renderizar con errores
        # (igual que ApprovePostView)
        return render(request, self.template_name, {
            'commentary': commentary,
            'post': commentary.post,
            'form': form,
        })

# VISTA PARA APROBACION DE COMENTARIOS

class CommentariesPendingView(LoginRequiredMixin, View):
    """
    Dashboard para ver y aprobar todos los comentarios pendientes.
    Solo accesible para admin o moderadores.
    """
    login_url = 'users:login'

    def get(self, request):

        if not request.user.profile.can_moderate:
            raise PermissionDenied

        # Traemos comentarios pendientes, del más antiguo al más nuevo
        # (el más antiguo lleva más tiempo esperando — fair queue)
        pending = Commentary.objects.filter(
            aprobated=False
        ).select_related(
            'author',       # evita N+1 queries al mostrar el nombre del autor
            'post',         # evita N+1 queries al mostrar el título del post
            'author__profile',
            'response_to',           # Traer el comentario padre si existe
            'response_to__author',   # y su autor, para mostrarlo en tabla
        ).order_by('created_at')

        return render(request, 'blog/dashboard/commentaries_pending.html', {
            'pending_commentaries': pending,
            'total_pending': pending.count(),
        })
    
# VISTA PARA EDICION Y ELIMINACION DE COMENTARIO
    
class EditCommentaryView(LoginRequiredMixin,CommentaryPermissionMixin,View):
    
    """
    Vista para editar un comentario.

    Hereda de 3 clases (analogía: un chef con 3 certificaciones):
    - LoginRequiredMixin  → certifica que el usuario está logueado
    - CommentaryPermissionMixin → certifica que tiene permiso
    - View               → es una vista de Django
    """
    login_url = 'users:login'

    def get(self, request, slug, pk):
        """Muestra el formulario con el comentario ya rellenado"""

        # get_commentary_or_403 viene del Mixin que creamos arriba
        # Si no tiene permiso, lanza 403 automáticamente
        commentary = self.get_commentary_or_403(pk, action='edit')

        # Prellenamos el form con los datos actuales del comentario
        # Analogía: abrir un documento Word ya escrito para modificarlo
        form = CommentaryForm(instance=commentary)

        return render(request, 'blog/commentaries/edit_commentary.html', {
            'form': form,
            'commentary': commentary,
            'post': commentary.post,
        })

    def post(self, request, slug, pk):
        """Procesa el formulario con los cambios"""

        commentary = self.get_commentary_or_403(pk, action='edit')

        # instance=commentary le dice a Django: "actualiza ESTE objeto,
        # no crees uno nuevo" — sin instance crearía un comentario duplicado
        form = CommentaryForm(request.POST, instance=commentary)

        if form.is_valid():
            edited = form.save(commit=False)

            # Marcamos que fue editado (tienes este campo en el modelo)
            edited.was_edited = True

            # Si el usuario no es admin, el comentario vuelve a moderación
            # Analogía: si reescribes una carta, debe ser revisada de nuevo
            # is admin sin parentesis gracias al @property
            #if not request.user.profile.is_admin:
            #    edited.aprobated = False

            edited.save()

            messages.success(request, '✓ Comentario actualizado')
            # USAR EL SLUG REAL DEL COMENTARIO (FIX CLAVE)
            return redirect('blog:posts_detail', slug=commentary.post.slug)
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, error)

            # En caso de error, también redirige correctamente
            return redirect('blog:posts_detail', slug=commentary.post.slug) 

class DeleteCommentaryView(LoginRequiredMixin,CommentaryPermissionMixin,View):
    """
    Vista para eliminar comentario.
    
    POST /blog/comentario/<id>/eliminar/
    
    Puede eliminar:
    - El autor del comentario
    - El autor del post
    - Admin
    - Mod
    """

    login_url = 'users:login'

    def get(self, request, slug, pk):
        """Muestra pantalla de confirmación antes de eliminar"""

        # action='delete' permite que admin/mod también puedan
        commentary = self.get_commentary_or_403(pk, action='delete')

        return render(request, 'blog/commentaries/delete_commentary.html', {
            'commentary': commentary,
            'post': commentary.post,
        })
    
    def post(self, request, slug, pk):
        """Ejecuta la eliminación después de confirmar"""

        commentary = self.get_commentary_or_403(pk, action='delete')

        # Guardamos el post para redirigir después de borrar
        # (después de borrar el comentario ya no podemos acceder a commentary.post)
        post_slug = commentary.post.slug

        commentary.delete()
        messages.success(request, '✓ Comentario eliminado')

        return redirect('blog:posts_detail', slug=post_slug)
