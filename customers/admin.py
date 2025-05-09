from django.contrib import admin
from .models import Client, Domain, SubscriptionStatus, Plan
# Register your models here.

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('name', 'subdomain', 'paid_until', 'on_trial', 'trial_end_date', 'plan')
    search_fields = ('name', 'subdomain')
    list_filter = ('on_trial', 'plan')
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'
    list_per_page = 20
    list_select_related = ('plan',)
    fieldsets = (
        (None, {
            'fields': ('name', 'subdomain', 'paid_until', 'on_trial', 'trial_end_date', 'plan')
        }),
    )
    readonly_fields = ('created_at', 'updated_at')

    def has_add_permission(self, request):
        return request.user.is_superuser    
    
@admin.register(Domain)
class DomainAdmin(admin.ModelAdmin):
    list_display = ('domain', 'tenant', 'is_primary')
    search_fields = ('domain',)
    list_filter = ('is_primary',)
    ordering = ('domain',)
    fieldsets = (
        (None, {
            'fields': ('domain', 'tenant', 'is_primary')
        }),
    )



@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'max_users', 'paystack_plan_code')
    search_fields = ('name', 'paystack_plan_code')
    list_filter = ('max_users',)
    ordering = ('name',)
    fieldsets = (
        (None, {
            'fields': ('name', 'price', 'max_users', 'paystack_plan_code')
        }),
    )



@admin.register(SubscriptionStatus)
class SubscriptionStatusAdmin(admin.ModelAdmin):
    list_display = ('client', 'is_active', 'renewal_due')
    list_filter = ('is_active',)
    search_fields = ('client__name',)
    ordering = ('-renewal_due',)
    fieldsets = (
        (None, {
            'fields': ('client', 'is_active', 'renewal_due')
        }),
    )