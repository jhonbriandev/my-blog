from django.urls import path
from .import views

# app_name = hace que las URLs sean "users:registro", "users:login", etc
app_name = 'users'

# Cuando alguien entre a la raíz del sitio
# Ejecuta la función inicio de views.py

urlpatterns = [
    #AUTENTIFICATION
    path('login/',views.login_view, name='login'), # Del archivo views, la funcion inicio, si la funcion cambia de nombre tambien cambia aqui
    path('register/',views.register_view, name='register'),
    path('logout/',views.logout_view, name = 'logout'),

    # PROFILE
    path('profile/',views.profile_view, name = 'profile'),
    path('profile/edit/',views.edit_profile_view, name = 'edit_profile'),
    # Nueva URL para ver el perfil de OTRO usuario
    # <int:user_id> es un número entero que identifica al usuario
    # Ejemplo: /users/profile/5/ → muestra el perfil del usuario con id=5
    # Estas url de preferencia al final para evitar conflictos
    path('profile/<int:user_id>/', views.public_profile_view, name='public_profile'),
]