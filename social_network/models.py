from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.conf import settings
from django import forms
from django.contrib.sessions.models import Session
from datetime import timedelta
import random
# import app.models as app_models

# python manage.py makemigrations
# python manage.py migrate

class User(AbstractUser):
    username = models.CharField(max_length=18, unique=True)
    photo = models.ImageField(
        upload_to='users/',
        null=True,
        blank=True,
        default='login.png'
    )

    background = models.ImageField(
        upload_to='backgrounds/',
        null=True,
        blank=True,
        default=None
    )

    description = models.TextField(max_length=100, blank=True, default='None')
    birthday = models.DateField(null=True, blank=True, default=None)
    language = models.CharField(
        max_length=20,
        choices=[
            ('Українська', 'українська'),
            ('English', 'english'),
        ],
        default='English',
    )
    wallet = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    currency = models.CharField(
        max_length=10,
        choices=[
            ('USD', 'USD $'),
            ('UAH', 'UAH ₴'),
        ],
        default='USD',
    )

    status = models.CharField(
        max_length=20,
        choices=[
            ('Online', 'Online'),
            ('Offline', 'Offline'),
        ],
        default='Offline',
    )
    contact = models.CharField(
        max_length=254, 
        unique=True, 
        null=True, 
        blank=True,
        help_text="Email or phone number"
    )
    email = models.EmailField(unique=True, null=True, blank=True)
    phone_number = models.CharField(max_length=20, unique=True, null=True, blank=True) 
    your_tag = models.CharField(max_length=100, unique=True, null=True, blank=True) 
 
    def save(self, *args, **kwargs): 
        if not self.your_tag: 
            self.your_tag = self.username 
        super().save(*args, **kwargs) 
 
    @property 
    def display_tag(self): 
        return f"@{self.your_tag}" if self.your_tag else f"@{self.username}" 

    subscribe = models.CharField(
        max_length=50,
        choices=[
            ('Basic', 'Basic'),
            ('Bin+', 'Bin+'),
            ('Bin_premium', 'Bin_premium'),
        ],
        default='Basic',
    )

    subscribe_period = models.CharField(
        max_length=50,
        choices=[
            ('monthly', 'Monthly'),
            ('yearly', 'Yearly'),
        ],
        default='monthly'
    )

    subscription_end = models.DateTimeField(null=True, blank=True)
    subscription_purchase_time = models.DateTimeField(null=True, blank=True)
    subscription_purchase_currency = models.CharField(
        max_length=3,
        choices=[('USD', 'USD'), ('UAH', 'UAH')],
        default='USD',
        null=True,
        blank=True
    )
    subscription_purchase_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0.00,
        null=True,
        blank=True
    )

    role = models.CharField(
        max_length=20,
        choices=[
            ('User', 'User'),
            ('Moderator', 'Moderator'),
            ('Administrator', 'Administrator'),
            ('System Bot', 'System Bot'),
        ],
        default='User',
    )

    two_factor_enabled = models.BooleanField(default=False)
    two_factor_secret = models.CharField(max_length=32, blank=True, null=True)
    custom_button_enabled = models.BooleanField(default=False)
    custom_option = models.CharField(max_length=1, default='1', choices=[
        ('1', 'Light-Dark'),
        ('2', 'Rainbow'),
        ('3', 'Bright'),
        ('4', 'Dark')
    ])
    color_text_button = models.CharField(
        max_length=10, 
        default='black', 
        choices=[('black', 'Black'), ('white', 'White')]
    )
    
    def get_active_sessions(self):
        sessions = []
        try:
            user_sessions = Session.objects.filter(expire_date__gte=timezone.now())

            for session in user_sessions:
                try:
                    session_data = session.get_decoded()
                    if '_auth_user_id' in session_data and str(self.id) == session_data['_auth_user_id']:
                        session_info = {
                            'key': session.session_key,
                            'device': self._get_device_info(session_data),
                            'location': self._get_location_info(session_data),
                            'last_activity': session.expire_date - timedelta(seconds=settings.SESSION_COOKIE_AGE),
                            'is_current': False
                        }
                        sessions.append(session_info)
                except Exception:
                    continue
                
        except Exception as e:
            print(f"Error getting sessions: {e}")

        return sessions

    def _get_device_info(self, session):
        user_agent = getattr(session, 'user_agent', 'Unknown device')
        if 'Mobile' in user_agent:
            return 'Mobile'
        elif 'Tablet' in user_agent:
            return 'Tablet'
        else:
            return 'Desktop'

    def _get_location_info(self, session):
        return 'Unknown location'

    def _get_current_session_key(self):
        return None

    def get_login_history(self):
        return LoginHistory.objects.filter(user=self)[:20]

    def record_login(self, request, success=True):
        device_info = request.META.get('HTTP_USER_AGENT', 'Unknown')[:200]
        ip_address = self._get_client_ip(request)
        
        LoginHistory.objects.create(
            user=self,
            device=device_info,
            ip_address=ip_address,
            location=self._get_location_from_ip(ip_address),
            success=success
        )

    def _get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    def _get_location_from_ip(self, ip_address):
        return 'Unknown'
    
class LoginHistory(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='login_history')
    timestamp = models.DateTimeField(default=timezone.now)
    device = models.CharField(max_length=200, blank=True)
    location = models.CharField(max_length=100, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    success = models.BooleanField(default=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.user.username} - {self.timestamp}"

class Card(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='cards')
    last4 = models.CharField(max_length=4)
    fingerprint = models.CharField(max_length=64, db_index=True)
    cardholder = models.CharField(max_length=100, blank=True, null=True)
    expiry_month = models.IntegerField()
    expiry_year = models.IntegerField()
    brand = models.CharField(max_length=50, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"**** **** ****{self.last4} ({self.cardholder or 'no-name'})"
class Message(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    text = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    
    file = models.FileField(upload_to='chat_files/', null=True, blank=True)
    file_name = models.CharField(max_length=255, null=True, blank=True)
    file_size = models.IntegerField(null=True, blank=True)
    file_type = models.CharField(max_length=100, null=True, blank=True)
    is_file = models.BooleanField(default=False)

    class Meta:
        ordering = ['timestamp']

class UserMessage(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='messages')
    text = models.TextField()
    level = models.CharField(
        max_length=20, 
        choices=[
            ('success', 'Success'),
            ('error', 'Error'), 
            ('warning', 'Warning'),
            ('info', 'Info')
        ],
        default='info'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username}: {self.text[:50]}"

class EmailVerificationCode(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    email = models.EmailField()
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(default=timezone.now)
    is_used = models.BooleanField(default=False)
    
    def is_valid(self):
        return not self.is_used and timezone.now() < self.expires_at
    
    def save(self, *args, **kwargs):
        if not self.pk:
            self.expires_at = timezone.now() + timedelta(minutes=10)
        super().save(*args, **kwargs)
    
    class Meta:
        db_table = 'email_verification_codes'