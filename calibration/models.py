from decimal import Decimal

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

from base.models import BaseModel


class Calibration(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='new_calibrations')
    sr_no = models.CharField(max_length=255, blank=True, null=True)
    lh_serial_no = models.CharField(max_length=255, blank=True, null=True)  # LH Serial No
    cert_no = models.CharField(max_length=255, unique=True, blank=True, null=True)  # Certificate No
    sticker_no = models.CharField(max_length=255, blank=True, null=True)  # Sticker No
    equipment_name = models.CharField(max_length=255, blank=True, null=True)  # Equipment Name
    company_name = models.CharField(max_length=255, blank=True, null=True)  # Company Name
    received_on = models.CharField(max_length=255, blank=True, null=True)  # Received on
    technician = models.CharField(max_length=255, blank=True, null=True)  # Technician
    date_of_calibration = models.CharField(max_length=255, blank=True, null=True)  # Date of Calibration
    expiry_date = models.CharField(max_length=255, blank=True, null=True)  # NEXT DATE OF Cal.
    validity = models.CharField(max_length=255, blank=True, null=True)  # Validity
    status = models.CharField(max_length=255, blank=True, null=True, default=None)  # Status
    note = models.TextField(blank=True, null=True)  # Note
    requested_by = models.CharField(max_length=255, blank=True, null=True)
    prepared_by = models.CharField(max_length=255, blank=True, null=True)  # Prepared By
    wasted_serial = models.CharField(max_length=255, blank=True, null=True)  # Wasted Serial No.
    invoice_no = models.CharField(max_length=255, blank=True, null=True)  # Invoice/Quote/PO No
    invoice_date = models.DateField(default=timezone.now, null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, default=Decimal('0.00'))  # Paid Amount
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, default=Decimal('0.00'))  # Total Amount
    cash_bank = models.CharField(max_length=255, blank=True, null=True)  # Cash/Bank
    client_rep_name = models.CharField(max_length=255, blank=True, null=True)  # Client Representative Name
    client_rep_number = models.CharField(max_length=255, blank=True, null=True)  # Client Representative Number
    email = models.CharField(max_length=255, blank=True, null=True)  # Email
    remarks = models.CharField(max_length=255, blank=True, null=True)  # Remarks

    def __repr__(self):
        return f'<Calibration {self.cert_no}>'

    def save(self, *args, **kwargs):
        # Extract custom attributes
        user = getattr(self, '_request_user', None)
        request = getattr(self, '_request', None)
        custom_message = getattr(self, '_activity_message', None)

        is_update = self.pk is not None

        # Handle status update based on isApprove
        if hasattr(self, 'isApprove') and self.isApprove is not None:
            self.status = "Verified ✅" if self.isApprove else "Pending"

        super().save(*args, **kwargs)

        # Activity log after save
        if user:
            from base.utils import log_activity
            action = custom_message if custom_message else (
                f"{'Updated' if is_update else 'Created'} calibration record {self.cert_no or self.pk}"
            )
            log_activity(user=user, action=action, request=request)

    @property
    def city(self):
        return self.user.profile.city if self.user and hasattr(self.user, 'profile') else None
