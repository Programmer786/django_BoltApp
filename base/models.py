from django.db import models
import uuid


class BaseModel(models.Model):
    uid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    isApprove = models.BooleanField(default=False)
    isReject = models.BooleanField(default=False)
    isActive = models.BooleanField(default=True)
    isCancel = models.BooleanField(default=False)
    cancel_reason = models.TextField(blank=True, null=True)
    isHold = models.BooleanField(default=False)
    hold_reason = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

