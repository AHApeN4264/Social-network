from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from . models import User, Card
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
from django.db.models import Avg, Q
from django.db import models
from functools import wraps
from django import forms
from django.core.paginator import Paginator
from django import template
import hashlib

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
def error(request):
    return render(request, 'error/error.html',)

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
        is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.headers.get('accept', '').find('application/json') != -1
        if is_ajax:
            def convert_amount(amount):
                try:
                    amt = Decimal(amount)
                except Exception:
                    amt = Decimal('0')
                if getattr(user, 'currency', 'USD') == 'UAH':
                    return f"{(amt * Decimal('42.1')).quantize(Decimal('0.01'))} ₴"
                return f"{amt.quantize(Decimal('0.01'))} $"

            price = convert_amount(getattr(user, 'wallet', 0) or 0)
            return JsonResponse({'price_converted': price})
    return redirect(request.META.get('HTTP_REFERER', '/'))


@login_required
def deposit_funds(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=400)

    user = request.user
    amount_raw = request.POST.get('amount')
    currency = request.POST.get('currency', getattr(user, 'currency', 'USD'))
    try:
        amount = Decimal(amount_raw or '0')
    except (InvalidOperation, TypeError):
        return JsonResponse({'error': 'Invalid amount'}, status=400)

    if currency == 'UAH':
        # UAH -> USD
        amount_usd = (amount / Decimal('42.1')).quantize(Decimal('0.01'))
    else:
        amount_usd = amount.quantize(Decimal('0.01'))

    try:
        with transaction.atomic():
            user.wallet = (user.wallet or Decimal('0.00')) + amount_usd
            user.save()
    except Exception as e:
        return JsonResponse({'error': 'Could not update wallet'}, status=500)

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


@login_required
def add_card(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=400)

    user = request.user
    card_number = (request.POST.get('card_number') or '').strip()
    cardholder = (request.POST.get('cardholder') or '').strip()
    expiry_month = request.POST.get('expiry_month')
    expiry_year = request.POST.get('expiry_year')

    if not card_number or not card_number.isdigit() or len(card_number) < 13 or len(card_number) > 19:
        return JsonResponse({'error': 'Invalid card number'}, status=400)
    try:
        expiry_month = int(expiry_month)
        expiry_year = int(expiry_year)
    except Exception:
        return JsonResponse({'error': 'Invalid expiry date'}, status=400)

    fp = hashlib.sha256(card_number.encode('utf-8')).hexdigest()

    if Card.objects.filter(user=user, fingerprint=fp).exists():
        return JsonResponse({'error': 'This card is already added'}, status=400)

    last4 = card_number[-4:]
    try:
        Card.objects.create(
            user=user,
            last4=last4,
            fingerprint=fp,
            cardholder=cardholder or None,
            expiry_month=expiry_month,
            expiry_year=expiry_year,
        )
    except Exception as e:
        return JsonResponse({'error': 'Could not save card'}, status=500)

    cards_qs = Card.objects.filter(user=user)
    cards = []
    for c in cards_qs:
        cards.append({'last4': c.last4, 'cardholder': c.cardholder or '', 'expiry': f"{c.expiry_month:02d}/{str(c.expiry_year)[-2:]}"})

    return JsonResponse({'cards': cards})

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
            return render(request, 'login/login.html')

        try:
            user = User.objects.get(Q(email=login_field) | Q(phone_number=login_field))
        except User.DoesNotExist:
            messages.error(request, "Користувача з таким email або номером телефону не знайдено.")
            return render(request, 'login/login.html')

        if not check_password(password, user.password):
            messages.error(request, "Невірний пароль.")
            return render(request, 'login/login.html')

        auth_login(request, user)
        return redirect('home')

    return render(request, 'login/login.html')

def forgot_password(request):
    return render(request, 'login/forgot-password.html')

def terms(request):
    return render(request, 'terms/terms.html')

@login_required
def delete_card(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=400)

    import json
    try:
        data = json.loads(request.body)
        last4 = data.get('last4')
    except Exception:
        return JsonResponse({'error': 'Invalid request'}, status=400)

    user = request.user
    
    from .models import Card
    try:
        card = Card.objects.filter(user=user, last4=last4).first()
        if card:
            card.delete()
        
        cards_qs = Card.objects.filter(user=user)
        cards = []
        for c in cards_qs:
            cards.append({
                'last4': c.last4,
                'cardholder': c.cardholder or '',
                'expiry': f"{c.expiry_month:02d}/{c.expiry_year}"
            })
        
        return JsonResponse({'success': True, 'cards': cards})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required(login_url='login')
