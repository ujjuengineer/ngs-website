from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from .models import ContactMessage, CompanyCertificate, DailyReport, PDFRecord, IndexingRecord, UploadingRecord, QCRecord, MetadataRecord
from django.urls import reverse_lazy, reverse
from django.views.generic.edit import CreateView, UpdateView
from .forms import CertificateForm, DailyReportForm, DailyReportBulkForm, DailyReportUpdateForm
from django.contrib.messages.views import SuccessMessageMixin
from django.views.generic import DetailView
import datetime
from django.http import HttpResponse
from openpyxl import Workbook
from django.forms import modelformset_factory
from django.db.models import Sum, Q
from datetime import timedelta
from django.utils import timezone
from .utils import sync_workflow_records
import datetime

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


@login_required
def daily_report_create_view(request):
    # 1. Determine the auto-name for the logged-in user
    user = request.user
    full_name = user.get_full_name().strip()
    auto_name = full_name if full_name else user.username

    duplicate_report = None

    # 2. Handle Form Submission (POST request)
    if request.method == 'POST':
        form = DailyReportForm(request.POST)
        if form.is_valid():
            year = form.cleaned_data.get('year')
            volume_num = form.cleaned_data.get('volume_num')
            location = form.cleaned_data.get('location')

            # Check if an identical report already exists
            existing = DailyReport.objects.filter(
                year=year, volume_num=volume_num, location=location
            ).first()

            if existing:
                duplicate_report = {
                    'pk': existing.pk,
                    'year': existing.year,
                    'volume_num': existing.volume_num,
                    'location': existing.get_location_display(),
                    'name': existing.name,
                    'created_at': existing.created_at,
                }

                return render(request, 'core/add_report.html', {
                    'form': form, # Keeps their input data on screen
                    'next': request.GET.get('next', ''),
                    'auto_name': auto_name,
                    'duplicate_report': duplicate_report,
                })

            # Save the new report with the auto_name enforced
            instance = form.save(commit=False)
            instance.name = auto_name
            instance.save()

            # create the submodel
            sync_workflow_records(instance, request.user)

            # Success notification
            messages.success(
                request, 
                f"Daily report for {instance.name} at {instance.get_location_display()} recorded successfully!"
            )

            # Determine where to redirect next
            next_url = request.GET.get('next') or request.POST.get('next')
            if next_url:
                return redirect(next_url)
            return redirect(reverse('add_daily_report'))

    # 3. Handle Initial Page Load (GET request)
    else:
        # Build initial data dictionary matching your CBV's get_initial logic
        initial_data = {
            'name': auto_name,
        }
        # for field in ['year', 'volume_num', 'location']:
        #     val = request.GET.get(field)
        #     if val:
        #         initial_data[field] = val

        form = DailyReportForm(initial=initial_data)

    context = {
        'form': form,
        'next': request.GET.get('next', ''),
        'auto_name': auto_name,
    }
    return render(request, 'core/add_report.html', context)

# ── DAILY REPORT: SINGLE ADD (login required) ──
# @method_decorator(login_required, name='dispatch')
# class DailyReportCreateView(SuccessMessageMixin, CreateView):
#     model = DailyReport
#     form_class = DailyReportForm
#     template_name = 'core/add_report.html'
#     success_message = "Daily report for %(name)s at %(location)s recorded successfully!"

#     def get_success_url(self):
#         next_url = self.request.GET.get('next') or self.request.POST.get('next')
#         if next_url:
#             return next_url
#         return reverse_lazy('add_daily_report')

#     def get_initial(self):
#         initial = super().get_initial()
#         for field in ['year', 'volume_num', 'location']:
#             val = self.request.GET.get(field)
#             if val:
#                 initial[field] = val
#         # Auto-fill name from logged-in user
#         user = self.request.user
#         full_name = user.get_full_name().strip()
#         initial['name'] = full_name if full_name else user.username
#         return initial

