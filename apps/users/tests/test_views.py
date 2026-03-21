import pytest
from django.urls import reverse
from django.contrib.auth.models import User
from apps.users.models import ProfileUser
from apps.users.tests.factories import UserFactory

@pytest.mark.django_db
class TestProfile:
    """Tests para vista de perfil"""
    def test_profile_require_login(self,client):
        """GET /users/profile/ sin login debe redirigir"""
        response = client.get(reverse('users:profile'))
        assert response.status_code == 302
        # response.url contiene la URL real, no el nombre de la ruta
        # usamos reverse() para convertir el nombre a URL real
        assert reverse('users:login') in response.url

    def test_profile_with_login(self,client):
        """Perfil con login debe mostrar datos"""
        user = UserFactory()
        # refresh_from_db recarga el usuario desde la BD
        # garantiza que todos los campos incluido el password estén correctos
        user.refresh_from_db()
        client.force_login(user)

        response = client.get(reverse('users:profile'))

        assert response.status_code == 200
        assert 'profile' in response.context

@pytest.mark.django_db
class TestRegister:
    """Tests para vista de registro"""

    def test_get_register_form(self, client):
        """GET /users/register/ debe mostrar formulario"""
        response = client.get(reverse('users:register'))
        # 200 significa que la página cargó correctamente
        assert response.status_code == 200
        # Verificamos que el contexto tiene el formulario
        assert 'form' in response.context
        # Verificamos que el campo email existe en el formulario
        assert 'email' in response.context['form'].fields

    def test_valid_register_user(self, client):
        """POST con datos válidos debe crear usuario"""
        data = {
            'username': 'juanperez',
            'email': 'juan@example.com',
            'first_name': 'Juan',
            'last_name': 'Pérez',
            'password1': 'MiPassword123!',
            'password2': 'MiPassword123!',
        }
        response = client.post(reverse('users:register'), data)

        # 302 significa redirección, señal de que el registro fue exitoso
        assert response.status_code == 302
        # Verificamos que redirige a la página correcta después del registro
        assert response.url == reverse('users:profile') # Proximamente sera index
        # Verificamos que el usuario realmente se creó en la BD
        assert User.objects.filter(username='juanperez').exists()

    def test_register_email_duplicated(self, client):
        """Email duplicado debe mostrar error"""
        # Usamos UserFactory en lugar de create_user manual
        # La factory crea el usuario con todos los campos necesarios
        existing_user = UserFactory(email='test@example.com')

        # Intentamos registrar otro usuario con el mismo email
        data = {
            'username': 'nuevo',
            'email': 'test@example.com',  # mismo email que existing_user
            'first_name': 'Test',
            'last_name': 'User',
            'password1': 'MiPassword123!',
            'password2': 'MiPassword123!',
        }
        response = client.post(reverse('users:register'), data)

        # 200 significa que NO redirigió, el formulario se mostró de nuevo con errores
        assert response.status_code == 200
        assert 'form' in response.context
        # errors no vacío confirma que el formulario detectó el email duplicado
        assert response.context['form'].errors

    def test_register_short_username(self, client):
        """Username menor a 3 caracteres debe fallar"""
        data = {
            'username': 'ab',  # solo 2 caracteres, debe fallar
            'email': 'test@example.com',
            'first_name': 'Test',
            'last_name': 'User',
            'password1': 'MiPassword123!',
            'password2': 'MiPassword123!',
        }
        response = client.post(reverse('users:register'), data)

        # 200 significa que el formulario regresó con errores
        assert response.status_code == 200
        # errors confirma que el username corto fue rechazado por la validación
        assert response.context['form'].errors


@pytest.mark.django_db
class TestLogin:
    """Tests para vista de login"""

    def test_get_login_form(self, client):
        """GET /users/login/ debe mostrar formulario"""
        response = client.get(reverse('users:login'))
        assert response.status_code == 200
        assert 'form' in response.context

    def test_login_with_username(self, client):
        """Login con username debe funcionar"""
        # UserFactory crea el usuario con password='testpass123' por defecto
        # gracias a PostGenerationMethodCall en la factory
        user = UserFactory()
        # skip_postgeneration_save=True en la factory no guarda el password en BD
        # save() fuerza que el password hasheado se persista correctamente
        user.save()
        data = {
            'user': user.username,  # usamos el username generado por Sequence
            'password': 'testpass123', # password fijo definido en la factory
            'remember_me': False,
        }
        response = client.post(reverse('users:login'), data)

        # 302 confirma que el login fue exitoso y redirigió
        assert response.status_code == 302
        

    def test_login_with_email(self, client):
        """Login con email debe funcionar"""
        # Creamos usuario con email conocido para usarlo en el login
        user = UserFactory(email='login@example.com')
        # skip_postgeneration_save=True en la factory no guarda el password en BD
        # save() fuerza que el password hasheado se persista correctamente
        user.save()
        data = {
            'user': user.email,     # usamos el email del usuario creado
            'password': 'testpass123',
            'remember_me': False,
        }
        response = client.post(reverse('users:login'), data)

        assert response.status_code == 302

    def test_login_password_incorrect(self, client):
        """Password incorrecto debe mostrar error"""
        user = UserFactory()

        data = {
            'user': user.username,
            'password': 'passwordincorrecto',  # password que no coincide
            'remember_me': False,
        }
        response = client.post(reverse('users:login'), data)

        # 200 significa que no redirigió, el login falló correctamente
        assert response.status_code == 200


@pytest.mark.django_db
class TestLogout:
    """Tests para vista de logout"""

    def test_logout_destroy_session(self, client):
        """Logout debe destruir la sesión"""
        # Creamos usuario con factory y autenticamos con force_login
        # force_login es mejor práctica porque no depende de username/password
        user = UserFactory()
        # skip_postgeneration_save=True en la factory no guarda el password en BD
        # save() fuerza que el password hasheado se persista correctamente
        user.save()
        client.force_login(user)

        # Verificamos que está autenticado accediendo al perfil
        response = client.get(reverse('users:profile'))
        assert response.status_code == 200

        # Ejecutamos logout
        response = client.get(reverse('users:logout'))
        # 302 confirma que logout redirigió correctamente
        assert response.status_code == 302

        # Intentamos acceder al perfil de nuevo
        # 302 confirma que la sesión se destruyó y redirige a login
        response = client.get(reverse('users:profile'))
        assert response.status_code == 302