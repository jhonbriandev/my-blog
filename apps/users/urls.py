from django.urls import path
from .import views

# Cuando alguien entre a la raíz del sitio
# Ejecuta la función inicio de views.py

urlpatterns = [
    path('',views.login_view, name='login'), # Del archivo views, la funcion inicio, si la funcion cambia de nombre tambien cambia aqui
    path('register/',views.register_view, name='register'),
]