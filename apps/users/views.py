from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from .forms import RegisterForm, LoginForm, EditProfileForm

@require_http_methods(["GET", "POST"])
# └─ Este decorador solo permite GET y POST en esta vista
# └─ Si alguien intenta DELETE, PATCH, etc, lanza error 405
def register_view(request):
    """
    Vista de registro de usuarios.
    
    GET: Mostrar formulario vacío
    POST: Procesar formulario y crear usuario
    """
    # Si el usuario ya está logueado, no necesita registrarse
    if request.user.is_authenticated:
        # request.user = usuario actual
        # is_authenticated = True si está logueado
        # redirect() = respuesta HTTP que dice "ve a esta URL"
        return redirect('blog:index')  # Redirige a home
    # ============ GET: Mostrar formulario ============
    if request.method == 'GET':
        form = RegisterForm()
        return render(request, 'users/register.html', {'form': form})
    # ============ POST: Procesar formulario ============
    if request.method == 'POST':
        # Crear formulario con datos enviados desde HTML
        # request.POST = diccionario con datos del form
        form = RegisterForm(request.POST)

        
        # Ejecutar TODAS las validaciones:
        # clean_email() - clean_username() - clean()
        # Validación de password (que coincidan)
        # Retorna True si todo está bien, False si hay errores
        if form.is_valid():
            # Crear el usuario
            user = form.save()

            # Obtener credenciales para auto-login
            username = form.cleaned_data['username']
            password = form.cleaned_data['password1']

            # Autenticar
            # Buscar usuario con ese username
            # Verificar que su password coincida (con hashing)
            # Retornar User si todo OK, None si falla
            user = authenticate(username=username, password=password)
            
            # Login
            # Crear sesión para este usuario
            # Guardar user.id en session
            # Ahora request.user == user en todas las siguientes requests
            login(request, user)

            # Mostrar mensaje de éxito
            # Guardar mensaje para mostrar en template
            # Mensajes duran UNA sola request (se borran después)
            # Tipos: success, error, warning, info
            messages.success(
                request,f'¡Bienvenido  {user.username}! Tu cuenta ha sido creada.'
            )
            # Redirigir a home
            return redirect('users:profile') # Se esta editando blog
        
        # Si las autentificaciones no son pasan, no es valido:
        else:
            # Imprimir errores en la consola del servidor para depuración
            print(form.errors.as_data())
            # Mostrar errores específicos de cada campo
            # Form.errors se convertira en un dict y buscamos un for para cada columna
            for field, errors in form.errors.items():
                # Otro bucle dentro del anterior, en este caso solo en la columna de errors
                for error in errors:
                    # Se mostraran los errores uno por uno
                    messages.error(request, f'Error en {field}: {error}')
        # Re-renderizar formulario con errores
        return render(request, 'users/register.html', {'form': form})

@require_http_methods(["GET", "POST"])
def login_view(request):
    """
    Vista de login.
    
    GET: Mostrar formulario
    POST: Validar credenciales y crear sesión
    
    IMPORTANTE: Permitir login con email O username
    """
    
    # Si ya está logueado, no necesita login
    if request.user.is_authenticated:
        return redirect('blog:index')
    
    # ============ GET: Mostrar formulario ============
    if request.method == 'GET':
        form = LoginForm()
        return render(request, 'users/login.html', {'form': form})
    
    # ============ POST: Validar y crear sesión ============
    if request.method == 'POST':
        form = LoginForm(request.POST)

        if form.is_valid():
            # Obtener datos del formulario
            username_or_email = form.cleaned_data.get('user')
            password = form.cleaned_data.get('password')
            remember_me = form.cleaned_data.get('remember_me') 

            # PASO 1: Buscar usuario por email O username
            user = None
            try:
                # Intentar buscar por email
                user_obj = User.objects.get(email=username_or_email) 
                user = authenticate(
                    request,
                    username = user_obj.username, # Necesitamos username para auth
                    password = password
                
                )
            except User.DoesNotExist:
                # Si no existe por email, intentar por username
                user = authenticate(
                    request,
                    username = username_or_email,
                    password = password
                )
            # PASO 2: Si credenciales son correctas
            if user is not None:
                # Crear la sesion
                login(request, user)
                # Si marcó "recuérdame", sesión dura 30 días
                if remember_me:
                    # Segundos en 30 días
                    request.session.set_expiry(30 * 24 * 60 * 60)
                messages.success(request, f'!Bienvenido {user.username}!')
                return redirect('users:profile')
            
            #PASO 3: Si credenciales son incorrectas
            else:
                # Mensaje genérico (NO decir si usuario existe o no)
                messages.error(request, 'Credenciales incorrectas')

        # Re-renderizar si form no válido
        return render(request, 'users/login.html',{'form':form})

