from django.shortcuts import render
from apps.blog.models import Post, Commentary, Category
from apps.api.serializers import PostSerializer, CategorySerializer, CommentarySerializer
from rest_framework.viewsets import ModelViewSet
from rest_framework import permissions
from rest_framework.permissions import IsAdminUser
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter
from rest_framework.pagination import PageNumberPagination
from rest_framework.decorators import action
from rest_framework.response import Response

# Permiso Personalizado para Post
class IsAuthorOrReadOnly(permissions.BasePermission):

    def has_permission(self, request, view):
        # Lectura para cualquiera, escritura solo autenticados
        # Esto permite que usuarios no autenticados puedan hacer GET (list/retrieve)
        if request.method in permissions.SAFE_METHODS:
            # En SAFE_METHODS estan incluidos GET, HEAD, OPTIONS (Metodos Lectura) 
            return True
        # Para POST, PUT, PATCH, DELETE requiere autenticación
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        # Permite leer cualquier objeto
        if request.method in permissions.SAFE_METHODS:
            return True 
        # Solo el autor puede modificar su propia tarea
        return obj.author == request.user
    
class PostViewSet(ModelViewSet):
    """
    ViewSet para API de posts
    Anteriormente fue de solo lectura por ReadOnlyModelViewSet
    Ahora se usa ModelViewSet para utilizar POST, PUT, PACH, DELETE

    """
    queryset = Post.objects.filter(
        status='published'
    ).order_by('-created_at')
    serializer_class = PostSerializer

    # Uso de OR (|):
    # - IsAuthorOrReadOnly permite lectura pública y escritura al autor
    # - IsAdminUser permite control total al administrador
    # Resultado:
    # Autor O Admin pueden modificar
    permission_classes =[IsAuthorOrReadOnly | IsAdminUser]
    # Permite buscar con ?search=django en la URL
    filter_backends =[DjangoFilterBackend,SearchFilter]
    search_fields = ['title','content']
    # Le decimos al ViewSet que busque posts por slug, no por ID.
    # Así la URL queda: /api/posts/mi-post/ en vez de /api/posts/1/
    lookup_field = 'slug'
    filterset_fields = ['category','author']
    pagination_class = PageNumberPagination

    # ACCION PERSONALIZADA

    @action(
        detail=True,          # detail=True significa que opera sobre UN post específico
        methods=['get'],      # Solo acepta peticiones GET
        url_path='commentaries' # La URL será: /api/posts/<slug>/commentaries/
    )
    def commentaries(self, request, slug=None):
        """
        Acción extra que devuelve los comentarios aprobados
        de un post específico.

        @action es un decorador que le dice al Router:
        "además de list() y retrieve(), este ViewSet
        tiene una acción extra en esta URL."
        """
        # Obtenemos el post usando el slug de la URL.
        # get_object() usa automáticamente lookup_field = 'slug'
        post = self.get_object()

        # Filtramos solo comentarios aprobados y de nivel raíz
        # (sin respuestas, igual que en nuestro sistema actual)
        commentaries = Commentary.objects.filter(
            post=post,
            aprobated=True,
            response_to=None
        ).order_by('created_at')

        # Serializamos la lista de comentarios
        serializer = CommentarySerializer(
            commentaries,
            many=True,                  # many=True porque son varios objetos
            context={'request': request} # El contexto permite generar URLs absolutas
        )

        return Response(serializer.data)

class CategoryViewSet(ModelViewSet):

    queryset = Category.objects.all().order_by('name')
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]
    # Así la URL queda: /api/categories/mi-category/ en vez de /api/categories/1/
    lookup_field = 'slug'

class CommentaryViewSet(ModelViewSet):
    """
    ViewSet de solo lectura para Comentarios aprobados.

    Genera automáticamente:
      - list()     → GET /api/commmentaries/
      - retrieve() → GET /api/commmentaries/<pk>/
    """

    # Solo comentarios aprobados, igual que en tu lógica actual
    queryset = Commentary.objects.filter(
        aprobated=True,
        response_to=None   # Solo comentarios raíz, no respuestas
    ).order_by('created_at')

    serializer_class = CommentarySerializer
    permission_classes = [permissions.AllowAny]