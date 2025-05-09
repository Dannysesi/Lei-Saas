"""
Django settings for saas project.

Generated by 'django-admin startproject' using Django 5.1.8.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.1/ref/settings/
"""

from pathlib import Path
import environ
import os
import dj_database_url

# Initialize environment variables
env = environ.Env(
    DEBUG=(bool, False)
)

# Take environment variables from .env file

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

environ.Env.read_env(os.path.join(BASE_DIR, '.env'))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-@+(n%bb*#@ie9h(m-vx()lq+r!lc+mdz!4lrv!qjlfxb7^!_(&'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env('DEBUG')

ALLOWED_HOSTS = [
    'lei-saas.onrender.com',
    '.lei-saas.onrender.com',  # for subdomains
    'localhost',  # optional for local dev
]


# Application definition

SHARED_APPS = [
    'django_tenants',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_hosts',
    'customers',
    'public',
    'onboarding'
]

TENANT_APPS = [
    'django.contrib.contenttypes',
    'django.contrib.auth',
    # 'django.contrib.admin',
    'django.contrib.sessions',
    'django.contrib.messages',
    'staffs',
]

INSTALLED_APPS = list(SHARED_APPS) + [app for app in TENANT_APPS if app not in SHARED_APPS]

TENANT_MODEL = "customers.Client"
TENANT_DOMAIN_MODEL = "customers.Domain"

MIDDLEWARE = [
    'django_hosts.middleware.HostsRequestMiddleware',  
    'django.middleware.security.SecurityMiddleware',
    'django_tenants.middleware.TenantMainMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'saas.subscription_middleware.SubscriptionMiddleware',
    'django_hosts.middleware.HostsResponseMiddleware',    
]

ROOT_URLCONF = 'saas.urls'

ROOT_HOSTCONF = 'saas.hosts'
DEFAULT_HOST = 'www'
# PARENT_HOST = 'lei-saas'
PUBLIC_SCHEMA_NAME = 'public'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'staffs.context_processors.user_limits',
            ],
        },
    },
]

WSGI_APPLICATION = 'saas.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases

DATABASE_ROUTERS = ('django_tenants.routers.TenantSyncRouter',)

# DATABASES = {
#     'default': {
#         'ENGINE': 'django_tenants.postgresql_backend',
#         'NAME': env('DB_NAME'),
#         'USER': env('DB_USER'),
#         'PASSWORD': env('DB_PASSWORD'),
#         'HOST': env('DB_HOST'),
#         'PORT': env('DB_PORT'),
#     }
# }


# DATABASES = {
#     'default': {
#         'ENGINE': 'django_tenants.postgresql_backend',  # <-- Important
#         'NAME': 'saas2',
#         'USER': 'saas2_user',
#         'PASSWORD': 'pInNWQ8gdTyxu9xz3gV4t2sBRqoK7Zbg',
#         'HOST': 'dpg-d0f52924d50c739tvbi0-a.oregon-postgres.render.com',
#         'PORT': '5432',
#     }
# }


DATABASES = {
    'default': dj_database_url.parse(
        os.getenv('DATABASE_URL'),
        engine='django_tenants.postgresql_backend',  # for django-tenants
    )
}


# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

AUTH_USER_MODEL = 'public.BaseUser'


# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/

STATIC_URL = 'static/'

# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


PAYSTACK_SECRET_KEY = env('PAYSTACK_SECRET_KEY')
PAYSTACK_PUBLIC_KEY = env('PAYSTACK_PUBLIC_KEY')
PAYSTACK_CALLBACK_URL = env('PAYSTACK_CALLBACK_URL')

EMAIL_BACKEND = env('EMAIL_BACKEND')
EMAIL_HOST = env('EMAIL_HOST')
EMAIL_PORT = env.int('EMAIL_PORT')

# BASE_DOMAIN = 'lei-saas'
GRACE_PERIOD_DAYS = env.int('GRACE_PERIOD_DAYS')


PARENT_HOST = 'lei-saas.onrender.com'
BASE_DOMAIN = 'lei-saas.onrender.com'
BASE_URL = 'https://lei-saas.onrender.com'
