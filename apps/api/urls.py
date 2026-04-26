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
Se usa el basename task o user
Pero el sistema genera automaticamente 
    basename='post'  --->   post-list, post-detail
    basename='category'  --->   category-list, category-detail
"""
router.register(r'posts', views.PostViewSet, basename='post')
router.register(r'categories', views.CategoryViewSet, basename='category')
router.register(r'commentaries', views.CommentaryViewSet, basename='commentary')

app_name = 'api'

urlpatterns = [
   path('',include(router.urls)),
]