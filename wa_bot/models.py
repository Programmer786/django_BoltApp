from datetime import timedelta

from django.db import models
from django.utils import timezone

KEEP_CONVERSATIONS_DAYS = 3

DEFAULT_WELCOME = (
    "👋 Welcome to *{brand}* verification.\n\n"
    "Send the *card number*, *certificate number*, *sticker number* or *report number* "
    "exactly as printed, and we will reply with the verified details.\n\n"
    "Example: 905951"
)
DEFAULT_NOT_FOUND = (
    "❌ No valid record found for *{number}*.\n\n"
    "Please check the number and send it exactly as printed on the card or certificate. "
    "If you believe this is a mistake, contact our office."
)
DEFAULT_RATE_LIMITED = (
    "⏳ You have reached the limit of lookups for now. Please try again in an hour."
)


class BotSettings(models.Model):
    """Single row (pk=1) edited from the WhatsApp Verification page."""
    enabled = models.BooleanField(default=True, help_text='Reply to incoming WhatsApp messages')
    use_ai = models.BooleanField(default=True, help_text='Let the free local AI answer general chat messages')
    brand = models.CharField(max_length=120, default='Bolt Inspection')
    office_contact = models.CharField(
        max_length=200, blank=True, default='info@boltinspection.com',
        help_text='Shown when people ask about prices, bookings, renewals or lost cards')
    welcome_text = models.TextField(default=DEFAULT_WELCOME)
    not_found_text = models.TextField(default=DEFAULT_NOT_FOUND)
    rate_limited_text = models.TextField(default=DEFAULT_RATE_LIMITED)
    max_lookups_per_hour = models.PositiveIntegerField(default=10)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'bot settings'
        verbose_name_plural = 'bot settings'

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return 'WhatsApp verification bot settings'


class BotState(models.Model):
    """Single row (pk=1): what the WhatsApp listener last reported."""
    STATE_CHOICES = [
        ('offline', 'Offline'),
        ('starting', 'Starting'),
        ('qr', 'Waiting for QR scan'),
        ('ready', 'Connected'),
        ('disconnected', 'Disconnected'),
    ]
    state = models.CharField(max_length=20, choices=STATE_CHOICES, default='offline')
    qr = models.TextField(blank=True, default='')
    phone = models.CharField(max_length=40, blank=True, default='')
    pending_command = models.CharField(max_length=20, blank=True, default='')  # e.g. "logout"
    last_seen = models.DateTimeField(null=True, blank=True)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class BotConversation(models.Model):
    RESULT_CHOICES = [
        ('found', 'Found'),
        ('not_found', 'Not found'),
        ('chat', 'Chat'),
        ('rate_limited', 'Rate limited'),
        ('disabled', 'Bot disabled'),
    ]
    phone = models.CharField(max_length=40, db_index=True)
    name = models.CharField(max_length=120, blank=True, default='')
    message = models.TextField(blank=True, default='')
    reply = models.TextField(blank=True, default='')
    result = models.CharField(max_length=20, choices=RESULT_CHOICES)
    matched_type = models.CharField(max_length=60, blank=True, default='')
    matched_number = models.CharField(max_length=120, blank=True, default='')
    used_ai = models.BooleanField(default=False)
    response_ms = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.phone} {self.result} {self.created_at:%Y-%m-%d %H:%M}'

    @classmethod
    def delete_expired(cls):
        cls.objects.filter(created_at__lt=timezone.now() - timedelta(days=KEEP_CONVERSATIONS_DAYS)).delete()
