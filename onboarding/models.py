from django.db import models
from django.core import signing
from customers.models import Plan
from django.conf import settings
from django.utils import timezone
from datetime import timedelta

class PreTenantSignup(models.Model):
    # Company Information
    company_name = models.CharField(max_length=100)
    company_email = models.EmailField()
    subdomain = models.CharField(max_length=63)  # Remove unique - validated at creation
    plan = models.ForeignKey(Plan, on_delete=models.SET_NULL, null=True)
    
    # Admin User Information
    admin_full_name = models.CharField(max_length=150)
    admin_email = models.EmailField()
    admin_password_encrypted = models.CharField(max_length=255)  # Encrypted, not hashed
    
    # Payment/State Tracking
    payment_reference = models.CharField(max_length=100, blank=True)
    payment_verified = models.BooleanField(default=False)
    payment_attempts = models.PositiveIntegerField(default=0)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()  # Auto-set to 24 hours later
    
    class Meta:
        verbose_name = "Pending Tenant Signup"
        indexes = [
            models.Index(fields=['subdomain']),
            models.Index(fields=['admin_email']),
        ]

    def __str__(self):
        return f"{self.company_name} ({self.subdomain})"

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(hours=24)
        super().save(*args, **kwargs)

    def encrypt_password(self, raw_password):
        """Encrypt password using Django's signing framework"""
        self.admin_password_encrypted = signing.dumps(raw_password)
        
    def decrypt_password(self):
        """Retrieve original password (for tenant user creation)"""
        return signing.loads(self.admin_password_encrypted)

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at