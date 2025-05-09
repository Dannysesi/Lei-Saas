from django.db import models
from django_tenants.models import TenantMixin
from public.models import BaseUser
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.utils.translation import gettext_lazy as _
from django.utils.text import slugify


class TenantUser(BaseUser):
    """Tenant-specific user extensions"""
    phone_number = models.CharField(_('phone number'), max_length=20, blank=True)
    department = models.CharField(max_length=100)
    position = models.CharField(max_length=100)

    is_tenant_admin = models.BooleanField(
        _('tenant admin status'),
        default=False,
        help_text=_('Designates whether the user can manage other users in this tenant.')
    )

    # Security fields
    must_change_password = models.BooleanField(
        _('must change password'),
        default=True
    )
    last_password_change = models.DateTimeField(
        _('last password change'),
        auto_now_add=True
    )

    class Meta:
        verbose_name = _('Tenant User')
        verbose_name_plural = _('Tenant Users')
        db_table = 'staff_tenantuser'

        
    def __str__(self):
        return self.get_full_name() or self.email
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()
    
    def get_short_name(self):
        return self.first_name

    @property
    def is_admin(self):
        return self.is_tenant_admin or self.is_staff or self.is_superuser
    
    def save(self, *args, **kwargs):
        if not self.username:  # Only set if username is empty
            # Create username from email (before @) or generate one
            base_username = self.email.split('@')[0] if '@' in self.email else slugify(self.get_full_name())
            self.username = base_username
            
            # Ensure uniqueness
            counter = 1
            while TenantUser.objects.filter(username=self.username).exists():
                self.username = f"{base_username}{counter}"
                counter += 1
                
        super().save(*args, **kwargs)

