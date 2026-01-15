from django.contrib import admin
from django.urls import path, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect
from django.contrib.auth.views import LogoutView
from social_network import consumers
from . import views
from .views import only_specific_user

def catch_all_redirect(request, path=None):
    return redirect('error')

# Админка для админа
admin_site = only_specific_user(admin.site.urls)

urlpatterns = [
    # Админка
    path('admin/', admin_site),
    # Страница ошибки
    path('error', views.error, name='error'),

    # Смена языка
    path('change-language/', views.change_language, name='change-language'),

    # Смена валюты
    path('change-currency/', views.change_currency, name='change-currency'),

    # Карта
    path('delete-card/', views.delete_card, name='delete-card'),
    path('add-card/', views.add_card, name='add-card'),
    path('deposit-funds/', views.deposit_funds, name='deposit-funds'),
    path('get_currency-conversion/', views.get_currency_conversion, name='get_currency-conversion'),

    # Theme
    path('save-custom-option/', views.save_custom_option, name='save_custom_option'),
    path('toggle-custom-button/', views.toggle_custom_button, name='toggle_custom_button'),
    path('save-button-text-color/', views.save_button_text_color, name='save_button_text_color'),
    # path('save-time-format/', views.save_time_format, name='save_time_format'),
    
    # Аутентификация
    path('register', views.register, name='register'),
    path('login', views.login, name='login'),
    path('forgot-password', views.forgot_password, name='forgot-password'),
    path('enter-gmail', views.enter_gmail, name='enter-gmail'),
    path('logout', LogoutView.as_view(next_page='/login'), name='logout'),

    # Условия подписки
    path('terms', views.terms, name='terms'),

    # Поиск на главном экране
    path('search-users/', views.search_users, name='search_users'),

    # Редактирование профиля
    path('upload_avatar/', views.upload_avatar, name='upload_avatar'),
    path('update_profile/', views.update_profile, name='update_profile'),
    path('upload_background/', views.upload_background, name='upload_background'),
    path('reset-avatar/', views.reset_avatar, name='reset_avatar'),
    path('remove_background/', views.remove_background, name='remove_background'),

    # Чат
    path('send-message/', views.send_message, name='send_message'),
    path('get-chat-messages/', views.get_chat_messages, name='get_chat_messages'),
    # история чатов
    path('get-recent-contacts/', views.get_recent_contacts, name='get_recent_contacts'),
    # просмотр профиля другого пользователя
    path('get-user-profile/', views.get_user_profile, name='get_user_profile'),
    # поиск по тегу
    path('get-user-by-tag/', views.get_user_by_tag, name='get-user-by-tag'),
    # файлы в чате
    path('upload-chat-file/', views.upload_chat_file, name='upload_chat_file'),
    # другое чата
    path('mark-messages-read/', views.mark_messages_read, name='mark_messages_read'),
    path('save-note/', views.save_note, name='save_note'),
    path('get-notes/', views.get_notes, name='get_notes'),

    # профиль
    path('check-user-exists/', views.check_user_exists, name='check_user_exists'),
    
    # security
    path('change-password/', views.change_password, name='change_password'),
    path('enable-2fa/', views.enable_2fa, name='enable_2fa'),
    path('disable-2fa/', views.disable_2fa, name='disable_2fa'),
    path('terminate-session/', views.terminate_session, name='terminate_session'),

    # Bin chat
    path('get_bin_messages', views.get_bin_messages, name='get_bin_messages'),
    path('get-bin-messages/', views.get_bin_messages, name='get-bin-messages'),
    path('send-bin-message/', views.send_message, name='send_bin_message'),
    path('get-verification-code-bin/', views.get_verification_code_bin, name='get_verification_code_bin'),
    path('create_bin_user/', views.create_bin_user, name='create_bin_user'),

    # Message management
    path('edit-message/', views.edit_message, name='edit_message'),
    path('delete-message/', views.delete_message, name='delete_message'),

    # WebSocket для чата
    re_path(r'ws/chat/(?P<room_name>\w+)/$', consumers.ChatConsumer.as_asgi()),

    path('verification-codes/', views.view_verification_codes, name='verification-codes'),

    # Главная страница
    path('', views.home, name='home'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

urlpatterns += [
    re_path(r'^(?P<path>.*)$', catch_all_redirect),
]