from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from .models import ContactMessage, CompanyCertificate, DailyReport
from django.urls import reverse_lazy, reverse
from django.views.generic.edit import CreateView, UpdateView
from .forms import CertificateForm, DailyReportForm, DailyReportBulkForm, DailyReportUpdateForm
from django.contrib.messages.views import SuccessMessageMixin
from django.views.generic import DetailView
import datetime
from django.http import HttpResponse
from openpyxl import Workbook
from django.forms import modelformset_factory


# ── HOME ──
def home(request):
    return render(request, 'core/home.html')


# ── CONTACT ──
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


# ── AUTH: LOGIN ──
def login_view(request):
    # Already logged in → go home
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            # Redirect to the page they were trying to access, or home
            next_url = request.GET.get('next', '/')
            return redirect(next_url)
        else:
            messages.error(request, 'Invalid username or password. Please try again.')

    return render(request, 'core/login.html')


# ── AUTH: LOGOUT ──
@login_required
def logout_view(request):
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('home')


# ── CERTIFICATES ──
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


# ── DAILY REPORT: SINGLE ADD (login required) ──
@method_decorator(login_required, name='dispatch')
class DailyReportCreateView(SuccessMessageMixin, CreateView):
    model = DailyReport
    form_class = DailyReportForm
    template_name = 'core/add_report.html'
    success_message = "Daily report for %(name)s at %(location)s recorded successfully!"

    def get_success_url(self):
        next_url = self.request.GET.get('next') or self.request.POST.get('next')
        if next_url:
            return next_url
        return reverse_lazy('add_daily_report')

    def get_initial(self):
        initial = super().get_initial()
        for field in ['year', 'volume_num', 'location']:
            val = self.request.GET.get(field)
            if val:
                initial[field] = val
        # Auto-fill name from logged-in user
        user = self.request.user
        full_name = user.get_full_name().strip()
        initial['name'] = full_name if full_name else user.username
        return initial

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['next'] = self.request.GET.get('next', '')
        # Pass the auto name so template can show it as read-only
        user = self.request.user
        full_name = user.get_full_name().strip()
        ctx['auto_name'] = full_name if full_name else user.username
        return ctx

    def form_valid(self, form):
        # Always override name with logged-in user's name (ignore form input)
        user = self.request.user
        full_name = user.get_full_name().strip()
        auto_name = full_name if full_name else user.username

        year = form.cleaned_data.get('year')
        volume_num = form.cleaned_data.get('volume_num')
        location = form.cleaned_data.get('location')

        # if existing then don't add 
        existing = DailyReport.objects.filter(
            year=year, volume_num=volume_num, location=location
        ).first()

        if existing:
            messages.warning(
                self.request,
                f"⚠️ A report for Year '{year}', Volume '{volume_num}', "
                f"Location '{existing.get_location_display()}' already exists. "
                f"Please update the existing record instead."
            )
            return redirect(reverse('update_daily_report', args=[existing.pk]))

        # Save with auto name
        instance = form.save(commit=False)
        instance.name = auto_name
        instance.save()
        # Trigger success message manually since we bypassed super().form_valid
        messages.success(self.request, f"Daily report for {instance.name} at {instance.get_location_display()} recorded successfully!")
        return redirect(self.get_success_url())


# ── DAILY REPORT: BULK ADD (login required) ──
@login_required
def add_multiple_reports_view(request):
    DailyReportFormSet = modelformset_factory(
        DailyReport,
        form=DailyReportBulkForm,
        extra=1,
        can_delete=False
    )

    # Auto-get name from logged-in user
    user = request.user
    full_name = user.get_full_name().strip()
    auto_name = full_name if full_name else user.username

    duplicate_reports = []

    if request.method == 'POST':
        formset = DailyReportFormSet(request.POST)

        if formset.is_valid():
            instances = formset.save(commit=False)
            saved_count = 0
            duplicate_reports = []

            for instance in instances:
                # Always use logged-in user's name
                instance.name = auto_name
                existing = DailyReport.objects.filter(
                    year=instance.year,
                    volume_num=instance.volume_num,
                    location=instance.location
                ).first()

                if existing:
                    duplicate_reports.append({
                        'pk': existing.pk,
                        'year': existing.year,
                        'volume_num': existing.volume_num,
                        'location': existing.get_location_display(),
                        'name': existing.name,
                        'date': existing.date,
                    })
                else:
                    instance.save()
                    saved_count += 1

            if saved_count:
                messages.success(request, f"Successfully saved {saved_count} daily report(s) for {auto_name}.")

            if duplicate_reports:
                formset = DailyReportFormSet(queryset=DailyReport.objects.none())
                return render(request, 'core/add_multiple_reports.html', {
                    'formset': formset,
                    'duplicate_reports': duplicate_reports,
                    'auto_name': auto_name,
                })

            if saved_count:
                return redirect('add_daily_report_bulk')

    else:
        formset = DailyReportFormSet(queryset=DailyReport.objects.none())

    return render(request, 'core/add_multiple_reports.html', {
        'formset': formset,
        'duplicate_reports': duplicate_reports,
        'auto_name': auto_name,
    })


