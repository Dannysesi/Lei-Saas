from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.http import HttpResponseBadRequest, HttpResponse
from django.conf import settings
from django.utils import timezone
from django_tenants.utils import schema_context, get_tenant_model
import requests
import json

from .forms import CompanyForm, TenantUserForm
from .models import PreTenantSignup
from customers.models import Client, Domain, Plan, SubscriptionStatus
from staffs.models import TenantUser
from django.contrib import messages
from django.conf import settings

def landing_page(request):
    """Render the landing page with call-to-action"""
    plans = Plan.objects.all()
    return render(request, 'onboarding/landing_page.html', {'plans': plans})

def company_step(request):
    if request.method == 'POST':
        form = CompanyForm(request.POST)
        if form.is_valid():
            # Store only serializable data in session
            request.session['onboarding_data'] = {
                'company': {
                    'company_name': form.cleaned_data['company_name'],
                    'company_email': form.cleaned_data['company_email'],
                    'subdomain': form.cleaned_data['subdomain'],
                    'plan_id': form.cleaned_data['plan'].id,  # Store ID instead of object
                },
                'step': 'company'
            }
            return redirect('tenant_user_step')
    else:
        form = CompanyForm()
    
    return render(request, 'onboarding/company_step.html', {'form': form})

def tenant_user_step(request):
    onboarding_data = request.session.get('onboarding_data', {})
    if not onboarding_data.get('company'):
        return redirect('onboarding:company')
    
    try:
        # Get the plan from the ID stored in session
        plan = Plan.objects.get(id=onboarding_data['company']['plan_id'])
    except Plan.DoesNotExist:
        messages.error(request, "Selected plan no longer exists")
        return redirect('company')
    
    if request.method == 'POST':
        form = TenantUserForm(request.POST)
        if form.is_valid():
            # Create PreTenantSignup with the retrieved plan
            company_data = onboarding_data['company']
            presignup = PreTenantSignup(
                company_name=company_data['company_name'],
                company_email=company_data['company_email'],
                subdomain=company_data['subdomain'],
                plan=plan,  # Use the retrieved plan object
                admin_full_name=form.cleaned_data['admin_full_name'],
                admin_email=form.cleaned_data['admin_email']
            )
            presignup.encrypt_password(form.cleaned_data['password1'])
            presignup.save()
            
            # Clear session data
            del request.session['onboarding_data']
            request.session['presignup_id'] = presignup.id
            return redirect('payment')
    else:
        form = TenantUserForm()
    
    return render(request, 'onboarding/tenant_user_step.html', {'form': form})

def initiate_payment(request):
    presignup_id = request.session.get('presignup_id')
    if not presignup_id:
        return redirect('company')
    
    presignup = get_object_or_404(PreTenantSignup, id=presignup_id)
    
    # Prevent duplicate payments
    if presignup.payment_verified:
        return redirect('payment_success')
    
    headers = {
        "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json"
    }
    
    callback_url = request.build_absolute_uri(
        reverse('payment_callback')
    )
    
    data = {
        "email": presignup.company_email,
        "amount": int(presignup.plan.price * 100),  # Convert to kobo
        "callback_url": callback_url,
        "metadata": {
            "presignup_id": presignup.id,
            "custom_fields": [
                {
                    "display_name": "Company Name",
                    "variable_name": "company_name",
                    "value": presignup.company_name
                }
            ]
        }
    }
    
    try:
        response = requests.post(
            "https://api.paystack.co/transaction/initialize",
            headers=headers,
            json=data
        )
        response.raise_for_status()
        payment_url = response.json()['data']['authorization_url']
        return redirect(payment_url)
    except requests.RequestException:
        messages.error(request, "Payment initialization failed. Please try again.")
        return redirect('payment_retry', presignup_id=presignup.id)

def payment_callback(request):
    reference = request.GET.get('reference')
    if not reference:
        return HttpResponseBadRequest("Missing payment reference")
    
    # Verify payment with Paystack
    headers = {
        "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        verify_response = requests.get(
            f"https://api.paystack.co/transaction/verify/{reference}",
            headers=headers
        )
        verify_response.raise_for_status()
        payment_data = verify_response.json()
        
        if payment_data['data']['status'] == 'success':
            presignup_id = payment_data['data']['metadata']['presignup_id']
            presignup = get_object_or_404(PreTenantSignup, id=presignup_id)
            
            # Mark as paid
            presignup.payment_reference = reference
            presignup.payment_verified = True
            presignup.save()
            
            # Create tenant and admin user
            return _complete_onboarding(presignup)
            
        return HttpResponseBadRequest("Payment not successful")
    except requests.RequestException:
        return HttpResponseBadRequest("Payment verification failed")

