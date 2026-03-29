from django.db import models
from django.contrib.auth.models import User
from apps.users.models import ProfileUser
from django.utils.text import slugify
from django.core.exceptions import ValidationError
from django.utils import timezone

class Category(models.Model):
    """Categorías para posts"""
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(max_length=500, blank=True)
    icon = models.CharField(max_length=50, blank=True)
    order = models.PositiveIntegerField(default=0)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)   

    class Meta:
        verbose_name = 'Categoria'
        verbose_name_plural = 'Categorias'
        ordering = ['order', 'name'] # Estos datos que ingrean a la tabla tendran la prioridad
                                     # De ser ordenados primero por orden y luego nombre
        indexes = [models.Index(fields=['slug'])]

    def __str__(self):
        # Retorna icono + nombre si hay icono, solo nombre si no hay
        return f"{self.icon}{self.name}" if self.icon else self.name

    def __repr__(self):
        # Delega al __repr__ por defecto de Django
        return super().__repr__()

    def get_posts_published(self):
        # Accede a los posts via related_name='posts' definido en Post.category
        return self.posts.filter(status='published').count()
        
        # Retorna el total de post por categoria, publicados, borradores y archivados
    def get_posts_total(self):
        return self.posts.count()


class PostQuerySet(models.QuerySet):
    """QuerySet customizado para los Post"""

    def published(self):
        # Filtra solo posts con estado 'published'
        return self.filter(status='published')

    def drafts(self):
        # Filtra solo posts con estado 'drafts'
        return self.filter(status='drafts')

    def recently_order(self):
        # Ordena por fecha de publicación, más reciente primero
        return self.order_by('-published_at')

    def order_popular(self):
        # Ordena por cantidad de vistas, más visto primero
        return self.order_by('-count_views')

    def from_author(self, user):
        # Filtra posts de un autor específico
        return self.filter(author=user)

    def with_prefetch(self):
        # Optimiza consultas trayendo relaciones en una sola query (evita N+1)
        return self.select_related(
            'author__profile',
            'category'
        # Aca usamos prefecth porque traemos uno o muchos comentarios
        # En otras relaciones como post a autor usaremos select por que traemos datos de uno a uno o muchos a uno
        ).prefetch_related('commentaries')


class PostManager(models.Manager):
    """Manager customizado para Post"""

    def get_queryset(self):
        # Instancia PostQuerySet para acceder a sus métodos desde el manager
        return PostQuerySet(self.model, using=self._db)

    def published(self):
        # Retorna todos los posts publicados
        return self.get_queryset().published()

    def popular(self):
        # Retorna los 10 posts más vistos entre los publicados
        return self.published().order_popular()[:10]

    def recently(self):
        # Retorna los 10 posts más recientes entre los publicados
        return self.published().recently_order()[:10]


