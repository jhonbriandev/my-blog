from rest_framework import serializers
from apps.blog.models import Post, Commentary, Category
from django.contrib.auth.models import User


"""
    USAREMOS VIEWSETS, MAS PROFESIONAL
    ESTO CREA AUTOMATICAMENTE:
    GET (list, detail)
    POST
    PUT
    DELETE
"""
# SERIALIZER PARA CATEGORIA

class CategorySerializer(serializers.ModelSerializer):
    """
    Convierte objetos Category a JSON y viceversa.
    Solo exponemos los campos que el cliente necesita ver.
    """
    class Meta:
        model = Category          # El modelo que vamos a serializar
        fields = ['id', 'name', 'slug']  # Campos que aparecerán en el JSON

# SERIALIZER PARA AUTOR

class AuthorSerializer(serializers.ModelSerializer):
    """
    Serializer simplificado del User.
    Lo usaremos anidado dentro de PostSerializer.
    No exponemos contraseñas ni datos sensibles.
    """
    class Meta:
        model = User
        fields = ['id', 'username']

# SERIALIZER PARA POST

class PostSerializer(serializers.ModelSerializer):
    """Serializer para los posts"""
    # Para texto simple string con nombre completo, llamarlo desde el metodo del modelo
    author_name = serializers.CharField(source = 'author.profile.get_fullname', read_only = True)
    # Para anidado dentro del Json con mas atributos
    #author_name = AuthorSerializer(source='author',read_only=True)
    categoria_name = CategorySerializer(source='category',read_only=True)
    # Campo calculado: no existe en el modelo, lo generamos aquí.
    # Cuenta los comentarios aprobados del post.
    total_commentaries = serializers.SerializerMethodField()
    # usas este campo especial. DRF busca automáticamente un método llamado get_<nombre_del_campo> en el serializer.

    class Meta:
        model = Post
        fields = ['id','title','categoria_name','slug',
                  'author_name', 'summary','count_views',
                  'published_at','total_commentaries']
    # get_<nombre_del_campo>     
    def get_total_commentaries(self,obj):
        """
        Método especial que DRF llama automáticamente para
        calcular el campo 'total_commentaries'.
        'obj' es la instancia del Post que se está serializando.
        """
        # Solo contamos comentarios aprobados y que no son respuestas a otros
        return obj.commentaries.filter(aprobated=True, response_to=None).count()
        
# SERIALIZER PARA COMENTARIOS

class CommentarySerializer(serializers.ModelSerializer):
    """Serializer para comentarios"""

    author_name = serializers.CharField(source = 'author.profile.get_fullname', read_only = True)
    post = serializers.CharField(source='post.slug', read_only=True)
    # En este caso esto si existe en Model
    # Pero es un booleano que dice si o no
    # Nuestra finalidad no es mostrar eso sino las respuestas anidadas
    # Por eso esta el aprobated
    response_to = serializers.SerializerMethodField()
    # Esto agregara un enlace para dirigirnos al post a donde pertenece el comentario
    post_url = serializers.HyperlinkedRelatedField(
    source='post',
    view_name='api:post-detail',
    lookup_field='slug',
    read_only=True
)
    class Meta:
        model = Commentary
        fields = ['id','content','author_name',
                  'post','post_url','aprobated','created_at','response_to']

    # Mostrar respuestas del comentario    
    def get_response_to(self, obj):
        """
        Devuelve las respuestas aprobadas de este comentario.
        Solo un nivel de profundidad
        """
        # usamos el related name de response_to = responses
        aprobated_responses = obj.responses.filter(aprobated=True)
        # Serializamos las respuestas usando este mismo serializer,
        # pero sin volver a incluir 'respuestas' (evitamos bucle infinito)
        return CommentarySerializer(
            aprobated_responses,
            many=True,
            context=self.context
        ).data
        


