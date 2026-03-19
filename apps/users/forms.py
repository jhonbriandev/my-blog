from django import forms
from django.contrib.auth.models import User
from apps.users.models import ProfileUser
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError

class RegisterForm(UserCreationForm):
    """
    Formulario de registro de usuarios.
    
    Hereda de UserCreationForm (Django built-in) que ya incluye:
    - password1 (Contraseña)
    - password2 (Confirmar contraseña)
    - Validación automática de coincidencia
    - Validación de complejidad de password
    
    Agregamos:
    - email (validation: único)
    - username (validation: único y 3-30 caracteres)
    - first_name y last_name
    """
    # Email - Campo obligatorio
    email = forms.EmailField(
        required=True,
        # Widget = cómo se renderiza en HTML
        widget=forms.EmailInput(attrs={
            'class': 'form-control',  # Bootstrap CSS
            'placeholder': 'your@email.com'
        })
    )
    # Username - Campo obligatorio
    username = forms.CharField(
        max_length=150,
        # help_text = texto de ayuda bajo el campo
        help_text='3-30 caracteres. Letras, números, @, ., +, -, _',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'nombre_usuario'
        })
    )
    # Nombre
    first_name = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Juan'
        })
    )
    
    # Apellido
    last_name = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Pérez'
        })
    )
    
    # Password 1 - Heredado de UserCreationForm pero lo configuramos
    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Contraseña segura'
        })
    )
    
    # Password 2 - Heredado de UserCreationForm pero lo configuramos
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirmar contraseña'
        })
    )
    
    # Meta = configuración del formulario
    class Meta:
        model = User  # Modelo a usar
        fields = ('username', 'email', 'first_name', 'last_name', 'password1', 'password2')

    # VALIDACIONES PERSONALIZADAS
    # clean_CAMPO = validar ese campo específicamente
    
    def clean_email(self):
        """Validar que el email sea único"""
        email = self.cleaned_data.get('email')
        
        # Buscar si existe otro usuario con ese email
        if User.objects.filter(email=email).exists():
            raise ValidationError(
                'Este email ya está registrado. Usa otro o inicia sesión.'
            )
        
        return email  # IMPORTANTE: siempre retornar el valor
    
    def clean_username(self):
        """Validar que el username sea válido"""
        username = self.cleaned_data.get('username')
        
        # Validación 1: Longitud mínima
        if len(username) < 3:
            raise ValidationError('Username debe tener al menos 3 caracteres')
        
        # Validación 2: No debe ser una palabra común
        palabras_prohibidas = ['admin', 'root', 'django', 'test']
        if username.lower() in palabras_prohibidas:
            raise ValidationError(f'Username "{username}" no permitido')
        
        return username
    
    def save(self, commit=True):
        """
        Override del método save.
        
        UserCreationForm.save() solo guarda username y passwords.
        Nosotros necesitamos guardar también email, first_name, last_name.
        
        commit=True → Guardar en BD inmediatamente
        commit=False → Solo crear objeto (útil para editar antes de guardar)
        """
        user = super().save(commit=False)
        
        # Agregar datos adicionales
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        
        # Ahora sí guardar
        if commit:
            user.save()
        
        return user

class LoginForm(forms.Form):
    """
    Formulario de login.
    
    NO hereda de nada porque es simple.
    Solo necesita usuario (email o username) y password.
    """

    user = forms.CharField(
        max_length=150,
        label='Usuario o Email',  # Texto del label en HTML
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nombre de usuario o Email',
            'autofocus' : True # Cursor aquí al cargar la página
        })

    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class' : 'form-control',
            'placeholder': 'Contraseña'   
        })
    )

    remember_me = forms.BooleanField(
        required=False,
        label= 'Recuerdame por 30 dias',
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })

    )
    # Este formulario NO valida nada porque la validación
    # se hace en la vista (buscamos usuario en BD)

    # Porque:
    # 1. El usuario NO EXISTE aún en el formulario (primer login)
    # 2. Queremos intentar login con email O username
    # 3. La lógica es más clara en la vista

class EditProfileForm(forms.ModelForm):
    """
    Formulario para editar perfil.
    
    ModelForm = formulario vinculado a un modelo Django
    Genera campos automáticamente basados en los campos del modelo.
    """

    class Meta:
        model = ProfileUser # Modelo Base
        fields = ['bio', 'profile_picture']# Solo estos campos editables
        widgets = {
            'bio': forms.Textarea(attrs={
                'class': 'form-control',
                'rows' : 4,
                'placeholder' : 'Cuentamos sobre ti',
                'maxlength': 500
            }),
            'profile_picture': forms.FileInput(attrs={
                'class': 'form-control',
                'accept' : 'image/*'  # Solo aceptar imágenes
            })
        }
        
        def clean_profile_picture(self):
            """Validar que la imagen sea válida"""
            picture = self.cleaned_data.get('profile_picture') # Con .get traemos el valor del diccionario
            
            if picture: # Igual a TRUE
                # Validar tamaño (máximo 5MB)
                if picture.size > 5 * 1024 * 1024:
                    raise ValidationError('La imagen no debe superar los 5MB')
                
                # Validar formato (solo JPEG y PNG)
                valid_formats = ['image/jpeg', 'image/png']
                if picture.content_type not in valid_formats:
                    raise ValidationError('Solo se aceptan imágenes JPEG y PNG')
            return picture
