from django_tenants.utils import tenant_context
from staffs.models import TenantUser
from django.conf import settings
import logging

def user_limits(request):
    context = {}
    
    if not hasattr(request, 'tenant'):
        return context
    
    try:
        with tenant_context(request.tenant):
            tenant = request.tenant
            if not tenant.plan:
                return context
                
            current_users = TenantUser.objects.count()
            max_users = tenant.plan.max_users
            
            context.update({
                'current_users': current_users,
                'max_users': max_users,
                'user_limit_reached': current_users >= max_users,
                'can_create_user': current_users < max_users
            })
            
    except Exception as e:
        logging.error(f"User limits error: {str(e)}", exc_info=True)
    
    return context