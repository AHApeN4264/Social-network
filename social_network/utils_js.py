from django.http import JsonResponse


def get_js_utilities_for_user(user):
    return {
        'themes': {},
        'current_year': None,
        'user_language': getattr(user, 'language', 'English'),
        'utilities_available': []
    }


def format_message_time(timestamp):
    return ''


def get_sticker_categories_localized(user_language='English'):
    return {}


