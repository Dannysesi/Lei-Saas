from django.core.management.base import BaseCommand
from django.utils import timezone
from customers.models import Client
from django.conf import settings
from django.core.mail import send_mail

class Command(BaseCommand):
    help = 'Checks and updates subscription statuses'
    
    def handle(self, *args, **options):
        today = timezone.now().date()
        grace_days = getattr(settings, 'GRACE_PERIOD_DAYS', 3)
        
        # Expired subscriptions (beyond grace period)
        expired = Client.objects.filter(
            paid_until__lt=today - timezone.timedelta(days=grace_days),
            is_active=True
        )
        for tenant in expired:
            tenant.is_active = False
            tenant.save()
            self.stdout.write(f"Deactivated {tenant.name}")
        
        # Entering grace period
        newly_expired = Client.objects.filter(
            paid_until=today - timezone.timedelta(days=1),
            grace_period_ends__isnull=True
        )
        for tenant in newly_expired:
            tenant.activate_grace_period(grace_days)
            self._send_reminder(tenant)
            
        self.stdout.write("Subscription check completed")

    def _send_reminder(self, tenant):
        subject = f"Renew your {tenant.name} subscription"
        message = f"Your grace period ends on {tenant.grace_period_ends}"
        send_mail(
            subject,
            message,
            'noreply@yourdomain.com',
            [tenant.email],
            fail_silently=False,
        )