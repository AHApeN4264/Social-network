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
import os
User = get_user_model()

def get_user_role(user):
    if not user.is_authenticated:
        return "User"
    if user.username.lower() == "ahapen_4264":
        return "Administrator"
    elif user.username.lower() == "andrey":
        return "Moderator"
    else:
        return "User"

def error(request):
    return render(request, 'error/error.html')

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
        if is_ajax:
            return JsonResponse({'success': True, 'language': lang})
        
        return redirect(request.META.get('HTTP_REFERER', '/'))

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
            language=lang
        )

        request.session['language'] = lang
        
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
    if request.method == 'GET':
        request.session.pop('verification_sent', None)
        request.session.pop('reset_email', None)
        request.session.pop('verification_code', None)
        request.session.pop('verification_code_expires', None)
    
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        
        if not email:
            messages.error(request, 'Будь ласка, введіть email')
            return render(request, 'login/enter-gmail.html')
        
        try:
            validate_email(email)
        except ValidationError:
            messages.error(request, 'Будь ласка, введіть коректний email')
            return render(request, 'login/enter-gmail.html')
        
        User = get_user_model()
        
        try:
            user = User.objects.get(email=email)
            
            verification_code = ''.join(random.choices(string.digits, k=6))
            
            UserMessage.objects.create(
                user=user,
                text=f'Verification Code: {verification_code}',
                level='success'
            )
            
            request.session['reset_email'] = email
            request.session['verification_code'] = verification_code
            request.session['verification_sent'] = True
            request.session['verification_code_expires'] = (timezone.now() + timedelta(minutes=10)).isoformat()
            
            messages.success(request, f'Код верифікації відправлено в ваш email')
            return redirect('forgot-password')
            
        except User.DoesNotExist:
            messages.error(request, 'Акаунт з таким email не знайдено')
    
    return render(request, 'login/enter-gmail.html')

def forgot_password(request):
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
                messages.error(request, 'Код верифікації закінчився. Будь ласка, запросіть новий.')
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
            messages.error(request, 'Код верифікації недійсний')
            return redirect('enter-gmail')
        
        if entered_code == stored_code:
            User = get_user_model()
            try:
                user = User.objects.get(email=email)
                
                auth_login(request, user)
                
                request.session.pop('verification_sent', None)
                request.session.pop('reset_email', None)
                request.session.pop('verification_code', None)
                request.session.pop('verification_code_expires', None)
                
                messages.success(request, f'Вітаємо, {user.username}! Ви успішно увійшли.')
                return redirect('home')
                
            except User.DoesNotExist:
                messages.error(request, 'Користувача не знайдено')
                return redirect('enter-gmail')
        else:
            messages.error(request, 'Невірний код підтвердження')
    
    return render(request, 'login/forgot-password.html', {
        'email': email,
        'verification_code': verification_code if is_code_valid else None,
        'lang': request.GET.get('lang', 'Українська')
    })

def send_verification_code(email, code):
    current_time = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
    
    subject = 'Email Verification Code'
    message = f'''
Verification Code: {code}
Time: {current_time}

This code is valid for 10 minutes.

If you did not request this change, please ignore this message.
'''
    
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [email],
        fail_silently=False,
    )


