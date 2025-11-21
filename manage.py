# python manage.py runserver

# Для запуска с телефона
# python manage.py runserver 0.0.0.0:8000

# создание ветки
# git checkout -b add_color-theme_chat_search-users_searsh-@tag-profile

# git add .
# git commit -m "add_color-theme_chat_search-users_searsh-@tag-profile"
# git push add_color-theme_chat_search-users_searsh-@tag-profile

#!/usr/bin/env python

"""Django's command-line utility for administrative tasks."""
import os
import sys

def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'main.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