class Post(models.Model):
    """Modelo principal de posts"""
    STATUS_CHOICES = [
        ('drafts', 'Drafts'),
        ('published', 'Published'),
        ('archived', 'Archived')
    ]

    # RELATIONS
    # ForeignKey trae el ID del User como llave foránea
    # DIRECCIÓN INVERSA (related_name): Desde User hacia Posts
    # "¿Qué posts escribió este usuario?"
    # user.posts.all()  Vas de User → todos sus Posts
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts')
    # null=True permite posts sin categoría asignada
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='posts', blank=True, null=True)

    # CONTENT
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    content = models.TextField()
    summary = models.CharField(max_length=200, blank=True)
    featured_image = models.ImageField(upload_to='posts/%Y/%m/', blank=True, null=True)

    # SEO
    seo_description = models.CharField(max_length=200, blank=True)
    seo_keywords = models.CharField(max_length=200, blank=True)

    # STATUS
    status = models.CharField(max_length=200, choices=STATUS_CHOICES, default='drafts')
    commentaries_permission = models.BooleanField(default=True)
    

    # STATISTICS
    count_views = models.PositiveIntegerField(default=0)
    count_commentaries = models.PositiveIntegerField(default=0, db_index=True)

    # DATES
    created_at = models.DateTimeField(auto_now_add=True)   # solo se guarda al crear
    updated_at = models.DateTimeField(auto_now=True)        # se actualiza en cada save
    published_at = models.DateTimeField(null=True, blank=True, db_index=True)

    # NUEVO CAMPO AGREGADO PARA SABER QUE ROL TIENE EL QUE ARCHIVA UN POST
    # Guarda el ROL de quien archivó, no quién fue.
    # Analogía: el sello dice "ARCHIVADO POR: MODERADOR", no el nombre de la persona.
    # Así la jerarquía funciona aunque el usuario cambie de rol después.
    archived_by_role= models.CharField(max_length=20,blank=True,default='',choices=ProfileUser.ROLE_CHOICES) # 'user', 'mod', 'admin

    objects = PostManager()  # reemplaza el manager por defecto de Django

    class Meta:
        verbose_name = 'Post'
        verbose_name_plural = 'Posts'
        ordering = ['-published_at', '-created_at']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['status', '-published_at']),
            models.Index(fields=['author']),
            models.Index(fields=['category']),
            models.Index(fields=['-count_views']),
        ]

    def __str__(self):
        # get_status_display() retorna el label legible del choices, ej: 'Published'
        return f"{self.title} ({self.get_status_display()})"

    def save(self, *args, **kwargs):
        # Genera el slug automáticamente si no existe
        if not self.slug:
            # Paso 1: convertir título a slug base
            base_slug = slugify(self.title)
            slug = base_slug

            # Paso 2: verificar si ese slug ya existe en BD
            # Usamos un contador para agregar un número al final si hay duplicado
            # Es como cuando guardas "documento.pdf" y ya existe,
            # el sistema lo llama "documento-1.pdf", "documento-2.pdf", etc.
            counter = 1
            while Post.objects.filter(slug=slug).exists():
                # Si ya existe, agregar número al final
                slug = f"{base_slug}-{counter}"
                counter += 1
            
            # Paso 3: asignar el slug único encontrado
            self.slug = slug

        # Asignar fecha de publicación la primera vez que se publica
        if self.status == 'published' and not self.published_at:
            self.published_at = timezone.now()

        super().save(*args, **kwargs)

    # METHODS
    def increase_views(self):
        from django.db.models import F
        # F() incrementa el valor directamente en BD, evita condiciones de carrera
        self.__class__.objects.filter(pk=self.pk).update(count_views=F('count_views') + 1)
        # Recarga el objeto para reflejar el nuevo valor en memoria
        self.refresh_from_db()

    def update_count_commentaries(self):
        # Cuenta comentarios aprobados y actualiza el campo en BD directamente
        count = self.commentaries.filter(aprobated=True).count()
        self.__class__.objects.filter(pk=self.pk).update(count_commentaries=count)

    def get_aprobated_commentaries(self):
        # select_related evita N+1 al traer el autor en la misma consulta
        return self.commentaries.filter(aprobated=True).select_related('author').order_by('-created_at')

    def can_be_edited_by(self, user):
        # Verifica autenticación antes de comparar identidad
        if not user or not user.is_authenticated:
            return False
        # Permite editar al autor del post o a un administrador
        return user == self.author or user.profile.is_admin

    def can_be_deleted_by(self, user):
        # Reutiliza la misma lógica de edición para eliminar
        return self.can_be_edited_by(user)

    def is_published(self):
        return self.status == 'published'

    def is_draft(self):
        return self.status == 'drafts'
    
    def is_archived(self):
        return self.status == 'archived'
    
    # Un admin archiva o desarchiva todo
    # Un mod archiva o desarchiva todo menos los post del admin
    # Un usuario solo archiva o desarchvia sus posts
    # Los visitantes no tienen permiso para esta accion

    def can_be_archived_by(self,user):
        if not user or not user.is_authenticated:
            return False
        profile = user.profile

        # ── Caso 1: archivar (post no está archivado aún) ─────────────
        if self.status != 'archived':
            is_author = user == self.author
            is_admin = profile.is_admin
            # Moderador puede excepto borrar posts del Admin
            is_mod_allowed = profile.can_moderate and not self.author.profile.is_admin
            return is_author or is_admin or is_mod_allowed
        """
        Se aprecia el uso del IF y no el ELIF
        Elif es de gran ayuda para evaluar un caso y si lo cumple sale del condicional
        En este caso usamos un IF con return, esto hace lo mismo que un ELIF
        Asi que usar(ELIF) no nos brinda ninguna ventaja y para mejor lectura del
        codigo, usaremos IF
        """
        # ── Caso 2: desarchivar (leemos el rol guardado) ───────────────
        # Analogía: para borrar un sello de "ARCHIVADO POR: ADMIN"
        # necesitas ser al menos admin.
        role = self.archived_by_role  # 'admin', 'mod', 'user' o ''

        if role == 'admin':
            return profile.is_admin                  # solo admin

        if role == 'mod':
            return profile.can_moderate            
            # mod o admin, no el autor
        if role == 'user':
            # Solo el autor puede, o un mod/admin
            return user == self.author or profile.can_moderate

        # Si archived_by_role está vacío (''),
        # asumimos que fue archivado por moderación (caso conservador).
        # Es mejor bloquear por error que dejar pasar por error.
        # Analogía: si no sabes quién puso el candado, no lo abras.
        return profile.can_moderate