def home(request):
    from datetime import date
    
    user = request.user
    role = get_user_role(user)

    if user.subscription_end and user.subscription_end < timezone.now():
        old_subscription = user.subscribe
        old_period = user.subscribe_period

        user.subscribe = 'Basic'
        user.subscribe_period = 'none'
        user.subscription_end = None
        user.save()

        msg = (
            f"Термін підписки {old_subscription} ({old_period}) закінчився."
            if user.language == 'Українська'
            else f"Your {old_subscription} ({old_period}) subscription has expired."
        )
        messages.warning(request, msg)

    def convert(amount):
        try:
            amt = Decimal(amount)
        except Exception:
            amt = Decimal('0')
        if getattr(user, 'currency', 'USD') == 'UAH':
            converted = (amt * Decimal('42.1')).quantize(Decimal('0.01'))
            return f"{converted} ₴"
        return f"{amt.quantize(Decimal('0.01'))} $"

    price_converted = convert(getattr(user, 'wallet', 0) or 0)

    subscription_prices_USD = {
        'bin_plus_monthly': Decimal('4.99'),
        'bin_plus_yearly': Decimal('49.99'),
        'bin_premium_monthly': Decimal('9.99'),
        'bin_premium_yearly': Decimal('99.99'),
        'bin_plus_test': Decimal('0.01'),
    }
    subscription_prices_UAH = {
        'bin_plus_monthly': Decimal('209.99'),
        'bin_plus_yearly': Decimal('419.99'),
        'bin_premium_monthly': Decimal('2099.99'),
        'bin_premium_yearly': Decimal('4199.99'),
        'bin_plus_test': Decimal('0.01'),
    }
    subscription_types = {
        'bin_plus_monthly': ('Bin+', 'monthly', 30),
        'bin_plus_yearly': ('Bin+', 'yearly', 365),
        'bin_premium_monthly': ('Bin_premium', 'monthly', 30),
        'bin_premium_yearly': ('Bin_premium', 'yearly', 365),
        'bin_plus_test': ('Bin+', 'test', 0),
    }

    if request.method == 'POST':
        if 'subscription_plan' in request.POST:
            plan = request.POST.get('subscription_plan')
            subscription_prices = (
                subscription_prices_UAH if getattr(user, 'currency', 'USD') == 'UAH'
                else subscription_prices_USD
            )

            if plan in subscription_prices:
                cost = subscription_prices[plan]
                if user.wallet >= cost:
                    try:
                        with transaction.atomic():
                            user.wallet -= cost
                            sub_name, sub_period, days_count = subscription_types[plan]
                            user.subscribe = sub_name
                            user.subscribe_period = sub_period
                            if plan == 'bin_plus_test':
                                user.subscription_end = timezone.now() + timedelta(seconds=15)
                            else:
                                user.subscription_end = timezone.now() + timedelta(days=days_count)
                            user.save()

                        msg = (
                            f"Підписка {user.subscribe} ({user.subscribe_period}) успішно оформлена!"
                            if user.language == 'Українська'
                            else f"Subscription {user.subscribe} ({user.subscribe_period}) successful!"
                        )
                        messages.success(request, msg)
                    except Exception:
                        messages.error(request, "Помилка при оформленні!" if user.language == 'Українська'
                                       else "Error processing subscription!")
                else:
                    missing = cost - user.wallet
                    messages.error(request, f"Недостатньо коштів! Потрібно ще {missing:.2f}."
                                   if user.language == 'Українська'
                                   else f"Not enough funds! You need {missing:.2f} more.")
            return redirect('home')
        
        profile_updated = False
        
        if 'photo' in request.FILES:
            user.photo = request.FILES['photo']
            profile_updated = True
        
        new_username = request.POST.get('username', '').strip()
        if new_username and new_username != user.username:
            user.username = new_username
            profile_updated = True
        
        new_description = request.POST.get('description', '').strip()
        if hasattr(user, 'description'):
            user.description = new_description
            profile_updated = True
        
        new_tag = request.POST.get('your_tag', '').strip()
        if hasattr(user, 'your_tag'):
            user.your_tag = new_tag
            profile_updated = True
        
        if 'day' in request.POST and 'month' in request.POST and 'year' in request.POST:
            try:
                day = int(request.POST.get('day'))
                month = int(request.POST.get('month'))
                year = int(request.POST.get('year'))
                new_birthday = date(year, month, day)
                user.birthday = new_birthday
                profile_updated = True
            except Exception as e:
                messages.error(request, f"Помилка дати: {e}" if user.language == 'Українська'
                               else f"Date error: {e}")
        
        if profile_updated:
            user.save()
            messages.success(request, "Профіль успішно оновлено!" if user.language == 'Українська'
                             else "Profile updated successfully!")
        
        return redirect('home')

    today = date.today()
    birthday = getattr(user, 'birthday', None) or today
    days = range(1, 32)
    months = range(1, 13)
    years = range(today.year - 100, today.year + 1)

    cards = Card.objects.filter(user=user)
    current_year = timezone.now().year

    return render(request, 'home/home.html', {
        'user': user,
        'price_converted': price_converted,
        'cards': cards,
        'months': months,
        'days': days,
        'years': years,
        'birthday': birthday,
        'expiry_years': range(current_year, current_year + 21),
    })



    # return render(request, 'home/home.html', {
    #     'user': user,
    #     'role': role,
    #     'days': days,
    #     'months': months,
    #     'years': years,
    #     'expiry_years': expiry_years,
    #     'birthday': birthday,
    #     'price_converted': price_converted,
    #     'cards': cards,
    #     'card_messages': {
    #         'invalid_card_number': 'Invalid card number' if user.language != 'Українська' else 'Невірний номер картки',
    #         'card_added': 'Card added' if user.language != 'Українська' else 'Картка додана',
    #         'add_card_failed': 'Add card failed' if user.language != 'Українська' else 'Помилка додавання',
    #         'cards_label': 'Cards' if user.language != 'Українська' else 'Картки',
    #         'no_cards': 'No cards added' if user.language != 'Українська' else 'Карт не додано',
    #     },
    # })