#     def get_context_data(self, **kwargs):
#         ctx = super().get_context_data(**kwargs)
#         ctx['next'] = self.request.GET.get('next', '')
#         # Pass the auto name so template can show it as read-only
#         user = self.request.user
#         full_name = user.get_full_name().strip()
#         ctx['auto_name'] = full_name if full_name else user.username
#         return ctx

#     def form_valid(self, form):
#         # Always override name with logged-in user's name (ignore form input)
#         user = self.request.user
#         full_name = user.get_full_name().strip()
#         auto_name = full_name if full_name else user.username

#         year = form.cleaned_data.get('year')
#         volume_num = form.cleaned_data.get('volume_num')
#         location = form.cleaned_data.get('location')

#         # if existing then don't add 
#         existing = DailyReport.objects.filter(
#             year=year, volume_num=volume_num, location=location
#         ).first()

#         if existing:
#             messages.warning(
#                 self.request,
#                 f"⚠️ A report for Year '{year}', Volume '{volume_num}', "
#                 f"Location '{existing.get_location_display()}' already exists. "
#                 f"Please update the existing record instead."
#             )
#             return redirect(reverse('update_daily_report', args=[existing.pk]))

#         # Save with auto name
#         instance = form.save(commit=False)
#         instance.name = auto_name
#         instance.save()
#         # Trigger success message manually since we bypassed super().form_valid
#         messages.success(self.request, f"Daily report for {instance.name} at {instance.get_location_display()} recorded successfully!")
#         return redirect(self.get_success_url())


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
        # just like creating a form = xyzform(request.post)
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
                    # create the submodels
                    sync_workflow_records(instance, request.user)
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

