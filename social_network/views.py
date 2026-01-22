from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from .models import User, Card, Message, LoginHistory, EmailVerificationCode, UserMessage
from django.contrib.auth.hashers import make_password, check_password
from django.contrib import messages
from django.contrib.auth import login as auth_login, authenticate, get_user_model, update_session_auth_hash
from django.urls import reverse
from decimal import Decimal, InvalidOperation
from datetime import date 
import datetime
from django.views.decorators.csrf import csrf_exempt
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.http import require_POST
from pathlib import Path
from datetime import date, timedelta, datetime
from django.contrib.auth.decorators import login_required
from django.db import transaction, models
from django.utils import timezone
from django.utils.timezone import now
from django.db.models import Max, Avg, Q
from django.db import models
from functools import wraps
from django import forms
from django.core.paginator import Paginator
from django import template
import re
from django.utils.safestring import mark_safe
import hashlib
import json
from django.contrib.sessions.models import Session
from django.core.mail import send_mail
from django.conf import settings
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
import random
import string
import requests
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
import os
import smtplib
from email.mime.text import MIMEText
import json

User = get_user_model()

def only_specific_user(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('error')
        
        if request.user.username != 'ahapen_4264':
            return redirect('error')
        
        return view_func(request, *args, **kwargs)
    return wrapper

def get_user_role(user):
    if not user.is_authenticated:
        return "User"
    
    username_lower = user.username.lower()
    
    if username_lower == "ahapen_4264":
        if user.role != 'Administrator':
            user.role = 'Administrator'
            user.is_staff = True  
            user.is_superuser = True
            user.save()
        return 'Administrator'
    
    elif username_lower == "andriy":
        if user.role != 'Moderator':
            user.role = 'Moderator'
            user.save()
        return 'Moderator'
    
    elif username_lower == "админ":
        if user.role != 'Administrator':
            user.role = 'Administrator'
            user.is_staff = True
            user.is_superuser = True
            user.save()
        return 'Administrator'
    
    elif username_lower == "bin":
        if user.role != 'System Bot':
            user.role = 'System Bot'
            user.is_active = True
            user.is_staff = False
            user.is_superuser = False
            user.save()
        return 'System Bot'
    
    return user.role if user.role else 'User'

def get_display_role(role):
    if role == 'Administrator':
        return '👑 Administrator'
    elif role == 'Moderator':
        return '🛡️ Moderator'
    elif role == 'System Bot':
        return '🤖 System Bot'
    else:
        return '👤 User'

@login_required
def get_user_profile(request):
    username = request.GET.get('username')
    
    if not username:
        return JsonResponse({'success': False, 'error': 'Username is required'})
    
    try:
        if username.lower() in ('bin', 'bin_bot'):
            bin_user = User.objects.filter(username__iexact='Bin_bot').first()
            if not bin_user:
                bin_user = create_bin_user()  # ваша функція створення
            user = bin_user
        else:
            user = User.objects.get(username=username)
        
        role = get_user_role(user)
        
        current_user_lang = getattr(request.user, 'language', 'English')
        
        display_role = ""
        if role == 'System Bot':
            display_role = '🤖 System Bot'
        elif role == 'Administrator':
            display_role = '👑 Administrator'
        elif role == 'Moderator':
            display_role = '🛡️ Moderator'
        elif role == 'User':
            if user.subscribe == 'System':
                display_role = '🤖 Bot'
            else:
                display_role = '👤 User' if current_user_lang != 'Українська' else '👤 Користувач'
        
        if user.birthday:
            if current_user_lang == 'Українська':
                months_ua = {
                    1: 'січня', 2: 'лютого', 3: 'березня', 4: 'квітня',
                    5: 'травня', 6: 'червня', 7: 'липня', 8: 'серпня',
                    9: 'вересня', 10: 'жовтня', 11: 'листопада', 12: 'грудня'
                }
                birthday_str = f"{user.birthday.day} {months_ua[user.birthday.month]}, {user.birthday.year}"
            else:
                months_en = [
                    'January', 'February', 'March', 'April', 'May', 'June',
                    'July', 'August', 'September', 'October', 'November', 'December'
                ]
                birthday_str = f"{months_en[user.birthday.month-1]} {user.birthday.day}, {user.birthday.year}"
        else:
            birthday_str = 'Not specified' if current_user_lang != 'Українська' else 'Не вказано'
        
        user_data = {
            'success': True,
            'username': user.username,
            'status': user.status or 'Offline',
            'your_tag': user.your_tag or '',
            'description': user.description or '',
            'birthday': birthday_str,
            'photo_url': user.photo.url if user.photo and hasattr(user.photo, 'url') else '/static/pictures/bin.jpg' if (user.role == 'System Bot' or user.username in ["Bin","Bin_bot"]) else '/static/pictures/login.png',
            'background_url': user.background.url if user.background and hasattr(user.background, 'url') else '',
            'subscribe': user.subscribe,
            'role': role,
            'display_role': display_role,
            'is_system_bot': role == 'System Bot'
        }
        
        return JsonResponse(user_data)
        
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'User not found'})
    except Exception as e:
        print(f"Error loading user profile: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)})

def error(request):
    lang = "English"
    if request.session.get("language"):
        lang = request.session["language"]
    elif request.user.is_authenticated and hasattr(request.user, "language"):
        lang = request.user.language

    return render(request, 'error/error.html', {"lang": lang})

def change_language(request):
    if request.method == "POST":
        lang = request.POST.get("language", "English")
        
        print(f"Changing language to: {lang}")

        request.session['language'] = lang
        request.session.modified = True
        
        if request.user.is_authenticated and hasattr(request.user, "language"):
            request.user.language = lang
            request.user.save()
            print(f"Saved language to user profile: {lang}")

        is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'
        
        redirect_path = request.POST.get('next') or request.META.get('HTTP_REFERER', '/')
        
        if not redirect_path or redirect_path == request.build_absolute_uri():
            redirect_path = '/'
        
        if is_ajax:
            return JsonResponse({'success': True, 'language': lang, 'redirect': redirect_path})

        return redirect(redirect_path)

    return redirect('/')

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

        rates_usd_to = {'USD': Decimal('1.0'), 'EUR': Decimal('0.917'), 'GBP': Decimal('0.773'), 'UAH': Decimal('41.45')}
        display_currency = (display_currency or 'USD').upper()
        factor = rates_usd_to.get(display_currency, Decimal('1.0'))

        if display_currency == 'UAH':
            symbol = '₴'
        elif display_currency == 'EUR':
            symbol = '€'
        elif display_currency == 'GBP':
            symbol = '£'
        else:
            symbol = '$'

        result = (amt * factor).quantize(Decimal('0.01'))
        return f"{result} {symbol} {display_currency}"

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

def register(request):
    lang = "English"
    if request.session.get("language"):
        lang = request.session["language"]
    elif request.user.is_authenticated and hasattr(request.user, "language"):
        lang = request.user.language

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
            password=make_password(password),
            language=lang,
            your_tag=f"@{username}"
        )       

        request.session['language'] = lang
        
        user.backend = 'django.contrib.auth.backends.ModelBackend'
        auth_login(request, user)
        return redirect('home')

    return render(request, 'login/register.html', {"lang": lang})

def login(request):
    lang = "English"
    if request.session.get("language"):
        lang = request.session["language"]
    elif request.user.is_authenticated and hasattr(request.user, "language"):
        lang = request.user.language

    if request.method == 'POST':
        login_field = request.POST.get('login_field', '').strip()
        password = request.POST.get('password', '').strip()

        if not login_field or not password:
            messages.error(request, "Будь ласка, заповніть всі поля.")
            return render(request, 'login/login.html')

        User = get_user_model()
        try:
            user = User.objects.get(Q(email=login_field) | Q(phone_number=login_field))
        except User.DoesNotExist:
            messages.error(request, "Користувача з таким email або номером телефону не знайдено.")
            return render(request, 'login/login.html')

        if not check_password(password, user.password):
            messages.error(request, "Невірний пароль.")
            return render(request, 'login/login.html')

        lang_from_session = request.session.get("language", "English")
        
        if hasattr(user, 'language') and user.language != lang_from_session:
            user.language = lang_from_session
            user.save()
        
        request.session['language'] = lang_from_session
        
        backend = 'django.contrib.auth.backends.ModelBackend'
        auth_login(request, user, backend=backend)
        return redirect('home')

    return render(request, 'login/login.html', {"lang": lang})

