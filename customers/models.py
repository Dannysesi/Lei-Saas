from django.db import models
from django_tenants.models import TenantMixin, DomainMixin
from django.utils import timezone
from datetime import timedelta
from django.core.exceptions import ValidationError
import re

# -----------------------------
# Plan Model
# -----------------------------
class Plan(models.Model):
    BASIC = 'Basic'
    PREMIUM = 'Premium'
    PLAN_CHOICES = [
        (BASIC, 'Basic'),
        (PREMIUM, 'Premium'),
    ]

    name = models.CharField(max_length=50, choices=PLAN_CHOICES)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    features = models.JSONField(blank=True, null=True)  # Use JSON for structured features
    max_users = models.PositiveIntegerField(default=1, help_text="Maximum users allowed to access the system.")
    max_employees = models.PositiveIntegerField(default=10, help_text="Maximum employees allowed on payroll.")
    paystack_plan_code = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return self.name

# -----------------------------
# Subdomain Validator
# -----------------------------
def validate_subdomain(value):
    """Validate that the subdomain contains only allowed characters"""
    if not re.match(r'^[a-z0-9-]+$', value):
        raise ValidationError('Subdomain can only contain lowercase letters, numbers, and hyphens')
    if value.startswith('-') or value.endswith('-'):
        raise ValidationError('Subdomain cannot start or end with a hyphen')

# -----------------------------
# Client (Tenant) Model
# -----------------------------
class Client(TenantMixin):
    name = models.CharField(max_length=100)
    subdomain = models.CharField(
        max_length=63,
        unique=True,
        validators=[validate_subdomain],
        help_text="Used in the URL (e.g., yourcompany.example.com)"
    )
    email = models.EmailField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=False)
    paid_until = models.DateField(blank=True, null=True)
    on_trial = models.BooleanField(default=True)
    trial_end_date = models.DateField(null=True, blank=True)
    plan = models.ForeignKey(Plan, on_delete=models.SET_NULL, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    grace_period_ends = models.DateField(null=True, blank=True)

    # django-tenants control
    auto_create_schema = True
    auto_drop_schema = True

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Organization"
        verbose_name_plural = "Organizations"
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        # Set schema name from subdomain
        self.schema_name = self.subdomain.lower()

        # Set trial end if it's on trial and not yet set
        if self.on_trial and not self.trial_end_date:
            self.trial_end_date = timezone.now().date() + timedelta(days=14)

        super().save(*args, **kwargs)

    @property
    def subscription_status(self):
        """Returns 'active', 'grace_period', or 'expired'"""
        today = timezone.now().date()
        
        if self.paid_until and self.paid_until >= today:
            return 'active'
        elif self.grace_period_ends and self.grace_period_ends >= today:
            return 'grace_period'
        return 'expired'
    
    def activate_grace_period(self, days=3):
        """Sets grace period expiration"""
        self.grace_period_ends = timezone.now().date() + timezone.timedelta(days=days)
        self.save()
    
    def renew_subscription(self, months=1):
        """Extends subscription period"""
        self.paid_until = timezone.now().date() + timezone.timedelta(days=30*months)
        self.grace_period_ends = None
        self.is_active = True
        self.save()

    def check_and_deactivate(self):
        if self.subscription_status == 'expired' and self.is_active:
            self.is_active = False
            self.save()

# -----------------------------
# Domain Model
# -----------------------------
class Domain(DomainMixin):
    def __str__(self):
        return self.domain

    class Meta:
        verbose_name = "Domain"
        verbose_name_plural = "Domains"

# -----------------------------
# Subscription Status (Optional)
# -----------------------------
class SubscriptionStatus(models.Model):
    client = models.OneToOneField(Client, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)
    renewal_due = models.DateField(blank=True, null=True)

    def __str__(self):
        return f"{self.client.name} - {'Active' if self.is_active else 'Inactive'}"

    class Meta:
        verbose_name = "Subscription Status"
        verbose_name_plural = "Subscription Statuses"
