from django import forms
from django.core.exceptions import ValidationError
from .models import Post,Commentary

class PostForm(forms.ModelForm):
    """
    Formulario para crear/editar posts.
    
    ModelForm genera campos automáticamente del modelo Post.
    Solo editamos: titulo, contenido, resumen, imagen, categoria, estado
    """
    class Meta:
        """
        La clase Meta se conecta con el modelo gracias a ModelForm
        y le indica a Django que campo y de que manera lo va a mostrar
        """
        model = Post
        fields = ['title','content','summary',
                  'featured_image','category']
        # Estado NO está aquí (no editable por usuario)
        widgets = {
           'title' : forms.TextInput(attrs={
              'class' : 'form-control',
              'placeholder' : 'Titulo del Post',
              'maxlength' : 200
           }),
           'content' : forms.Textarea(attrs={
              'class' : 'form-control',
              'rows' : 12,
              'placeholder' : 'Contenido Completo...',
              'id' : 'editor' # Para integrar editro de texto luego
           }),
           'summary' : forms.Textarea(attrs={
              'class' : 'form-control',
              'rows' : 3,
              'placeholder' : 'Resumen para listados (opcional)',
              'maxlength' : 500
           }),
           'featured_image' : forms.FileInput(attrs={
               'class' : 'form-control',
               'accept' : 'image/*'              
           }),
           'category' : forms.Select(attrs={
               'class' : 'form-select'
           }),

        }
    def clean_title(self):
        """Validar titulo"""
        # Usamos self.para ref al formulario actual, en cleaned
        # se encuentra todos los datos en dict,
        # y con .get obtendras el valor requerido

        title = self.cleaned_data.get('title')

        if len(title) < 5:
            raise ValidationError('Titulo debe tener al menos 5 caracteres')
        if len(title) > 200:
            raise ValidationError('Titulo no puede exceder a 200 caracteres')
        return title
    
    def clean_content(self):
        """Validar Contenido"""
        content = self.cleaned_data.get('content')

        if len(content) < 50:
            raise ValidationError('Contenido debe tener al menos 50 caracteres')
        
        return content
    
    def clean_featured_image(self):
        """Validar imagen — aplica solo cuando se sube una imagen NUEVA"""
        featured_image = self.cleaned_data.get('featured_image')
         # hasattr verifica si el objeto tiene el atributo .content_type
        # Solo los archivos NUEVOS recién subidos tienen .content_type
        # Las imágenes ya guardadas en BD (ImageFieldFile) NO lo tienen
        # Es como distinguir un sobre sellado nuevo de uno que ya fue abierto
        if featured_image and hasattr(featured_image, 'content_type'):
        # Aquí adentro AMBAS validaciones son seguras
        # porque ya confirmamos que es un archivo nuevo
            if featured_image.size > 5 * 1024 * 1024: 
                raise ValidationError('Imagen no puede exceder 5 MB')
    
            if featured_image.content_type not in ['image/jpeg', 'image/png', 'image/webp']:  
                raise ValidationError('Solo se permiten imágenes JPEG, PNG o WebP')
        return featured_image

class ApprovePostForm(forms.Form):
    """
    Formulario SIMPLE para que ADMIN apruebe/rechace posts.
    
    No es ModelForm porque solo es para tomar una decisión.
    
    El ADMIN:
    - Ve el post completo
    - Decide: APROBAR o RECHAZAR
    - Si rechaza, debe dar motivo (feedback para el autor)
    """
    DECISION_CHOICES = [
        ('approve','Aprobar y publicar'),
        ('rejected','Rechazar(Dar feedback)'),
    ]

    decision = forms.ChoiceField(
        choices = DECISION_CHOICES,
        widget = forms.RadioSelect,
        label= '¿Que deseas hacer?'
    )

    rejected_reason = forms.CharField(
        widget = forms.Textarea(attrs={
           'class' : 'form-control',
           'rows' :4,
           'placeholder' : 'Si rechazas, explica el por que...' 
        }),
        required = False,
        label = 'Feedback para el autor (Si rechazas)'
    )

    def clean(self):
        """Validar que si rechaza, debe dar motivo"""
        cleaned_data = super().clean()
        decision = cleaned_data.get('decision')
        reason = cleaned_data.get('rejected_reason')

        # Si decide rechazar, el motivo es Obligatorio
        if decision == 'rejected' and not reason:
            raise ValidationError('Debes dar un motivo si rechazas un post')
        return cleaned_data


class CommentaryForm(forms.ModelForm):
    """
    Formulario para que usuarios dejen comentarios en posts.
    
    Solo necesita el contenido: el autor y el post
    se asignan en la vista (igual que author en PostForm).
    
    Si es una respuesta a otro comentario, response_to
    también se asigna en la vista, no aqui
    """
    class Meta:
        model = Commentary
        fields = ['content']
        widgets = {
            'content' : forms.Textarea(attrs={
                'class' : 'form-control',
                'rows' : 3,
                'placeholder' : 'Tu comentario aqui...',
                'maxlength' : 1000
            })
            
        }
    
    def clean_content(self):
        """Validar Contenido"""
        # Atrapamos el field, esto debe llamarse tal cual lo tenemos en la BD
        content = self.cleaned_data.get('content')

        # strip() elimina espacios al inicio y final
        # Evita comentarios con solo espacios vacíos

        if len(content.strip()) < 5:
            raise forms.ValidationError(
                'El comentario debe tener al menos 5 caracteres')
        elif len(content) > 1000:
            raise forms.ValidationError(
                'El comentario no puede exceder los 1000 caracteres')
        return content



class ApproveCommentaryForm(forms.Form):
    """
    Formulario para que el moderador decida qué hacer con un comentario.
    
    Igual que ApprovePostForm pero para comentarios.
    Solo tiene dos opciones: aprobar o eliminar.
    No tiene 'rechazar con motivo' porque los comentarios son cortos —
    no tiene sentido pedir al usuario que lo reescriba, es mejor
    aprobarlo o borrarlo directamente.
    """

    DECISIONS_COMMENTARIES = [
        ('approve', 'Aprobar — publicar este comentario'),
        ('delete',  'Eliminar — borrar este comentario'),
    ]

    decision = forms.ChoiceField(
        choices=DECISIONS_COMMENTARIES,
        widget=forms.RadioSelect,  # Botones de radio, más claro que un dropdown
        label='Decisión'
    )