def enter_gmail(request):
    lang = "English"
    if request.session.get("language"):
        lang = request.session["language"]
    elif request.user.is_authenticated and hasattr(request.user, "language"):
        lang = request.user.language

    if request.method == 'GET':
        request.session.pop('verification_sent', None)
        request.session.pop('reset_email', None)
        request.session.pop('verification_code', None)
        request.session.pop('verification_code_expires', None)

    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        print(f"\n" + "="*50)
        print(f"🔍 DEBUG ENTER_GMAIL START")
        print(f"Email received: {email}")
        
        if not email:
            messages.error(request, 'Please enter email' if lang != 'Українська' else 'Будь ласка, введіть email')
            return render(request, 'login/enter-gmail.html', {"lang": lang})

        try:
            validate_email(email)
        except ValidationError:
            messages.error(request, 'Please enter a valid email' if lang != 'Українська' else 'Будь ласка, введіть коректний email')
            return render(request, 'login/enter-gmail.html', {"lang": lang})

        User = get_user_model()

        try:
            user = User.objects.get(email=email)
            print(f"✅ User found: {user.username} (ID: {user.id})")
            
            code = str(random.randint(100000, 999999))
            print(f"✅ Generated code: {code}")
            
            verification_code_obj = EmailVerificationCode.objects.create(
                user=user,
                email=email,
                code=code,
                expires_at=timezone.now() + timedelta(minutes=10)
            )
            
            print(f"✅ EmailVerificationCode created: ID {verification_code_obj.id}")
            
            try:
                bin_user = User.objects.filter(username__in=["Bin","Bin_bot"]).first()
                
                if not bin_user:
                    print(f"⚠️ Bin user not found, creating...")
                    bin_user = User.objects.create(
                        username="Bin_bot",
                        email="bin@system.com",
                        password=make_password('bin_password_' + str(random.randint(1000, 9999))),
                        is_active=True,
                        status="Online",
                        role="System Bot"
                    )
                    print(f"✅ Created Bin: {bin_user.username} (ID: {bin_user.id})")
                else:
                    print(f"✅ Bin exists: {bin_user.username} (ID: {bin_user.id})")
                
                print(f"🤔 Attempting to create message:")
                print(f"   From: {bin_user.username} (ID: {bin_user.id})")
                print(f"   To: {user.username} (ID: {user.id})")
                
                message_text = f"Ваш код верифікації для входу: {code}. Код дійсний 10 хвилин."
                if lang != 'Українська':
                    message_text = f"Your verification code for login: {code}. Code valid for 10 minutes."
                
                try:
                    message = Message(
                        sender=bin_user,
                        receiver=user,
                        text=message_text,
                        timestamp=timezone.now()
                    )
                    
                    message.full_clean()
                    
                    message.save()
                    
                    print(f"✅ Message created successfully!")
                    print(f"   Message ID: {message.id}")
                    print(f"   Text: {message.text}")
                    print(f"   Time: {message.timestamp}")
                    
                except Exception as msg_error:
                    print(f"❌ Error creating message: {str(msg_error)}")
                    print(f"   Message fields check:")
                    print(f"   - sender type: {type(bin_user)}")
                    print(f"   - receiver type: {type(user)}")
                    print(f"   - sender_id: {bin_user.id if hasattr(bin_user, 'id') else 'NO ID'}")
                    print(f"   - receiver_id: {user.id if hasattr(user, 'id') else 'NO ID'}")
                    import traceback
                    traceback.print_exc()
                    
                    print(f"🔄 Trying alternative method...")
                    
                    from django.db import connection
                    with connection.cursor() as cursor:
                        cursor.execute(
                            "INSERT INTO messenger_message (sender_id, receiver_id, text, timestamp, is_read) VALUES (%s, %s, %s, %s, %s)",
                            [bin_user.id, user.id, message_text, timezone.now(), False]
                        )
                    print(f"✅ Message inserted via raw SQL")
                
            except Exception as e:
                print(f"❌ ERROR in Bin section: {str(e)}")
                print(f"   Error type: {type(e).__name__}")
                import traceback
                traceback.print_exc()
            
            request.session['reset_email'] = email
            request.session['verification_code'] = code
            request.session['verification_sent'] = True
            request.session['verification_code_expires'] = verification_code_obj.expires_at.isoformat()
            
            print(f"✅ Session saved:")
            print(f"   Email: {email}")
            print(f"   Code: {code}")
            print(f"   Expires: {verification_code_obj.expires_at}")
            
            print(f"🔍 DEBUG ENTER_GMAIL END")
            print("="*50 + "\n")
            
            return redirect('forgot-password')
            
        except User.DoesNotExist:
            print(f"❌ User with email {email} not found")
            messages.error(request,
                'Account with this email not found' if lang != 'Українська'
                else 'Акаунт з таким email не знайдено'
            )
            return render(request, 'login/enter-gmail.html', {
                'lang': lang,
                'email': email
            })
        except Exception as e:
            print(f"❌ General error: {str(e)}")
            import traceback
            traceback.print_exc()
            messages.error(request,
                'Error generating code. Please try again.' if lang != 'Українська'
                else 'Помилка генерації коду. Спробуйте ще раз.'
            )
            return render(request, 'login/enter-gmail.html', {"lang": lang})

    return render(request, 'login/enter-gmail.html', {
        'lang': lang,
        'show_code': False
    })

def forgot_password(request):
    lang = "English"
    if request.session.get("language"):
        lang = request.session["language"]
    elif request.user.is_authenticated and hasattr(request.user, "language"):
        lang = request.user.language
        
    if not request.session.get('verification_sent'):
        return redirect('enter-gmail')
    
    email = request.session.get('reset_email')
    verification_code = request.session.get('verification_code')
    
    expires_str = request.session.get('verification_code_expires')
    is_code_valid = True
    
    if expires_str:
        try:
            expires = timezone.datetime.fromisoformat(expires_str)
            if timezone.now() > expires:
                is_code_valid = False
                if lang == 'Українська':
                    message_text = 'Код верифікації закінчився. Будь ласка, запросіть новий.'
                else:
                    message_text = 'Verification code has expired. Please request a new one.'
                
                messages.error(request, message_text)
                request.session.pop('verification_sent', None)
                request.session.pop('reset_email', None)
                request.session.pop('verification_code', None)
                request.session.pop('verification_code_expires', None)
                return redirect('enter-gmail')
        except Exception as e:
            is_code_valid = False
    
    if request.method == 'POST':
        entered_code = request.POST.get('verification_code', '').strip()
        stored_code = request.session.get('verification_code')
        
        if not is_code_valid:
            if lang == 'Українська':
                message_text = 'Код верифікації недійсний'
            else:
                message_text = 'Verification code is invalid'
            messages.error(request, message_text)
            return redirect('enter-gmail')
        
        if entered_code == stored_code:
            User = get_user_model()
            try:
                user = User.objects.get(email=email)
                
                user.backend = 'django.contrib.auth.backends.ModelBackend'
                auth_login(request, user)
                
                try:
                    bin_user = User.objects.filter(username__in=["Bin","Bin_bot"]).first()
                    welcome_message = f"Вітаємо, {user.username}! Ви успішно увійшли в систему."
                    if lang != 'Українська':
                        welcome_message = f"Welcome, {user.username}! You have successfully logged in."
                    
                    Message.objects.create(
                        sender=bin_user,
                        receiver=user,
                        text=welcome_message,
                        timestamp=timezone.now()
                    )
                except Exception as e:
                    print(f"Could not send welcome message from Bin: {e}")
                
                request.session.pop('verification_sent', None)
                request.session.pop('reset_email', None)
                request.session.pop('verification_code', None)
                request.session.pop('verification_code_expires', None)
                
                messages.success(request,
                    f'Вітаємо, {user.username}! Ви успішно увійшли.' if lang == 'Українська'
                    else f'Welcome, {user.username}! You have successfully logged in.'
                )
                return redirect('home')
                
            except User.DoesNotExist:
                messages.error(request,
                    'Користувача не знайдено' if lang == 'Українська'
                    else 'User not found'
                )
                return redirect('enter-gmail')
        else:
            messages.error(request,
                'Невірний код підтвердження' if lang == 'Українська'
                else 'Incorrect verification code'
            )
    
    return render(request, 'login/forgot-password.html', {
        'email': email,
        'verification_code': verification_code if is_code_valid else None,
        'lang': lang,
        'instructions': 'Введіть код з повідомлення від Bin_bot' if lang == 'Українська' else 'Enter the code from Bin_bot message'
    })

def send_code(to_email):
    code = random.randint(100000, 999999)
    
    try:
        user = User.objects.get(email=to_email)
        
        try:
            bin_user = User.objects.filter(username__in=["Bin","Bin_bot"]).first()
            if not bin_user:
                bin_user = User.objects.create(
                    username="Bin_bot",
                    email='bin@system.com',
                    password=make_password('bin_password'),
                    is_active=True,
                    status='Online',
                    role='System Bot'
                )
            
            message = Message.objects.create(
                sender=bin_user,
                receiver=user,
                text=f"Ваш код верифікації: {code}. Код дійсний 10 хвилин.",
                timestamp=timezone.now()
            )
            
            print(f"✅ Code message sent to chat from Bin to {user.username}")
            
        except Exception as e:
            print(f"⚠️ Could not create Bin message: {e}")
        
        send_mail(
            subject='Код підтвердження - Bin Messenger',
            message=f'Ваш код підтвердження: {code}\nКод дійсний протягом 10 хвилин.',
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[to_email],
            fail_silently=False,
            html_message=f'''
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 10px;">
                    <h2 style="color: #0056b3; text-align: center;">Код підтвердження</h2>
                    <p>Вітаємо!</p>
                    <p>Ви отримали цей лист, тому що хтось (можливо, ви) намагається відновити доступ до вашого акаунта в <strong>Bin Messenger</strong>.</p>
                    
                    <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; text-align: center; margin: 20px 0; border: 2px dashed #28a745;">
                        <p style="margin: 0; font-size: 14px; color: #666;">Ваш код підтвердження:</p>
                        <h1 style="color: #28a745; font-size: 48px; margin: 10px 0; letter-spacing: 5px;">{code}</h1>
                        <p style="margin: 0; font-size: 14px; color: #666;">Код дійсний протягом <strong>10 хвилин</strong></p>
                    </div>
                    
                    <p><strong>Якщо ви не намагалися відновити пароль:</strong></p>
                    <ul>
                        <li>Просто проігноруйте цей лист</li>
                        <li>Код автоматично стане недійсним через 10 хвилин</li>
                        <li>Ваш акаунт залишається в безпеці</li>
                    </ul>
                    
                    <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
                    
                    <p style="font-size: 12px; color: #666; text-align: center;">
                        Це автоматичне повідомлення. Будь ласка, не відповідайте на нього.<br>
                        © 2023 Bin Messenger. Усі права захищені.
                    </p>
                </div>
            </body>
            </html>
            '''
        )
        
        print(f"✓ Email sent to {to_email}")
        print(f"📧 Code: {code}")
        return code
        
    except User.DoesNotExist:
        print(f"✗ User with email {to_email} not found")
        return None
    except smtplib.SMTPAuthenticationError as e:
        print(f"✗ SMTP Authentication Error for {to_email}: {e}")
        return None
    except Exception as e:
        print(f"✗ General email error for {to_email}: {e}")
        return None

