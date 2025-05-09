# subscription_middleware.py
from django.utils import timezone
from django.http import HttpResponseRedirect
from django.conf import settings

class SubscriptionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        # Skip checks for:
        # - Public schema
        # - Auth pages
        # - Renewal path itself
        skip_paths = ['/account/', '/renew/', '/static/', '/media/']
        if not hasattr(request, 'tenant') or any(request.path.startswith(p) for p in skip_paths):
            return self.get_response(request)
            
        tenant = request.tenant
        today = timezone.now().date()
        grace_days = getattr(settings, 'GRACE_PERIOD_DAYS', 3)
        
        # Check if subscription is expired (beyond grace period)
        is_expired = (
            tenant.paid_until and 
            tenant.paid_until < today - timezone.timedelta(days=grace_days) and
            not tenant.is_active
        )
        
        if is_expired and not request.path.startswith('/renew/'):
            # Redirect to same subdomain's renewal page
            return HttpResponseRedirect(f'/renew/')
            
        return self.get_response(request)