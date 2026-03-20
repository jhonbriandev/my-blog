from django.urls import path
from .import views

# app_name = hace que las URLs sean "users:registro", "users:login", etc
app_name = 'users'

# Cuando alguien entre a la raíz del sitio
# Ejecuta la función inicio de views.py

urlpatterns = [
    #AUTENTIFICATION
    path('',views.login_view, name='login'), # Del archivo views, la funcion inicio, si la funcion cambia de nombre tambien cambia aqui
    path('register/',views.register_view, name='register'),
    path('logout/',views.logout_view, name = 'logout'),

    # PROFILE
    path('profile/',views.profile_view, name = 'profile'),
    path('profile/edit/',views.edit_profile_view, name = 'edit_profile')
]