class Commentary(models.Model):
    """Modelo de comentarios"""

    # RELATIONS
    # Cada comentario pertenece a un post y a un autor
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='commentaries')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='commentaries')
    # Autorreferencia: permite responder a otro comentario (hilo de respuestas)
    response_to = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='responses')

    # CONTENT
    content = models.TextField()
    aprobated = models.BooleanField(default=False, db_index=True)
    was_edited = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)  # corregido: auto_now + nombre correcto

    class Meta:
        verbose_name = 'Comentario'
        verbose_name_plural = 'Comentarios'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['post', 'aprobated']),
            models.Index(fields=['author']),
            models.Index(fields=['aprobated', '-created_at']),
        ]

    def __str__(self):
        # Muestra preview de 50 chars con '...' si el contenido es más largo
        preview = self.content[:50] + '...' if len(self.content) > 50 else self.content
        return f"Comentario de {self.author.username}: {preview}"

    def save(self, *args, **kwargs):
        # Valida el comentario antes de guardarlo
        self.full_clean()
        super().save(*args, **kwargs)
        # Actualiza el contador de comentarios del post tras cada guardado
        self.post.update_count_commentaries()

    def clean(self):
        # Valida longitud mínima eliminando espacios vacíos
        if len(self.content.strip()) < 5:
            raise ValidationError('El comentario debe tener al menos 5 caracteres')
        if len(self.content) > 1000:
            raise ValidationError('El comentario no puede exceder 1000 caracteres')
        # Verifica que el post permita comentarios
        # Mas eficiente que "if self.post" (no hace query a BD)
        if self.post_id:
            if not self.post.commentaries_permission:
                raise ValidationError('Este post no permite comentarios')
            # Los posts archivados no aceptan comentarios
            if self.post.status == 'archived':
                raise ValidationError('No se pueden comentar en posts archivados')

    # METHODS
    def can_be_edited_by(self, user):
        if not user or not user.is_authenticated:
            return False
        return (
            user == self.author or       # el autor del comentario
            user == self.post.author or  # el autor del post
            user.profile.is_admin      # o un administrador
        )

    def can_be_eliminated_by(self, user):
        # Misma lógica que edición para eliminación
        if not user or not user.is_authenticated:
            return False
        return (
            user == self.author or
            user == self.post.author or
            user.profile.is_admin
        )

    def get_response(self):
        # 'responses' es el related_name de response_to, trae las respuestas aprobadas
        return self.responses.filter(aprobated=True).select_related('author')

    def get_name_author(self):
        # get_full_name() es método nativo de User, retorna nombre completo o username si está vacío
        return self.author.get_full_name() or self.author.username