# ── REPORT LIST (login required — users see only their own reports) ──
@login_required
def report_list_view(request):
    # Superusers/staff see all reports; regular users see only their own
    if request.user.is_staff or request.user.is_superuser:
        queryset = DailyReport.objects.all()
    else:
        queryset = DailyReport.objects.filter(name=request.user.get_full_name().upper() or request.user.username.upper())

    filter_date = request.GET.get('date', '').strip()
    filter_month = request.GET.get('month', '').strip()
    filter_location = request.GET.get('location', '').strip()
    filter_name = request.GET.get('name', '').strip()

    if filter_date:
        queryset = queryset.filter(date=filter_date)

    if filter_month:
        try:
            year_part, month_part = map(int, filter_month.split('-'))
            queryset = queryset.filter(date__year=year_part, date__month=month_part)
        except ValueError:
            pass

    if filter_location:
        queryset = queryset.filter(location=filter_location)

    if filter_name and (request.user.is_staff or request.user.is_superuser):
        queryset = queryset.filter(name__icontains=filter_name)

    if 'export_excel' in request.GET:
        wb = Workbook()
        ws = wb.active
        ws.title = "Filtered Reports"
        headers = ['Date', 'Location', 'Employee Name', 'Year', 'Volume No.',
                   'No. Deeds', 'No. Pages', 'PDF', 'Indexing', 'Uploading', 'QC', 'Metadata']
        ws.append(headers)
        for report in queryset:
            ws.append([
                report.date.strftime('%Y-%m-%d') if report.date else '',
                report.get_location_display(), report.name, report.year, report.volume_num,
                report.num_of_deed, report.num_of_page,
                "Yes" if report.pdf_deed else "No",
                "Yes" if report.indexing else "No",
                "Yes" if report.uploading else "No",
                "Yes" if report.QC else "No",
                "Yes" if report.metadata else "No",
            ])
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename=Reports_Export_{datetime.date.today()}.xlsx'
        wb.save(response)
        return response

    existing_dates = DailyReport.objects.dates('date', 'month', order='DESC')
    available_months = [
        {'value': d.strftime('%Y-%m'), 'display': d.strftime('%B %Y')}
        for d in existing_dates
    ]

    context = {
        'reports': queryset,
        'locations': DailyReport.LOCATION_CHOICES,
        'available_months': available_months,
        'selected_date': filter_date,
        'selected_month': filter_month,
        'selected_location': filter_location,
        'selected_name': filter_name,
        'is_admin': request.user.is_staff or request.user.is_superuser,
    }
    return render(request, 'core/report_list.html', context)


# ── UPDATE REPORT SEARCH (login required) ──
@login_required
def update_report_search_view(request):
    report = None
    not_found = False
    searched = False

    year = request.GET.get('year', '').strip()
    volume_num = request.GET.get('volume_num', '').strip()
    location = request.GET.get('location', '').strip()

    if year and volume_num and location:
        searched = True
        try:
            report = DailyReport.objects.get(
                year=year, volume_num=volume_num, location=location
            )
        except DailyReport.DoesNotExist:
            not_found = True
        except DailyReport.MultipleObjectsReturned:
            report = DailyReport.objects.filter(
                year=year, volume_num=volume_num, location=location
            ).order_by('-date').first()

    context = {
        'report': report,
        'not_found': not_found,
        'searched': searched,
        'year': year,
        'volume_num': volume_num,
        'location': location,
        'locations': DailyReport.LOCATION_CHOICES,
    }
    return render(request, 'core/update_report_search.html', context)


# ── UPDATE REPORT FORM (login required) ──
@method_decorator(login_required, name='dispatch')
class DailyReportUpdateView(SuccessMessageMixin, UpdateView):
    model = DailyReport
    form_class = DailyReportUpdateForm  # Switch to new update form
    template_name = 'core/update_report.html'
    success_message = "Report updated successfully!"

    def get_success_url(self):
        report = self.object
        return reverse('update_report_search') + \
            f"?year={report.year}&volume_num={report.volume_num}&location={report.location}"