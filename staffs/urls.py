from django.contrib import admin
from django.urls import path, include
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.dashboard, name='dashboard'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('change-password/', views.change_password, name='change_password'),
    path('onboarding-error/', views.onboarding_error, name='onboarding_error'),
    path('users/', views.UserListView.as_view(), name='user_list'),
    path('create/', views.UserCreateView.as_view(), name='user_create'),
    path('<int:pk>/', views.UserDetailView.as_view(), name='user_detail'),
    path('<int:pk>/update/', views.UserUpdateView.as_view(), name='user_update'),

    
    # Password reset URLs (for forgotten passwords)
    path('password/reset/', views.TenantPasswordResetView.as_view(
        template_name='staffs/password_reset_form.html',
        html_email_template_name='staffs/password_reset_email.html',
        success_url='/password/reset/done/'
    ), name='password_reset'),
    
    path('password/reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='staffs/password_reset_done.html'
    ), name='password_reset_done'),
    
    path('password/reset/confirm/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='staffs/password_reset_confirm.html',
        success_url='/password/reset/complete/'
    ), name='password_reset_confirm'),
    
    path('password/reset/complete/', auth_views.PasswordResetCompleteView.as_view(
        template_name='staffs/password_reset_complete.html'
    ), name='password_reset_complete'),

    path('renew/', views.renew_subscription, name='renew_subscription'),
    path('renew/callback/', views.renewal_callback, name='renewal_callback'),
]