@login_required
def view_verification_codes(request):
    codes = EmailVerificationCode.objects.all().order_by('-created_at')
    
    total_codes = codes.count()
    valid_codes = codes.filter(expires_at__gt=timezone.now(), is_used=False).count()
    used_codes = codes.filter(is_used=True).count()
    expired_codes = codes.filter(expires_at__lt=timezone.now(), is_used=False).count()
    
    filter_type = request.GET.get('filter', 'all')
    if filter_type == 'valid':
        codes = codes.filter(expires_at__gt=timezone.now(), is_used=False)
    elif filter_type == 'used':
        codes = codes.filter(is_used=True)
    elif filter_type == 'expired':
        codes = codes.filter(expires_at__lt=timezone.now(), is_used=False)
    
    search_email = request.GET.get('search', '')
    if search_email:
        codes = codes.filter(email__icontains=search_email)
    
    paginator = Paginator(codes, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'verification_codes.html', {
        'codes': page_obj,
        'total_codes': total_codes,
        'valid_codes': valid_codes,
        'used_codes': used_codes,
        'expired_codes': expired_codes,
        'filter_type': filter_type,
        'search_email': search_email,
        'lang': getattr(request.user, 'language', 'English')
    })

def is_verification_code_valid(request):
    expires_str = request.session.get('verification_code_expires')
    if not expires_str:
        return False
    
    try:
        expires = timezone.datetime.fromisoformat(expires_str)
        return timezone.now() < expires
    except:
        return False
    
class VerificationCodeCleanupMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        expires_str = request.session.get('verification_code_expires')
        if expires_str:
            try:
                expires = timezone.datetime.fromisoformat(expires_str)
                if timezone.now() > expires:
                    request.session.pop('verification_sent', None)
                    request.session.pop('reset_email', None)
                    request.session.pop('verification_code', None)
                    request.session.pop('verification_code_expires', None)
            except:
                pass
        
        response = self.get_response(request)
        return response
    
class VerificationCodeCleanupMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        expires_str = request.session.get('verification_code_expires')
        if expires_str:
            try:
                expires = timezone.datetime.fromisoformat(expires_str)
                if timezone.now() > expires:
                    request.session.pop('verification_sent', None)
                    request.session.pop('reset_email', None)
                    request.session.pop('verification_code', None)
                    request.session.pop('verification_code_expires', None)
            except:
                pass
        
        response = self.get_response(request)
        return response

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
def search_users(request):
    query = request.GET.get('q', '').strip()
    results = []

    if query:
        users = User.objects.filter(
            Q(your_tag__icontains=query) | 
            Q(username__icontains=query)
        )[:10]
        
        results = []
        for u in users:
            user_data = {
                'username': u.username,
                'your_tag': u.your_tag or '',
            }
            if u.photo and u.photo.url:
                user_data['avatar_url'] = u.photo.url
            else:
                if u.role == "System Bot" or u.username in ["Bin","Bin_bot"]:
                    user_data['avatar_url'] = '/static/pictures/bin.jpg'
                else:
                    user_data['avatar_url'] = '/static/pictures/login.png' 
            results.append(user_data)

    return JsonResponse(results, safe=False)

@login_required(login_url='login')
def upload_avatar(request):
    user = request.user

    if request.method == 'POST' and request.FILES.get('photo'):
        photo = request.FILES['photo']
        filename = photo.name.lower()

        if filename.endswith('.gif') and user.subscribe == 'Basic':
            messages.error(
                request,
                "Гіф-аватари доступні лише для підписки Bin+ або Bin Premium."
                if getattr(user, 'language', 'English') == 'Українська'
                else "GIF avatars are available only for Bin+ or Bin Premium subscriptions."
            )
            return redirect('home')

        user.photo = photo
        user.save()

        messages.success(
            request,
            "Аватар оновлено!" if getattr(user, 'language', 'English') == 'Українська' else "Avatar updated!"
        )
        return redirect('home')

    return redirect('home')

@login_required(login_url='login')
def upload_background(request):
    user = request.user

    if request.method == 'POST' and request.FILES.get('background'):
        background = request.FILES['background']
        filename = background.name.lower()

        if user.subscribe == 'Basic':
            messages.error(
                request,
                "Фони профілю доступні лише для підписки Bin+ або Bin Premium."
                if getattr(user, 'language', 'English') == 'Українська'
                else "Profile backgrounds are available only for Bin+ or Bin Premium subscriptions."
            )
            return redirect('home')
        
        if filename.endswith('.gif'):
            msg_text = (
                "GIF-фони не підтримуються. Будь ласка, завантажте зображення."
                if getattr(user, 'language', 'English') == 'Українська'
                else "GIF backgrounds are not supported. Please upload an image."
            )
            is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'
            if is_ajax:
                return JsonResponse({'success': False, 'error': msg_text}, status=400)
            messages.error(request, msg_text)
            return redirect('home')

        user.background = background
        user.save()

        success_message = "Фон оновлено!" if getattr(user, 'language', 'English') == 'Українська' else "Background updated!"
        is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'

        if is_ajax:
            return JsonResponse({
                'success': True,
                'background_url': user.background.url if user.background and hasattr(user.background, 'url') else '',
                'message': success_message
            })

        messages.success(
            request,
            success_message
        )
        return redirect('home')

    return redirect('home')


@login_required(login_url='login')
@require_POST
def set_builtin_background(request):
    """Set a built-in background by copying a server-side image into user's background file field."""
    user = request.user

    if user.subscribe == 'Basic':
        return JsonResponse({'success': False, 'error': 'Not allowed'}, status=403)

    try:
        payload = json.loads(request.body.decode('utf-8'))
        builtin = payload.get('builtin')
    except Exception:
        return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)

    if not builtin or '..' in builtin or '/' in builtin or '\\' in builtin:
        return JsonResponse({'success': False, 'error': 'Invalid filename'}, status=400)

    import os
    from django.core.files import File as DjangoFile

    static_path = os.path.join(settings.BASE_DIR, 'static', 'wallpapers', builtin)
    media_path = os.path.join(settings.BASE_DIR, 'media', 'backgrounds', builtin)

    source_path = None
    if os.path.exists(static_path):
        source_path = static_path
    elif os.path.exists(media_path):
        source_path = media_path

    if not source_path:
        return JsonResponse({'success': False, 'error': 'File not found'}, status=404)

    try:
        with open(source_path, 'rb') as f:
            django_file = DjangoFile(f)
            user.background.save(builtin, django_file, save=True)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

    return JsonResponse({'success': True, 'background_url': user.background.url if user.background and hasattr(user.background, 'url') else ''})

def _get_js_utilities_for_user(user):
    current_year = now().year
    themes = {
        'light': {
            'bg': '#f7fafc',
            'surface': '#ffffff',
            'text': '#000000',
            'accent': '#0d6efd',
            'muted': '#666'
        },
        'dark': {
            'bg': '#0b1220',
            'surface': '#0f1720',
            'text': '#e6eef6',
            'accent': '#60a5fa',
            'muted': '#9ca3af'
        },
        'pink': {
            'bg': '#fff6fb',
            'surface': '#ffffff',
            'text': '#2b2a2a',
            'accent': '#ff6fa3',
            'muted': '#666'
        },
        'green': {
            'bg': '#f6fffb',
            'surface': '#ffffff',
            'text': '#022b22',
            'accent': '#10b981',
            'muted': '#666'
        }
    }

    utilities_available = ['formatTime', 'applyTheme', 'truncateText']

    return {
        'themes': themes,
        'current_year': current_year,
        'user_language': getattr(user, 'language', 'English'),
        'utilities_available': utilities_available,
    }


def format_message_time(timestamp):
    if not timestamp:
        return ''
    if isinstance(timestamp, str):
        try:
            timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        except Exception:
            return ''
    elif not isinstance(timestamp, datetime):
        return ''

    now_dt = now()
    if timestamp.date() == now_dt.date():
        return timestamp.strftime('%H:%M')
    elif timestamp.year == now_dt.year:
        return timestamp.strftime('%b %d')
    else:
        return timestamp.strftime('%Y-%m-%d')


def get_sticker_categories_localized(user_language='English'):
    is_uk = user_language == 'Українська'
    return {
        'people': 'Люди' if is_uk else 'People',
        'animals': 'Тварини' if is_uk else 'Animals',
        'transport': 'Транспорт' if is_uk else 'Transport',
        'nature': 'Природа' if is_uk else 'Nature',
        'food': 'Їжа' if is_uk else 'Food',
        'love': 'Любов' if is_uk else 'Love',
        'flags': 'Прапори' if is_uk else 'Flags',
        'hands': 'Руки' if is_uk else 'Hands',
        'misc': 'Інше' if is_uk else 'Misc',
        'extras': 'Додатково' if is_uk else 'Extras'
    }


@login_required
def get_js_utilities(request):
    """Return JS utilities JSON for the front-end (inlined implementation)."""
    user = request.user
    return JsonResponse(_get_js_utilities_for_user(user))

