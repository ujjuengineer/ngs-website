from django.contrib import admin
from django.urls import path
from django.contrib.auth import views as auth_views
from core import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),
    path('contact/', views.contact, name='contact'),

    # ── AUTH ──
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # ── CERTIFICATES ──
    path('certificate/add/', views.CertificateCreateView.as_view(), name='add_certificate'),
    path('certificate/verify/<path:certificate_number>/', views.CertificateVerifyView.as_view(), name='verify_certificate'),

    # ── REPORTS (login required) ──
    path('report/daily/add/', views.daily_report_create_view, name='add_daily_report'),
    path('reports/daily/', views.report_list_view, name='report_list'),
    path('report/daily/add/bulk/', views.add_multiple_reports_view, name='add_daily_report_bulk'),
    path('report/daily/update/', views.update_report_search_view, name='update_report_search'),
    path('report/daily/update/<int:pk>/', views.daily_report_update_view, name='update_daily_report'),
]

# path('report/daily/add/', views.DailyReportCreateView.as_view(), name='add_daily_report')
# path('report/daily/update/<int:pk>/', views.DailyReportUpdateView.as_view(), name='update_daily_report'),