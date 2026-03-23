from django.urls import path
from .views import PostListView, PostCreateView,PostDeleteView,PostDetailView,PostUpdateView,IndexView,MyCommentariesView,MyPostsView, ApprovePostView,PostsPendientesView

app_name = 'blog'

urlpatterns = [
    # POSTS
    path('', IndexView.as_view(), name='index'),
    path('posts/', PostListView.as_view(), name='posts_list'),
    path('posts/create/', PostCreateView.as_view(), name='posts_create'),

    # PARA VER MIS POSTS

    # IMPORTANTE: van ANTES de <slug:slug>/ para que Django no las
    # confunda con un slug. Django lee las rutas de arriba hacia abajo
    # y 'my-posts' podría interpretarse como un slug si va después.
    path('my-posts/', MyPostsView.as_view(), name='my_posts'),
    path('my-commentaries/', MyCommentariesView.as_view(), name='my_commentaries'),

        # APROBACION DE POSTS
    path('dashboard/',PostsPendientesView.as_view(), name='posts_pending'),
    path('dashboard/<int:post_id>/approve',ApprovePostView.as_view(), name='approve_post'),
    
    path('<slug:slug>/', PostDetailView.as_view(), name='posts_detail'),
    path('<slug:slug>/update/', PostUpdateView.as_view(), name='posts_update'),
    path('<slug:slug>/delete/', PostDeleteView.as_view(), name='posts_delete'),



   
]