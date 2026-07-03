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
from datetime import date, timedelta
from django.utils import timezone
from .utils import sync_workflow_records
import datetime
from itertools import chain


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

import datetime
from itertools import chain
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Q
from django.http import HttpResponse
from django.shortcuts import render
from .models import DailyReport, PDFRecord, IndexingRecord, UploadingRecord, QCRecord, MetadataRecord

@login_required
def report_list_view(request):
    # Setup the base user role check right away
    is_admin = request.user.is_staff or request.user.is_superuser

    # Standardize user full name for filtering personal metrics
    user_full_name = request.user.get_full_name().upper() if request.user.get_full_name() else request.user.username.upper()

    # 🌟 LEVEL ACCESS GATEWAY 🌟
    if is_admin:
        # Admins pull comprehensive datasets across the entire workforce
        pdf_data = PDFRecord.objects.all()
        ind_data = IndexingRecord.objects.all()
        upload_data = UploadingRecord.objects.all()
        qc_data = QCRecord.objects.all()
        metadata_data = MetadataRecord.objects.all()
        
        # Admins see all logs out-of-the-box
        scanning_report = DailyReport.objects.all()
    else:
        # Regular employees are strictly limited to their own record contributions
        pdf_data = PDFRecord.objects.filter(created_by=request.user)
        ind_data = IndexingRecord.objects.filter(created_by=request.user)
        upload_data = UploadingRecord.objects.filter(created_by=request.user)
        qc_data = QCRecord.objects.filter(created_by=request.user)
        metadata_data = MetadataRecord.objects.filter(created_by=request.user)
        
        # Scanners only see their own names mapped on DailyReports
        scanning_report = DailyReport.objects.none()
        if request.user.username.endswith('-S'):
            scanning_report = DailyReport.objects.filter(name=user_full_name)

    # Collect unique DailyReport IDs from all active records 
    daily_report_ids = set(chain(
        pdf_data.values_list('daily_report_id', flat=True),
        ind_data.values_list('daily_report_id', flat=True),
        upload_data.values_list('daily_report_id', flat=True),
        qc_data.values_list('daily_report_id', flat=True),
        metadata_data.values_list('daily_report_id', flat=True),
    ))

    # Fetch corresponding DailyReport objects matching the sub-model IDs
    daily_reports = DailyReport.objects.filter(id__in=daily_report_ids)

    # NOTE : all the above data can be simply be created by 1 single query
    # daily_reports = DailyReport.objects.filter(
    #     Q(pdf_records__created_by=request.user) |
    #     Q(indexing_records__created_by=request.user) |
    #     Q(uploading_records__created_by=request.user) |
    #     Q(qc_records__created_by=request.user) |
    #     Q(metadata_records__created_by=request.user)
    # ).distinct()

    # Combine the datasets into a single unified workspace query
    final_report = (daily_reports | scanning_report).distinct()
    # print(final_report)
    # print(daily_reports)
    # print(final_report)

    # Capture URL GET Filter Parameters
    filter_date = request.GET.get('date', '').strip()
    filter_month = request.GET.get('month', '').strip()
    filter_location = request.GET.get('location', '').strip()
    filter_name = request.GET.get('name', '').strip()
    filter_stage = request.GET.get('workflow_stage', '').strip()


    # Apply Standard Date Filter
    if filter_date:
        pdf_data = pdf_data.filter(created_at__date=filter_date)
        ind_data = ind_data.filter(created_at__date=filter_date)
        upload_data = upload_data.filter(created_at__date=filter_date)
        qc_data = qc_data.filter(created_at__date=filter_date) 
        metadata_data = metadata_data.filter(created_at__date=filter_date)

        # For admins, this filters all global daily reports by that date. For regular scanners, it filters just theirs.
        scanning_report = scanning_report.filter(date=filter_date) 
        

        daily_report_ids = set(chain(
            pdf_data.values_list('daily_report_id', flat=True),
            ind_data.values_list('daily_report_id', flat=True),
            upload_data.values_list('daily_report_id', flat=True),
            qc_data.values_list('daily_report_id', flat=True),
            metadata_data.values_list('daily_report_id', flat=True),
        ))

        daily_reports = DailyReport.objects.filter(id__in=daily_report_ids)
        final_report = (daily_reports | scanning_report).distinct()

    # Apply Standard Month Filter
    if filter_month:
        try:
            year_part, month_part = map(int, filter_month.split('-'))
            
            pdf_data = pdf_data.filter(created_at__year=year_part, created_at__month=month_part)
            ind_data = ind_data.filter(created_at__year=year_part, created_at__month=month_part)
            upload_data = upload_data.filter(created_at__year=year_part, created_at__month=month_part)
            qc_data = qc_data.filter(created_at__year=year_part, created_at__month=month_part)
            metadata_data = metadata_data.filter(created_at__year=year_part, created_at__month=month_part)

            scanning_report = scanning_report.filter(date__year=year_part, date__month=month_part)

            daily_report_ids = set(chain(
                pdf_data.values_list('daily_report_id', flat=True),
                ind_data.values_list('daily_report_id', flat=True),
                upload_data.values_list('daily_report_id', flat=True),
                qc_data.values_list('daily_report_id', flat=True),
                metadata_data.values_list('daily_report_id', flat=True),
            ))

            daily_reports = DailyReport.objects.filter(id__in=daily_report_ids)
            final_report = (daily_reports | scanning_report).distinct()

        except ValueError:
            pass

    if filter_location:
        final_report = final_report.filter(location=filter_location)

    # Naming query filtering is now accessible globally across the expanded workspace for admins
    if filter_name and is_admin:
        name_q = (
            Q(name__icontains=filter_name) |
            Q(pdf_records__created_by__username__icontains=filter_name) |
            Q(pdf_records__created_by__first_name__icontains=filter_name) |
            Q(pdf_records__created_by__last_name__icontains=filter_name) |
            Q(indexing_records__created_by__username__icontains=filter_name) |
            Q(indexing_records__created_by__first_name__icontains=filter_name) |
            Q(indexing_records__created_by__last_name__icontains=filter_name) |
            Q(uploading_records__created_by__username__icontains=filter_name) |
            Q(uploading_records__created_by__first_name__icontains=filter_name) |
            Q(uploading_records__created_by__last_name__icontains=filter_name) |
            Q(qc_records__created_by__username__icontains=filter_name) |
            Q(qc_records__created_by__first_name__icontains=filter_name) |
            Q(qc_records__created_by__last_name__icontains=filter_name) |
            Q(metadata_records__created_by__username__icontains=filter_name) |
            Q(metadata_records__created_by__first_name__icontains=filter_name) |
            Q(metadata_records__created_by__last_name__icontains=filter_name)
        )
        final_report = final_report.filter(name_q).distinct()

    # Workflow Sub-Model Stage Filtering
    # ==========================================
    # Refactored Workflow Sub-Model Stage Filtering
    # ==========================================
    if filter_stage:
        if filter_stage == 'pdf':
            if is_admin:
                # Admins see any daily report that has a PDF entry
                final_report = final_report.filter(pdf_records__isnull=False)
            else:
                # Regular users only see reports where THEY created the PDF entry
                final_report = final_report.filter(pdf_records__created_by=request.user)
                
        elif filter_stage == 'indexing':
            if is_admin:
                final_report = final_report.filter(indexing_records__isnull=False)
            else:
                final_report = final_report.filter(indexing_records__created_by=request.user)
                
        elif filter_stage == 'uploading':
            if is_admin:
                final_report = final_report.filter(uploading_records__isnull=False)
            else:
                final_report = final_report.filter(uploading_records__created_by=request.user)
                
        elif filter_stage == 'qc':
            if is_admin:
                final_report = final_report.filter(qc_records__isnull=False)
            else:
                final_report = final_report.filter(qc_records__created_by=request.user)
                
        elif filter_stage == 'metadata':
            if is_admin:
                final_report = final_report.filter(metadata_records__isnull=False)
            else:
                final_report = final_report.filter(metadata_records__created_by=request.user)

    # Note: Because Django chains filters using "AND" logic, any other active 
    # query parameters (date, location, name) will cleanly pile on top of this.

    # Calculate Global Totals for the current workspace (Consolidated Metrics)
    totals = final_report.aggregate(
        sum_deeds=Sum('num_of_deed'),
        sum_pages=Sum('num_of_page'),
        sum_pdf=Sum('num_of_deed', filter=Q(pdf_deed=True)),
        sum_indexing=Sum('num_of_deed', filter=Q(indexing=True)),
        sum_uploading=Sum('num_of_deed', filter=Q(uploading=True)),
        sum_qc=Sum('num_of_deed', filter=Q(QC=True)),
        sum_metadata=Sum('num_of_page', filter=Q(metadata=True))
    )

    # Calculate User Metrics (Personal Performance Summary)
    # Calculate User Metrics (Personal Performance Summary)
    user_metrics = {
        # 1. Pages Scanned (Only tracks if user is a scanner account ending with -S)
        'pages_scanned_count': (
            final_report.filter(name__iexact=user_full_name).aggregate(s=Sum('num_of_page'))['s'] or 0
        ) if request.user.username.endswith('-S') else 0,
        
        # 2. PDF Created (Sum of deeds from daily reports where this user created the PDF work entry)
        'pdf_count': PDFRecord.objects.filter(
            created_by=request.user, 
            daily_report__in=final_report,
            daily_report__pdf_deed=True  # Confirms the PDF checkbox status is active
        ).aggregate(s=Sum('daily_report__num_of_deed'))['s'] or 0,
        
        # 3. Indexing Done (Sum of deeds from daily reports indexed by this user)
        'indexing_count': IndexingRecord.objects.filter(
            created_by=request.user, 
            daily_report__in=final_report,
            daily_report__indexing=True  # Confirms the Indexing checkbox status is active
        ).aggregate(s=Sum('daily_report__num_of_deed'))['s'] or 0,
        
        # 4. Uploading Done (Sum of deeds from daily reports uploaded by this user)
        'uploading_count': UploadingRecord.objects.filter(
            created_by=request.user, 
            daily_report__in=final_report,
            daily_report__uploading=True  # Confirms the Uploading checkbox status is active
        ).aggregate(s=Sum('daily_report__num_of_deed'))['s'] or 0,
        
        # 5. QC Verified (Sum of deeds from daily reports QC verified by this user)
        'qc_count': QCRecord.objects.filter(
            created_by=request.user, 
            daily_report__in=final_report,
            daily_report__QC=True          # Confirms the QC checkbox status is active
        ).aggregate(s=Sum('daily_report__num_of_deed'))['s'] or 0,
        
        # 6. Metadata Saved (Sum of pages from daily reports metadata processed by this user)
        'metadata_count': MetadataRecord.objects.filter(
            created_by=request.user, 
            daily_report__in=final_report,
            daily_report__metadata=True    # Confirms the Metadata checkbox status is active
        ).aggregate(s=Sum('daily_report__num_of_page'))['s'] or 0,
    }

    # Excel Export Engine
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

        for report in final_report:
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

        # Setup custom output mapping inside Excel according to user authorization levels
        if is_admin:
            summary_rows = [
                ("Total Number of volume", len(final_report)),  
                ("Total Deeds", totals['sum_deeds'] or 0),  
                ("Total Pages", totals['sum_pages'] or 0),
                ("Total PDF Created (Global)", totals['sum_pdf'] or 0),
                ("Total Indexing (Global)", totals['sum_indexing'] or 0),
                ("Total Uploading (Global)", totals['sum_uploading'] or 0),
                ("Total QC (Global)", totals['sum_qc'] or 0),
                ("Total Metadata (Global)", totals['sum_metadata'] or 0),
                ("Total Pages Scanned (By You)", user_metrics['pages_scanned_count']),
                ("Total PDF Created (By You)", user_metrics['pdf_count']),
                ("Total Indexing (By You)", user_metrics['indexing_count']),
                ("Total Uploading (By You)", user_metrics['uploading_count']),
                ("Total QC (By You)", user_metrics['qc_count']),
                ("Total Metadata (By You)", user_metrics['metadata_count']),
            ]
        else:
            summary_rows = [
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

    # Context Preparation
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

    ends_with_s = str(request.user.username).endswith('-S')

    context = {
        'reports': final_report,
        'total_deeds': totals['sum_deeds'],
        'total_pages': totals['sum_pages'],
        'total_pdf': totals['sum_pdf'],          
        'total_indexing': totals['sum_indexing'], 
        'total_uploading': totals['sum_uploading'],
        'total_qc': totals['sum_qc'],            
        'total_metadata': totals['sum_metadata'],    
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
        'ends_with_s' : ends_with_s,
    }
    return render(request, 'core/report_list.html', context)

# @login_required
# def report_list_view(request):

#     # Standardize user full name for filtering
#     user_full_name = request.user.get_full_name().upper() if request.user.get_full_name() else request.user.username.upper()

#     # Fetch PDF, Indexing, Uploading, QC, and Metadata records created by the logged-in user
#     pdf_data = PDFRecord.objects.filter(created_by=request.user)
#     ind_data = IndexingRecord.objects.filter(created_by=request.user)
#     upload_data = UploadingRecord.objects.filter(created_by=request.user)
#     qc_data = QCRecord.objects.filter(created_by=request.user)
#     metadata_data = MetadataRecord.objects.filter(created_by=request.user)

#     # Collect unique DailyReport IDs from all records
#     daily_report_ids = set(chain(
#         pdf_data.values_list('daily_report_id', flat=True),
#         ind_data.values_list('daily_report_id', flat=True),
#         upload_data.values_list('daily_report_id', flat=True),
#         qc_data.values_list('daily_report_id', flat=True),
#         metadata_data.values_list('daily_report_id', flat=True),
#     ))

#     # Fetch the corresponding DailyReport objects
#     daily_reports = DailyReport.objects.filter(id__in=daily_report_ids)

#     # NOTE : all the above data can be simply be created by 1 single query
#     # daily_reports = DailyReport.objects.filter(
#     #     Q(pdf_records__created_by=request.user) |
#     #     Q(indexing_records__created_by=request.user) |
#     #     Q(uploading_records__created_by=request.user) |
#     #     Q(qc_records__created_by=request.user) |
#     #     Q(metadata_records__created_by=request.user)
#     # ).distinct()

#     # if username ends with -S, then get the scanning report (daily report created by current user)
#     scanning_report = DailyReport.objects.none()
#     if request.user.username.endswith('-S'):
#         scanning_report = DailyReport.objects.filter(name=user_full_name)

#     # get the final report
#     final_report = (daily_reports | scanning_report).distinct() # | considered as union

#     # setup the base queryset
#     is_admin = request.user.is_staff or request.user.is_superuser

#     if is_admin:
#         final_report = DailyReport.objects.all() # if user is admin the show the complete daily report

#     # Capture URL GET Filter Parameters
#     filter_date = request.GET.get('date', '').strip()
#     filter_month = request.GET.get('month', '').strip()
#     filter_location = request.GET.get('location', '').strip()
#     filter_name = request.GET.get('name', '').strip()
#     filter_stage = request.GET.get('workflow_stage', '').strip()

#     # Apply Standard Filters
#     if filter_date:
#         # Use __date lookup to extract the calendar date from the created_at datetime field
#         pdf_data = pdf_data.filter(created_at__date=filter_date)
#         ind_data = ind_data.filter(created_at__date=filter_date)
#         upload_data = upload_data.filter(created_at__date=filter_date)
#         qc_data = qc_data.filter(created_by=request.user, created_at__date=filter_date) # assuming qc matches pattern
#         metadata_data = metadata_data.filter(created_at__date=filter_date)

#         # If the user is a scanner (ends with -S), we also need to filter their scanning reports by date!
#         if request.user.username.endswith('-S'):
#             # DailyReport has a plain .date field 
#             scanning_report = scanning_report.filter(date=filter_date) 

#         # Re-collect unique IDs from the sub-models based on the new date filters
#         daily_report_ids = set(chain(
#             pdf_data.values_list('daily_report_id', flat=True),
#             ind_data.values_list('daily_report_id', flat=True),
#             upload_data.values_list('daily_report_id', flat=True),
#             qc_data.values_list('daily_report_id', flat=True),
#             metadata_data.values_list('daily_report_id', flat=True),
#         ))

#         daily_reports = DailyReport.objects.filter(id__in=daily_report_ids)
        
#         # Re-combine the updated subsets into the final report queryset
#         final_report = (daily_reports | scanning_report).distinct()

#     if filter_month:
#         try:
#             year_part, month_part = map(int, filter_month.split('-'))
            
#             # 1. Filter sub-models using __year and __month lookups on the created_at field
#             pdf_data = pdf_data.filter(created_at__year=year_part, created_at__month=month_part)
#             ind_data = ind_data.filter(created_at__year=year_part, created_at__month=month_part)
#             upload_data = upload_data.filter(created_at__year=year_part, created_at__month=month_part)
#             qc_data = qc_data.filter(created_at__year=year_part, created_at__month=month_part)
#             metadata_data = metadata_data.filter(created_at__year=year_part, created_at__month=month_part)

#             # 2. Filter scanning reports (DailyReport uses its standard date field)
#             if request.user.username.endswith('-S'):
#                 scanning_report = scanning_report.filter(date__year=year_part, date__month=month_part)

#             # 3. Re-collect unique IDs from the month-filtered sub-models
#             daily_report_ids = set(chain(
#                 pdf_data.values_list('daily_report_id', flat=True),
#                 ind_data.values_list('daily_report_id', flat=True),
#                 upload_data.values_list('daily_report_id', flat=True),
#                 qc_data.values_list('daily_report_id', flat=True),
#                 metadata_data.values_list('daily_report_id', flat=True),
#             ))

#             daily_reports = DailyReport.objects.filter(id__in=daily_report_ids)
            
#             # 4. Re-combine the updated subsets into your final report queryset
#             final_report = (daily_reports | scanning_report).distinct()

#         except ValueError:
#             pass

#     if filter_location:
#         final_report = final_report.filter(location=filter_location)

#     if filter_name and is_admin:
#         final_report = final_report.filter(name__icontains=filter_name)

#     # 2. 🌟 DYNAMIC WORKFLOW SUB-MODEL STAGE FILTER 🌟
#     if filter_stage:
#         if filter_stage == 'pdf':
#             final_report = final_report.filter(pdf_records__isnull=False)
#         elif filter_stage == 'indexing':
#             final_report = final_report.filter(indexing_records__isnull=False)
#         elif filter_stage == 'uploading':
#             final_report = final_report.filter(uploading_records__isnull=False)
#         elif filter_stage == 'qc':
#             final_report = final_report.filter(qc_records__isnull=False)
#         elif filter_stage == 'metadata':
#             final_report = final_report.filter(metadata_records__isnull=False)

#     # Calculate Global Totals for the current queryset (Consolidated Metrics)
#     # Conditional aggregation sums values only if the respective workflow checkbox is checked
#     totals = final_report.aggregate(
#         sum_deeds=Sum('num_of_deed'),
#         sum_pages=Sum('num_of_page'),
#         sum_pdf=Sum('num_of_deed', filter=Q(pdf_deed=True)),
#         sum_indexing=Sum('num_of_deed', filter=Q(indexing=True)),
#         sum_uploading=Sum('num_of_deed', filter=Q(uploading=True)),
#         sum_qc=Sum('num_of_deed', filter=Q(QC=True)),
#         sum_metadata=Sum('num_of_page', filter=Q(metadata=True))
#     )

#     # Calculate User Metrics (Personal Performance Summary)
#     user_metrics = {
#         # 🌟 Only calculate pages scanned if the user's username ends with -S, otherwise default to 0
#         'pages_scanned_count': (
#             final_report.filter(name__iexact=user_full_name).aggregate(s=Sum('num_of_page'))['s'] or 0
#         ) if request.user.username.endswith('-S') else 0,
        
#         # Total Deeds for reports where this user created the PDF
#         'pdf_count': PDFRecord.objects.filter(
#             created_by=request.user, 
#             daily_report__in=final_report
#         ).aggregate(s=Sum('daily_report__num_of_deed'))['s'] or 0,
        
#         # Total Deeds for reports where this user did the Indexing
#         'indexing_count': IndexingRecord.objects.filter(
#             created_by=request.user, 
#             daily_report__in=final_report
#         ).aggregate(s=Sum('daily_report__num_of_deed'))['s'] or 0,
        
#         # Total Deeds for reports where this user handled Uploading 
#         'uploading_count': UploadingRecord.objects.filter(
#             created_by=request.user, 
#             daily_report__in=final_report
#         ).aggregate(s=Sum('daily_report__num_of_deed'))['s'] or 0,
        
#         # Total Deeds for reports where this user did the Quality Check (QC)
#         'qc_count': QCRecord.objects.filter(
#             created_by=request.user, 
#             daily_report__in=final_report
#         ).aggregate(s=Sum('daily_report__num_of_deed'))['s'] or 0,
        
#         # Total Pages for reports where this user entered the Metadata
#         'metadata_count': MetadataRecord.objects.filter(
#             created_by=request.user, 
#             daily_report__in=final_report
#         ).aggregate(s=Sum('daily_report__num_of_page'))['s'] or 0,
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

#         for report in final_report:
#             row_data = [
#                 report.date.strftime('%d/%m/%Y') if report.date else '',
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

#         # Dynamically build summary rows based on user role
#         if is_admin:
#             # Admins get everything: Global Consolidated Metrics + Personalized Summary
#             summary_rows = [
#                 ("Total Number of volume", len(queryset)),  
#                 ("Total Deeds", totals['sum_deeds'] or 0),  
#                 ("Total Pages", totals['sum_pages'] or 0),
#                 ("Total PDF Created (Global)", totals['sum_pdf'] or 0),
#                 ("Total Indexing (Global)", totals['sum_indexing'] or 0),
#                 ("Total Uploading (Global)", totals['sum_uploading'] or 0),
#                 ("Total QC (Global)", totals['sum_qc'] or 0),
#                 ("Total Metadata (Global)", totals['sum_metadata'] or 0),
#                 ("Total Pages Scanned (By You)", user_metrics['pages_scanned_count']),
#                 ("Total PDF Created (By You)", user_metrics['pdf_count']),
#                 ("Total Indexing (By You)", user_metrics['indexing_count']),
#                 ("Total Uploading (By You)", user_metrics['uploading_count']),
#                 ("Total QC (By You)", user_metrics['qc_count']),
#                 ("Total Metadata (By You)", user_metrics['metadata_count']),
#             ]
#         else:
#             # Regular users only see their own personal performance metrics
#             summary_rows = [
#                 ("Total Pages Scanned (By You)", user_metrics['pages_scanned_count']),
#                 ("Total PDF Created (By You)", user_metrics['pdf_count']),
#                 ("Total Indexing (By You)", user_metrics['indexing_count']),
#                 ("Total Uploading (By You)", user_metrics['uploading_count']),
#                 ("Total QC (By You)", user_metrics['qc_count']),
#                 ("Total Metadata (By You)", user_metrics['metadata_count']),
#             ]

#         # Write out whatever rows were packed into summary_rows
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
            
#             # Formats the bottom outline cleanly on whichever row finishes the file
#             if label == "Total Metadata (By You)":
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

#     # Context Preparation
#     existing_dates = DailyReport.objects.dates('date', 'month', order='DESC')
#     available_months = [
#         {'value': d.strftime('%Y-%m'), 'display': d.strftime('%B %Y')}
#         for d in existing_dates
#     ]

#     workflow_stages = [
#         {'value': 'pdf', 'display': 'PDF Report'},
#         {'value': 'indexing', 'display': 'Indexing Report'},
#         {'value': 'uploading', 'display': 'Uploading Report'},
#         {'value': 'qc', 'display': 'QC Report'},
#         {'value': 'metadata', 'display': 'Metadata Report'},
#     ]

#     ends_with_s = str(request.user.username).endswith('-S')

#     context = {
#         'reports': final_report,
#         'total_deeds': totals['sum_deeds'],
#         'total_pages': totals['sum_pages'],
#         'total_pdf': totals['sum_pdf'],          
#         'total_indexing': totals['sum_indexing'], 
#         'total_uploading': totals['sum_uploading'],
#         'total_qc': totals['sum_qc'],            
#         'total_metadata': totals['sum_metadata'],    
#         'user_metrics': user_metrics,
#         'locations': DailyReport.LOCATION_CHOICES,
#         'available_months': available_months,
#         'workflow_stages': workflow_stages,       
#         'selected_date': filter_date,
#         'selected_month': filter_month,
#         'selected_location': filter_location,
#         'selected_name': filter_name,
#         'selected_stage': filter_stage,           
#         'is_admin': is_admin,
#         'ends_with_s' : ends_with_s,
#     }
#     return render(request, 'core/report_list.html', context)


# @login_required
# def report_list_view(request):
#     is_admin = request.user.is_staff or request.user.is_superuser
    
#     # Standardize user full name for filtering
#     user_full_name = request.user.get_full_name().upper() if request.user.get_full_name() else request.user.username.upper()

#     # 1. 🌟 FILTER BASED ON ENGAGEMENT / ROLE 🌟
#     if is_admin:
#         base_queryset = DailyReport.objects.all()
#     else:
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
#     filter_stage = request.GET.get('workflow_stage', '').strip()

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

#     # Calculate Global Totals for the current queryset
#     totals = queryset.aggregate(
#         sum_deeds=Sum('num_of_deed'),
#         sum_pages=Sum('num_of_page')
#     )

#     # Calculate User Metrics (Personal Performance Summary)
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
#                 report.date.strftime('%d/%m/%Y') if report.date else '',
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
            
#             # Apply terminal thick bottom line to the last summary item
#             if label == "Total Metadata (By You)":
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
#         'workflow_stages': workflow_stages,       
#         'selected_date': filter_date,
#         'selected_month': filter_month,
#         'selected_location': filter_location,
#         'selected_name': filter_name,
#         'selected_stage': filter_stage,           
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