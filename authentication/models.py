import logging
import uuid
from django.core.exceptions import ValidationError
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)

from django.conf import settings
from base.emails import send_account_created_email
from base.models import BaseModel


class Profile(BaseModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    is_email_verified = models.BooleanField(default=False)
    email_token = models.CharField(max_length=100, blank=True, null=True)
    profile_image = models.ImageField(upload_to='profile', blank=True, null=True, default='profile/profile.jpg')
    title = models.CharField(max_length=100, blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    address = models.CharField(max_length=200, blank=True, null=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"

    def has_profile_image(self):
        """Check if the user has a profile image."""
        return bool(self.profile_image)

    def clean(self):
        """Validate the profile instance."""
        if not self.user:
            raise ValidationError("Profile must be linked to a user.")


@receiver(post_save, sender=User)
def send_email_token(sender, instance, created, **kwargs):
    try:
        if created:
            email_token = str(uuid.uuid4())
            profile, profile_created = Profile.objects.get_or_create(
                user=instance, defaults={'email_token': email_token}
            )
            # Profile already existed before user was saved — assign a fresh token
            if not profile_created:
                profile.email_token = email_token
                profile.save()

    except Exception as e:
        logger.error(f"Error creating profile for user {instance.username}: {e}")
        raise


class ActivityLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    browser_info = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.user} - {self.action} @ {self.timestamp}"
    

class Note(models.Model):
    class NoteType(models.TextChoices):
        CERTIFICATE = 'certificate', 'Certificate'
        CARD = 'card', 'Card'
        TRAINING = 'training', 'Training'
        NDT = 'ndt', 'NDT'
        CALIBRATION = 'calibration', 'Calibration'

    type = models.CharField(max_length=30, unique=True, choices=NoteType.choices)
    note = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['type']

    def __str__(self):
        return self.get_type_display()