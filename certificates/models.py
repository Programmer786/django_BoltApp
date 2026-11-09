from decimal import Decimal

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

from base.models import BaseModel


class Certificate(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='new_certificates')
    sr_no = models.CharField(max_length=255, blank=True, null=True)
    lh_serial_no = models.CharField(max_length=255, blank=True, null=True)
    cert_no = models.CharField(max_length=255, unique=True, blank=False, null=False, help_text="Certificate number must be unique and cannot be empty")
    sticker_no = models.TextField(blank=True, null=True)
    eq_serial_no = models.TextField(blank=True, null=True)
    equipment_type = models.TextField(blank=True, null=True)
    company_name = models.CharField(max_length=255, blank=True, null=True)
    inspection_date = models.CharField(max_length=255, blank=True, null=True)
    expiry_date = models.CharField(max_length=255, blank=True, null=True)
    remaining_months = models.CharField(max_length=255, blank=True, null=True)
    plate_no = models.CharField(max_length=255, blank=True, null=True)
    manufacturer = models.CharField(max_length=255, blank=True, null=True)
    inspected_by = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=255, blank=True, null=True, default=None)
    note = models.TextField(blank=True, null=True)
    requested_by = models.CharField(max_length=255, blank=True, null=True)
    prepared_by = models.CharField(max_length=255, blank=True, null=True)
    wasted_serial = models.CharField(max_length=255, blank=True, null=True)
    invoice_no = models.CharField(max_length=255, blank=True, null=True)
    invoice_date = models.DateField(default=timezone.now, null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, default=Decimal('0.00'))  # Paid Amount
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, default=Decimal('0.00'))  # Total Amount
    cash_bank = models.CharField(max_length=255, blank=True, null=True)
    client_rep_name = models.CharField(max_length=255, blank=True, null=True)
    client_rep_number = models.CharField(max_length=255, blank=True, null=True)
    email = models.CharField(max_length=255, blank=True, null=True)
    remarks = models.CharField(max_length=255, blank=True, null=True)
    project_location = models.CharField(max_length=255, blank=True, null=True)
    date_of_report = models.CharField(max_length=255, blank=True, null=True)
    date_of_last_inspection = models.CharField(max_length=255, blank=True, null=True)
    reference_standard = models.CharField(max_length=255, blank=True, null=True)
    type_model_year = models.CharField(max_length=255, blank=True, null=True)
    bucket_capacity = models.CharField(max_length=255, blank=True, null=True)
    summary_description_1 = models.CharField(max_length=255, blank=True, null=True, default="Was the Examination carried out within an interval as recommended?")
    summary_result_1 = models.CharField(max_length=255, blank=True, null=True, default="No")  # PASSED, NO, FAILED
    summary_comments_1 = models.CharField(max_length=255, blank=True, null=True, default="Through Examination")
    summary_description_2 = models.CharField(max_length=255, blank=True, null=True, default="Overall inspection result:")
    summary_result_2 = models.CharField(max_length=255, blank=True, null=True, default="No")  # PASSED, NO, FAILED
    summary_comments_2 = models.CharField(max_length=255, blank=True, null=True, default="Safe to use")
    summary_description_3 = models.CharField(max_length=255, blank=True, null=True, default="Identification of any part found to have defective which is or could become danger to person and a description of the defect.")
    summary_result_3 = models.CharField(max_length=255, blank=True, null=True, default="No")  # PASSED, NO, FAILED
    summary_comments_3 = models.CharField(max_length=255, blank=True, null=True, default="If yes, please describe: (in case of defect found)")

    def __repr__(self):
        return f'<Certificate {self.cert_no}>'

    def save(self, *args, **kwargs):
        user = getattr(self, '_request_user', None)
        request = getattr(self, '_request', None)
        custom_message = getattr(self, '_activity_message', None)

        is_update = self.pk is not None

        # Handle status update
        if hasattr(self, 'isApprove') and self.isApprove is not None:
            self.status = "Verified ✅" if self.isApprove else "Pending"

        super().save(*args, **kwargs)

        if user:
            from base.utils import log_activity
            action = custom_message if custom_message else (
                f"{'Updated' if is_update else 'Created'} certificate {self.cert_no}"
            )
            log_activity(user=user, action=action, request=request)

    @property
    def city(self):
        profile = getattr(self.user, 'profile', None) if self.user else None
        return getattr(profile, 'city', None)


def normalize_equipment_type(value):
    return ' '.join((value or '').split()).upper()


class EquipmentType(models.Model):
    """Choices for Certificate.equipment_type, which itself stays plain text."""
    name = models.CharField(max_length=200, unique=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name
