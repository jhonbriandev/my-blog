from django.urls import path,include
from rest_framework.routers import DefaultRouter
from apps.api import views

# El Default router reconoce la vista y genera todas las
# URL disponibles
router = DefaultRouter()

# Registramos el ViewSet de posts
# r'posts' → será la URL /api/posts/
# basename='post' → prefijo para los nombres de las URLs generadas
"""
El basename define el NOMBRE INTERNO de las URLs que genera el router.

    basename='post'      →   post-list, post-detail
    basename='category'  →   category-list, category-detail

Estos nombres se usan para referenciar URLs en el código, por ejemplo:
    view_name='api:post-detail'
    view_name='api:category-detail'

El lookup_field define cómo se ACCEDE al detalle en la URL.
No todos los ViewSets usan el mismo, depende del modelo:

    PostViewSet     → lookup_field='slug'  →  /posts/<slug>/
    CategoryViewSet → lookup_field='slug'  →  /categories/<slug>/
    CommentaryViewSet → lookup_field='pk'  →  /commentaries/<pk>/  (defecto)

El basename es OBLIGATORIO cuando el ViewSet no tiene queryset fijo,
como en MyPostViewSet que usa get_queryset() dinámico.
"""
router.register(r'posts', views.PostViewSet, basename='post')
router.register(r'categories', views.CategoryViewSet, basename='category')
router.register(r'commentaries', views.CommentaryViewSet, basename='commentary')
router.register(r'users',views.RegisterViewSet, basename = 'users')
router.register(r'my-posts',views.MyPostViewSet, basename = 'my-posts')

app_name = 'api'

urlpatterns = [
   path('',include(router.urls)),
]

"""
BASENAME y VIEW_NAME

El basename define el PREFIJO para nombrar las URLs que genera el router.
El router toma ese prefijo y crea dos nombres automáticamente:

    basename='post'      →   post-list, post-detail
    basename='category'  →   category-list, category-detail

El view_name USA esos nombres generados para referenciar URLs en el código:

    basename='post'  genera  'post-detail'
                     y se usa como  view_name='api:post-detail'

En este proyecto cada ViewSet usa su propio lookup_field,
lo que cambia cómo se ve la URL pero NO el nombre:

    PostViewSet      lookup_field='slug'  →  /posts/<slug>/
    CategoryViewSet  lookup_field='slug'  →  /categories/<slug>/
    CommentaryViewSet lookup_field='pk'   →  /commentaries/<pk>/

El basename es OBLIGATORIO cuando el ViewSet no tiene queryset fijo,
como MyPostViewSet que usa get_queryset() dinámico en vez de queryset = ...
"""