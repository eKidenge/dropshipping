#!/bin/bash
# start.sh

python manage.py migrate

# Create admin if doesn't exist
python manage.py shell -c "
from django.contrib.auth import get_user_model;
User = get_user_model();
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@dropshipping.com', 'admin123')
"

gunicorn dropshipping.wsgi:application