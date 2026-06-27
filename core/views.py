from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import ContactMessage, CompanyCertificate, DailyReport
from django.urls import reverse_lazy, reverse
from django.views.generic.edit import CreateView, UpdateView
from .forms import CertificateForm, DailyReportForm, DailyReportBulkForm
from django.contrib.messages.views import SuccessMessageMixin
from django.views.generic import DetailView
import datetime
from django.http import HttpResponse
from openpyxl import Workbook
from django.forms import modelformset_factory


def home(request):
    return render(request, 'core/home.html')


def contact(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        subject = request.POST.get('subject', '').strip()
        message = request.POST.get('message', '').strip()

        if name and email and subject and message:
            ContactMessage.objects.create(
                name=name, email=email, phone=phone,
                subject=subject, message=message
            )
            messages.success(request, 'Thank you! Your message has been received. We will contact you shortly.')
        else:
            messages.error(request, 'Please fill in all required fields.')
        return redirect('home')
    return redirect('home')


class CertificateCreateView(CreateView):
    model = CompanyCertificate
    form_class = CertificateForm
    template_name = 'core/add_certificate.html'
    success_url = reverse_lazy('add_certificate')
    success_message = "Certificate for %(recipient_name)s was created successfully!"


class CertificateVerifyView(DetailView):
    model = CompanyCertificate
    template_name = 'core/verify_certificate.html'
    context_object_name = 'certificate'
    slug_field = 'certificate_number'
    slug_url_kwarg = 'certificate_number'


class DailyReportCreateView(SuccessMessageMixin, CreateView):
    model = DailyReport
    form_class = DailyReportForm
    template_name = 'core/add_report.html'
    success_message = "Daily report for %(name)s at %(location)s recorded successfully!"

    def get_success_url(self):
        # If came from update search page, go back there after submit
        next_url = self.request.GET.get('next') or self.request.POST.get('next')
        if next_url:
            return next_url
        return reverse_lazy('add_daily_report')

    def get_initial(self):
        # Pre-fill form fields if passed via GET (from update search page)
        initial = super().get_initial()
        for field in ['year', 'volume_num', 'location']:
            val = self.request.GET.get(field)
            if val:
                initial[field] = val
        return initial

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['next'] = self.request.GET.get('next', '')
        return ctx


def add_multiple_reports_view(request):
    DailyReportFormSet = modelformset_factory(
        DailyReport,
        form=DailyReportBulkForm,
        extra=1,
        can_delete=False
    )

    if request.method == 'POST':
        formset = DailyReportFormSet(request.POST)
        master_name = request.POST.get('master_name', '').strip()

        if not master_name:
            messages.error(request, "Please enter the Employee Name before submitting.")
        elif formset.is_valid():
            instances = formset.save(commit=False)
            for instance in instances:
                instance.name = master_name
                instance.save()
            messages.success(request, f"Successfully saved {len(instances)} daily reports!")
            return redirect('add_daily_report_bulk')
    else:
        formset = DailyReportFormSet(queryset=DailyReport.objects.none())

    return render(request, 'core/add_multiple_reports.html', {'formset': formset})



def report_list_view(request):
    queryset = DailyReport.objects.all()

    # 1. Capture incoming filter data
    filter_date = request.GET.get('date', '').strip()
    filter_month = request.GET.get('month', '').strip()  # Format expected: "YYYY-MM"
    filter_location = request.GET.get('location', '').strip()
    filter_name = request.GET.get('name', '').strip()

    # 2. Apply filters independently
    if filter_date:
        queryset = queryset.filter(date=filter_date)
        
    if filter_month:
        try:
            # Split "2026-06" into year=2026 and month=6
            year_part, month_part = map(int, filter_month.split('-'))
            queryset = queryset.filter(date__year=year_part, date__month=month_part)
        except ValueError:
            pass # Handle invalid formats gracefully
        
    if filter_location:
        queryset = queryset.filter(location=filter_location)
        
    if filter_name:
        queryset = queryset.filter(name__icontains=filter_name)

    # 3. Handle Excel Export (Preserves the new monthly filtering)
    if 'export_excel' in request.GET:
        wb = Workbook()
        ws = wb.active
        ws.title = "Filtered Reports"
        headers = ['Date', 'Location', 'Employee Name', 'Year', 'Volume No.', 'No. Deeds', 'No. Pages', 'PDF', 'Indexing', 'Uploading', 'QC', 'Metadata']
        ws.append(headers)
        for report in queryset:
            ws.append([
                report.date.strftime('%Y-%m-%d') if report.date else '',
                report.get_location_display(), report.name, report.year, report.volume_num,
                report.num_of_deed, report.num_of_page,
                "Yes" if report.pdf_deed else "No", "Yes" if report.indexing else "No",
                "Yes" if report.QC else "NO",
                "Yes" if report.uploading else "No", "Yes" if report.metadata else "No",
            ])
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename=Reports_Export_{datetime.date.today()}.xlsx'
        wb.save(response)
        return response

    # 4. Generate dynamic list of months available in the database for the dropdown
    # This grabs all unique dates, sorts them, and extracts unique YYYY-MM pairs
    existing_dates = DailyReport.objects.dates('date', 'month', order='DESC')
    available_months = []
    for d in existing_dates:
        available_months.append({
            'value': d.strftime('%Y-%m'),      # Used in backend processing: "2026-06"
            'display': d.strftime('%B %Y')     # Visible to users: "June 2026"
        })

    context = {
        'reports': queryset,
        'locations': DailyReport.LOCATION_CHOICES,
        'available_months': available_months,
        'selected_date': filter_date,
        'selected_month': filter_month,
        'selected_location': filter_location,
        'selected_name': filter_name,
    }
    return render(request, 'core/report_list.html', context)

# def report_list_view(request):
#     queryset = DailyReport.objects.all()

#     filter_date = request.GET.get('date', '').strip()
#     filter_location = request.GET.get('location', '').strip()
#     filter_name = request.GET.get('name', '').strip()

#     if filter_date:
#         queryset = queryset.filter(date=filter_date)
#     if filter_location:
#         queryset = queryset.filter(location=filter_location)
#     if filter_name:
#         queryset = queryset.filter(name__icontains=filter_name)

#     if 'export_excel' in request.GET:
#         wb = Workbook()
#         ws = wb.active
#         ws.title = "Daily Reports"
#         headers = [
#             'Date', 'Location', 'Employee Name', 'Year', 'Volume No.',
#             'No. of Deeds', 'No. of Pages', 'PDF Complete', 'Indexing', 'Uploading', 'Metadata'
#         ]
#         ws.append(headers)
#         for report in queryset:
#             ws.append([
#                 report.date.strftime('%Y-%m-%d') if report.date else '',
#                 report.get_location_display(),
#                 report.name,
#                 report.year,
#                 report.volume_num,
#                 report.num_of_deed,
#                 report.num_of_page,
#                 "Yes" if report.pdf_deed else "No",
#                 "Yes" if report.indexing else "No",
#                 "Yes" if report.uploading else "No",
#                 "Yes" if report.metadata else "No",
#             ])
#         response = HttpResponse(
#             content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
#         )
#         response['Content-Disposition'] = f'attachment; filename=Daily_Reports_{datetime.date.today()}.xlsx'
#         wb.save(response)
#         return response

#     locations = DailyReport.LOCATION_CHOICES
#     context = {
#         'reports': queryset,
#         'locations': locations,
#         'selected_date': filter_date,
#         'selected_location': filter_location,
#         'selected_name': filter_name,
#     }
#     return render(request, 'core/report_list.html', context)


# ── UPDATE REPORT: Search by Year + Volume Number + Location ──

def update_report_search_view(request):
    """
    Step 1: Search for a report by Year + Volume Number + Location.
    - If found → redirect to the update form.
    - If not found → show a prompt asking if they want to add it.
    """
    report = None
    not_found = False
    searched = False

    # Pre-fill search values from GET params
    year = request.GET.get('year', '').strip()
    volume_num = request.GET.get('volume_num', '').strip()
    location = request.GET.get('location', '').strip()

    if year and volume_num and location:
        searched = True
        try:
            report = DailyReport.objects.get(
                year=year,
                volume_num=volume_num,
                location=location
            )
        except DailyReport.DoesNotExist:
            not_found = True
        except DailyReport.MultipleObjectsReturned:
            # If multiple records match, take the most recent one
            report = DailyReport.objects.filter(
                year=year,
                volume_num=volume_num,
                location=location
            ).order_by('-date').first()

    locations = DailyReport.LOCATION_CHOICES

    context = {
        'report': report,
        'not_found': not_found,
        'searched': searched,
        'year': year,
        'volume_num': volume_num,
        'location': location,
        'locations': locations,
    }
    return render(request, 'core/update_report_search.html', context)


class DailyReportUpdateView(SuccessMessageMixin, UpdateView):
    """
    Step 2: Update form for a found report.
    After saving, redirect back to search page.
    """
    model = DailyReport
    form_class = DailyReportForm
    template_name = 'core/update_report.html'
    success_message = "Report updated successfully!"

    def get_success_url(self):
        # Go back to search pre-filled with the same search params
        report = self.object
        return reverse('update_report_search') + \
            f"?year={report.year}&volume_num={report.volume_num}&location={report.location}"


# from django.shortcuts import render, redirect
# from django.contrib import messages
# from .models import ContactMessage, CompanyCertificate, DailyReport
# from django.urls import reverse_lazy
# from django.views.generic.edit import CreateView
# from .forms import CertificateForm, DailyReportForm, DailyReportBulkForm
# from django.contrib.messages.views import SuccessMessageMixin
# from django.views.generic import DetailView
# import datetime
# from django.http import HttpResponse
# from openpyxl import Workbook
# from django.forms import modelformset_factory


# def home(request):
#     return render(request, 'core/home.html')

# def contact(request):
#     if request.method == 'POST':
#         name = request.POST.get('name', '').strip()
#         email = request.POST.get('email', '').strip()
#         phone = request.POST.get('phone', '').strip()
#         subject = request.POST.get('subject', '').strip()
#         message = request.POST.get('message', '').strip()

#         if name and email and subject and message:
#             ContactMessage.objects.create(
#                 name=name,
#                 email=email,
#                 phone=phone,
#                 subject=subject,
#                 message=message
#             )
#             messages.success(request, 'Thank you! Your message has been received. We will contact you shortly.')
#         else:
#             messages.error(request, 'Please fill in all required fields.')
#         return redirect('home')
#     return redirect('home')


# class CertificateCreateView(CreateView):
#     model = CompanyCertificate
#     form_class = CertificateForm
#     template_name = 'core/add_certificate.html'
    
#     # Where to redirect the user after successfully adding a certificate
#     # Change 'certificate_list' to whatever your success URL name is
#     success_url = reverse_lazy('add_certificate')

#     success_message = "Certificate for %(recipient_name)s was created successfully!"


# class CertificateVerifyView(DetailView):
#     model = CompanyCertificate
#     template_name = 'core/verify_certificate.html'
#     context_object_name = 'certificate'
    
#     # Tell Django to look up the certificate by its number instead of its primary key ID
#     slug_field = 'certificate_number'
#     slug_url_kwarg = 'certificate_number'


# # adds single report at a time
# class DailyReportCreateView(SuccessMessageMixin, CreateView):
#     model = DailyReport
#     form_class = DailyReportForm
#     template_name = 'core/add_report.html'
    
#     # Redirects back to this form for sequential data entry
#     success_url = reverse_lazy('add_daily_report')
    
#     # Success alert message
#     success_message = "Daily report for %(name)s at %(location)s recorded successfully!"


# # adds multiple report at a time
# def add_multiple_reports_view(request):
#     # 🌟 Switched form target to DailyReportBulkForm here 🌟
#     DailyReportFormSet = modelformset_factory(
#         DailyReport, 
#         form=DailyReportBulkForm, 
#         extra=1, 
#         can_delete=False
#     )

#     if request.method == 'POST':
#         formset = DailyReportFormSet(request.POST)
#         master_name = request.POST.get('master_name', '').strip()

#         if not master_name:
#             messages.error(request, "Please enter the Employee Name before submitting.")
#         elif formset.is_valid():
#             instances = formset.save(commit=False)
#             for instance in instances:
#                 instance.name = master_name
#                 instance.save()
                
#             messages.success(request, f"Successfully saved {len(instances)} daily reports!")
#             return redirect('add_daily_report_bulk')
#     else:
#         formset = DailyReportFormSet(queryset=DailyReport.objects.none())

#     return render(request, 'reports/add_multiple_reports.html', {
#         'formset': formset,
#     })

# def report_list_view(request):
#     # Fetch all records initially
#     queryset = DailyReport.objects.all()

#     # 1. # Grab the GET parameters from the URL
#     filter_date = request.GET.get('date', '').strip()
#     filter_location = request.GET.get('location', '').strip()
#     filter_name = request.GET.get('name', '').strip()

#     # 2. Apply filters dynamically if they exist
#     if filter_date:
#         queryset = queryset.filter(date=filter_date)
        
#     if filter_location:
#         queryset = queryset.filter(location=filter_location)
        
#     if filter_name:
#         queryset = queryset.filter(name__icontains=filter_name)

#     # 3. Check if the user clicked the "Download Excel" button
#     if 'export_excel' in request.GET:
#         # Create an in-memory Excel workbook
#         wb = Workbook()
#         ws = wb.active
#         ws.title = "Daily Reports"

#         # Define headers
#         headers = [
#             'Date', 'Location', 'Employee Name', 'Year', 'Volume No.', 
#             'No. of Deeds', 'No. of Pages', 'PDF Complete', 'Indexing', 'Uploading', 'Metadata'
#         ]
#         ws.append(headers)

#         # Write filtered data rows
#         for report in queryset:
#             ws.append([
#                 report.date.strftime('%Y-%m-%d') if report.date else '',
#                 report.get_location_display(),
#                 report.name,
#                 report.year,
#                 report.volume_num,
#                 report.num_of_deed,
#                 report.num_of_page,
#                 "Yes" if report.pdf_deed else "No",
#                 "Yes" if report.indexing else "No",
#                 "Yes" if report.uploading else "No",
#                 "Yes" if report.metadata else "No",
#             ])

#         # Prepare HTTP Response with correct content-type header for spreadsheet delivery
#         response = HttpResponse(
#             content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
#         )
#         response['Content-Disposition'] = f'attachment; filename=Daily_Reports_{datetime.date.today()}.xlsx'
#         wb.save(response)
#         return response

#     # Extract distinct locations for the filter dropdown options menu
#     locations = DailyReport.LOCATION_CHOICES

#     context = {
#         'reports': queryset,
#         'locations': locations,
#         'selected_date': filter_date,
#         'selected_location': filter_location,
#         'selected_name': filter_name,
#     }
#     return render(request, 'core/report_list.html', context)