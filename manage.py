# python manage.py runserver
# daphne --bind 0.0.0.0 --port 8000 main.asgi:application

# создание ветки
# git checkout -b Add_Bot_Bin_Currency_conversion_Security_Stikers_Uploads_photos/videos_Account_recovery_Copy/edit/delete_messages_Scroll_Hour_format_Support_Edit_Color_theme_Chat_Terms_Subscription_Profile

# git add .
# git commit -m "Add_Bot_Bin_Currency_conversion_Security_Stikers_Uploads_photos/videos_Account_recovery_Copy/edit/delete_messages_Scroll_Hour_format_Support_Edit_Color_theme_Chat_Terms_Subscription_Profile"
# git push -u origin Add_Bot_Bin_Currency_conversion_Security_Stikers_Uploads_photos/videos_Account_recovery_Copy/edit/delete_messages_Scroll_Hour_format_Support_Edit_Color_theme_Chat_Terms_Subscription_Profile

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
