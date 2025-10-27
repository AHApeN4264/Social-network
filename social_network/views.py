from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from .models import User
from django.contrib.auth.hashers import make_password, check_password
from django.contrib import messages
from django.contrib.auth import login as auth_login, authenticate
from django.urls import reverse
from decimal import Decimal, InvalidOperation
from datetime import date 
import datetime
from django.views.decorators.csrf import csrf_exempt
from datetime import date, timedelta, datetime
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db import transaction, models
from django.utils import timezone
from django.utils.timezone import now
from django.db.models import Avg
from django.db import models
from functools import wraps
from django import forms
from django.core.paginator import Paginator
from django import template

User = get_user_model()

def get_user_role(user):
    if not user.is_authenticated:
        return "User"
    if user.username.lower() == "AHAPEN_4264":
        return "Administrator"
    elif user.username.lower() == "Andrey":
        return "Moderator"
    else:
        return "User"

def change_language(request):
    if request.method == "POST":
        lang = request.POST.get("language", "English")
        user = request.user
        user.language = lang
        user.save()
    return redirect(request.META.get('HTTP_REFERER', '/'))

def change_currency(request):
    if request.method == "POST":
        cur = request.POST.get("currency", "USD")
        user = request.user
        user.currency = cur
        user.save()
        # If request is AJAX/fetch, return JSON with new converted value so the client can update without reload
        is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.headers.get('accept', '').find('application/json') != -1
        if is_ajax:
            # compute simple conversion (same logic as in home)
            def convert_amount(amount):
                try:
                    amt = Decimal(amount)
                except Exception:
                    amt = Decimal('0')
                if getattr(user, 'currency', 'USD') == 'UAH':
                    return f"{(amt * Decimal('42.1')).quantize(Decimal('0.01'))} ₴"
                return f"{amt.quantize(Decimal('0.01'))} $"

            # Return the user's wallet converted to the current display currency
            price = convert_amount(getattr(user, 'wallet', 0) or 0)
            return JsonResponse({'price_converted': price})
    return redirect(request.META.get('HTTP_REFERER', '/'))


