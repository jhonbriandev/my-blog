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