from decimal import Decimal

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

from base.models import BaseModel


class Training(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='new_trainings')
    sr_no = models.CharField(max_length=255, blank=True, null=True)
    card_no = models.CharField(max_length=255, blank=True, null=True)
    cert_no = models.CharField(max_length=255, blank=True, null=True)
    name_of_trainee = models.CharField(max_length=255, blank=True, null=True)
    company_name = models.CharField(max_length=255, blank=True, null=True)
    iqama_no = models.CharField(max_length=255, blank=True, null=True)
    issue_date = models.CharField(max_length=255, blank=True, null=True)
    expiry_date = models.CharField(max_length=255, blank=True, null=True)
    remaining_months = models.CharField(max_length=255, blank=True, null=True)
    trade = models.CharField(max_length=255, blank=True, null=True)
    holo_gram_no = models.CharField(max_length=255, blank=True, null=True)
    assessed_by_resource_person = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=255, blank=True, null=True, default=None)
    note = models.TextField(blank=True, null=True)
    wasted_serial = models.CharField(max_length=255, blank=True, null=True)
    requested_by = models.CharField(max_length=255, blank=True, null=True)
    prepared_by = models.CharField(max_length=255, blank=True, null=True)
    invoice_no = models.CharField(max_length=255, blank=True, null=True)
    invoice_date = models.DateField(default=timezone.now, null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, default=Decimal('0.00'))  # Paid Amount
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, default=Decimal('0.00'))  # Total Amount
    cash_bank = models.CharField(max_length=255, blank=True, null=True)
    client_rep_name = models.CharField(max_length=255, blank=True, null=True)
    client_rep_number = models.CharField(max_length=255, blank=True, null=True)
    email = models.CharField(max_length=255, blank=True, null=True)
    remarks = models.CharField(max_length=255, blank=True, null=True)

    def __repr__(self):
        return f'<Training {self.card_no}>'

    def save(self, *args, **kwargs):
        user = getattr(self, '_request_user', None)
        request = getattr(self, '_request', None)
        custom_message = getattr(self, '_activity_message', None)

        is_update = self.pk is not None

        # Update status based on isApprove flag
        if hasattr(self, 'isApprove') and self.isApprove is not None:
            self.status = "Verified ✅" if self.isApprove else "Pending"

        super().save(*args, **kwargs)

        # Log activity
        if user:
            from base.utils import log_activity  # Your centralized logging function
            action = custom_message or f"{'Updated' if is_update else 'Created'} Training card {self.card_no}"
            log_activity(user=user, action=action, request=request)

    @property
    def city(self):
        profile = getattr(self.user, 'profile', None) if self.user else None
        return getattr(profile, 'city', None)