@login_required
def deposit_funds(request):
    """Accepts POST deposit via AJAX. Expects 'amount' and 'currency' in POST data.
    Adds the deposit (converted to base USD) to user's wallet and returns new converted display string.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=400)

    user = request.user
    amount_raw = request.POST.get('amount')
    currency = request.POST.get('currency', getattr(user, 'currency', 'USD'))
    try:
        amount = Decimal(amount_raw or '0')
    except (InvalidOperation, TypeError):
        return JsonResponse({'error': 'Invalid amount'}, status=400)

    # Convert incoming amount to USD for storage assuming wallet stores USD.
    if currency == 'UAH':
        # UAH -> USD
        amount_usd = (amount / Decimal('42.1')).quantize(Decimal('0.01'))
    else:
        amount_usd = amount.quantize(Decimal('0.01'))

    # Update wallet atomically
    try:
        with transaction.atomic():
            user.wallet = (user.wallet or Decimal('0.00')) + amount_usd
            user.save()
    except Exception as e:
        return JsonResponse({'error': 'Could not update wallet'}, status=500)

    # Return the updated wallet formatted according to user's display currency
    def convert_amount_display(amount_val, display_currency):
        try:
            amt = Decimal(amount_val)
        except Exception:
            amt = Decimal('0')

        if display_currency == 'UAH':
            return f"{(amt * Decimal('42.1')).quantize(Decimal('0.01'))} ₴"
        return f"{amt.quantize(Decimal('0.01'))} $"

    price = convert_amount_display(user.wallet, getattr(user, 'currency', 'USD'))
    return JsonResponse({'price_converted': price})

register = template.Library()

def register(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        contact = request.POST.get('contact', '').strip()
        password = request.POST.get('password', '').strip()

        if not username or not contact or not password:
            messages.error(request, "Будь ласка, заповніть всі необхідні поля")
            return redirect('register')

        email = None
        phone_number = None

        if '@' in contact and '.' in contact:
            email = contact
        elif contact.isdigit():
            phone_number = contact
        else:
            messages.error(request, "Неправильний формат контакту. Введіть email або номер телефону.")
            return redirect('register')

        if User.objects.filter(username=username).exists():
            messages.error(request, f"Користувач з ім'ям '{username}' вже існує")
            return redirect('register')
        if email and User.objects.filter(email=email).exists():
            messages.error(request, f"Користувач з email '{email}' вже існує")
            return redirect('register')
        if phone_number and User.objects.filter(phone_number=phone_number).exists():
            messages.error(request, f"Користувач з номером телефону '{phone_number}' вже існує")
            return redirect('register')

        user = User.objects.create(
            username=username,
            email=email,
            phone_number=phone_number,
            password=make_password(password)
        )

        auth_login(request, user)

        return redirect('home')

    return render(request, 'login/register.html')


def login(request):
    if request.method == 'POST':
        login_field = request.POST.get('login_field', '').strip()
        password = request.POST.get('password', '').strip()

        if not login_field or not password:
            messages.error(request, "Будь ласка, заповніть всі поля.")
            return render(request, 'login.html')

        try:
            user = User.objects.get(models.Q(email=login_field) | models.Q(phone_number=login_field))
        except User.DoesNotExist:
            messages.error(request, "Користувача з таким email або номером телефону не знайдено.")
            return render(request, 'login.html')

        if not check_password(password, user.password):
            messages.error(request, "Невірний пароль.")
            return render(request, 'login.html')

        auth_login(request, user)
        return redirect('home')

    return render(request, 'login/login.html')

def forgot_password(request):
    return render(request, 'login/forgot-password.html')

def register_delete(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        phone_number = request.POST.get('phone_number')
        email = request.POST.get('email')
        password = request.POST.get('password')
        user = None
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            try:
                user = User.objects.get(phone_number=phone_number)
            except User.DoesNotExist:
                try:
                    user = User.objects.get(email=email)
                except User.DoesNotExist:
                    user = None
        if user:
            if check_password(password, user.password):
                user.delete()
                messages.success(request, "Користувача успішно видалено")
                return redirect('login')
            else:
                messages.error(request, "Невірний пароль")
        else:
            messages.error(request, "Користувач з такими даними не знайдений")

    return render(request, 'register-delete.html')

@login_required(login_url='login')
def home(request):
    user = request.user
    role = get_user_role(user)

    def convert(amount):
        """Простая функция конвертации без фильтров.

        Works with Decimal or numeric types and returns a formatted string
        using Decimal arithmetic to avoid mixing floats with Decimal.
        """
        try:
            amt = Decimal(amount)
        except Exception:
            amt = Decimal('0')

        if getattr(user, 'currency', 'USD') == 'UAH':
            converted = (amt * Decimal('42.1')).quantize(Decimal('0.01'))
            return f"{converted} ₴"

        converted = amt.quantize(Decimal('0.01'))
        return f"{converted} $"

    # Use the user's wallet value as the displayed base amount (stored in USD in `user.wallet`)
    price_converted = convert(getattr(user, 'wallet', 0) or 0)

    days = list(range(1, 32))
    months = list(range(1, 13))
    years = list(range(1900, timezone.now().year + 1))

    birthday = user.birthday or user.date_joined.date()

    if request.method == 'POST':
        username_new = request.POST.get('username', '').strip()
        description = request.POST.get('description', '').strip()
        your_tag = request.POST.get('your_tag', '').strip()
        day = request.POST.get('day')
        month = request.POST.get('month')
        year = request.POST.get('year')

        # Update username if provided and different
        if username_new and username_new != user.username:
            # ensure uniqueness
            if User.objects.filter(username=username_new).exclude(pk=user.pk).exists():
                messages.error(request, f"Username '{username_new}' is already taken")
                return redirect('home')
            else:
                user.username = username_new

        user.description = description if description else None

        if your_tag:
            if not your_tag.startswith('@'):
                your_tag = f"@{your_tag}"
            user.your_tag = your_tag
        else:
            user.your_tag = f"@{user.username}"

        if day and month and year:
            try:
                user.birthday = date(int(year), int(month), int(day))
            except ValueError:
                pass

        user.save()
        return redirect('home')

    return render(request, 'home/home.html', {
        'user': user,
        'role': role,
        'days': days,
        'months': months,
        'years': years,
        'birthday': birthday,
        'price_converted': price_converted,
    })