@login_required
def update_profile(request):
    if request.method == 'POST':
        user = request.user
        user.username = request.POST.get('username', user.username)
        desc = request.POST.get('description', user.description)

        if user.subscribe == 'Bin_premium':
            max_len = 150
        elif user.subscribe == 'Bin+':
            max_len = 100
        else:
            max_len = 70

        if desc is None:
            desc = ''
        if len(desc) > max_len:
            desc = desc[:max_len]
            messages.warning(request, (
                "Опис був обрізаний до максимальної довжини." if getattr(user, 'language', 'English') == 'Українська' else "Description was truncated to the maximum length."
            ))

        user.description = desc
        
        your_tag = request.POST.get('your_tag', user.your_tag)
        if your_tag:
            your_tag = your_tag.lstrip('@')
            user.your_tag = '@' + your_tag
        else:
            user.your_tag = ''
        
        day = request.POST.get('day')
        month = request.POST.get('month')
        year = request.POST.get('year')

        if day and month and year:
            try:
                user.birthday = date(int(year), int(month), int(day))
            except Exception:
                pass
            
        user.show_birthday = 'show_birthday' in request.POST

        if 'photo' in request.FILES:
            photo = request.FILES['photo']
            filename = photo.name.lower()
            if filename.endswith('.gif') and user.subscribe == 'Basic':
                messages.error(
                    request,
                    "Гіф-аватари доступні лише для підписки Bin+ або Bin Premium."
                    if getattr(user, 'language', 'English') == 'Українська'
                    else "GIF avatars are available only for Bin+ or Bin Premium subscriptions."
                )
                return redirect('home')
            user.photo = photo

        if 'background' in request.FILES:
            background = request.FILES['background']
            filename = background.name.lower()
            
            if user.subscribe == 'Basic':
                messages.error(
                    request,
                    "Фони профілю доступні лише для підписки Bin+ або Bin Premium."
                    if getattr(user, 'language', 'English') == 'Українська'
                    else "Profile backgrounds are available only for Bin+ or Bin Premium subscriptions."
                )
                return redirect('home')
            
            elif user.subscribe == 'Bin+' and filename.endswith('.gif'):
                messages.error(
                    request,
                    "Гіф-фони доступні лише для підписки Bin Premium."
                    if getattr(user, 'language', 'English') == 'Українська'
                    else "GIF backgrounds are available only for Bin Premium subscription."
                )
                return redirect('home')
            
            user.background = background

        if request.POST.get('remove_background') == 'true':
            user.background = None

        custom_button = request.POST.get('custom_button')
        if custom_button is not None:
            user.custom_button_enabled = str(custom_button).lower() in ['1','true','on','yes']

        custom_option = request.POST.get('custom_option')
        if custom_option in ['1','2','3']:
            user.custom_option = custom_option

        user.save()
        messages.success(request, "Profile updated successfully." if getattr(user, 'language', 'English') != 'Українська' else "Профіль оновлено!")
        return redirect('home')

    return redirect('home')

@login_required(login_url='login')
def reset_avatar(request):
    if request.method == 'POST':
        user = request.user
        
        user.photo = 'login.png'
        user.save()
        
        is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'
        
        if is_ajax:
            return JsonResponse({
                'success': True,
                'avatar_url': '/static/pictures/login.png',
                'message': 'Аватар скинуто до базового!' if getattr(user, 'language', 'English') == 'Українська' else 'Avatar reset to default!'
            })
        else:
            messages.success(
                request,
                "Аватар скинуто до базового!" if getattr(user, 'language', 'English') == 'Українська' else "Avatar reset to default!"
            )
            return redirect('home')
    
    return JsonResponse({'error': 'Invalid request'}, status=400)


@login_required
def toggle_custom_button(request):
    """AJAX endpoint to toggle the custom button setting for a user."""
    if request.method == 'POST':
        try:
            if request.content_type == 'application/json':
                data = json.loads(request.body)
                enabled = data.get('enabled')
            else:
                enabled = request.POST.get('enabled')

            enabled_bool = str(enabled).lower() in ['1', 'true', 'on', 'yes'] if enabled is not None else False
            user = request.user
            user.custom_button_enabled = enabled_bool
            user.save()
            return JsonResponse({'success': True, 'enabled': enabled_bool})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

    return JsonResponse({'error': 'Invalid request'}, status=400)

@login_required(login_url='login')
def remove_background(request):
    user = request.user

    if request.method == 'POST':
        user.background = None
        user.save()

        messages.success(
            request,
            "Фон видалено!" if getattr(user, 'language', 'English') == 'Українська' else "Background removed!"
        )
        return redirect('home')

    return redirect('home')

@login_required
def send_message(request):
    if request.method == 'POST':
        try:
            if request.content_type == 'application/json':
                try:
                    data = json.loads(request.body)
                except json.JSONDecodeError:
                    return JsonResponse({'error': 'Invalid JSON'}, status=400)
            else:
                data = request.POST
            
            receiver_username = data.get('receiver')
            text = data.get('text')
            
            if not receiver_username or not isinstance(receiver_username, str):
                return JsonResponse({'error': 'Invalid receiver'}, status=400)
            
            if not text or not isinstance(text, str) or text.strip() == '':
                return JsonResponse({'error': 'Message text cannot be empty'}, status=400)
            
            if len(text.strip()) > 1000:
                return JsonResponse({'error': 'Message too long'}, status=400)
            
            text = text.strip()
            receiver_username = receiver_username.strip()
            
            if receiver_username == request.user.username:
                return JsonResponse({'error': 'Cannot send message to yourself'}, status=400)
            
            try:
                receiver = User.objects.get(username=receiver_username)
            except User.DoesNotExist:
                return JsonResponse({'error': 'User not found'}, status=404)

            if receiver.role == 'System Bot' or receiver.username.lower() in ['bin', 'bin_bot']:
                return JsonResponse({'error': 'Cannot send messages to system bots'}, status=400)
            
            message = Message.objects.create(
                sender=request.user,
                receiver=receiver,
                text=text
            )
            
            return JsonResponse({
                'success': True, 
                'message_id': message.id,
                'timestamp': message.timestamp.isoformat(),
                'text': message.text
            })
            
        except Exception as e:
            print(f"Error sending message: {str(e)}")
            return JsonResponse({'error': 'Server error: ' + str(e)}, status=500)
    
    return JsonResponse({'error': 'Invalid method'}, status=400)
    
@login_required
def get_recent_contacts(request):
    if not request.user.is_authenticated:
        return JsonResponse([], safe=False)

    try:
        subquery = Message.objects.filter(
            Q(sender=request.user) | Q(receiver=request.user)
        ).values(
            'sender', 'receiver'
        ).annotate(
            last_message_time=Max('timestamp')
        ).order_by('-last_message_time')

        contacts = []
        processed_users = set()

        for item in subquery:
            if item['sender'] == request.user.id:
                contact_id = item['receiver']
            else:
                contact_id = item['sender']

            if contact_id in processed_users:
                continue

            if contact_id == request.user.id:
                continue

            try:
                contact_user = User.objects.get(id=contact_id)

                last_message = Message.objects.filter(
                    (Q(sender=request.user) & Q(receiver=contact_user)) |
                    (Q(sender=contact_user) & Q(receiver=request.user))
                ).order_by('-timestamp').first()

                unread_count = Message.objects.filter(
                    sender=contact_user,
                    receiver=request.user,
                    is_read=False
                ).count()

                if contact_user.photo and hasattr(contact_user.photo, 'url'):
                    avatar_url = contact_user.photo.url
                else:
                    avatar_url = '/static/pictures/login.png'

                contacts.append({
                    'id': contact_user.id,
                    'username': contact_user.username,
                    'your_tag': contact_user.your_tag or '',
                    'avatar_url': avatar_url,
                    'last_message': last_message.text if last_message else 'No messages yet',
                    'last_message_time': last_message.timestamp.isoformat() if last_message else None,
                    'unread_count': unread_count
                })

                processed_users.add(contact_id)

                if len(contacts) >= 15:
                    break

            except User.DoesNotExist:
                continue

        system_usernames = ['Bin_bot', 'Favorites']
        for sys_un in system_usernames:
            if not any(c['username'].lower() == sys_un.lower() for c in contacts):
                try:
                    sys_user = None
                    if sys_un.lower() == 'bin_bot':
                        sys_user = User.objects.filter(username__iexact='Bin_bot').first() or create_bin_user()
                    else:
                        sys_user = User.objects.filter(username__iexact='Favorites').first()
                        if not sys_user:
                            sys_user = User.objects.create(
                                username='Favorites',
                                photo='static/pictures/login.png',
                                email=f'favorites@{request.get_host()}',
                                password=make_password('favorites_system_password'),
                                description='System Favorites chat',
                                your_tag='@favorites',
                                status='Online',
                                is_active=True,
                                subscribe='System',
                                language='English',
                                role='System Bot'
                            )
                    if sys_user:
                        contacts.append({
                            'id': sys_user.id,
                            'username': sys_user.username,
                            'your_tag': sys_user.your_tag or '',
                            'avatar_url': sys_user.photo.url if getattr(sys_user, 'photo', None) and hasattr(sys_user.photo, 'url') else '/static/pictures/bin.jpg' if getattr(sys_user, 'role', '') == 'System Bot' else '/static/pictures/login.png',
                            'last_message': 'No messages yet',
                            'last_message_time': None,
                            'unread_count': 0
                        })
                except Exception:
                    pass

        return JsonResponse(contacts, safe=False)

    except Exception as e:
        print(f"Error getting recent contacts: {str(e)}")
        return JsonResponse([], safe=False)