@login_required
def report_list_view(request):
    is_admin = request.user.is_staff or request.user.is_superuser
    
    # Standardize user full name for filtering
    user_full_name = request.user.get_full_name().upper() if request.user.get_full_name() else request.user.username.upper()

    # 1. 🌟 FILTER BASED ON ENGAGEMENT / ROLE 🌟
    if is_admin:
        base_queryset = DailyReport.objects.all()
    else:
        base_queryset = DailyReport.objects.filter(
            Q(name__iexact=user_full_name) |
            Q(pdf_records__created_by=request.user) |
            Q(indexing_records__created_by=request.user) |
            Q(uploading_records__created_by=request.user) |
            Q(qc_records__created_by=request.user) |
            Q(metadata_records__created_by=request.user)
        ).distinct()

    # Capture URL GET Filter Parameters
    filter_date = request.GET.get('date', '').strip()
    filter_month = request.GET.get('month', '').strip()
    filter_location = request.GET.get('location', '').strip()
    filter_name = request.GET.get('name', '').strip()
    filter_stage = request.GET.get('workflow_stage', '').strip()

    # Apply Standard Filters
    queryset = base_queryset

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

    if filter_name and is_admin:
        queryset = queryset.filter(name__icontains=filter_name)

    # 2. 🌟 DYNAMIC WORKFLOW SUB-MODEL STAGE FILTER 🌟
    if filter_stage:
        if filter_stage == 'pdf':
            queryset = queryset.filter(pdf_records__isnull=False)
        elif filter_stage == 'indexing':
            queryset = queryset.filter(indexing_records__isnull=False)
        elif filter_stage == 'uploading':
            queryset = queryset.filter(uploading_records__isnull=False)
        elif filter_stage == 'qc':
            queryset = queryset.filter(qc_records__isnull=False)
        elif filter_stage == 'metadata':
            queryset = queryset.filter(metadata_records__isnull=False)

    # Calculate Global Totals for the current queryset
    totals = queryset.aggregate(
        sum_deeds=Sum('num_of_deed'),
        sum_pages=Sum('num_of_page')
    )

    # Calculate User Metrics (Personal Performance Summary)
    user_metrics = {
        # Total pages from reports explicitly created/owned by this user
        'pages_scanned_count': queryset.filter(name__iexact=user_full_name).aggregate(s=Sum('num_of_page'))['s'] or 0,
        
        # Total Deeds for reports where this user created the PDF
        'pdf_count': PDFRecord.objects.filter(created_by=request.user, daily_report__in=queryset).aggregate(s=Sum('daily_report__num_of_deed'))['s'] or 0,
        
        # Total Deeds for reports where this user did the Indexing
        'indexing_count': IndexingRecord.objects.filter(created_by=request.user, daily_report__in=queryset).aggregate(s=Sum('daily_report__num_of_deed'))['s'] or 0,
        
        # Total Deeds for reports where this user handled Uploading
        'uploading_count': UploadingRecord.objects.filter(created_by=request.user, daily_report__in=queryset).aggregate(s=Sum('daily_report__num_of_deed'))['s'] or 0,
        
        # Total Deeds for reports where this user did the Quality Check (QC)
        'qc_count': QCRecord.objects.filter(created_by=request.user, daily_report__in=queryset).aggregate(s=Sum('daily_report__num_of_deed'))['s'] or 0,
        
        # Total Pages for reports where this user entered the Metadata
        'metadata_count': MetadataRecord.objects.filter(created_by=request.user, daily_report__in=queryset).aggregate(s=Sum('daily_report__num_of_page'))['s'] or 0,
    }

    # 3. Excel Export Engine
    if 'export_excel' in request.GET:
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        from openpyxl.utils import get_column_letter

        wb = Workbook()
        ws = wb.active
        ws.title = "Filtered Reports"
        
        header_font = Font(name='Calibri', size=11, bold=True, color='FFFFFF')
        header_fill = PatternFill(start_color='1F2935', end_color='1F2935', fill_type='solid')
        data_font = Font(name='Calibri', size=11, bold=False)
        
        summary_label_font = Font(name='Calibri', size=11, bold=True, color='1F2935')
        summary_val_font = Font(name='Calibri', size=11, bold=True, color='000000')
        summary_fill = PatternFill(start_color='F8F9FA', end_color='F8F9FA', fill_type='solid')
        
        center_align = Alignment(horizontal='center', vertical='center')
        left_align = Alignment(horizontal='left', vertical='center')
        right_align = Alignment(horizontal='right', vertical='center')
        
        thin_side = Side(border_style="thin", color="D3D3D3")
        thick_bottom_side = Side(border_style="medium", color="1F2935")
        thin_border = Border(left=thin_side, right=thin_side, top=thin_side, bottom=thin_side)

        headers = ['Date', 'Location', 'Employee Name', 'Year', 'Volume No.',
                   'No. Deeds', 'No. Pages', 'PDF', 'Indexing', 'Uploading', 'QC', 'Metadata']
        ws.append(headers)
        
        ws.row_dimensions[1].height = 24
        for cell in ws[1]:
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = center_align
            cell.border = thin_border

        for report in queryset:
            row_data = [
                report.date.strftime('%d/%m/%Y') if report.date else '',
                report.get_location_display(), 
                report.name, 
                report.year, 
                report.volume_num,
                report.num_of_deed, 
                report.num_of_page,
                "Yes" if report.pdf_deed else "No",
                "Yes" if report.indexing else "No",
                "Yes" if report.uploading else "No",
                "Yes" if report.QC else "No",
                "Yes" if report.metadata else "No",
            ]
            ws.append(row_data)
            
            current_row = ws.max_row
            ws.row_dimensions[current_row].height = 20
            for col_idx, cell in enumerate(ws[current_row], start=1):
                cell.font = data_font
                cell.border = thin_border
                if col_idx in [1, 4, 5, 6, 7, 8, 9, 10, 11, 12]:
                    cell.alignment = center_align
                else:
                    cell.alignment = left_align

        ws.append([]) # Spacer

        # Combined Dataset Summary + Personalized User Summary Metrics
        summary_rows = [
            ("Total Number of volume", len(queryset)),  
            ("Total Deeds", totals['sum_deeds'] or 0),  
            ("Total Pages", totals['sum_pages'] or 0),
            ("Total Pages Scanned (By You)", user_metrics['pages_scanned_count']),
            ("Total PDF Created (By You)", user_metrics['pdf_count']),
            ("Total Indexing (By You)", user_metrics['indexing_count']),
            ("Total Uploading (By You)", user_metrics['uploading_count']),
            ("Total QC (By You)", user_metrics['qc_count']),
            ("Total Metadata (By You)", user_metrics['metadata_count']),
        ]

        for label, val in summary_rows:
            ws.append(["", "", "", "", label, val])
            s_row = ws.max_row
            ws.row_dimensions[s_row].height = 22
            
            lbl_cell = ws.cell(row=s_row, column=5)
            lbl_cell.font = summary_label_font
            lbl_cell.alignment = right_align
            lbl_cell.fill = summary_fill
            lbl_cell.border = Border(left=thin_side, top=thin_side, bottom=thin_side)
            
            val_cell = ws.cell(row=s_row, column=6)
            val_cell.font = summary_val_font
            val_cell.alignment = center_align
            val_cell.fill = summary_fill
            val_cell.border = Border(right=thin_side, top=thin_side, bottom=thin_side)
            
            # Apply terminal thick bottom line to the last summary item
            if label == "Total Metadata (By You)":
                lbl_cell.border = Border(left=thin_side, top=thin_side, bottom=thick_bottom_side)
                val_cell.border = Border(right=thin_side, top=thin_side, bottom=thick_bottom_side)

        for col in ws.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col:
                if cell.value:
                    max_len = max(max_len, len(str(cell.value)))
            ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename=Reports_Export_{datetime.date.today()}.xlsx'
        wb.save(response)
        return response

    # 4. Context Preparation
    existing_dates = DailyReport.objects.dates('date', 'month', order='DESC')
    available_months = [
        {'value': d.strftime('%Y-%m'), 'display': d.strftime('%B %Y')}
        for d in existing_dates
    ]

    workflow_stages = [
        {'value': 'pdf', 'display': 'PDF Report'},
        {'value': 'indexing', 'display': 'Indexing Report'},
        {'value': 'uploading', 'display': 'Uploading Report'},
        {'value': 'qc', 'display': 'QC Report'},
        {'value': 'metadata', 'display': 'Metadata Report'},
    ]

    context = {
        'reports': queryset,
        'total_deeds': totals['sum_deeds'],
        'total_pages': totals['sum_pages'],
        'user_metrics': user_metrics,
        'locations': DailyReport.LOCATION_CHOICES,
        'available_months': available_months,
        'workflow_stages': workflow_stages,       
        'selected_date': filter_date,
        'selected_month': filter_month,
        'selected_location': filter_location,
        'selected_name': filter_name,
        'selected_stage': filter_stage,           
        'is_admin': is_admin,
    }
    return render(request, 'core/report_list.html', context)

