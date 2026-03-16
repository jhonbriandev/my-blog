from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class ProfileUser(models.Model):
    ROLE_CHOICES = [
        ('user','User'),
        ('mod', 'Moderator'),
        ('admin', 'Administrator')
    ]
    user = models.OneToOneField(User,on_delete = models.CASCADE, related_name= 'profile', primary_key = True)
    rol = models.CharField(max_length= 20, choices= ROLE_CHOICES, default='user', help_text='Rol del usuario. Admin solo puede ser asignado por superuser')
    bio = models.TextField(max_length=500, blank=True, null = True,  help_text='Biografía del usuario (máximo 500 caracteres)')
    profile_picture = models.ImageField(upload_to='profiles/%Y/%m/', blank=True,null=True,
                                        default='profiles/default_avatar.png', help_text='Foto de perfil (JPEG, PNG, máximo 5MB)')
    is_moderator = models.BooleanField(default= False, help_text='Indica si el usuario puede moderar contenido')
    has_email_confirmated = models.BooleanField(default=False,help_text='Email ha sido confirmado por el usuario')
    subscribe_notifications = models.BooleanField(default = True,help_text='Recibir notificaciones por email')
    created_at = models.DateTimeField(auto_now_add = True, help_text='Fecha de creación del perfil')
    updated_at = models.DateTimeField(auto_now_add = True, help_text='Última fecha de actualización')
    updated_at = models.DateTimeField(auto_now = True, help_text='Última fecha de actualización')
    date_last_access = models.DateTimeField(null = True, blank=True, help_text='Último acceso al sitio')

    class Meta:
        verbose_name = 'Perfil de Usuario'
        verbose_name_plural = 'Perfiles de Usuario'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['rol']),
            models.Index(fields=['user']),
        ]
    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} - {self.rol}"
    def __repr__(self):
        return super().__repr__()
    def is_admin(self):
        return  self.rol == 'admin' or self.user.is_superuser
    def is_regular_user(self):
        return self.rol == 'user'
    def can_moderate(self):
        return self.is_moderator or self.is_admin()
    """def can_delete_commentaries(self,commentaries):
        return(

    def can_delete_commentary(self, commentary):
        return (
            self.is_admin() or
            commentaries.author == self.user or
            commentaries.post.author == self.user
            commentary.author == self.user or
            commentary.post.author == self.user
        )
    """

    def get_avatar_url(self):
        return self.profile_picture.url if self.profile_picture else '/static/images/default_avatar.png'
    def get_fullname(self):
        full_name = self.user.get_full_name()
        return full_name if full_name else self.user.username
    
    # Solo estamos aumentado este comentario