@login_required
def mark_messages_read(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=400)
    
    try:
        data = json.loads(request.body)
        sender_username = data.get('sender')
        
        if not sender_username:
            return JsonResponse({'error': 'Sender username required'}, status=400)
        
        try:
            sender = User.objects.get(username=sender_username)
        except User.DoesNotExist:
            return JsonResponse({'error': 'Sender not found'}, status=404)
        
        updated = Message.objects.filter(
            sender=sender,
            receiver=request.user,
            is_read=False
        ).update(is_read=True)
        
        return JsonResponse({
            'success': True,
            'marked_count': updated
        })
        
    except Exception as e:
        print(f"Error marking messages as read: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def save_note(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=400)
    
    try:
        data = json.loads(request.body)
        text = data.get('text', '').strip()
        
        if not text:
            return JsonResponse({'error': 'Note text cannot be empty'}, status=400)
        
        note = Message.objects.create(
            sender=request.user,
            receiver=request.user,
            text=text,
            is_read=True
        )
        
        return JsonResponse({
            'success': True,
            'note_id': note.id,
            'timestamp': note.timestamp.isoformat()
        })
        
    except Exception as e:
        print(f"Error saving note: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def get_notes(request):
    try:
        notes = Message.objects.filter(
            sender=request.user,
            receiver=request.user
        ).order_by('timestamp')
        
        notes_data = [{
            'id': note.id,
            'text': note.text,
            'timestamp': note.timestamp.isoformat(),
            'is_file': note.is_file,
            'file_url': default_storage.url(note.file) if note.file else None,
            'file_name': note.file_name,
            'file_type': note.file_type,
            'file_size': note.file_size
        } for note in notes]
        
        return JsonResponse(notes_data, safe=False)
        
    except Exception as e:
        print(f"Error getting notes: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def get_bin_messages(request):
    try:
        bin_user = User.objects.filter(username__iexact='Bin_bot').first()
        if not bin_user:
            bin_user = create_bin_user()

        msgs = Message.objects.filter(
            (Q(sender=bin_user) & Q(receiver=request.user)) |
            (Q(sender=request.user) & Q(receiver=bin_user))
        ).order_by('timestamp')

        messages_data = []
        for msg in msgs:
            messages_data.append({
                'id': msg.id,
                'sender': msg.sender.username if msg.sender else None,
                'text': msg.text,
                'timestamp': msg.timestamp.isoformat() if msg.timestamp else None,
                'is_sent': msg.sender == request.user,
                'is_file': getattr(msg, 'is_file', False),
                'file_url': default_storage.url(msg.file) if getattr(msg, 'file', None) else None,
                'file_name': getattr(msg, 'file_name', None),
                'file_type': getattr(msg, 'file_type', None),
                'file_size': getattr(msg, 'file_size', None),
            })

        return JsonResponse(messages_data, safe=False)
    except Exception as e:
        print(f"Error loading Bin messages: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


def get_room_name(user1, user2):
    users = sorted([str(user1).lower(), str(user2).lower()])
    return f"chat_{users[0]}_{users[1]}"

@login_required
def edit_message(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'}, status=400)
    
    try:
        data = json.loads(request.body)
        message_id = data.get('message_id')
        new_text = data.get('text', '').strip()
        
        if not message_id or not new_text:
            return JsonResponse({'success': False, 'error': 'Invalid parameters'}, status=400)
        
        try:
            message = Message.objects.get(id=message_id)
        except Message.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Message not found'}, status=404)
        
        if message.sender != request.user:
            return JsonResponse({'success': False, 'error': 'You can only edit your own messages'}, status=403)
        
        if not hasattr(message, 'original_text'):
            message.original_text = message.text
        
        message.text = new_text
        message.edited_at = timezone.now()
        message.save()
        
        try:
            room_name = get_room_name(request.user.username, message.receiver.username)
            channel_layer = get_channel_layer()
            
            async_to_sync(channel_layer.group_send)(
                room_name,
                {
                    'type': 'message_edited',
                    'message_id': message_id,
                    'text': new_text,
                    'sender': request.user.username,
                    'receiver': message.receiver.username,
                    'timestamp': message.edited_at.isoformat(),
                    'edited': True
                }
            )
        except Exception as e:
            print(f"Error broadcasting edit notification: {str(e)}")
        
        return JsonResponse({
            'success': True,
            'message_id': message.id,
            'text': new_text,
            'timestamp': message.edited_at.isoformat(),
            'edited': True
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        print(f"Error editing message: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@login_required
def delete_message(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'}, status=400)
    
    try:
        data = json.loads(request.body)
        message_id = data.get('message_id')
        
        if not message_id:
            return JsonResponse({'success': False, 'error': 'Message ID required'}, status=400)
        
        try:
            message = Message.objects.get(id=message_id)
        except Message.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Message not found'}, status=404)
        
        if message.sender != request.user and message.receiver != request.user:
            return JsonResponse({'success': False, 'error': 'You can only delete messages in chats you participate in'}, status=403)

        if getattr(message, 'file', None):
            try:
                message.file.delete(save=False)
            except Exception as e:
                print(f"Error deleting attached file: {str(e)}")
        
        sender_username = message.sender.username
        receiver_username = message.receiver.username
        message_id_to_delete = message.id
        
        message.delete()
        
        try:
            room_name = get_room_name(sender_username, receiver_username)
            channel_layer = get_channel_layer()
            
            async_to_sync(channel_layer.group_send)(
                room_name,
                {
                    'type': 'message_deleted',
                    'message_id': message_id_to_delete,
                    'sender': sender_username,
                    'receiver': receiver_username,
                }
            )
        except Exception as e:
            print(f"Error broadcasting delete notification: {str(e)}")
        
        return JsonResponse({'success': True})
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        print(f"Error deleting message: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@login_required
def send_message(request):
    print(f"\n{'='*50}")
    print(f"DEBUG send_message - User: {request.user.username}")
    print(f"Method: {request.method}")
    print(f"Content-Type: {request.content_type}")
    print(f"Headers: {dict(request.headers)}")
    
    if request.method != 'POST':
        print("ERROR: Not POST method")
        return JsonResponse({'error': 'Invalid method'}, status=400)
    
    try:
        if request.content_type == 'application/json':
            try:
                data = json.loads(request.body.decode('utf-8'))
                print(f"JSON data: {data}")
            except Exception as e:
                print(f"JSON parse error: {e}")
                return JsonResponse({'error': 'Invalid JSON'}, status=400)
        else:
            data = request.POST.dict()
            print(f"Form data: {data}")
        
        receiver_username = data.get('receiver', '').strip()
        text = data.get('text', '').strip()
        
        print(f"Receiver: {receiver_username}")
        print(f"Text: {text}")
        
        if not receiver_username:
            return JsonResponse({'error': 'Receiver is required'}, status=400)
        
        if not text:
            return JsonResponse({'error': 'Message text is required'}, status=400)
        
        try:
            receiver = User.objects.get(username=receiver_username)
            print(f"Receiver found: {receiver.username}")
        except User.DoesNotExist:
            print(f"Receiver not found: {receiver_username}")
            return JsonResponse({'error': f'User "{receiver_username}" not found'}, status=404)
        
        message = Message.objects.create(
            sender=request.user,
            receiver=receiver,
            text=text
        )
        
        print(f"Message created: ID={message.id}")
        
        return JsonResponse({
            'success': True,
            'message_id': message.id,
            'text': message.text,
            'sender': request.user.username,
            'receiver': receiver.username,
            'timestamp': message.timestamp.isoformat(),
        })
        
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
def get_verification_code_bin(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=400)
    
    try:
        user = request.user
        
        code = str(random.randint(100000, 999999))
        print(f"✅ Generated Bin verification code for {user.username}: {code}")
        
        bin_user = User.objects.filter(username__iexact='Bin_bot').first()
        if not bin_user:
            bin_user = create_bin_user()
        
        lang = getattr(user, 'language', 'English')
        
        if lang == 'Українська':
            message_text = f"Ваш код верифікації: {code}. Код дійсний 10 хвилин."
        else:
            message_text = f"Your verification code: {code}. Code valid for 10 minutes."
        
        message = Message.objects.create(
            sender=bin_user,
            receiver=user,
            text=message_text,
            timestamp=timezone.now()
        )
        
        try:
            channel_layer = get_channel_layer()
            room_name = '_'.join(sorted([user.username, 'Bin']))
            room_name = re.sub(r'[^\\w]', '', room_name)
            async_to_sync(channel_layer.group_send)(
                'chat_' + room_name,
                {
                    'type': 'chat_message',
                    'message': message_text,
                    'sender': 'Bin',
                    'receiver': user.username,
                    'timestamp': message.timestamp.isoformat(),
                    'message_id': message.id
                }
            )
        except Exception as e:
            print('Failed to broadcast Bin message:', str(e))

        print(f"✅ Verification code sent from Bin to {user.username}")
        
        if user.email:
            EmailVerificationCode.objects.create(
                user=user,
                email=user.email,
                code=code,
                expires_at=timezone.now() + timedelta(minutes=10)
            )
        
        return JsonResponse({
            'success': True,
            'code': code,
            'message': message_text,
            'message_id': message.id,
            'expires_at': (timezone.now() + timedelta(minutes=10)).isoformat()
        })
        
    except Exception as e:
        print(f"❌ Error generating Bin code: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
def get_recent_contacts(request):
    if not request.user.is_authenticated:
        return JsonResponse([], safe=False)
    
    try:
        subquery = Message.objects.filter(
            (Q(sender=request.user) | Q(receiver=request.user))
        ).exclude(
            Q(sender__username__in=["Bin","Bin_bot"]) | Q(receiver__username__in=["Bin","Bin_bot"]) 
        ).values(
            'sender', 'receiver'
        ).annotate(
            last_message_time=Max('timestamp')
        ).order_by('-last_message_time')
        
        contacts = []
        processed_users = set()
        
        for item in subquery:
            if item['sender'] == request.user.id:
                contact_id = item['receiver']
            else:
                contact_id = item['sender']
            
            if contact_id in processed_users:
                continue
                
            if contact_id == request.user.id:
                continue
                
            try:
                contact_user = User.objects.get(id=contact_id)
                
                if contact_user.role == 'System Bot' or contact_user.username in ["Bin","Bin_bot"]:
                    continue
                
                last_message = Message.objects.filter(
                    (Q(sender=request.user) & Q(receiver=contact_user)) |
                    (Q(sender=contact_user) & Q(receiver=request.user))
                ).order_by('-timestamp').first()
                
                unread_count = Message.objects.filter(
                    sender=contact_user,
                    receiver=request.user,
                    is_read=False
                ).count()
                
                if contact_user.photo and hasattr(contact_user.photo, 'url'):
                    avatar_url = contact_user.photo.url
                else:
                    avatar_url = '/static/pictures/login.png'
                
                contacts.append({
                    'id': contact_user.id,
                    'username': contact_user.username,
                    'your_tag': contact_user.your_tag or '',
                    'avatar_url': avatar_url,
                    'last_message': last_message.text if last_message else 'No messages yet',
                    'last_message_time': last_message.timestamp.isoformat() if last_message else None,
                    'unread_count': unread_count
                })
                
                processed_users.add(contact_id)
                
                if len(contacts) >= 15:
                    break
                    
            except User.DoesNotExist:
                continue
        
        return JsonResponse(contacts, safe=False)
        
    except Exception as e:
        print(f"Error getting recent contacts: {str(e)}")
        return JsonResponse([], safe=False)

def get_user_by_tag(request):
    tag = request.GET.get('tag', '').strip().lstrip('@')
    
    if not tag:
        return JsonResponse({'success': False, 'error': 'No tag provided'})

    if tag.lower() == 'bin':
        return JsonResponse({'success': False, 'error': f'User with tag @{tag} not found'})
    
    try:
        if tag.lower() == 'bin_bot':
            user = User.objects.filter(username__iexact='Bin_bot').first()
            if not user:
                user = create_bin_user()
        else:
            user = User.objects.filter(
                models.Q(your_tag__iexact=tag) | 
                models.Q(username__iexact=tag)
            ).first()
        
        if user:
            avatar = '/static/pictures/login.png'
            if user.photo and hasattr(user.photo, 'url'):
                avatar = user.photo.url
            elif user.role == 'System Bot' or user.username.lower() == 'bin_bot':
                avatar = '/static/pictures/bin.jpg'

            return JsonResponse({
                'success': True,
                'username': user.username,
                'your_tag': user.your_tag or '',
                'avatar_url': avatar
            })
        else:
            return JsonResponse({
                'success': False, 
                'error': f'User with tag @{tag} not found'
            })
            
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
    
def process_mentions_in_text(text):
    if not text:
        return text
    
    import re
    
    def replace_mention(match):
        username = match.group(1).lower()
        
        if username == "bin_bot":
            return f'<span class="message-mention" data-username="@bin_bot" onclick="openUserProfile(\'Bin_bot\')">@bin_bot</span>'
        
        try:
            user = User.objects.filter(
                Q(username__iexact=username) | 
                Q(your_tag__iexact=f"@{username}")
            ).first()
            
            if user:
                return f'<span class="message-mention" data-username="@{user.username}" onclick="openUserProfile(\'{user.username}\')">@{user.username}</span>'
        except:
            pass
        
        return match.group(0)
    
    pattern = r'@(\w+)'
    return re.sub(pattern, replace_mention, text)

@login_required
def change_password(request):
    if request.method == 'POST':
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        if not request.user.check_password(current_password):
            messages.error(request, 'Current password is incorrect')
            return redirect('home')
        
        if new_password != confirm_password:
            messages.error(request, 'New passwords do not match')
            return redirect('home')
        
        if len(new_password) < 8:
            messages.error(request, 'Password must be at least 8 characters long')
            return redirect('home')
        
        request.user.set_password(new_password)
        request.user.save()
        
        update_session_auth_hash(request, request.user)
        
        messages.success(request, 'Password changed successfully')
        return redirect('home')
    
    return redirect('home')

@login_required
def enable_2fa(request):
    if request.method == 'POST':
        request.user.two_factor_enabled = True
        request.user.save()
        messages.success(request, 'Two-factor authentication enabled')
    
    return redirect('home')

@login_required
def disable_2fa(request):
    if request.method == 'POST':
        request.user.two_factor_enabled = False
        request.user.save()
        messages.success(request, 'Two-factor authentication disabled')
    
    return redirect('home')

@login_required
def terminate_session(request):
    if request.method == 'POST':
        session_key = request.POST.get('session_key')
        messages.success(request, 'Session terminated successfully')
        return redirect('home')
    
    return redirect('home')

@login_required
def get_currency_conversion(request):
    try:
        user = request.user
        base_amount = Decimal(str(user.wallet or 0))
        base_currency = (user.currency or 'USD').upper()

        rates_to_usd = {
            'USD': Decimal('1.0'),
            'EUR': Decimal('1.091'),
            'GBP': Decimal('1.294'),
            'UAH': Decimal('0.0241'),
        }

        def format_currency_dec(d):
            s = f"{d:,.2f}"
            return s.replace(',', ' ').replace('.', ',')

        def convert(amount, base_cur, target_cur):
            usd = (amount * rates_to_usd.get(base_cur, Decimal('1.0')))
            target = (usd / rates_to_usd.get(target_cur, Decimal('1.0'))).quantize(Decimal('0.01'))
            return target

        targets = ['USD', 'EUR', 'GBP', 'UAH']
        symbols = {'USD': '$', 'EUR': '€', 'GBP': '£', 'UAH': '₴'}
        flags = {'USD': '🇺🇸', 'EUR': '🇪🇺', 'GBP': '🇬🇧', 'UAH': '🇺🇦'}

        converted = {}
        for t in targets:
            val = convert(base_amount, base_currency, t)
            converted[t] = {
                'value': str(val),
                'formatted': f"{flags[t]}{format_currency_dec(val)} {symbols[t]} {t}"
            }

        return JsonResponse({
            'success': True,
            'converted': converted,
            'price_converted': converted.get(base_currency, converted['USD'])['formatted']
        })

    except Exception as e:
        print(f"Currency conversion error: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
def upload_chat_file(request):
    print(f"Upload file request: {request.method}, files: {request.FILES}, POST: {request.POST}")
    
    if request.method == 'POST' and request.FILES.get('file'):
        file = request.FILES['file']
        receiver_username = request.POST.get('receiver')
        text = request.POST.get('text', '')
        
        print(f"File info: name={file.name}, size={file.size}, type={file.content_type}")
        print(f"Receiver: {receiver_username}, text: {text}")
        
        if not receiver_username:
            return JsonResponse({'error': 'Receiver is required'}, status=400)
        
        try:
            receiver = User.objects.get(username=receiver_username)
        except User.DoesNotExist:
            return JsonResponse({'error': 'Receiver not found'}, status=404)

        if receiver.role == 'System Bot' or receiver.username.lower() in ['bin', 'bin_bot']:
            return JsonResponse({'error': 'Cannot send files to system bots'}, status=400)
        
        max_size = get_file_size_limit(request.user)
        
        if file.size > max_size:
            limit_mb = max_size // (1024 * 1024)
            lang = getattr(request.user, 'language', 'English')
            
            if lang == 'Українська':
                error_msg = f'Розмір файлу перевищує ваш ліміт ({limit_mb}MB). Оновіть підписку, щоб відправляти більші файли.'
            else:
                error_msg = f'File size exceeds your limit ({limit_mb}MB). Upgrade your subscription to send larger files.'
            
            return JsonResponse({'error': error_msg}, status=400)
        
        allowed_types = [
            'image/jpeg', 'image/png', 'image/gif', 'image/webp',
            'application/pdf', 'text/plain',
            'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'application/zip', 'application/x-rar-compressed',
            'video/mp4', 'video/avi', 'video/quicktime', 'video/x-msvideo',
            'video/x-matroska', 'video/webm', 'video/mpeg'
        ]
        
        if file.content_type not in allowed_types:
            lang = getattr(request.user, 'language', 'English')
            
            if lang == 'Українська':
                error_msg = 'Недозволений тип файлу. Дозволені: зображення, відео, PDF, текстові файли, документи'
            else:
                error_msg = 'File type not allowed. Allowed types: images, videos, PDF, text files, documents'
            
            return JsonResponse({'error': error_msg}, status=400)
        
        file_extension = os.path.splitext(file.name)[1]
        timestamp = int(timezone.now().timestamp())
        safe_filename = f"chat_{request.user.id}_{receiver.id}_{timestamp}{file_extension}"
        
        file_content = file.read()
        saved_path = f'chat_files/{safe_filename}'
        
        try:
            saved_name = default_storage.save(saved_path, ContentFile(file_content))
            print(f"File saved as: {saved_name}")
            
            recent = Message.objects.filter(
                sender=request.user,
                receiver=receiver,
                file_name=file.name,
                file_size=file.size,
                timestamp__gte=timezone.now() - timedelta(seconds=10)
            ).first()

            if recent:
                print(f"Duplicate upload detected, reusing message id: {recent.id}")
                message = recent
            else:
                message = Message.objects.create(
                    sender=request.user,
                    receiver=receiver,
                    text=text,
                    file=saved_name,
                    file_name=file.name,
                    file_size=file.size,
                    file_type=file.content_type,
                    is_file=True
                )

            file_url = default_storage.url(saved_name)
            print(f"File URL: {file_url}")

            try:
                import re
                channel_layer = get_channel_layer()
                room_name = '_'.join(sorted([request.user.username, receiver.username]))
                room_group_name = 'chat_' + re.sub(r'[^\w]', '', room_name)

                async_to_sync(channel_layer.group_send)(
                    room_group_name,
                    {
                        'type': 'chat_message',
                        'message': text or '[file]',
                        'sender': request.user.username,
                        'receiver': receiver.username,
                        'timestamp': message.timestamp.isoformat(),
                        'file_url': file_url,
                        'file_name': message.file_name,
                        'file_type': message.file_type,
                        'file_size': message.file_size,
                        'message_id': message.id
                    }
                )
            except Exception as e:
                print(f"Error broadcasting file message: {e}")
            
            return JsonResponse({
                'success': True,
                'file_url': file_url,
                'file_name': message.file_name,
                'file_type': message.file_type,
                'file_size': message.file_size,
                'text': message.text,
                'message_id': message.id,
                'timestamp': message.timestamp.isoformat(),
                'sender': request.user.username
            })
            
        except Exception as e:
            print(f"Error saving file: {str(e)}")
            return JsonResponse({'error': f'Error saving file: {str(e)}'}, status=500)
    
    return JsonResponse({'error': 'Invalid request or no file provided'}, status=400)

@login_required
@require_POST
def save_video_state(request):
    try:
        data = json.loads(request.body)
        video_id = data.get('video_id')
        current_time = data.get('current_time', 0)
        is_paused = data.get('is_paused', True)
        
        request.session['current_video_id'] = video_id
        request.session['current_video_time'] = current_time
        request.session['current_video_paused'] = is_paused
        request.session.modified = True
        
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@require_POST
def clear_video_state(request):
    try:
        if 'current_video_id' in request.session:
            del request.session['current_video_id']
        if 'current_video_time' in request.session:
            del request.session['current_video_time']
        if 'current_video_paused' in request.session:
            del request.session['current_video_paused']
        request.session.modified = True
        
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def get_chat_messages(request):
    other_username = request.GET.get('username')
    if not other_username:
        return JsonResponse({'error': 'Username parameter required'}, status=400)

    try:
        if other_username.lower() == 'bin_bot':
            other_user = User.objects.filter(username__iexact='Bin_bot').first()
            if not other_user:
                other_user = create_bin_user()
        else:
            other_user = User.objects.get(username=other_username)

        messages = Message.objects.filter(
            (models.Q(sender=request.user) & models.Q(receiver=other_user)) |
            (models.Q(sender=other_user) & models.Q(receiver=request.user))
        ).order_by('timestamp')

        messages_data = []
        for msg in messages:
            message_data = {
                'id': msg.id,
                'text': msg.text,
                'timestamp': msg.timestamp.isoformat(),
                'is_sent': msg.sender == request.user,
                'is_read': msg.is_read,
                'sender': msg.sender.username,
                'sender_avatar': (msg.sender.photo.url if getattr(msg.sender, 'photo', None) and hasattr(msg.sender.photo, 'url') else ('/static/pictures/bin.jpg' if getattr(msg.sender, 'role', '') == 'System Bot' or msg.sender.username in ["Bin","Bin_bot"] else '/static/pictures/login.png')),
                'is_file': msg.is_file,
                'file_url': default_storage.url(msg.file) if msg.file else None,
                'file_name': msg.file_name,
                'file_type': msg.file_type,
                'file_size': msg.file_size,
                'edited': bool(msg.edited_at),
                'edited_at': msg.edited_at.isoformat() if msg.edited_at else None
            }
            messages_data.append(message_data)

        return JsonResponse(messages_data, safe=False)

    except User.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=404)
    except Exception as e:
        print(f"Error loading chat messages: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def start_chat(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=400)

    try:
        data = json.loads(request.body) if request.content_type == 'application/json' else request.POST
        other_username = (data.get('username') or data.get('receiver') or '').strip()
        if not other_username:
            return JsonResponse({'error': 'username required'}, status=400)

        if other_username.lower() == 'bin' or other_username.lower() == 'bin_bot':
            other_user = User.objects.filter(username__iexact='Bin_bot').first() or create_bin_user()
        else:
            other_user = User.objects.get(username=other_username)

        room_name = get_room_name(request.user.username, other_user.username)
        return JsonResponse({'success': True, 'room_name': room_name, 'username': other_user.username})

    except User.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=404)
    except Exception as e:
        print(f"Error starting chat: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)
        
    except User.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=404)
    except Exception as e:
        print(f"Error loading chat messages: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)

@require_POST
@csrf_exempt
def save_custom_option(request):
    if request.user.is_authenticated:
        try:
            data = json.loads(request.body)
            custom_option = data.get('custom_option')
            if custom_option in ['1', '2', '3', '4']:
                request.user.custom_option = custom_option
                request.user.save()
                return JsonResponse({'success': True})
            return JsonResponse({'success': False, 'error': 'Invalid option'})
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Invalid JSON'})
    return JsonResponse({'success': False, 'error': 'Not authenticated'})

@require_POST
@csrf_exempt
def toggle_custom_button(request):
    if request.user.is_authenticated:
        try:
            data = json.loads(request.body)
            enabled = data.get('enabled', False)
            request.user.custom_button_enabled = enabled
            request.user.save()
            return JsonResponse({'success': True})
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Invalid JSON'})
    return JsonResponse({'success': False, 'error': 'Not authenticated'})

@login_required
def save_button_text_color(request):
    if request.method == 'POST':
        try:
            if request.content_type == 'application/json':
                data = json.loads(request.body)
            else:
                data = request.POST
            text_color = data.get('button_text_color', '').strip().lower()
            if text_color not in ['white', 'black']:
                return JsonResponse({'success': False, 'error': 'Invalid color value'})
            request.user.color_text_button = text_color
            request.user.save()
            
            return JsonResponse({'success': True})
            
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Invalid JSON'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

def check_user_exists(request):
    username = request.GET.get('username', '')
    exists = User.objects.filter(username=username).exists()
    return JsonResponse({'exists': exists})

def create_bin_user():
    try:
        bin_user = User.objects.filter(username__in=["Bin"]).first()

        if bin_user:
            bin_user.description = "Official Bin Messenger bot. I provide verification codes and assistance."
            bin_user.your_tag = "@Bin"
            bin_user.status = "Online"
            bin_user.is_active = True
            bin_user.subscribe = 'Bin_premium'
            bin_user.subscription_end = None
            bin_user.subscription_period = 'forever'
            bin_user.role = "System Bot"
            bin_user.birthday = date(2025, 12, 20)

            if not bin_user.photo or getattr(bin_user.photo, 'name', '') in ['', 'login.png']:
                bin_user.photo = bin_user.photo

            bin_user.save()
            return bin_user

        else:
            bin_user = User.objects.create(
                username="Bin",
                photo='static/pictures/bin.jpg',
                email="bot@bin-messenger.com",
                password=make_password(
                    'bin_system_password_' + str(random.randint(1000, 9999))
                ),
                description="Official Bin Messenger bot. I provide verification codes and assistance.",
                your_tag="@Bin",
                status="Online",
                is_active=True,
                subscribe='Bin_premium',
                subscription_end=None,
                subscription_period='forever',
                language="English",
                role="System Bot",
                birthday=date(2025, 12, 20),
                wallet=Decimal('0.00')
            )
            return bin_user

    except Exception as e:
        print(f"Error creating Bin user: {e}")
        return None

@staff_member_required(login_url='/error')
@login_required
def verification_codes(request):
    codes = EmailVerificationCode.objects.all().order_by('-created_at')
    
    total_codes = codes.count()
    valid_codes = codes.filter(expires_at__gt=timezone.now(), is_used=False).count()
    used_codes = codes.filter(is_used=True).count()
    expired_codes = codes.filter(expires_at__lt=timezone.now(), is_used=False).count()
    
    filter_type = request.GET.get('filter', 'all')
    if filter_type == 'valid':
        codes = codes.filter(expires_at__gt=timezone.now(), is_used=False)
    elif filter_type == 'used':
        codes = codes.filter(is_used=True)
    elif filter_type == 'expired':
        codes = codes.filter(expires_at__lt=timezone.now(), is_used=False)
    
    search_email = request.GET.get('search', '')
    if search_email:
        codes = codes.filter(email__icontains=search_email)
    
    paginator = Paginator(codes, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'codes': page_obj,
        'total_codes': total_codes,
        'valid_codes': valid_codes,
        'used_codes': used_codes,
        'expired_codes': expired_codes,
        'filter_type': filter_type,
        'search_email': search_email,
        'lang': getattr(request.user, 'language', 'English')
    }
    
    return render(request, 'login_codes/verification_codes.html', context)

def get_file_size_limit(user):
    if user.subscribe == 'Bin_premium':
        return 50 * 1024 * 1024
    elif user.subscribe == 'Bin+':
        return 20 * 1024 * 1024
    else:
        return 10 * 1024 * 1024

@login_required
def get_file_upload_limit(request):
    user = request.user
    limit_bytes = get_file_size_limit(user)
    limit_mb = limit_bytes // (1024 * 1024)
    
    return JsonResponse({
        'limit_bytes': limit_bytes,
        'limit_mb': limit_mb,
        'subscription': user.subscribe,
        'max_file_size': f"{limit_mb}MB"
    })

@login_required(login_url='login')
def home(request):
    lang = "English"

    if request.session.get("language"):
        lang = request.session["language"]
    elif request.user.is_authenticated and hasattr(request.user, "language"):
        lang = request.user.language

    if request.user.is_authenticated and hasattr(request.user, "language"):
        if request.session.get("language") and request.user.language != request.session.get("language"):
            request.user.language = request.session.get("language")
            request.user.save()
        elif not request.session.get("language") and hasattr(request.user, "language"):
            request.session['language'] = request.user.language
            lang = request.user.language

    user = request.user
    role = get_user_role(user)

    create_bin_user()

    viewed_username = request.GET.get('username')

    if viewed_username:
        try:
            profile_user = User.objects.get(username=viewed_username)
        except User.DoesNotExist:
            profile_user = user
            messages.warning(request, "Пользователь не найден, показываем ваш профиль")
    else:
        profile_user = user

    search_query = request.GET.get('search', '').strip()
    found_users = []
    if search_query:
        from django.db.models import Q
        if not search_query.startswith('@'):
            search_query = '@' + search_query
        found_users = User.objects.filter(Q(your_tag__iexact=search_query)).exclude(id=user.id)

    if profile_user.subscription_end and profile_user.subscription_end < timezone.now():
        old_subscription = profile_user.subscribe
        old_period = profile_user.subscribe_period
        profile_user.subscribe = 'Basic'
        profile_user.subscribe_period = 'none'
        profile_user.subscription_end = None
        profile_user.save()

        msg = (
            f"Термін підписки {old_subscription} ({old_period}) закінчився."
            if profile_user.language == 'Українська'
            else f"Your {old_subscription} ({old_period}) subscription has expired."
        )
        messages.warning(request, msg)

    def format_description(text):
        if not text:
            return "No description"

        def repl(match):
            username = match.group(1)
            try:
                target = User.objects.get(username=username)
                return f'<a href="javascript:void(0)" onclick="openUserProfile(\'{target.username}\'); return false;" class="profile-mention" data-username="@{target.username}">@{username}</a>'
            except User.DoesNotExist:
                return f'<span class="profile-mention">@{username}</span>'

        formatted = re.sub(r'@(\w+)', repl, text)
        return mark_safe(formatted)

    description_html = format_description(profile_user.description)

    def convert(amount):
        try:
            amt = Decimal(amount)
        except Exception:
            amt = Decimal('0')
        if getattr(profile_user, 'currency', 'USD') == 'UAH':
            converted = (amt * Decimal('42.1')).quantize(Decimal('0.01'))
            return f"{converted} ₴"
        return f"{amt.quantize(Decimal('0.01'))} $"

    price_converted = convert(getattr(profile_user, 'wallet', 0) or 0)

    background_url = None
    background_exists = False
    if profile_user.background:
        background_url = profile_user.background.url
        background_exists = True

    subscription_prices_USD = {
        'bin_plus_monthly': Decimal('4.99'),
        'bin_plus_yearly': Decimal('49.99'),
        'bin_premium_monthly': Decimal('9.99'),
        'bin_premium_yearly': Decimal('99.99'),
    }
    
    subscription_types = {
        'bin_plus_monthly': ('Bin+', 'monthly', 30),
        'bin_plus_yearly': ('Bin+', 'yearly', 365),
        'bin_premium_monthly': ('Bin_premium', 'monthly', 30),
        'bin_premium_yearly': ('Bin_premium', 'yearly', 365),
    }

    if request.method == 'POST':
        action = request.POST.get('action')

        if 'subscription_plan' in request.POST:
            plan = request.POST.get('subscription_plan')
            
            if plan in subscription_prices_USD:
                cost_usd = subscription_prices_USD[plan]
                
                current_currency = getattr(profile_user, 'currency', 'USD')
                if current_currency == 'UAH':
                    cost_for_check = cost_usd * Decimal('42.1')
                else:
                    cost_for_check = cost_usd
                
                if profile_user.wallet >= cost_for_check:
                    try:
                        with transaction.atomic():
                            profile_user.wallet -= cost_for_check
                            sub_name, sub_period, days_count = subscription_types[plan]
                            profile_user.subscribe = sub_name
                            profile_user.subscribe_period = sub_period
                            profile_user.subscription_end = timezone.now() + timedelta(days=days_count)
                            profile_user.subscription_purchase_time = timezone.now()
                            profile_user.subscription_purchase_amount = cost_usd
                            profile_user.subscription_purchase_currency = current_currency
                            profile_user.save()

                        msg = (
                            f"Підписка {profile_user.subscribe} ({profile_user.subscribe_period}) успішно оформлена!"
                            if profile_user.language == 'Українська'
                            else f"Subscription {profile_user.subscribe} ({profile_user.subscribe_period}) successful!"
                        )
                        messages.success(request, msg)
                    except Exception:
                        messages.error(
                            request,
                            "Помилка при оформленні!" if profile_user.language == 'Українська'
                            else "Error processing subscription!"
                        )
                else:
                    missing = cost_for_check - profile_user.wallet
                    messages.error(
                        request,
                        f"Недостатньо коштів! Потрібно ще {missing:.2f}."
                        if profile_user.language == 'Українська'
                        else f"Not enough funds! You need {missing:.2f} more."
                    )
            return redirect('home')

        if action == "refund_subscription":
            if profile_user.subscribe != "Basic" and getattr(profile_user, "subscription_purchase_time", None):
                time_diff = timezone.now() - profile_user.subscription_purchase_time        

                if time_diff <= timedelta(hours=24):
                    purchase_amount = getattr(profile_user, 'subscription_purchase_amount', Decimal('0.00'))
                    purchase_currency = getattr(profile_user, 'subscription_purchase_currency', 'USD')
                    
                    if purchase_amount == Decimal('0.00'):
                        if profile_user.subscribe == 'Bin+':
                            purchase_amount = Decimal('4.99') if profile_user.subscribe_period == 'monthly' else Decimal('49.99')
                        elif profile_user.subscribe == 'Bin_premium':
                            purchase_amount = Decimal('9.99') if profile_user.subscribe_period == 'monthly' else Decimal('99.99')

                    current_currency = getattr(profile_user, 'currency', 'USD')
                    
                    if purchase_currency == 'UAH':
                        original_charged_amount = purchase_amount * Decimal('42.1')
                    else:
                        original_charged_amount = purchase_amount
                    
                    refund_amount = original_charged_amount

                    profile_user.wallet += refund_amount
                    profile_user.subscribe = 'Basic'
                    profile_user.subscribe_period = 'none'
                    profile_user.subscription_end = None
                    profile_user.subscription_purchase_time = None
                    profile_user.subscription_purchase_currency = None
                    profile_user.subscription_purchase_amount = Decimal('0.00')
                    profile_user.photo = 'login.png'
                    profile_user.background = None
                    profile_user.save()     

                    def format_refund_amount(amount, currency):
                        if currency == 'UAH':
                            return f"{amount.quantize(Decimal('0.01'))} ₴"
                        return f"{amount.quantize(Decimal('0.01'))} $"

                    refund_display = format_refund_amount(refund_amount, current_currency)
                    
                    messages.success(
                        request,
                        f"Підписку скасовано. Повернено {refund_display}!"
                        if profile_user.language == "Українська"
                        else f"Subscription refunded. {refund_display} returned!"
                    )
                else:
                    messages.error(
                        request,
                        "Термін повернення підписки минув." if profile_user.language == "Українська"
                        else "The refund period has expired."
                    )       

            return redirect("home")

    today = date.today()
    birthday = getattr(profile_user, 'birthday', None) or today
    days = range(1, 32)
    months = range(1, 13)
    years = range(today.year - 100, today.year + 1)
    cards = Card.objects.filter(user=profile_user)
    current_year = timezone.now().year

    active_sessions = profile_user.get_active_sessions()
    login_history = profile_user.get_login_history()

    can_refund = False
    if profile_user.subscribe != 'Basic' and getattr(profile_user, 'subscription_purchase_time', None):
        time_diff = timezone.now() - profile_user.subscription_purchase_time
        can_refund = time_diff <= timedelta(hours=24)

    file_size_limit_mb = get_file_size_limit(profile_user) // (1024 * 1024)

    sticker_category_labels = {
        'people': 'Люди' if lang == 'Українська' else 'People',
        'animals': 'Тварини' if lang == 'Українська' else 'Animals',
        'transport': 'Транспорт' if lang == 'Українська' else 'Transport',
        'nature': 'Природа' if lang == 'Українська' else 'Nature',
        'food': 'Їжа' if lang == 'Українська' else 'Food',
        'love': 'Любов' if lang == 'Українська' else 'Love',
        'flags': 'Прапори' if lang == 'Українська' else 'Flags',
        'misc': 'Інше' if lang == 'Українська' else 'Misc',
        'extras': 'Додатково' if lang == 'Українська' else 'Extras'
    }

    sticker_category_labels_json = json.dumps(sticker_category_labels, ensure_ascii=False)

    template = 'home/home_uk.html' if lang == 'Українська' else 'home/home_en.html'
    return render(request, template, {
        'user': user,
        'profile_user': profile_user,
        'description_html': description_html,
        'price_converted': price_converted,
        'cards': cards,
        'months': months,
        'days': days,
        'years': years,
        'birthday': birthday,
        'expiry_years': range(current_year, current_year + 21),
        'can_refund': can_refund,
        'background_url': background_url,
        'background_exists': background_exists,
        'active_sessions': active_sessions,
        'login_history': login_history,
        'lang': lang,
        'sticker_category_labels_json': sticker_category_labels_json,
        'file_size_limit_mb': file_size_limit_mb,
    })