# @login_required
# def report_list_view(request):
#     is_admin = request.user.is_staff or request.user.is_superuser
    
#     # 1. 🌟 FILTER BASED ON ENGAGEMENT / ROLE 🌟
#     # Admins see everything. Regular users see records they created OR sub-stages they completed.
#     if is_admin:
#         base_queryset = DailyReport.objects.all()
#     else:
#         user_full_name = request.user.get_full_name().upper() if request.user.get_full_name() else request.user.username.upper()
#         base_queryset = DailyReport.objects.filter(
#             Q(name__iexact=user_full_name) |
#             Q(pdf_records__created_by=request.user) |
#             Q(indexing_records__created_by=request.user) |
#             Q(uploading_records__created_by=request.user) |
#             Q(qc_records__created_by=request.user) |
#             Q(metadata_records__created_by=request.user)
#         ).distinct()

#     # Capture URL GET Filter Parameters
#     filter_date = request.GET.get('date', '').strip()
#     filter_month = request.GET.get('month', '').strip()
#     filter_location = request.GET.get('location', '').strip()
#     filter_name = request.GET.get('name', '').strip()
#     filter_stage = request.GET.get('workflow_stage', '').strip() # 🌟 New Dropdown Parameter

#     # Apply Standard Filters
#     queryset = base_queryset

