from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from .models import*




@admin.register(Category) # Igual a usar admin.site.register(Category,CategoryAdmin)
class CategoryAdmin(admin.ModelAdmin):
    """Admin para Categorías"""
    
    # Columnas a mostrar
    # Haremos referencia del metodo get_posts_published que tiene Category
    # Este justamente esta construido en el Model
    list_display = ['name','active','get_posts_published','get_posts_total','order']
    
    # Filtros laterales
    list_filter = ['active', 'created_at']
    
    # Buscar en estos campos
    search_fields = ['name', 'description']
    
    # Campos edit
    fields = ['name', 'slug', 'description', 'icon', 'order', 'active']
    
    # Auto-generar slug
    prepopulated_fields = {'slug': ('name',)}
    
    def posts_count(self, obj):
        """Mostrar número de posts con color"""
        count = obj.posts.filter(status='published').count()
        return format_html(
            '<span style="background: #4CAF50; color: white; padding: 3px 8px; border-radius: 3px;"><b>{}</b></span>',
            count
        )
    posts_count.short_description = 'Posts Publicados'


# ============ ADMIN COMENTARIOS (INLINE) ============

class ComentaryInline(admin.TabularInline):
    """
    Inline para ver comentarios dentro del admin de Post.
    
    Permite ver/aprobar comentarios sin ir a otra página.
    """
    
    model = Commentary
    extra = 0  # No mostrar filas vacías
    fields = ['author', 'content_preview', 'aprobated', 'created_at']
    readonly_fields = ['author', 'content_preview', 'created_at']
    can_delete = True
    
    def content_preview(self, obj):
        """Mostrar preview del contenido"""
        preview = obj.content[:100]
        if len(obj.content) > 100:
            preview += '...'
        return preview
    content_preview.short_description = 'Contenido'

    # ============ ADMIN POSTS ============

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    """Admin para Posts"""
    
    # Columnas a mostrar en lista
    list_display = [
        'title',
        'author_link',
        'status_badge',
        'count_views',
        'commentaries_count_display',
        'published_at',
    ]
    
    # Filtros laterales
    list_filter = ['status', 'category', 'created_at', 'commentaries_permission']
    
    # Búsqueda
    search_fields = ['title', 'content', 'author__username']
    
    # Timeline by date
    date_hierarchy = 'published_at'
    
    # Orden por defecto
    ordering = ['-published_at']
    
    # Secciones de edición
    fieldsets = (
        ('Información Básica', {
            'fields': ('title', 'slug', 'author', 'category')
        }),
        ('Contenido', {
            'fields': ('content', 'summary', 'featured_image', 'image_preview')
        }),
        ('SEO', {
            'fields': ('seo_description', 'seo_keywords'),
            'classes': ('collapse',)  # Colapsable
        }),
        ('Publicación', {
            'fields': ('status', 'commentaries_permission')
        }),
        ('Estadísticas', {
            'fields': ('count_views', 'count_commentaries'),
            'classes': ('collapse',)
        }),
        ('Fechas', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
            'description': 'Campos de solo lectura'
        }),
    )
    
    # Solo lectura
    readonly_fields = [
        'count_views', 'count_commentaries',
        'created_at', 'updated_at', 'image_preview'
    ]
    
    # Auto-slug
    prepopulated_fields = {'slug': ('title',)}
    
    # Inline de comentarios
    inlines = [ComentaryInline]
    
    # Métodos para columnas
    
    def author_link(self, obj):
        """Mostrar autor como enlace"""
        url = reverse('admin:auth_user_change', args=[obj.author.id])
        return format_html('<a href="{}">{}</a>', url, obj.author.username)
    author_link.short_description = 'Autor'
    
    def status_badge(self, obj):
        """Mostrar estado con color"""
        colors = {
            'drafts': '#FF9800',
            'published': '#4CAF50',
            'archived': '#9E9E9E'
        }
        color = colors.get(obj.status, '#999')
        return format_html(
            '<span style="background: {}; color: white; padding: 4px 8px; border-radius: 3px;"><b>{}</b></span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Estado'
    
    def commentaries_count_display(self, obj):
        """Mostrar aprobados vs pendientes"""
        aprobated = obj.commentaries.filter(aprobated=True).count()
        pending = obj.commentaries.filter(aprobated=False).count()
        return format_html(
            '✓ {} | ⧗ {}',
            aprobated, pending
        )
    commentaries_count_display.short_description = 'Comentarios'
    
    def image_preview(self, obj):
        """Mostrar preview de imagen"""
        if obj.featured_image:
            return format_html(
                '<img src="{}" width="200" />',
                obj.featured_image.url
            )
        return 'Sin imagen'
    image_preview.short_description = 'Vista Previa'
    
    # ACCIONES EN LOTE
    
    actions = ['publish_posts', 'archive_posts', 'approve_commentaries']
    
    def publish_posts(self, request, queryset):
        """Acción: Publicar posts seleccionados"""
        from django.utils import timezone
        
        count = queryset.filter(status='drafts').update(
            status='published',
            publish_at=timezone.now()
        )
        
        self.message_user(
            request,
            f'{count} posts publicados ✓'
        )
    publish_posts.short_description = '📤 Publicar posts seleccionados'
    
    def archive_posts(self, request, queryset):
        """Acción: Archivar posts"""
        count = queryset.update(status='archived')
        self.message_user(request, f'{count} posts archivados')
    archive_posts.short_description = '📦 Archivar posts'
    
    def approve_commentaries(self, request, queryset):
        """Acción: Aprobar todos los comentarios de estos posts"""
        from .models import Commentary
        
        commentaries = Commentary.objects.filter(
            post__in=queryset,
            aprobated=False
        )
        count = commentaries.update(aprobated=True)
        
        self.message_user(request, f'{count} comentarios aprobados ✓')
    approve_commentaries.short_description = '✓ Aprobar comentarios pendientes'



