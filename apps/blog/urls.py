from django.urls import path
from .views import PostListView, PostCreateView,PostDeleteView,PostDetailView,PostUpdateView,IndexView,MyCommentariesView,MyPostsView, ApprovePostView,PostsPendingView,AddCommentaryView,DeleteCommentaryView
from .views import ApproveCommentaryView,CommentariesPendingView,EditCommentaryView,ToggleArchivePostView

app_name = 'blog'

urlpatterns = [
    # INDEX PRINCIPAL
    
    path('', IndexView.as_view(), name='index'),

    # PARA VER MIS POSTS

    # IMPORTANTE: van ANTES de <slug:slug>/ para que Django no las
    # confunda con un slug. Django lee las rutas de arriba hacia abajo
    # y 'my-posts' podría interpretarse como un slug si va después.
    path('my-posts/', MyPostsView.as_view(), name='my_posts'),
    path('my-commentaries/', MyCommentariesView.as_view(), name='my_commentaries'),

    # APROBACION DE POSTS

    # Ruta donde se visualiza la lista de post pendientes
    path('pending-p/',PostsPendingView.as_view(), name='posts_pending'),
    # Ruta donde aprobaremos o rechazaremos el post
    # El campo name obtiene el mismo nombre que colocamos en la {{ url }} del template
    path('pending-p/<int:post_id>/approve/',ApprovePostView.as_view(), name='approve_post'),
    
    
    # COMENTARIOS

        # <slug> identifica el post, <pk> identifica el comentario específico
    path('<slug:slug>/comment/<int:pk>/edit/',EditCommentaryView.as_view(),name='edit_commentary'),
    path('<slug:slug>/comment/<int:pk>/delete/',DeleteCommentaryView.as_view(), name='delete_commentary'),
    path('<slug:slug>/comment/', AddCommentaryView.as_view(), name='add_commentary'),

    # APROBACION DE COMENTARIOS

    path('pending-c/',CommentariesPendingView.as_view(),name='commentaries_pending'),
    path('pending-c/<int:commentary_id>/approve/',ApproveCommentaryView.as_view(), name='approve_commentary'),

    # POSTS
    
    path('posts/', PostListView.as_view(), name='posts_list'),
    path('posts/create/', PostCreateView.as_view(), name='posts_create'),
    
    path('<slug:slug>/update/', PostUpdateView.as_view(), name='posts_update'),
    path('<slug:slug>/delete/', PostDeleteView.as_view(), name='posts_delete'),
    path('<slug:slug>/archive/', ToggleArchivePostView.as_view(), name='posts_toggle_archive'),

    # SIEMPRE AL FINAL

    path('<slug:slug>/', PostDetailView.as_view(), name='posts_detail'),

   
]