#     if filter_date:
#         queryset = queryset.filter(date=filter_date)

#     if filter_month:
#         try:
#             year_part, month_part = map(int, filter_month.split('-'))
#             queryset = queryset.filter(date__year=year_part, date__month=month_part)
#         except ValueError:
#             pass

#     if filter_location:
#         queryset = queryset.filter(location=filter_location)

#     if filter_name and is_admin:
#         queryset = queryset.filter(name__icontains=filter_name)

#     # 2. 🌟 DYNAMIC WORKFLOW SUB-MODEL STAGE FILTER 🌟
#     if filter_stage:
#         if filter_stage == 'pdf':
#             queryset = queryset.filter(pdf_records__isnull=False)
#         elif filter_stage == 'indexing':
#             queryset = queryset.filter(indexing_records__isnull=False)
#         elif filter_stage == 'uploading':
#             queryset = queryset.filter(uploading_records__isnull=False)
#         elif filter_stage == 'qc':
#             queryset = queryset.filter(qc_records__isnull=False)
#         elif filter_stage == 'metadata':
#             queryset = queryset.filter(metadata_records__isnull=False)

#     # Calculate Totals
#     totals = queryset.aggregate(
#         sum_deeds=Sum('num_of_deed'),
#         sum_pages=Sum('num_of_page')
#     )

#     user_metrics = {

#         # Total pages from reports explicitly created/owned by this user
#         'pages_scanned_count': queryset.filter(name__iexact=user_full_name).aggregate(s=Sum('num_of_page'))['s'] or 0,

#         # Total Deeds for reports where this user created the PDF
#         'pdf_count': PDFRecord.objects.filter(created_by=request.user, daily_report__in=queryset).aggregate(s=Sum('daily_report__num_of_deed'))['s'] or 0,
        
#         # Total Deeds for reports where this user did the Indexing
#         'indexing_count': IndexingRecord.objects.filter(created_by=request.user, daily_report__in=queryset).aggregate(s=Sum('daily_report__num_of_deed'))['s'] or 0,
        
#         # Total Deeds for reports where this user handled Uploading
#         'uploading_count': UploadingRecord.objects.filter(created_by=request.user, daily_report__in=queryset).aggregate(s=Sum('daily_report__num_of_deed'))['s'] or 0,
        
#         # Total Deeds for reports where this user did the Quality Check (QC)
#         'qc_count': QCRecord.objects.filter(created_by=request.user, daily_report__in=queryset).aggregate(s=Sum('daily_report__num_of_deed'))['s'] or 0,
        
#         # Total Pages for reports where this user entered the Metadata
#         'metadata_count': MetadataRecord.objects.filter(created_by=request.user, daily_report__in=queryset).aggregate(s=Sum('daily_report__num_of_page'))['s'] or 0,
#     }

#     # 3. Excel Export Engine
#     if 'export_excel' in request.GET:
#         from openpyxl import Workbook
#         from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
#         from openpyxl.utils import get_column_letter

#         wb = Workbook()
#         ws = wb.active
#         ws.title = "Filtered Reports"
        
#         header_font = Font(name='Calibri', size=11, bold=True, color='FFFFFF')
#         header_fill = PatternFill(start_color='1F2935', end_color='1F2935', fill_type='solid')
#         data_font = Font(name='Calibri', size=11, bold=False)
        
#         summary_label_font = Font(name='Calibri', size=11, bold=True, color='1F2935')
#         summary_val_font = Font(name='Calibri', size=11, bold=True, color='000000')
#         summary_fill = PatternFill(start_color='F8F9FA', end_color='F8F9FA', fill_type='solid')
        
