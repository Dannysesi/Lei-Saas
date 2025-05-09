from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import authenticate
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, AuthenticationForm
from .models import TenantUser
from django.core.exceptions import ValidationError

class EmailAuthenticationForm(forms.Form):
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)

    def __init__(self, request=None, *args, **kwargs):
        self.request = request
        super().__init__(*args, **kwargs)

    def clean(self):
        email = self.cleaned_data.get('email')
        password = self.cleaned_data.get('password')

        if email and password:
            self.user = authenticate(self.request, email=email, password=password)
            if self.user is None:
                raise forms.ValidationError("Invalid email or password.")
        return self.cleaned_data

    def get_user(self):
        return self.user


class TenantUserCreationForm(UserCreationForm):
    class Meta:
        model = TenantUser
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2')
    
    def __init__(self, *args, **kwargs):
        self.tenant = kwargs.pop('tenant', None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        if self.tenant and not self.instance.pk:  # Only for new users
            can_create, error = TenantUser.check_user_limit(self.tenant)
            if not can_create:
                self.add_error(None, error)  # Add as non-field error
        return cleaned_data

    def save(self, commit=True):
        if self.tenant and not self.instance.pk:
            can_create, error = TenantUser.check_user_limit(self.tenant)
            if not can_create:
                raise ValidationError(error)
        return super().save(commit)

class TenantUserProfileForm(forms.ModelForm):
    class Meta:
        model = TenantUser
        fields = ['department', 'position', 'phone_number', 'is_tenant_admin', 'is_active']

class TenantUserChangeForm(UserChangeForm):
    class Meta:
        model = TenantUser
        fields = '__all__'

class TenantUserAdminForm(forms.ModelForm):
    class Meta:
        model = TenantUser
        fields = [
            'email',
            'first_name',
            'last_name',
            'is_tenant_admin',
            'is_active',
            'department',
            'position',
            'phone_number'
        ]

class TenantAuthenticationForm(AuthenticationForm):
    def confirm_login_allowed(self, user):
        if not user.is_active:
            raise forms.ValidationError(
                "This account is inactive.",
                code='inactive',
            )
        if not hasattr(user, 'is_tenant_admin'):
            raise forms.ValidationError(
                "This account is not a tenant user.",
                code='invalid_user_type',
            )