from django.db import models
from django.contrib.auth.models import User


class ContactCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'contact categories'

    def __str__(self):
        return self.name


class WhatsAppContact(models.Model):
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=30, unique=True)  # e.g. +923045159631
    category = models.ForeignKey(ContactCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='contacts')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.phone})"

    @property
    def initials(self):
        parts = self.name.strip().split()
        if len(parts) >= 2:
            return (parts[0][0] + parts[-1][0]).upper()
        return self.name[:2].upper() if self.name else '??'


class WhatsAppMessage(models.Model):
    STATUS_CHOICES = [
        ('queued', 'Queued'),
        ('sending', 'Sending'),
        ('sent', 'Sent'),
        ('partial', 'Partial'),
        ('failed', 'Failed'),
    ]
    TYPE_CHOICES = [
        ('single', 'Single'),
        ('bulk', 'Bulk'),
    ]
    MODE_CHOICES = [
        ('text', 'Custom Text'),
        ('template', 'Template'),
    ]
    VIA_CHOICES = [
        ('twilio', 'Twilio API'),
        ('selenium', 'WhatsApp Web'),
        ('meta', 'Meta Cloud API'),
    ]

    sent_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    message_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    mode = models.CharField(max_length=10, choices=MODE_CHOICES, default='text')
    via = models.CharField(max_length=10, choices=VIA_CHOICES, default='twilio')
    body = models.TextField(blank=True, null=True)
    image_url = models.TextField(blank=True, null=True)
    content_sid = models.CharField(max_length=100, blank=True, null=True)
    content_variables = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='queued')
    total_sent = models.IntegerField(default=0)
    total_failed = models.IntegerField(default=0)
    total_recipients = models.IntegerField(default=0)
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-sent_at']

    @property
    def image_display_url(self):
        """Path that works on whichever host is serving this page (image_url
        stores an absolute URL built for Twilio, which may point elsewhere)."""
        url = self.image_url or ''
        return '/media/' + url.split('/media/', 1)[1] if '/media/' in url else url


class WhatsAppMessageLog(models.Model):
    message = models.ForeignKey(WhatsAppMessage, on_delete=models.CASCADE, related_name='logs')
    contact = models.ForeignKey(WhatsAppContact, on_delete=models.SET_NULL, null=True, blank=True)
    phone = models.CharField(max_length=30)
    contact_name = models.CharField(max_length=255, blank=True)
    sid = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(max_length=10, choices=[('sent', 'Sent'), ('failed', 'Failed')], default='sent')
    error = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.phone} — {self.status}"