#         center_align = Alignment(horizontal='center', vertical='center')
#         left_align = Alignment(horizontal='left', vertical='center')
#         right_align = Alignment(horizontal='right', vertical='center')
        
#         thin_side = Side(border_style="thin", color="D3D3D3")
#         thick_bottom_side = Side(border_style="medium", color="1F2935")
#         thin_border = Border(left=thin_side, right=thin_side, top=thin_side, bottom=thin_side)

#         headers = ['Date', 'Location', 'Employee Name', 'Year', 'Volume No.',
#                    'No. Deeds', 'No. Pages', 'PDF', 'Indexing', 'Uploading', 'QC', 'Metadata']
#         ws.append(headers)
        
#         ws.row_dimensions[1].height = 24
#         for cell in ws[1]:
#             cell.font = header_font
#             cell.fill = header_fill
#             cell.alignment = center_align
#             cell.border = thin_border

#         for report in queryset:
#             row_data = [
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
#                 "Yes" if report.QC else "No",
#                 "Yes" if report.metadata else "No",
#             ]
#             ws.append(row_data)
            
#             current_row = ws.max_row
#             ws.row_dimensions[current_row].height = 20
#             for col_idx, cell in enumerate(ws[current_row], start=1):
#                 cell.font = data_font
#                 cell.border = thin_border
#                 if col_idx in [1, 4, 5, 6, 7, 8, 9, 10, 11, 12]:
#                     cell.alignment = center_align
#                 else:
#                     cell.alignment = left_align

#         ws.append([]) # Spacer

#         # Combined Dataset Summary + Personalized User Summary Metrics
#         summary_rows = [
#             ("Total Number of volume", len(queryset)),  
#             ("Total Deeds", totals['sum_deeds'] or 0),  
#             ("Total Pages", totals['sum_pages'] or 0),
#             ("Total Pages Scanned (By You)", user_metrics['pages_scanned_count']),
#             ("Total PDF Created (By You)", user_metrics['pdf_count']),
#             ("Total Indexing (By You)", user_metrics['indexing_count']),
#             ("Total Uploading (By You)", user_metrics['uploading_count']),
#             ("Total QC (By You)", user_metrics['qc_count']),
#             ("Total Metadata (By You)", user_metrics['metadata_count']),
#         ]

#         for label, val in summary_rows:
#             ws.append(["", "", "", "", label, val])
#             s_row = ws.max_row
#             ws.row_dimensions[s_row].height = 22
            
#             lbl_cell = ws.cell(row=s_row, column=5)
#             lbl_cell.font = summary_label_font
#             lbl_cell.alignment = right_align
#             lbl_cell.fill = summary_fill
#             lbl_cell.border = Border(left=thin_side, top=thin_side, bottom=thin_side)
            
#             val_cell = ws.cell(row=s_row, column=6)
#             val_cell.font = summary_val_font
#             val_cell.alignment = center_align
#             val_cell.fill = summary_fill
#             val_cell.border = Border(right=thin_side, top=thin_side, bottom=thin_side)
            
#             if label == "Total Pages":
#                 lbl_cell.border = Border(left=thin_side, top=thin_side, bottom=thick_bottom_side)
#                 val_cell.border = Border(right=thin_side, top=thin_side, bottom=thick_bottom_side)

#         for col in ws.columns:
#             max_len = 0
#             col_letter = get_column_letter(col[0].column)
#             for cell in col:
#                 if cell.value:
#                     max_len = max(max_len, len(str(cell.value)))
#             ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

#         response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
#         response['Content-Disposition'] = f'attachment; filename=Reports_Export_{datetime.date.today()}.xlsx'
#         wb.save(response)
#         return response