@login_required
def email(request):
    messages_list = UserMessage.objects.filter(user=request.user).order_by('-created_at')
    
    verification_code = None
    verification_message = messages_list.filter(
        text__startswith='Verification Code:',
        created_at__gte=timezone.now() - timedelta(minutes=10)
    ).first()
    
    if verification_message:
        import re
        match = re.search(r'Verification Code: (\d+)', verification_message.text)
        if match:
            verification_code = match.group(1)
    
    paginator = Paginator(messages_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'email_template.html', {
        'messages_list': page_obj,
        'verification_code': verification_code,
        'lang': request.GET.get('lang', 'Українська')
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

@login_required
def delete_message(request, message_id):
    try:
        message = UserMessage.objects.get(id=message_id, user=request.user)
        message.delete()
        messages.success(request, 'Повідомлення видалено' if getattr(request.user, 'language', 'English') == 'Українська' else 'Message deleted')
    except UserMessage.DoesNotExist:
        messages.error(request, 'Повідомлення не знайдено' if getattr(request.user, 'language', 'English') == 'Українська' else 'Message not found')
    
    return redirect('email')

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
            Q(your_tag__icontains=query) | Q(username__icontains=query)
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
        
        elif user.subscribe == 'Bin+' and filename.endswith('.gif'):
            messages.error(
                request,
                "Гіф-фони доступні лише для підписки Bin Premium."
                if getattr(user, 'language', 'English') == 'Українська'
                else "GIF backgrounds are available only for Bin Premium subscription."
            )
            return redirect('home')

        user.background = background
        user.save()

        messages.success(
            request,
            "Фон оновлено!" if getattr(user, 'language', 'English') == 'Українська' else "Background updated!"
        )
        return redirect('home')

    return redirect('home')

@login_required
def update_profile(request):
    if request.method == 'POST':
        user = request.user
        user.username = request.POST.get('username', user.username)
        user.description = request.POST.get('description', user.description)
        user.your_tag = request.POST.get('your_tag', user.your_tag)

        day = request.POST.get('day')
        month = request.POST.get('month')
        year = request.POST.get('year')

        if day and month and year:
            try:
                user.birthday = date(int(year), int(month), int(day))
            except Exception:
                pass

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

        user.save()
        messages.success(request, "Profile updated successfully." if getattr(user, 'language', 'English') != 'Українська' else "Профіль оновлено!")
        return redirect('home')

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
def get_chat_messages(request):
    other_username = request.GET.get('username')
    if not other_username:
        return JsonResponse({'error': 'Username parameter required'}, status=400)
    
    try:
        other_user = User.objects.get(username=other_username)
        
        messages = Message.objects.filter(
            (models.Q(sender=request.user) & models.Q(receiver=other_user)) |
            (models.Q(sender=other_user) & models.Q(receiver=request.user))
        ).order_by('timestamp')
        
        Message.objects.filter(
            sender=other_user,
            receiver=request.user,
            is_read=False
        ).update(is_read=True)
        
        messages_data = []
        for msg in messages:
            message_data = {
                'id': msg.id,
                'text': msg.text,
                'timestamp': msg.timestamp.isoformat(),
                'is_sent': msg.sender == request.user,
                'is_read': msg.is_read,
                'sender': msg.sender.username
            }
            
            messages_data.append(message_data)
        
        return JsonResponse(messages_data, safe=False)
        
    except User.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=404)
    except Exception as e:
        print(f"Error loading chat messages: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)
    
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
                
                # Ограничение количество контактов
                if len(contacts) >= 15:
                    break
                    
            except User.DoesNotExist:
                continue
        
        return JsonResponse(contacts, safe=False)
        
    except Exception as e:
        print(f"Error getting recent contacts: {str(e)}")
        return JsonResponse([], safe=False)

@login_required
def mark_messages_read(request):
    """Позначити повідомлення як прочитані"""
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
    """Зберегти нотатку користувача"""
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
    """Отримати всі нотатки користувача"""
    try:
        notes = Message.objects.filter(
            sender=request.user,
            receiver=request.user
        ).order_by('timestamp')
        
        notes_data = [{
            'id': note.id,
            'text': note.text,
            'timestamp': note.timestamp.isoformat()
        } for note in notes]
        
        return JsonResponse(notes_data, safe=False)
        
    except Exception as e:
        print(f"Error getting notes: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def get_user_profile(request):
    username = request.GET.get('username')
    
    if not username:
        return JsonResponse({'success': False, 'error': 'Username is required'})
    
    try:
        user = User.objects.get(username=username)
        
        user_data = {
            'success': True,
            'username': user.username,
            'status': user.status or 'Offline',
            'your_tag': user.your_tag or '',
            'description': user.description or '',
            'birthday': user.birthday.strftime('%B %d, %Y') if user.birthday else 'Not specified',
            'photo_url': user.photo.url if user.photo and hasattr(user.photo, 'url') else '/static/pictures/login.png',
            'background_url': user.background.url if user.background and hasattr(user.background, 'url') else '',
            'subscribe': user.subscribe
        }
        
        return JsonResponse(user_data)
        
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'User not found'})
    except Exception as e:
        print(f"Error loading user profile: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)})
    
def get_user_by_tag(request):
    tag = request.GET.get('tag', '').strip().lstrip('@')
    
    if not tag:
        return JsonResponse({'success': False, 'error': 'No tag provided'})
    
    try:
        user = User.objects.filter(
            models.Q(your_tag__iexact=tag) | 
            models.Q(username__iexact=tag)
        ).first()
        
        if user:
            return JsonResponse({
                'success': True,
                'username': user.username
            })
        else:
            return JsonResponse({
                'success': False, 
                'error': f'User with tag @{tag} not found'
            })
            
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

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
        base_amount = float(user.wallet)
        base_currency = user.currency
        
        exchange_rates = {
            'USD': {'USD': 1.0, 'EUR': 0.917, 'GBP': 0.773, 'UAH': 41.45},
            'EUR': {'USD': 1.091, 'EUR': 1.0, 'GBP': 0.843, 'UAH': 45.21},
            'GBP': {'USD': 1.294, 'EUR': 1.186, 'GBP': 1.0, 'UAH': 53.63},
            'UAH': {'USD': 0.0241, 'EUR': 0.0221, 'GBP': 0.0186, 'UAH': 1.0}
        }
        
        rates = exchange_rates.get(base_currency, exchange_rates['USD'])
        
        def format_currency(amount):
            return f"{amount:,.2f}".replace(',', ' ').replace('.', ',')
        
        converted = {
            'usd': f"🇺🇸{format_currency(base_amount * rates['USD'])}$ USD",
            'eur': f"🇪🇺{format_currency(base_amount * rates['EUR'])}€ EUR",
            'gbp': f"🇬🇧{format_currency(base_amount * rates['GBP'])}£ GBP", 
            'uah': f"🇺🇦{format_currency(base_amount * rates['UAH'])}₴ UAH"
        }
        
        return JsonResponse({
            'success': True,
            'converted': converted
        })
        
    except Exception as e:
        print(f"Currency conversion error: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

@login_required
# @csrf_exempt
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
        
        if file.size > 50 * 1024 * 1024:
            return JsonResponse({'error': 'File too large. Maximum size is 50MB.'}, status=400)
        
        import os
        from django.utils import timezone
        from django.core.files.storage import default_storage
        from django.core.files.base import ContentFile
        
        file_extension = os.path.splitext(file.name)[1]
        timestamp = int(timezone.now().timestamp())
        safe_filename = f"chat_{request.user.id}_{receiver.id}_{timestamp}{file_extension}"
        
        file_content = file.read()
        saved_path = f'chat_files/{safe_filename}'
        
        try:
            saved_name = default_storage.save(saved_path, ContentFile(file_content))
            print(f"File saved as: {saved_name}")
            
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
def get_chat_messages(request):
    other_username = request.GET.get('username')
    if not other_username:
        return JsonResponse({'error': 'Username parameter required'}, status=400)
    
    try:
        other_user = User.objects.get(username=other_username)
        
        messages = Message.objects.filter(
            (models.Q(sender=request.user) & models.Q(receiver=other_user)) |
            (models.Q(sender=other_user) & models.Q(receiver=request.user))
        ).order_by('timestamp')
        
        Message.objects.filter(
            sender=other_user,
            receiver=request.user,
            is_read=False
        ).update(is_read=True)
        
        messages_data = []
        for msg in messages:
            message_data = {
                'id': msg.id,
                'text': msg.text,
                'timestamp': msg.timestamp.isoformat(),
                'is_sent': msg.sender == request.user,
                'is_read': msg.is_read,
                'sender': msg.sender.username,
                'is_file': msg.is_file,
                'file_url': default_storage.url(msg.file) if msg.file else None,
                'file_name': msg.file_name,
                'file_type': msg.file_type,
                'file_size': msg.file_size
            }
            
            messages_data.append(message_data)
        
        return JsonResponse(messages_data, safe=False)
        
    except User.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=404)
    except Exception as e:
        print(f"Error loading chat messages: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)

def check_user_exists(request):
    username = request.GET.get('username', '')
    exists = User.objects.filter(username=username).exists()
    return JsonResponse({'exists': exists})

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

    search_query = request.GET.get('search', '').strip()
    found_users = []
    if search_query:
        from django.db.models import Q
        if not search_query.startswith('@'):
            search_query = '@' + search_query
        found_users = User.objects.filter(Q(your_tag__iexact=search_query)).exclude(id=user.id)

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

    def format_description(text):
        if not text:
            return "No description"

        def repl(match):
            username = match.group(1)
            try:
                target = User.objects.get(username=username)
                url = reverse('home') + f"?profile={target.username}"
                return f'<a href="{url}" style="color:#0056b3;">@{username}</a>'
            except User.DoesNotExist:
                return f'<span style="color:#0056b3;">@{username}</span>'

        formatted = re.sub(r'@(\w+)', repl, text)
        return mark_safe(formatted)

    description_html = format_description(user.description)

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

    background_url = None
    background_exists = False
    if user.background:
        background_url = user.background.url
        background_exists = True

    subscription_prices_USD = {
        'bin_plus_monthly': Decimal('4.99'),
        'bin_plus_yearly': Decimal('49.99'),
        'bin_premium_monthly': Decimal('9.99'),
        'bin_premium_yearly': Decimal('99.99'),
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
        action = request.POST.get('action')

        if 'subscription_plan' in request.POST:
            plan = request.POST.get('subscription_plan')
            
            if plan in subscription_prices_USD:
                cost_usd = subscription_prices_USD[plan]
                
                current_currency = getattr(user, 'currency', 'USD')
                if current_currency == 'UAH':
                    cost_for_check = cost_usd * Decimal('42.1')
                else:
                    cost_for_check = cost_usd
                
                if user.wallet >= cost_for_check:
                    try:
                        with transaction.atomic():
                            user.wallet -= cost_for_check
                            sub_name, sub_period, days_count = subscription_types[plan]
                            user.subscribe = sub_name
                            user.subscribe_period = sub_period
                            user.subscription_end = (
                                timezone.now() + timedelta(seconds=15)
                                if plan == 'bin_plus_test'
                                else timezone.now() + timedelta(days=days_count)
                            )
                            user.subscription_purchase_time = timezone.now()
                            user.subscription_purchase_amount = cost_usd
                            user.subscription_purchase_currency = current_currency
                            user.save()

                        msg = (
                            f"Підписка {user.subscribe} ({user.subscribe_period}) успішно оформлена!"
                            if user.language == 'Українська'
                            else f"Subscription {user.subscribe} ({user.subscribe_period}) successful!"
                        )
                        messages.success(request, msg)
                    except Exception:
                        messages.error(
                            request,
                            "Помилка при оформленні!" if user.language == 'Українська'
                            else "Error processing subscription!"
                        )
                else:
                    missing = cost_for_check - user.wallet
                    messages.error(
                        request,
                        f"Недостатньо коштів! Потрібно ще {missing:.2f}."
                        if user.language == 'Українська'
                        else f"Not enough funds! You need {missing:.2f} more."
                    )
            return redirect('home')

        if action == "refund_subscription":
            if user.subscribe != "Basic" and getattr(user, "subscription_purchase_time", None):
                time_diff = timezone.now() - user.subscription_purchase_time        

                if time_diff <= timedelta(hours=24):
                    purchase_amount = getattr(user, 'subscription_purchase_amount', Decimal('0.00'))
                    purchase_currency = getattr(user, 'subscription_purchase_currency', 'USD')
                    
                    if purchase_amount == Decimal('0.00'):
                        if user.subscribe == 'Bin+':
                            purchase_amount = Decimal('4.99') if user.subscribe_period == 'monthly' else Decimal('49.99')
                        elif user.subscribe == 'Bin_premium':
                            purchase_amount = Decimal('9.99') if user.subscribe_period == 'monthly' else Decimal('99.99')

                    current_currency = getattr(user, 'currency', 'USD')
                    
                    if purchase_currency == 'UAH':
                        original_charged_amount = purchase_amount * Decimal('42.1')
                    else:
                        original_charged_amount = purchase_amount
                    
                    refund_amount = original_charged_amount

                    user.wallet += refund_amount
                    user.subscribe = 'Basic'
                    user.subscribe_period = 'none'
                    user.subscription_end = None
                    user.subscription_purchase_time = None
                    user.subscription_purchase_currency = None
                    user.subscription_purchase_amount = Decimal('0.00')
                    user.photo = 'login.png'
                    user.background = None
                    user.save()     

                    def format_refund_amount(amount, currency):
                        if currency == 'UAH':
                            return f"{amount.quantize(Decimal('0.01'))} ₴"
                        return f"{amount.quantize(Decimal('0.01'))} $"

                    refund_display = format_refund_amount(refund_amount, current_currency)
                    
                    messages.success(
                        request,
                        f"Підписку скасовано. Повернено {refund_display}!"
                        if user.language == "Українська"
                        else f"Subscription refunded. {refund_display} returned!"
                    )
                else:
                    messages.error(
                        request,
                        "Термін повернення підписки минув." if user.language == "Українська"
                        else "The refund period has expired."
                    )       

            return redirect("home")

    today = date.today()
    birthday = getattr(user, 'birthday', None) or today
    days = range(1, 32)
    months = range(1, 13)
    years = range(today.year - 100, today.year + 1)
    cards = Card.objects.filter(user=user)
    current_year = timezone.now().year

    active_sessions = user.get_active_sessions()
    login_history = user.get_login_history()

    can_refund = False
    if user.subscribe != 'Basic' and getattr(user, 'subscription_purchase_time', None):
        time_diff = timezone.now() - user.subscription_purchase_time
        can_refund = time_diff <= timedelta(hours=24)

    return render(request, 'home/home.html', {
        'user': user,
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
    })