from decimal import Decimal

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

from base.models import BaseModel


class NonDestructiveTesting(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='new_non_destructive_testing')
    sr_no = models.CharField(max_length=255, blank=True, null=True)
    lh_serial_no = models.CharField(max_length=255, blank=True, null=True)  # LH Serial No
    report_no = models.CharField(max_length=255, unique=True, blank=True, null=True)  # Report No.
    id_serial_no = models.CharField(max_length=255, blank=True, null=True)  # ID / Serial No
    material = models.CharField(max_length=255, blank=True, null=True)  # Material
    structure_description = models.CharField(max_length=255, blank=True, null=True)  # Structure Description
    inspection_type = models.CharField(max_length=255, blank=True, null=True)  # Inspection Type
    inspection_date = models.CharField(max_length=255, blank=True, null=True)  # Inspection Date
    expiry_date = models.CharField(max_length=255, blank=True, null=True)  # Expiry Date
    remaining_months = models.CharField(max_length=255, blank=True, null=True)  # Remaining Months
    company_name = models.CharField(max_length=255, blank=True, null=True)  # Company Name
    joint_type = models.CharField(max_length=255, blank=True, null=True)  # Joint Type
    inspected_by = models.CharField(max_length=255, blank=True, null=True)  # Inspected By
    status = models.CharField(max_length=255, blank=True, null=True, default=None)  # Status
    note = models.TextField(blank=True, null=True)  # Note
    requested_by = models.CharField(max_length=255, blank=True, null=True)
    prepared_by = models.CharField(max_length=255, blank=True, null=True)  # Prepared By
    wasted_serial = models.CharField(max_length=255, blank=True, null=True)  # Wasted Serial No.
    approved_by = models.CharField(max_length=255, blank=True, null=True)  # Approved By
    received_by = models.CharField(max_length=255, blank=True, null=True)  # Received By
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
        return f'<NDT {self.report_no}>'

    def save(self, *args, **kwargs):
        user = getattr(self, '_request_user', None)
        request = getattr(self, '_request', None)
        custom_message = getattr(self, '_activity_message', None)

        is_update = self.pk is not None

        # Handle status based on isApprove flag
        if hasattr(self, 'isApprove') and self.isApprove is not None:
            self.status = "Verified ✅" if self.isApprove else "Pending"

        super().save(*args, **kwargs)

        # Log activity
        if user:
            from base.utils import log_activity  # Make sure this utility exists
            action = custom_message or f"{'Updated' if is_update else 'Created'} NDT report {self.report_no}"
            log_activity(user=user, action=action, request=request)

    @property
    def city(self):
        profile = getattr(self.user, 'profile', None) if self.user else None
        return getattr(profile, 'city', None)
