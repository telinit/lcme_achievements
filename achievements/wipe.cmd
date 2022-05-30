@echo off

del /f /s /q db.sqlite3
del /f /s /q main_app\migrations

python manage.py flush --noinput
python manage.py makemigrations --noinput
python manage.py makemigrations main_app --noinput
python manage.py migrate --noinput

echo from main_app.models import User; User.objects.create_superuser('admin', 'myemail@example.com', 'admin') | python manage.py shell