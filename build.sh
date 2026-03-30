# build.sh
#!/usr/bin/env bash

# Detener si cualquier comando falla
set -o errexit

# --- BLOQUE 1: Instalar dependencias ---
# Render instala todo desde requirements.txt
pip install -r requirements.txt

# --- BLOQUE 2: Recolectar archivos estáticos ---
# Copia todos los CSS, JS e imágenes a una carpeta que Render puede servir
python manage.py collectstatic --no-input

# --- BLOQUE 3: Aplicar migraciones ---
# Crea/actualiza las tablas en la base de datos de producción
python manage.py migrate