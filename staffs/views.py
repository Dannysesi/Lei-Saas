from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.forms import AuthenticationForm
from django_tenants.utils import tenant_context
from customers.models import Client
from .models import TenantUser
from django.http import HttpResponseForbidden
from django.views.generic import ListView, CreateView, UpdateView, DetailView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from .forms import *
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.views import PasswordResetView
from django.utils import timezone
import requests
from django.conf import settings
from django.urls import reverse
from django.http import HttpResponseBadRequest, HttpResponse
from customers.models import Plan, SubscriptionStatus
from django.db import transaction



def onboarding_error(request):
    return render(request, 'staffs/onboarding_error.html')


@login_required
def dashboard(request):
    with tenant_context(request.tenant):
        try:
            tenantuser = TenantUser.objects.get(email=request.user.email)
        except TenantUser.DoesNotExist:
            messages.error(request, "User profile not found. Please contact your administrator.")
            return redirect('onboarding_error')


        return render(request, 'staffs/dashboard.html', {
            'user': request.user,
            'tenantuser': tenantuser,
        })


def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Keep the user logged in
            
            # Update the must_change_password flag
            with tenant_context(request.tenant):
                tenant_user = TenantUser.objects.get(id=request.user.id)
                tenant_user.must_change_password = False
                tenant_user.save()
            
            messages.success(request, 'Your password has been changed successfully.')
            return redirect('dashboard')
    else:
        form = PasswordChangeForm(request.user)
    
    return render(request, 'staffs/change_password.html', {'form': form})

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    form = AuthenticationForm(request, data=request.POST or None)

    if request.method == 'POST' and form.is_valid():
        user = form.get_user()
        current_tenant = request.tenant

        # Confirm user exists inside this tenant's schema
        with tenant_context(current_tenant):
            from staffs.models import TenantUser
            try:
                tenant_user = TenantUser.objects.get(id=user.id)
                login(request, user)
                
                # Check if password change is required
                if tenant_user.must_change_password:
                    return redirect('change_password')
                
                return redirect('dashboard')
            except TenantUser.DoesNotExist:
                messages.error(request, "Invalid email or password.")
                return redirect('login')

    return render(request, 'staffs/login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('login')

class TenantPasswordResetView(PasswordResetView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        with tenant_context(self.request.tenant):
            context['site_name'] = self.request.tenant.name
            context['domain'] = self.request.tenant.domain_url
        return context


class TenantAdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        from staffs.models import TenantUser

        try:
            tenant_user = TenantUser.objects.get(pk=self.request.user.pk)
            return tenant_user.is_tenant_admin or tenant_user.is_staff
        except TenantUser.DoesNotExist:
            return self.request.user.is_staff


class UserListView(TenantAdminRequiredMixin, ListView):
    model = TenantUser
    template_name = 'staffs/user_list.html'
    context_object_name = 'users'
    paginate_by = 20
    
    def get_queryset(self):
        return TenantUser.objects.all().order_by('last_name', 'first_name')

class UserCreateView(TenantAdminRequiredMixin, CreateView):
    model = TenantUser
    form_class = TenantUserCreationForm
    template_name = 'staffs/user_create_form.html'
    success_url = reverse_lazy('user_list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['tenant'] = self.request.tenant
        return kwargs

    def form_valid(self, form):
        try:
            return super().form_valid(form)
        except ValidationError as e:
            messages.error(self.request, str(e))
            return self.form_invalid(form)

    @transaction.atomic
    def form_valid(self, form):
        # Final atomic check
        can_create, error = TenantUser.check_user_limit(self.request.tenant)
        if not can_create:
            messages.error(self.request, error)
            return redirect('user_list')
            
        response = super().form_valid(form)
        messages.success(self.request, f"User {self.object.email} created successfully")
        return redirect('user_profile_setup', pk=self.object.pk)
        #return redirect('user_profile_setup', pk=self.object.pk)


    

class UserProfileSetupView(TenantAdminRequiredMixin, UpdateView):
    model = TenantUser
    form_class = TenantUserProfileForm
    template_name = 'staffs/user_profile_setup.html'
    success_url = reverse_lazy('user_list')

class UserUpdateView(TenantAdminRequiredMixin, UpdateView):
    model = TenantUser
    form_class = TenantUserAdminForm
    template_name = 'staffs/user_form.html'
    
    def get_success_url(self):
        return reverse_lazy('user_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request,
            f"User {self.object.get_full_name()} updated successfully."
        )
        return response

class UserDetailView(TenantAdminRequiredMixin, DetailView):
    model = TenantUser
    template_name = 'staffs/user_detail.html'
    context_object_name = 'staff_user'


def features(request):
    return render(request, 'staffs/features.html', {
        'user': request.user,
    })

def pricing(request):
    return render(request, 'staffs/pricing.html', {
        'user': request.user,
    })


def renew_subscription(request):
    tenant = request.tenant
    
    if request.method == 'POST':
        # Reuse the payment flow but keep user in tenant context
        headers = {
            "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
            "Content-Type": "application/json"
        }
        
        # Use tenant's subdomain for callback
        callback_url = f"http://{request.get_host()}/renew/callback/"
        
        data = {
            "email": tenant.email,
            "amount": int(tenant.plan.price * 100),
            "callback_url": callback_url,
            "metadata": {
                "tenant_id": tenant.id,
                "renewal": True
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
        except Exception as e:
            messages.error(request, f"Payment failed: {str(e)}")
            return redirect('renew_subscription')
    
    context = {
        'tenant': tenant,
        'grace_period': settings.GRACE_PERIOD_DAYS,
    }
    return render(request, 'staffs/renew_subscription.html', context)

def renewal_callback(request):
    reference = request.GET.get('reference')
    if not reference:
        return HttpResponseBadRequest("Missing reference")
    
    headers = {
        "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(
            f"https://api.paystack.co/transaction/verify/{reference}",
            headers=headers
        )
        response.raise_for_status()
        data = response.json()
        
        if data['data']['status'] == 'success':
            tenant = request.tenant
            tenant.renew_subscription(months=12)
            messages.success(request, "Subscription renewed successfully!")
            return redirect('dashboard')  # Redirect to tenant dashboard
            
        messages.error(request, "Payment verification failed")
    except Exception as e:
        messages.error(request, f"Error: {str(e)}")
    
    return redirect('renew_subscription')