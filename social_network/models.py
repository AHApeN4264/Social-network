from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.conf import settings
from django import forms
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
    your_tag = models.CharField(max_length=30, unique=True, null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.your_tag:
            self.your_tag = self.username
        super().save(*args, **kwargs)

    @property
    def display_tag(self):
        return f"@{self.your_tag}" if self.your_tag else f"@{self.username}"

    subscribe = models.CharField(
        max_length=20,
        choices=[
            ('Basic', 'Basic'),
            ('Bin+', 'Bin+'),
            ('Bin_premium', 'Bin_premium'),
        ],
        default='Basic',
    )

    subscribe_period = models.CharField(
        max_length=10,
        choices=[
            ('monthly', 'Monthly'),
            ('yearly', 'Yearly'),
        ],
        default='monthly'
    )

    subscription_end = models.DateTimeField(null=True, blank=True)

    role = models.CharField(
        max_length=20,
        choices=[
            ('User', 'User'),
            ('Moderator', 'Moderator'),
            ('Administrator', 'Administrator'),
        ],
        default='User',
    )


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