def logout_view(request):
    """
    Vista de logout.
    
    Muy simple: destruye sesión y redirige.
    """
    # Destruir sesion y borrar cookies
    logout(request)
    messages.success(request, 'Has cerrado sesión exitosamente')
    return redirect('users:login')


@login_required(login_url='users:login')
# Si no esta logueado lo debes dirigir a login
def profile_view(request):
    """Vista de perfil del usuario.
    
    Solo accesible para usuarios autenticados."""
    # request.user = usuario autentificado
    # request.user.profile = ProfileUser (One to One)

    context = {
        'profile' : request.user.profile,
        'posts_count' : request.user.posts.count(),
        'commentaries_count' : request.user.commentaries.count(),
    
    }
                
    return render(request,'users/profile.html',context)

@login_required(login_url='users:login')
# Si no esta logueado lo debes dirigir a login
def edit_profile_view(request):
    """
    Vista para editar perfil del usuario.
    
    GET: Mostrar formulario con datos actuales
    POST: Guardar cambios
    """
    # ============ GET: Mostrar formulario ============
    if request.method == 'GET':
        # Instanciar form con datos actuales (instance=...)
        form = EditProfileForm(instance = request.user.profile)
        return render(request,'users/edit_profile.html',{'form':form})
    # ============ POST: Guardar cambios ============
    if request.method == 'POST':
        # Instanciar form con datos enviados
        form = EditProfileForm(
            request.POST, # Datos del formulario
            request.FILES,  # Archivos (imagen)
            instance = request.user.profile # Objeto a actualizar   
        )
        if form.is_valid():
            form.save() # Guardar cambios en BD

            messages.success(request, 'Perfil actualizado exitosamente')
            return redirect('users:profile')
        # Si no válido, re-renderizar con errores
        return render(request, 'users/edit_profile.html'),{'form':form}

def public_profile_view(request, user_id):
    """
    Vista pública del perfil de cualquier usuario.
    No requiere login — cualquier visitante puede verla.
    
    Recibe:
    - user_id: viene de la URL /users/profile/5/
    """
    from django.contrib.auth.models import User
    from django.shortcuts import get_object_or_404, render
    from apps.blog.models import Post

    # Buscar el usuario por ID
    # Si no existe → página 404 automáticamente
    profile_user = get_object_or_404(User, id=user_id)

    # Sus 5 posts publicados más recientes
    user_posts = Post.objects.published().filter(
        author=profile_user
    ).order_by('-published_at')[:5]

    # Total de posts publicados (para el contador)
    posts_count = Post.objects.published().filter(
        author=profile_user
    ).count()

    # Total de comentarios aprobados (para el contador)
    commentaries_count = profile_user.commentaries.filter(
        aprobated=True
    ).count()

    context = {
        'profile_user': profile_user,   # El dueño del perfil
        'user_posts': user_posts,        # Sus últimos posts
        'posts_count': posts_count,      # Contador de posts
        'commentaries_count': commentaries_count,  # Contador de comentarios
    }

    return render(request, 'users/public_profile.html', context)

