from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.core.exceptions import ValidationError
from django.utils import timezone

class Category(models.Model):
    """Categorías para posts"""
    name = models.CharField(max_length=100, unique= True)
    slug = models.SlugField(max_length=100, unique= True)
    description = models.TextField(max_length=500, blank = True)
    icon = models.CharField(max_length= 50, blank= True)
    order = models.PositiveIntegerField(default=0)
    active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now_add= True)

    class Meta:
        verbose_name = 'Categoria'
        verbose_name_plural = 'Categorias'
        ordering = ['order','name']
        indexes = [models.Index(fields=['slug'])]
    def __str__(self):
        return f"{self.icon}{self.name}" if self.icon else self.name
    # Si existe icono y nombre, retornara ambos, sin embargo si no hay icono solo retornanara nombre
    def __repr__(self):
        return super().__repr__()
    def get_posts_published(self):
        return self.posts.filter(status = 'published').count()

class PostQuerySet(models.QuerySet):
    """QuerySet customizado para los Post"""
    def published(self):
        # Retorna los posts que pasan el filtro de publicados
        return self.filter(status = 'published')
    def drafts(self):
        # Retorna los posts que pasan el filtro de escritos pero no publicados
        return self.filter(status = 'drafts')
    def recently_order(self):
        # Retorna los posts que fueron publicados ordenandolos por fecha de publicacion
        return self.order_by('-published_at')
    def order_popular(self):
        return self.order_by('-count_views') 
    def from_author(self,user):
        return self.filter(author = user)
    def with_prefetch(self):
        return self.select_related(
            'author',
            'author_profile',
            'category'
        ).prefetch_related('commentaries')

class PostManager(models.Manager):
    """Manager customizado para Post"""
    def get_queryset(self):
        # Retorna un objeto instanciado de PostQuerySet
        # A diferencia de la clase anterior que usa herencia, esta usa instancia
        return PostQuerySet(self.model, using=self._db) # ← retorna un PostQuerySet
    def published(self):
        return self.get_queryset().published()
    def popular(self):
        return self.published().order_popular()[:10]
    def recently(self):
        return self.published().recently_order()[:10]

class Post(models.Model):
    """Modelo principal de posts"""
    STATUS_CHOICES = [
        ('drafts','Drafts'),
        ('published','Published'),
        ('archived','Archived')
    ]
    # RELATIONS
    # El campo se llama author pero es la llave foranea que llega desde User, del campo ID
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts')
    category = models.ForeignKey(Category, on_delete= models.CASCADE, related_name= 'posts', blank= True, null= True)
    
    # CONTENT
    title = models.CharField(max_length = 200)
    slug = models.SlugField(max_length = 200, unique= True)
    content = models.TextField()
    summary = models.CharField(max_length=200, blank= True)
    featured_image = models.ImageField(upload_to='posts/%Y/%m/', blank=True, null=True)

    #SEO
    seo_description = models.CharField(max_length= 200, blank= True)
    seo_keywords = models.CharField(max_length= 200, blank= True)

    #STATUS
    status = models.CharField(
        max_length= 200,
        choices= STATUS_CHOICES,
        default= 'drafts'
    )
    commentaries_permission = models.BooleanField(default=True)
    
    #STATISTICS
    count_views = models.PositiveIntegerField(default=0)
    count_commentaries = models.PositiveIntegerField(default=0, db_index= True)

    #DATES
    created_at = models.DateTimeField(auto_now_add= True)
    updated_at = models.DateTimeField(auto_now_add= True)
    published_at = models.DateTimeField(null= True, blank= True, db_index= True)

    objects = PostManager()

    class Meta:
        verbose_name = 'Post'
        verbose_name_plural = 'Posts'
        ordering = ['-published_at','-created_at']
        indexes = [
            models.Index(fields = ['slug']),
            models.Index(fields = ['status', '-published_at']),
            models.Index(fields=['author']),
            models.Index(fields=['category']),
            models.Index(fields=['-count_views']),
        ]
    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"
    def save(self,*args,**kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        if self.status == 'published' and not self.published_at:
            self.published_at = timezone.now()
        super().save(*args,**kwargs)