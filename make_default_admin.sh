#!/bin/sh

script_path=$(dirname $(readlink -f $0))

cd "$script_path/achievements"

echo 'from main_app.models import User; User.objects.create_superuser("admin", "myemail@example.com", "admin")' | python manage.py shell
