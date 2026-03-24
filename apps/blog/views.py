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
from .models import Post,Commentary,Category
from .forms import PostForm, ApprovePostForm

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
            # Gracia a esto traemos el autor del post Y su perfil en la misma query
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
            if self.request.user != obj.author and not self.request.user.profile.is_admin():
                raise Http404('Post no encontrado')
        
        return obj
    
    def get_context_data(self, **kwargs):
        """Agregar comentarios y formulario al contexto"""
        context = super().get_context_data(**kwargs)
        
        post = self.object
        
        # INCREMENTAR VISTAS
        post.increase_views()
        # atomic() = operación safe (evita race conditions)
        
        # COMENTARIOS APROBADOS
        context['commentaries'] = post.get_aprobated_commentaries()
        
        # FORMULARIO DE COMENTARIO (si está logueado)
        # if self.request.user.is_authenticated:
        #    context['commentary_form'] = ComentaryForm()
        
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
        if self.request.user.profile.is_admin():
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
        if not self.request.user.profile.can_moderate():
            queryset = queryset.filter(author=self.request.user)

        # Si ES moderador/admin: ver todos (sin filtro adicional)
        return queryset
    
    def form_valid(self, form):
        """Actualizar post cuando form es válido"""
        
        #post = form.save(commit=False)
        
        # LÓGICA: Si cambió de borrador a publicado, establecer fecha
        #if form.cleaned_data['status'] == 'published' and not post.published_at:
        #    post.published_at = timezone.now()
        
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
        if not self.request.user.profile.can_moderate():
            queryset = queryset.filter(author=self.request.user)

        # Si ES moderador/admin: ver todos (sin filtro adicional
        return queryset
    
    def delete(self, request, *args, **kwargs):
        """Override para mostrar mensaje antes de eliminar"""
        messages.success(request, '✓ Post eliminado')
        return super().delete(request, *args, **kwargs)


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

        # Contar por separado publicados y borradores
        # Útil para mostrar "3 publicados / 1 borrador" en el template
        context['published_count'] = Post.objects.filter(
            author=self.request.user,
            status='published'
        ).count()

        context['drafts_count'] = Post.objects.filter(
            author=self.request.user,
            status='drafts'
        ).count()

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
        return Commentary.objects.filter(
            author=self.request.user
        ).select_related('post').order_by('-created_at')

# VISTA PARA ADMIN

class PostsPendientesView(LoginRequiredMixin, ListView):
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
    
    def get_queryset(self):
        """
        SEGURIDAD: Solo ADMIN puede acceder.
        
        Retorna posts en estado BORRADOR (pendientes de revisión).
        select_related('author', 'category') evita N+1 queries:
        sin esto, Django haría una consulta extra por cada post
        para traer el autor y la categoría.
        """
        
        # Validar que es ADMIN (no moderador, no usuario regular)
        if not self.request.user.profile.is_admin():
            raise PermissionDenied('Solo ADMIN puede ver posts pendientes')
        
        # Posts en BORRADOR ordenados por más antiguos primero
        # (los que llevan más tiempo esperando revisión)
        return Post.objects.filter(
            status='drafts'
        ).select_related('author', 'category').order_by('created_at')
    
    def get_context_data(self, **kwargs):
        """
        Agregar estadísticas al contexto del dashboard.
        El campo  que usaremos es 'published_at'.
        'rejected': usaba status='rejected' que no existe en STATUS_CHOICES.
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
       ├─ estado = 'rejected'
       ├─ motivo_rechazo = feedback
       ├─ aprobado_por = admin
       ├─ fecha_aprobacion = ahora
       └─ Email a autor con motivo
    """

    login_url = 'users:login'
    template_name = 'blog/dashboard/approve_posts.html'

    def get(self, request, post_id):
        """GET: Mostrar post + formulario de aprobación"""
        # Obtener post
        post = get_object_or_404(Post, id=post_id)

        # Validar que es ADMIN
        if not request.user.profile.is_admin():
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
        if not request.user.profile.is_admin():
            raise PermissionDenied('Solo ADMIN puede aprobar')
        
        # Procesar formulario
        form = ApprovePostForm(request.POST)
        
        if form.is_valid():
            decision = form.cleaned_data['decision']
            
            if decision == 'approve':
                # ✅ APROBAR: Post pasa a PUBLICADO
                # status='published' = el único estado de "aprobado" que tenemos
                post.status = 'published'
                post.published_at = timezone.now()
                post.save()
                
                # Enviar email al autor notificando aprobación
                
                messages.success(
                    request,
                    f'✅ Post "{post.title}" ha sido APROBADO y publicado'
                )
            
            elif decision == 'rejected':
                # RECHAZAR: Post pasa a RECHAZADO
                # La alternativa es volver a 'drafts' (borrador)
                # Así el autor puede editarlo y volver a enviarlo
                reason = form.cleaned_data['rejected_reason']
                
                post.status = 'drafts'
                post.published_at = None
                post.save()
                
                # Enviar email al autor con feedback/motivo
                
                messages.warning(
                    request,
                    f'Post "{post.title}" ha sido RECHAZADO. Autor notificado'
                )
            
            # Redirigir a dashboard de pendientes
            return redirect('blog:posts_pending')
        
        # Si form no es válido, re-renderizar con errores
        context = {'post': post, 'form': form}
        return render(request, self.template_name, context)