from django.contrib import admin
from django.urls import path, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect
from django.contrib.auth.views import LogoutView
from . import views

# Редирект для неизвестных URL
def catch_all_redirect(request, path=None):
    if request.user.is_authenticated:
        return redirect('error')
    return redirect('login')

urlpatterns = [
    # Админка
    path('admin/', admin.site.urls),

    # не нравильное напровление
    path('error', views.error, name='error'),

    # Смена языка
    path('change-language/', views.change_language, name='change-language'),

    # Смена валюты
    path('change-currency/', views.change_currency, name='change-currency'),

    # Карта
    path('delete-card/', views.delete_card, name='delete-card'),
    path('add-card/', views.add_card, name='add-card'),
    path('deposit-funds/', views.deposit_funds, name='deposit-funds'),
    # Аутентификация
    path('register', views.register, name='register'),
    path('login', views.login, name='login'),
    path('forgot-password', views.forgot_password, name='forgot-password'),
    path('logout', LogoutView.as_view(next_page='/login/'), name='logout'),

    # Условия подписки
    path('terms', views.terms, name='terms'),
    # Главная страница с редиректом
    # path('', lambda request: redirect('home', id=request.user.id) if request.user.is_authenticated else redirect('login/')),

    # Страница home с параметром id
    path('', views.home, name='home'),

]

# Медиафайлы в режиме DEBUG
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Catch-all редирект для любых других URL
urlpatterns += [
    re_path(r'^(?P<path>.*)$', catch_all_redirect),
]
