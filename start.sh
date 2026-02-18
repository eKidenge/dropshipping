#!/bin/bash
# start.sh

python manage.py migrate

# Create admin using environment variables
python manage.py shell -c "
from django.contrib.auth import get_user_model;
import os;
User = get_user_model();
username = os.environ.get('DJANGO_ADMIN_USERNAME', 'admin');
email = os.environ.get('DJANGO_ADMIN_EMAIL', 'admin@dropshipping.com');
password = os.environ.get('DJANGO_ADMIN_PASSWORD', 'admin123');
if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username, email, password)
"

gunicorn dropshipping.wsgi:application --bind 0.0.0.0:$PORT