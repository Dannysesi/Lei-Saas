from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    # your other paths here
    path('', include('onboarding.urls')),
]