#!/bin/sh

script_path=$(dirname $(readlink -f $0))

cd "$script_path/achievements"

python manage.py migrate
python manage.py runserver 0.0.0.0:8000
