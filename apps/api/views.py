from django.shortcuts import render
from rest_framework import permissions
from apps.blog.models import Post, Commentary, Category
from apps.api.serializers import PostSerializer, CategorySerializer, CommentarySerializer
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticatedOrReadOnly, AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter
from rest_framework.pagination import PageNumberPagination
from rest_framework.decorators import action
from rest_framework.response import Response


class PostViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet para API de posts
    Es de solo lectura, la escritura se realiza en el blog
    ReadOnlyModelViewSet genera automáticamente DOS acciones:
      - list()     → GET /api/posts/           (lista todos)
      - retrieve() → GET /api/posts/<slug>/    (detalle de uno)
    """
    queryset = Post.objects.filter(
        status='published'
    ).order_by('-created_at')
    serializer_class = PostSerializer
    permission_classes =[permissions.AllowAny]
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
        # (sin respuestas, igual que en tu sistema actual)
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

class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet de solo lectura para Categorías.

    Genera automáticamente:
      - list()     → GET /api/categories/
      - retrieve() → GET /api/categories/<pk>/
    """
    queryset = Category.objects.all().order_by('name')
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]

class CommentaryViewSet(viewsets.ReadOnlyModelViewSet):
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