def _complete_onboarding(presignup):
    """Handle tenant and user creation after successful payment"""
    # Create tenant
    tenant = Client.objects.create(
        name=presignup.company_name,
        email=presignup.company_email,
        subdomain=presignup.subdomain,
        plan=presignup.plan,
        is_active=True,
        paid_until=timezone.now().date() + timezone.timedelta(days=365)
    )
    
    # Create domain
    Domain.objects.create(
        domain=f"{presignup.subdomain}.{settings.BASE_DOMAIN}",
        tenant=tenant,
        is_primary=True
    )

    SubscriptionStatus.objects.create(
        client=tenant,
        is_active=True,
        renewal_due=timezone.now().date() + timezone.timedelta(days=365)  # Same as paid_until
    )

    with schema_context(tenant.schema_name):
        # Generate username from email
        base_username = presignup.admin_email.split('@')[0]
        username = base_username
        
        # Ensure username is unique within tenant
        counter = 1
        while TenantUser.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1

        admin = TenantUser.objects.create(
            username=username,  # Add this line
            email=presignup.admin_email,
            first_name=presignup.admin_full_name.split()[0],
            last_name=' '.join(presignup.admin_full_name.split()[1:]),
            is_tenant_admin=True,
            is_staff=True,
            is_active=True
        )
        admin.set_password(presignup.decrypt_password())
        admin.save()
    
    # Clean up
    presignup.delete()
    
    # Redirect to tenant login
    tenant_url = f"http://{presignup.subdomain}.{settings.BASE_DOMAIN}:8000/login/"
    return redirect(tenant_url)

def payment_webhook(request):
    """Handle Paystack webhook for payment notifications"""
    if request.method == 'POST':
        try:
            # Verify signature (important for security)
            signature = request.headers.get('x-paystack-signature')
            if not _verify_paystack_signature(request.body, signature):
                return HttpResponseBadRequest("Invalid signature")
            
            payload = json.loads(request.body)
            event = payload.get('event')
            
            if event == 'charge.success':
                reference = payload['data']['reference']
                presignup_id = payload['data']['metadata']['presignup_id']
                
                # Double-check payment status
                if not PreTenantSignup.objects.filter(
                    id=presignup_id,
                    payment_reference=reference,
                    payment_verified=True
                ).exists():
                    _complete_onboarding(get_object_or_404(PreTenantSignup, id=presignup_id))
                
                return HttpResponse("Webhook processed", status=200)
            
            return HttpResponse("Event not handled", status=200)
        except Exception as e:
            return HttpResponseBadRequest(f"Error processing webhook: {str(e)}")
    
    return HttpResponseBadRequest("Invalid method")

def _verify_paystack_signature(payload, signature):
    """Verify Paystack webhook signature"""
    import hmac
    import hashlib
    
    computed_signature = hmac.new(
        settings.PAYSTACK_SECRET_KEY.encode('utf-8'),
        payload,
        digestmod=hashlib.sha512
    ).hexdigest()
    
    return hmac.compare_digest(computed_signature, signature)



#################################################################################
#                       RENEWAL ERROR -> REVIEW THIS!!!                         #
##################################################################################
def renew_subscription(request):
    # Get the current tenant (already exists)
    tenant = request.tenant
    
    if request.method == 'POST':
        # Get the selected plan (could add plan selection to form)
        plan = tenant.plan  # Or get from request.POST if offering upgrades
        
        # Prepare Paystack payment
        headers = {
            "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
            "Content-Type": "application/json"
        }
        
        callback_url = request.build_absolute_uri(
            reverse('onboarding:renewal_callback')
        )
        
        data = {
            "email": tenant.email,
            "amount": int(plan.price * 100),  # Convert to kobo
            "callback_url": callback_url,
            "metadata": {
                "tenant_id": tenant.id,
                "renewal": True  # Mark as renewal payment
            }
        }
        
        try:
            response = requests.post(
                "https://api.paystack.co/transaction/initialize",
                headers=headers,
                json=data
            )
            response.raise_for_status()
            return redirect(response.json()['data']['authorization_url'])
        except requests.RequestException as e:
            messages.error(request, f"Payment initialization failed: {str(e)}")
            return redirect('renew_subscription')
    
    # GET request - show renewal page
    context = {
        'tenant': tenant,
        'grace_period': settings.GRACE_PERIOD_DAYS,
        'grace_period_ends': tenant.grace_period_ends,
    }
    return render(request, 'onboarding/renew_subscription.html', context)

def renewal_callback(request):
    """Handle Paystack callback for renewals"""
    reference = request.GET.get('reference')
    if not reference:
        return HttpResponseBadRequest("Missing payment reference")
    
    # Verify payment with Paystack
    headers = {
        "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        verify_response = requests.get(
            f"https://api.paystack.co/transaction/verify/{reference}",
            headers=headers
        )
        verify_response.raise_for_status()
        payment_data = verify_response.json()
        
        if payment_data['data']['status'] == 'success':
            tenant_id = payment_data['data']['metadata']['tenant_id']
            tenant = get_object_or_404(Client, id=tenant_id)
            
            # Renew subscription (1 month default)
            tenant.renew_subscription(months=1)
            
            # Update subscription status
            SubscriptionStatus.objects.filter(client=tenant).update(
                is_active=True,
                renewal_due=tenant.paid_until
            )
            
            messages.success(request, "Subscription renewed successfully!")
            return redirect(f"http://{tenant.subdomain}.{settings.BASE_DOMAIN}/dashboard/")
            
        messages.error(request, "Payment verification failed")
        return redirect('renew_subscription')
    except requests.RequestException:
        messages.error(request, "Payment verification failed")
        return redirect('renew_subscription')