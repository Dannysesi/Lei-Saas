from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from .models import PreTenantSignup
from customers.models import Client  # For subdomain validation

class CompanyForm(forms.ModelForm):
    class Meta:
        model = PreTenantSignup
        fields = ['company_name', 'company_email', 'subdomain', 'plan']
        widgets = {
            'plan': forms.RadioSelect  # Better UX for plan selection
        }

    def clean_subdomain(self):
        subdomain = self.cleaned_data['subdomain'].lower()
        
        # Check if subdomain is already taken (either in PreTenant or Client)
        if (PreTenantSignup.objects.filter(subdomain=subdomain).exists() or
            Client.objects.filter(subdomain=subdomain).exists()):
            raise ValidationError("This subdomain is not available. Please choose another.")
            
        return subdomain

class TenantUserForm(forms.ModelForm):
    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
        help_text="Your password must contain at least 8 characters."
    )
    password2 = forms.CharField(
        label="Password confirmation",
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
        help_text="Enter the same password as before, for verification."
    )

    class Meta:
        model = PreTenantSignup
        fields = ['admin_full_name', 'admin_email']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['admin_email'].widget.attrs.update({'autocomplete': 'email'})

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')
        
        if password1 and password2 and password1 != password2:
            self.add_error('password2', "Your passwords don't match.")
            
        # Validate password strength
        try:
            validate_password(password1)
        except ValidationError as e:
            self.add_error('password1', e)
            
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        # Use encryption instead of hashing (since we need the raw password later)
        instance.encrypt_password(self.cleaned_data['password1'])
        
        if commit:
            instance.save()
        return instance