#     # 4. Context Preparation
#     existing_dates = DailyReport.objects.dates('date', 'month', order='DESC')
#     available_months = [
#         {'value': d.strftime('%Y-%m'), 'display': d.strftime('%B %Y')}
#         for d in existing_dates
#     ]

#     # Explicit Workflow Options for the frontend template HTML dropdown
#     workflow_stages = [
#         {'value': 'pdf', 'display': 'PDF Report'},
#         {'value': 'indexing', 'display': 'Indexing Report'},
#         {'value': 'uploading', 'display': 'Uploading Report'},
#         {'value': 'qc', 'display': 'QC Report'},
#         {'value': 'metadata', 'display': 'Metadata Report'},
#     ]

#     context = {
#         'reports': queryset,
#         'total_deeds': totals['sum_deeds'],
#         'total_pages': totals['sum_pages'],
#         'user_metrics': user_metrics,
#         'locations': DailyReport.LOCATION_CHOICES,
#         'available_months': available_months,
#         'workflow_stages': workflow_stages,       # 🌟 Sent to template
#         'selected_date': filter_date,
#         'selected_month': filter_month,
#         'selected_location': filter_location,
#         'selected_name': filter_name,
#         'selected_stage': filter_stage,           # 🌟 Preserves active choice
#         'is_admin': is_admin,
#     }
#     return render(request, 'core/report_list.html', context)


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

@login_required
def daily_report_update_view(request, pk):
    # 1. Fetch the existing report instance
    report = get_object_or_404(DailyReport, pk=pk)
    user = request.user

    # data for submodels
    full_name = user.get_full_name().strip()
    current_updater_name = full_name if full_name else user.username
    
    # Define our fields
    BOOLEAN_FIELDS = ['pdf_deed', 'indexing', 'uploading', 'QC', 'metadata']
    PROTECTED_FIELDS = ['date', 'location', 'name', 'year', 'volume_num', 'num_of_deed', 'num_of_page']
    
    # Check if the record is older than 24 hours
    is_expired = timezone.now() > report.created_at + timedelta(hours=24)

    # 1. Initialize the form based on request method
    if request.method == 'POST':
        form = DailyReportUpdateForm(request.POST, instance=report)
    else:
        form = DailyReportUpdateForm(instance=report)

    # 2. 🌟 APPLY DISABLING LOGIC HERE (Runs for BOTH GET and POST) 🌟
    if is_expired and not user.is_superuser:
        for field_name, field in form.fields.items():
            if field_name not in BOOLEAN_FIELDS:
                field.disabled = True

    # 2. Handle Form Submission (POST)
    if request.method == 'POST':
        
        if form.is_valid():
            # Enforce 24-hour rule protection on post-back for non-superusers
            if is_expired and not user.is_superuser:
                original = DailyReport.objects.get(pk=report.pk)
                for field in PROTECTED_FIELDS:
                    setattr(form.instance, field, getattr(original, field)) # checkout this one
            
            updated_report = form.save()

            # create the submodels
            sync_workflow_records(updated_report, request.user)


            messages.success(request, "Report updated successfully!")
            
            # Read the hidden tracking URL sent by the form
            back_to_url = request.POST.get('back_to_url')
            if back_to_url:
                return redirect(back_to_url)
                
            # Default fallback url matching your old get_success_url
            return redirect(
                reverse('update_report_search') + 
                f"?year={report.year}&volume_num={report.volume_num}&location={report.location}"
            )
        
        # Apply field disabling logic if older than 24 hours (and not an admin)
        if is_expired and not user.is_superuser:
            for field_name, field in form.fields.items():
                if field_name not in BOOLEAN_FIELDS:
                    field.disabled = True

    # 4. Handle referer url tracking context
    if request.method == 'GET':
        back_to_url = request.META.get('HTTP_REFERER', '')
    else:
        back_to_url = request.POST.get('back_to_url', '')

    context = {
        'form': form,
        'report': report,
        'back_to_url': back_to_url,
    }
    
    return render(request, 'core/update_report.html', context)