from django.contrib import admin
from django.urls import path
from core import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),
    path('contact/', views.contact, name='contact'),
    path('certificate/add/', views.CertificateCreateView.as_view(), name='add_certificate'),
    path('certificate/verify/<path:certificate_number>/', views.CertificateVerifyView.as_view(), name='verify_certificate'),
    path('report/daily/add/', views.DailyReportCreateView.as_view(), name='add_daily_report'),
    path('reports/daily/', views.report_list_view, name='report_list'),
    path('report/daily/add/bulk/', views.add_multiple_reports_view, name='add_daily_report_bulk'),
    path('report/daily/update/', views.update_report_search_view, name='update_report_search'),
    path('report/daily/update/<int:pk>/', views.DailyReportUpdateView.as_view(), name='update_daily_report'),
]


# from django.contrib import admin
# from django.urls import path
# from core import views

# urlpatterns = [
#     path('admin/', admin.site.urls),
#     path('', views.home, name='home'),
#     path('contact/', views.contact, name='contact'),
#     path('certificate/add/', views.CertificateCreateView.as_view(), name='add_certificate'),
#     path('certificate/verify/<path:certificate_number>/', views.CertificateVerifyView.as_view(), name='verify_certificate'),
#     path('report/daily/add/', views.DailyReportCreateView.as_view(), name='add_daily_report'),
#     path('reports/daily/', views.report_list_view, name='report_list'),
#     path('report/daily/add/bulk/', views.add_multiple_reports_view, name='add_daily_report_bulk'),
# ]
