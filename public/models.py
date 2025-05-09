from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
from customers.models import *


class BaseUser(AbstractUser):
    is_tech_admin = models.BooleanField(
        _('tech admin status'),
        default=False,
        help_text=_('Designates whether the user can access all tenants as a system administrator.')
    )
    
        
    def __str__(self):
        return self.email
    
    # Resolve relationship conflicts
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groups',
        blank=True,
        help_text='The groups this user belongs to.',
        related_name="public_user_set",
        related_query_name="public_user",
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name="public_user_set",
        related_query_name="public_user",
    )

    class Meta:
        verbose_name = _('System User')
        verbose_name_plural = _('System Users')
        db_table = 'public_users' 

    def __str__(self):
        return self.email

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()