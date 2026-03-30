Sitio web generado con python y django denominado My Blog
# Blog Django — Proyecto Portfolio

Blog completo desarrollado con Django 4.2+ como proyecto de portfolio.

## Características principales

- Sistema de roles: Admin, Moderador, Usuario
- CRUD de posts con flujo de aprobación (borrador → publicado → archivado)
- Sistema de comentarios con hilos de respuesta y moderación
- Notificaciones por email automáticas
- API REST con Django REST Framework
- Autenticación de usuarios completa

## Tecnologías

- Python 3.11 / Django 4.2
- PostgreSQL
- Django REST Framework
- Bootstrap 5
- pytest / pytest-django

## Instalación local

1. Clona el repositorio:
```bash
   git clone https://github.com/tu-usuario/tu-repo.git
   cd tu-repo
```

2. Crea y activa el entorno virtual:
```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate     # Windows
```

3. Instala las dependencias:
```bash
   pip install -r requirements.txt
```

4. Crea el archivo `.env` en la raíz con las siguientes variables:
```
   SECRET_KEY=genera-una-clave-aqui
   DEBUG=True
   DB_NAME=nombre_bd
   DB_USER=usuario
   DB_PASSWORD=contraseña
   DB_HOST=localhost
   DB_PORT=5432
```

5. Aplica las migraciones:
```bash
   python manage.py migrate
```

6. Crea un superusuario:
```bash
   python manage.py createsuperuser
```

7. Ejecuta el servidor:
```bash
   python manage.py runserver
```

## Ejecutar tests
```bash
pytest
```