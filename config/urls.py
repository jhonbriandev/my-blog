"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path , include
from apps.api.urls import router
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework_simplejwt.views import (
    TokenObtainPairView,   # Vista para hacer LOGIN y obtener el token
    TokenRefreshView,      # Vista para RENOVAR el token cuando expira
)



urlpatterns = [
    path('admin/', admin.site.urls),

    # Creacion de api root, lista de APIs, visible en la raiz /api
    # Usamos el router creado en api/urls para obtener las rutas incluidas en ese objeto
    # Agregamos el namespace 'api' aquí
    path('api/', include((router.urls, 'api'))),
    # api auth se encargara de la validacion de login, sin eso no podremos usar token ni POST, PATCH, DELETE
    path('api-auth/', include('rest_framework.urls')),
    # Ruta de login → aquí envías usuario y contraseña, recibes el token
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    # Ruta de renovación → aquí envías el refresh token y recibes uno nuevo
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    path('',include('apps.blog.urls')),
    path('users/',include('apps.users.urls')),
    # Para Swagger
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)