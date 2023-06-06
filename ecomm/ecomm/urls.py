"""
URL configuration for ecomm project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from toko import views
from toko.views import ExtendedSignupView, ExtendedLoginView, ExtendedLogoutView

urlpatterns = [
    path('contact/', views.contact_view, name='contact'),
    path('admin/', admin.site.urls),
    path('accounts/signup/', ExtendedSignupView.as_view(), name='account_signup'),
    path('accounts/login/', ExtendedLoginView.as_view(), name='account_login'),
    path('accounts/logout/', ExtendedLogoutView.as_view(), name='logout'),
    path('accounts/', include('allauth.urls')),
    path('paypal/', include('paypal.standard.ipn.urls')),
    path('', include('toko.urls', namespace='toko')),
    path('search-and-filter/', views.search_and_filter_view, name='search_and_filter'),
    path('filter/', views.filter_view, name='filter'),
    
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

