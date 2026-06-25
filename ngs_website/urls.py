from django.contrib import admin
from django.urls import path
from core import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),
    path('contact/', views.contact, name='contact'),
    path('certificate/add/', views.CertificateCreateView.as_view(), name='add_certificate'),
    path('certificate/verify/<path:certificate_number>/', views.CertificateVerifyView.as_view(), name='verify_certificate'),
]

# TEST 