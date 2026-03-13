import pytest
from django.contrib.auth.models import User
from apps.users.models import ProfileUser

@pytest.mark.django_db
class TesttProfileUser:
    def test_create_profile_with_user(self):
        """Test creación automática de perfil"""
        user = User.objects.create_user(
            username= 'testuser',
            email= 'test@test.com',
            password= 'testpass123'
        )
        #Los ASSERT son alertas
        
        assert ProfileUser.objects.filter(user = user).exists()
        # El primer user es el campo de la tabla Profileuser primary key
        # El segundo user es de la variable creada arriba
        assert user.profile.rol == 'user'
        # Accedemos al perfil desde el lado de User, usando el related name = user
        # Luego verificamos que user tenga el valor de user osea usuario
        
    def test_is_admin_if_rol_admin(self):
        """Test es_admin retorna True"""
        # Este test valida el correcto comportamiento de admin
        # Al inicio nuestro user ingresa sin privilegios solo es un user
        # Posteriormente intercambiamos el rol de user a admin, no es necesario que este en el create porque 
        # Por logica de negocio todos inician como usuarios y luego pueden escalar o no.
        user = User.objects.create_user(
            username= 'testuser',
            password= 'testpass123'
        )
        user.profile.rol = 'admin'
        user.profile.save()
        # Aqui se guarda el admin
        assert user.profile.is_admin()
        # Indicara True si se inserto de manera correcta el rol admin, o pasara el test
    def test_is_admin_if_superuser(self):
        # No solo un admin creado por el django.admin es un administrador 
        # Sino tambien el superusuario
        # Validaremos si un superusuario tambien es admin, usaremos el metodo creado en models
        """Test es_admin retorna True para superuser"""
        user = User.objects.create_superuser(
            # El create super user es clave para identificar si se guardara o no como superusuario
            username='admin',
            email='admin@example.com',
            password='admin123'
        )
        assert user.profile.is_admin()
        # Esto es un metodo creado en models
    def test_get_fullname(self):
        """Test obtener nombre completo"""
        user = User.objects.create_user(
            username= 'jhondev',
            first_name = 'Jhon',
            last_name = 'AC',
            password= 'pass'
        )
        assert user.profile.get_fullname() == 'Jhon AC'
        # assert user.profile.get_fullname() == 'Nombre diferente', si ejecutamos esto, verifcamos que el
        # nombre completo no es igual que el ejemplo, por lo cual el test no pasara
        # Usaremos el metodo creado en models para igualar el assert con los datos
        # Ingresados arriba, datos del usuario