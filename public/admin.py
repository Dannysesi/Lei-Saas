from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from .models import BaseUser  # fixed import

@admin.register(BaseUser)
class UserAdmin(BaseUserAdmin):
    model = BaseUser
    list_display = ('email', 'first_name', 'last_name', 'is_staff', 'is_active', 'is_tech_admin')  # removed is_verified
    list_filter = ('is_staff', 'is_active', 'is_tech_admin')  # removed is_verified
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('email',)

    fieldsets = (
        (None, {'fields': ('username', 'email', 'password')}),  # include username if using AbstractUser
        (_('Personal info'), {'fields': ('first_name', 'last_name',)}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser', 'is_tech_admin', 'groups', 'user_permissions')}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'first_name', 'last_name', 'password1', 'password2', 'is_staff', 'is_active'),
        }),
    )
