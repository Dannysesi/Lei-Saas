from django.contrib import admin
from django.urls import path, include
from onboarding import views

urlpatterns = [
    path('', views.landing_page, name='landing'),
    path('company/', views.company_step, name='company'),
    path('admin-user/', views.tenant_user_step, name='tenant_user_step'),
    path('payment/', views.initiate_payment, name='payment'),
    path('callback/', views.payment_callback, name='payment_callback'),
    path('webhook/', views.payment_webhook, name='payment_webhook'),
    path('renew/', views.renew_subscription, name='renew_subscription'),
    path('renew/callback/', views.renewal_callback, name='renewal_callback'),
]