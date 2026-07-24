import csv
from io import BytesIO

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin, GroupAdmin as BaseGroupAdmin
from django.contrib.auth.models import User, Group
from django.db import models
from django.http import HttpResponse
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html

from unfold.admin import ModelAdmin, TabularInline
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm
from unfold.contrib.filters.admin import (
    ChoicesDropdownFilter,
    DropdownFilter,
    RangeDateFilter,
    RelatedDropdownFilter,
)
from .models import ContactMessage, CompanyCertificate, DailyReport, PDFRecord, IndexingRecord, UploadingRecord, QCRecord, MetadataRecord
from .utils import sync_workflow_records


# ── Daily Report export helpers ────────────────────────────
DAILY_REPORT_EXPORT_HEADERS = [
    "Date",
    "Employee",
    "District",
    "Location",
    "Year",
    "Volume",
    "Pages",
    "Deeds",
    "Scanning",
    "PDF",
    "Indexing",
    "Uploading",
    "QC",
    "Metadata",
    "Created at",
]


def _yn(value):
    return "Yes" if bool(value) else "No"


def _dr_row(report):
    return [
        report.date.strftime("%Y-%m-%d") if report.date else "",
        report.name or "",
        report.get_district_display() if report.district else "",
        report.get_location_display() if report.location else "",
        report.year or "",
        report.volume_num or "",
        report.num_of_page if report.num_of_page is not None else "",
        report.num_of_deed if report.num_of_deed is not None else "",
        _yn(report.scanning),
        _yn(report.pdf_deed),
        _yn(report.indexing),
        _yn(report.uploading),
        _yn(report.QC),
        _yn(report.metadata),
        timezone.localtime(report.created_at).strftime("%Y-%m-%d %H:%M") if report.created_at else "",
    ]


def _dr_iter_rows(queryset):
    for report in queryset.iterator(chunk_size=500):
        yield _dr_row(report)


def _dr_filename(ext):
    stamp = timezone.localtime().strftime("%Y%m%d-%H%M")
    return f"daily-reports-{stamp}.{ext}"


def export_daily_reports_csv(queryset):
    """Stream a filtered DailyReport queryset as CSV."""
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{_dr_filename("csv")}"'
    # Excel-friendly UTF-8 BOM so Unicode names render correctly
    response.write("\ufeff")
    writer = csv.writer(response)
    writer.writerow(DAILY_REPORT_EXPORT_HEADERS)
    for row in _dr_iter_rows(queryset):
        writer.writerow(row)
    return response


def export_daily_reports_xlsx(queryset):
    """Return the filtered DailyReport queryset as an .xlsx download."""
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Daily Reports"

    header_font = Font(bold=True, color="FFFFFFFF")
    header_fill = PatternFill("solid", fgColor="FF16A34A")
    center = Alignment(horizontal="center", vertical="center")

    sheet.append(DAILY_REPORT_EXPORT_HEADERS)
    for col_idx, _ in enumerate(DAILY_REPORT_EXPORT_HEADERS, start=1):
        cell = sheet.cell(row=1, column=col_idx)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center

    widths = [12, 22, 14, 16, 8, 10, 8, 8, 10, 8, 10, 12, 8, 10, 18]
    for col_idx, width in enumerate(widths, start=1):
        sheet.column_dimensions[get_column_letter(col_idx)].width = width

    for row in _dr_iter_rows(queryset):
        sheet.append(row)

    sheet.freeze_panes = "A2"

    buf = BytesIO()
    workbook.save(buf)
    buf.seek(0)

    response = HttpResponse(
        buf.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = f'attachment; filename="{_dr_filename("xlsx")}"'
    return response

admin.site.index_title = "Dashboard"


class PremiumAdmin(ModelAdmin):
    """Shared responsive list controls for all admin pages."""

    list_per_page = 25
    list_max_show_all = 100
    list_filter_submit = True
    list_filter_sheet = False
    show_full_result_count = False


# ── USERS & GROUPS (restyled with the Unfold theme) ──
admin.site.unregister(User)
admin.site.unregister(Group)


@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
    # Unfold-styled forms so the add/change user pages match the admin theme
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm

    list_display = ('username', 'full_name_display', 'role_display', 'is_active', 'last_login')
    list_filter = ('is_staff', 'is_superuser', 'is_active')
    search_fields = ('username', 'first_name', 'last_name', 'email')
    search_help_text = "Search by username, name, or email"
    ordering = ('username',)
    list_per_page = 25
    list_filter_submit = True
    list_filter_sheet = False

    add_fieldsets = (
        ('Account Credentials', {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2'),
            'description': "Usernames ending with -S are treated as scanner accounts.",
        }),
        ('Employee Details', {
            'classes': ('wide',),
            'fields': ('first_name', 'last_name', 'email'),
            'description': "First and last name appear as the employee name on daily reports.",
        }),
        ('Permissions', {
            'classes': ('wide',),
            'fields': ('is_active', 'is_staff', 'is_superuser'),
            'description': "Staff status makes this user an admin who can see all reports.",
        }),
    )

    fieldsets = (
        ('Account Credentials', {'fields': ('username', 'password')}),
        ('Employee Details', {'fields': ('first_name', 'last_name', 'email')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important Dates', {'fields': ('last_login', 'date_joined'), 'classes': ('collapse',)}),
    )

    def full_name_display(self, obj):
        return obj.get_full_name() or "—"
    full_name_display.short_description = "Full Name"

    def role_display(self, obj):
        if obj.is_superuser:
            return format_html('<strong style="color:#dc2626;">Superuser</strong>')
        if obj.is_staff:
            return format_html('<strong style="color:#d97706;">Admin</strong>')
        if obj.username.endswith('-S'):
            return format_html('<strong style="color:#15803d;">Scanner</strong>')
        return "Employee"
    role_display.short_description = "Role"


@admin.register(Group)
class GroupAdmin(BaseGroupAdmin, ModelAdmin):
    pass


class ReportYearDropdownFilter(DropdownFilter):
    title = "year"
    parameter_name = "year"

    def lookups(self, request, model_admin):
        years = DailyReport.objects.order_by("-year").values_list("year", flat=True).distinct()
        return [(year, year) for year in years if year]

    def queryset(self, request, queryset):
        return queryset.filter(year=self.value()) if self.value() else queryset


class RelatedReportYearDropdownFilter(ReportYearDropdownFilter):
    parameter_name = "daily_report__year"

    def queryset(self, request, queryset):
        return (
            queryset.filter(daily_report__year=self.value())
            if self.value()
            else queryset
        )


class CertificateTypeDropdownFilter(DropdownFilter):
    title = "certificate title"
    parameter_name = "certificate_name"

    def lookups(self, request, model_admin):
        names = (
            CompanyCertificate.objects.order_by("certificate_name")
            .values_list("certificate_name", flat=True)
            .distinct()
        )
        return [(name, name) for name in names if name]

    def queryset(self, request, queryset):
        return (
            queryset.filter(certificate_name=self.value())
            if self.value()
            else queryset
        )


@admin.register(ContactMessage)
class ContactMessageAdmin(PremiumAdmin):
    list_display = ('name', 'email', 'phone', 'subject', 'created_at', 'is_read')
    list_filter = ('is_read', ('created_at', RangeDateFilter))
    search_fields = ('name', 'email', 'subject')
    search_help_text = "Search by name, email, or subject"
    readonly_fields = ('created_at',)
    actions = ['mark_as_read']

    def mark_as_read(self, request, queryset):
        queryset.update(is_read=True)
    mark_as_read.short_description = "Mark selected as read"



@admin.register(CompanyCertificate)
class CompanyCertificateAdmin(PremiumAdmin):
    # Removed 'expiry_date' from the end of this list
    list_display = ('certificate_number', 'recipient_name', 'certificate_name', 'issue_date')
    
    list_display_links = ('certificate_number', 'recipient_name')
    search_fields = ('recipient_name', 'certificate_number', 'certificate_name')
    search_help_text = "Search by recipient, certificate number, or title"
    list_filter = (
        CertificateTypeDropdownFilter,
        ('issue_date', RangeDateFilter),
    )
    
    # Cleaned up the fieldsets layout to remove the dates breakdown
    fieldsets = (
        ('Certificate Identification', {
            'fields': ('certificate_number', 'certificate_name')
        }),
        ('Recipient Information', {
            'fields': ('recipient_name',)
        }),
        ('Issue Date', {
            'fields': ('issue_date',)
        }),
    )

# --- Optional: Tabular Inlines ---
# This lets administrators view and edit the sub-records directly at the bottom
# of the DailyReport page without leaving the screen!
class PDFRecordInline(TabularInline):
    model = PDFRecord
    extra = 0
    fields = ('created_by', 'name', 'created_at')

class IndexingRecordInline(TabularInline):
    model = IndexingRecord
    extra = 0
    fields = ('created_by', 'name', 'created_at')

class UploadingRecordInline(TabularInline):
    model = UploadingRecord
    extra = 0
    fields = ('created_by', 'name', 'created_at')

class QCRecordInline(TabularInline):
    model = QCRecord
    extra = 0
    fields = ('created_by', 'name', 'created_at')

class MetadataRecordInline(TabularInline):
    model = MetadataRecord
    extra = 0
    fields = ('created_by', 'name', 'created_at')


# --- Main DailyReport Admin ---
@admin.register(DailyReport)
class DailyReportAdmin(PremiumAdmin):
    list_before_template = "admin/core/dailyreport_list_header.html"
    list_fullwidth = True
    list_display = (
        'serial_no',
        'date',
        'name',
        'district_badge',
        'archive_location',
        'deed_cell',
        'page_cell',
        'pdf_badge',
        'indexing_badge',
        'uploading_badge',
        'qc_badge',
        'edit_button',
    )
    list_display_links = ('name',)
    list_filter = (
        ('district', ChoicesDropdownFilter),
        ('location', ChoicesDropdownFilter),
        ReportYearDropdownFilter,
        'pdf_deed',
        'indexing',
        'uploading',
        'QC',
        'metadata',
    )
    # Open filters in an off-canvas drawer (opened via the hero button)
    list_filter_sheet = True
    list_filter_submit = True
    search_fields = ('name', 'year', 'volume_num', 'district', 'location')
    search_help_text = "Search by employee, year, volume, district, or location"

    readonly_fields = ('district',)

    actions = ("export_selected_as_csv", "export_selected_as_xlsx")

    # Embed the inline tables nicely at the bottom of the edit layout
    inlines = [PDFRecordInline, IndexingRecordInline, UploadingRecordInline, QCRecordInline, MetadataRecordInline]

    _STAGE_LABEL = {True: "Done", False: "—"}

    class Media:
        css = {"all": ("core/css/admin-premium.css",)}
        js = ("core/js/admin-filters-drawer.js",)

    # ── Custom columns ─────────────────────────────────────────
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Stash the request so serial_no can compute against the current page
        self._current_request = request
        return qs

    def serial_no(self, obj):
        request = getattr(self, "_current_request", None)
        page = 1
        per_page = self.list_per_page
        if request is not None:
            try:
                page = max(int(request.GET.get("p", 0)) + 1, 1)
            except (TypeError, ValueError):
                page = 1
        counter = getattr(self, "_row_counter", 0) + 1
        self._row_counter = counter
        # Reset when a new page loads (row 1 for that page)
        base = (page - 1) * per_page
        return format_html(
            '<span class="ngs-dr-sl">{}</span>',
            base + counter if counter <= per_page else counter,
        )
    serial_no.short_description = "Sl no"

    def district_badge(self, obj):
        label = obj.get_district_display() if obj.district else "—"
        return format_html(
            '<span class="ngs-dr-district">{}</span>',
            label,
        )
    district_badge.short_description = "District"
    district_badge.admin_order_field = "district"

    def archive_location(self, obj):
        town = obj.get_location_display() if obj.location else "—"
        year = obj.year or "—"
        volume = obj.volume_num or "—"
        return format_html(
            '<div class="ngs-dr-loc">'
            '<span class="ngs-dr-loc-year">{}</span>'
            '<span class="ngs-dr-loc-vol">{} · Vol {}</span>'
            '</div>',
            town,
            year,
            volume,
        )
    archive_location.short_description = "Location"
    archive_location.admin_order_field = "location"

    def deed_cell(self, obj):
        val = obj.num_of_deed
        if val is None:
            return format_html('<span class="ngs-dr-num ngs-dr-num-empty">—</span>')
        return format_html('<span class="ngs-dr-num">{}</span>', f"{val:,}")
    deed_cell.short_description = "Deed"
    deed_cell.admin_order_field = "num_of_deed"

    def page_cell(self, obj):
        val = obj.num_of_page
        if val is None:
            return format_html('<span class="ngs-dr-num ngs-dr-num-empty">—</span>')
        return format_html('<span class="ngs-dr-num">{}</span>', f"{val:,}")
    page_cell.short_description = "Page"
    page_cell.admin_order_field = "num_of_page"

    def _stage_badge(self, done, letter):
        cls = "ngs-dr-stage ngs-dr-stage-done" if done else "ngs-dr-stage ngs-dr-stage-todo"
        return format_html(
            '<span class="{}" title="{}"><span class="ngs-dr-stage-dot"></span>{}</span>',
            cls,
            "Completed" if done else "Pending",
            letter,
        )

    def pdf_badge(self, obj):
        return self._stage_badge(obj.pdf_deed, "PDF")
    pdf_badge.short_description = "PDF"
    pdf_badge.admin_order_field = "pdf_deed"

    def indexing_badge(self, obj):
        return self._stage_badge(obj.indexing, "IDX")
    indexing_badge.short_description = "Indexing"
    indexing_badge.admin_order_field = "indexing"

    def uploading_badge(self, obj):
        return self._stage_badge(obj.uploading, "UP")
    uploading_badge.short_description = "Uploading"
    uploading_badge.admin_order_field = "uploading"

    def qc_badge(self, obj):
        return self._stage_badge(obj.QC, "QC")
    qc_badge.short_description = "QC"
    qc_badge.admin_order_field = "QC"

    def edit_button(self, obj):
        """Compact edit pill."""
        url = reverse('admin:core_dailyreport_change', args=[obj.pk])
        return format_html(
            '<a href="{}" class="ngs-dr-edit">'
            '<span class="material-symbols-outlined">edit</span>Edit</a>',
            url,
        )
    edit_button.short_description = ""

    # ── KPI + pipeline stats for the header ────────────────────
    def changelist_view(self, request, extra_context=None):
        self._row_counter = 0
        extra_context = extra_context or {}

        qs = self.get_queryset(request)
        total = qs.count()
        agg = qs.aggregate(
            pages=models.Sum("num_of_page"),
            deeds=models.Sum("num_of_deed"),
        )
        pages = agg["pages"] or 0
        deeds = agg["deeds"] or 0
        districts = qs.exclude(district="").values("district").distinct().count()
        pdf_done = qs.filter(pdf_deed=True).count()
        idx_done = qs.filter(indexing=True).count()
        up_done = qs.filter(uploading=True).count()
        qc_done = qs.filter(QC=True).count()
        meta_done = qs.filter(metadata=True).count()

        def _pct(part):
            return round((part / total) * 100) if total else 0

        district_label_map = dict(DailyReport.DISTRICT_CHOICES)
        district_rows = (
            qs.exclude(district="")
            .values("district")
            .annotate(count=models.Count("id"))
            .order_by("-count")
        )
        district_chips = [
            {
                "code": row["district"],
                "label": district_label_map.get(row["district"], row["district"].title()),
                "count": row["count"],
                "pct": _pct(row["count"]),
            }
            for row in district_rows
        ]

        extra_context["dr_kpis"] = [
            {"label": "Reports", "value": f"{total:,}", "hint": "volumes", "icon": "description"},
            {"label": "Pages", "value": f"{pages:,}", "hint": "scanned", "icon": "menu_book"},
            {"label": "Deeds", "value": f"{deeds:,}", "hint": "recorded", "icon": "folder_open"},
            {"label": "Districts", "value": f"{districts:,}", "hint": "active", "icon": "location_on"},
            {"label": "PDF done", "value": f"{_pct(pdf_done)}%", "hint": f"{pdf_done:,} of {total:,}", "icon": "picture_as_pdf"},
            {"label": "QC done", "value": f"{_pct(qc_done)}%", "hint": f"{qc_done:,} of {total:,}", "icon": "verified"},
        ]
        extra_context["dr_pipeline"] = [
            {"label": "PDF", "done": pdf_done, "pct": _pct(pdf_done), "icon": "picture_as_pdf"},
            {"label": "Indexing", "done": idx_done, "pct": _pct(idx_done), "icon": "toc"},
            {"label": "Uploading", "done": up_done, "pct": _pct(up_done), "icon": "cloud_upload"},
            {"label": "QC", "done": qc_done, "pct": _pct(qc_done), "icon": "task_alt"},
            {"label": "Metadata", "done": meta_done, "pct": _pct(meta_done), "icon": "bookmark_added"},
        ]
        extra_context["dr_district_chips"] = district_chips
        extra_context["dr_add_url"] = reverse("admin:core_dailyreport_add")
        extra_context["dr_total"] = total

        # Count active filter params (excluding pagination / ordering / search)
        _skip = {"p", "o", "q", "all", "e", "_changelist_filters"}
        extra_context["dr_active_filters"] = sum(
            1 for key, value in request.GET.items()
            if key not in _skip and value not in ("", None)
        )

        # One-click export URLs preserve the current filter + search context
        export_qs = request.GET.urlencode()
        base_csv = reverse("admin:core_dailyreport_export_csv")
        base_xlsx = reverse("admin:core_dailyreport_export_xlsx")
        extra_context["dr_export_csv_url"] = f"{base_csv}?{export_qs}" if export_qs else base_csv
        extra_context["dr_export_xlsx_url"] = f"{base_xlsx}?{export_qs}" if export_qs else base_xlsx

        return super().changelist_view(request, extra_context)

    # ── Bulk export actions (selected rows) ────────────────────
    @admin.action(description="Export selected reports as CSV")
    def export_selected_as_csv(self, request, queryset):
        return export_daily_reports_csv(queryset)

    @admin.action(description="Export selected reports as Excel (.xlsx)")
    def export_selected_as_xlsx(self, request, queryset):
        return export_daily_reports_xlsx(queryset)

    # ── One-click filtered export (uses the current changelist filters) ──
    def get_urls(self):
        urls = super().get_urls()
        info = (self.model._meta.app_label, self.model._meta.model_name)
        custom = [
            path(
                "export/csv/",
                self.admin_site.admin_view(self.export_filtered_csv_view),
                name="%s_%s_export_csv" % info,
            ),
            path(
                "export/xlsx/",
                self.admin_site.admin_view(self.export_filtered_xlsx_view),
                name="%s_%s_export_xlsx" % info,
            ),
        ]
        return custom + urls

    def _filtered_queryset_from_request(self, request):
        """Reuse Django admin's ChangeList so exports honour every active filter/search."""
        list_display = self.get_list_display(request)
        list_display_links = self.get_list_display_links(request, list_display)
        list_filter = self.get_list_filter(request)
        search_fields = self.get_search_fields(request)
        sortable_by = self.get_sortable_by(request)

        ChangeList = self.get_changelist(request)
        cl = ChangeList(
            request,
            self.model,
            list_display,
            list_display_links,
            list_filter,
            self.date_hierarchy,
            search_fields,
            self.list_select_related,
            self.list_per_page,
            self.list_max_show_all,
            self.list_editable,
            self,
            sortable_by,
            self.search_help_text,
        )
        return cl.get_queryset(request)

    def export_filtered_csv_view(self, request):
        return export_daily_reports_csv(self._filtered_queryset_from_request(request))

    def export_filtered_xlsx_view(self, request):
        return export_daily_reports_xlsx(self._filtered_queryset_from_request(request))

    def save_model(self, request, obj, form, change):
        """
        Overrides the admin panel save process. 
        If an admin checks or unchecks a box, it fires our workflow synchronization function.
        """
        # 1. Save the main DailyReport model changes first
        super().save_model(request, obj, form, change)
        
        # 2. Automatically sync sub-models using the logged-in Administrator account
        sync_workflow_records(obj, request.user)
    
    


# --- Standalone Sub-Model Registration ---
# This registers them as independent searchable menus on the Admin homepage
# @admin.register(PDFRecord)
# class PDFRecordAdmin(admin.ModelAdmin):
#     list_display = ('daily_report', 'created_by', 'name', 'created_at')
#     search_fields = ('name', 'daily_report__volume_num')

@admin.register(PDFRecord)
class PDFRecordAdmin(PremiumAdmin):
    # 1. Swap 'daily_report' with our new custom method 'link_to_daily_report'
    list_display = ('link_to_daily_report', 'name', 'created_at')
    search_fields = ('name', 'daily_report__year', 'created_by__username')
    search_help_text = "Search by employee, year, or username"
    list_filter = (
        RelatedReportYearDropdownFilter,
        ('daily_report__location', ChoicesDropdownFilter),
        ('created_by', RelatedDropdownFilter),
        ('created_at', RangeDateFilter),
    )

    def link_to_daily_report(self, obj):
        """
        Generates a secure html anchor tag linking directly 
        to the parent DailyReport change form.
        """
        if obj.daily_report:
            # Reverse lookup the admin URL path dynamically
            # Format: admin:<app_label>_<model_name>_change
            url = reverse('admin:core_dailyreport_change', args=[obj.daily_report.id])
            return format_html('<a href="{}" style="font-weight: bold; color: #15803d;">{}</a>', url, obj.daily_report)
        return "-"

    # 2. Give the column a clean display header and allow it to sort correctly
    link_to_daily_report.short_description = "Daily Report"
    link_to_daily_report.admin_order_field = "daily_report"

@admin.register(IndexingRecord)
class IndexingRecordAdmin(PremiumAdmin):
    list_display = ('link_to_daily_report', 'created_by', 'name', 'created_at')
    search_fields = ('name', 'daily_report__year', 'created_by__username')
    search_help_text = "Search by employee, year, or username"
    list_filter = (
        RelatedReportYearDropdownFilter,
        ('daily_report__location', ChoicesDropdownFilter),
        ('created_by', RelatedDropdownFilter),
        ('created_at', RangeDateFilter),
    )

    def link_to_daily_report(self, obj):
        """
        Generates a secure html anchor tag linking directly 
        to the parent DailyReport change form.
        """
        if obj.daily_report:
            # Reverse lookup the admin URL path dynamically
            # Format: admin:<app_label>_<model_name>_change
            url = reverse('admin:core_dailyreport_change', args=[obj.daily_report.id])
            return format_html('<a href="{}" style="font-weight: bold; color: #15803d;">{}</a>', url, obj.daily_report)
        return "-"

    # 2. Give the column a clean display header and allow it to sort correctly
    link_to_daily_report.short_description = "Daily Report"
    link_to_daily_report.admin_order_field = "daily_report"

@admin.register(UploadingRecord)
class UploadingRecordAdmin(PremiumAdmin):
    list_display = ('link_to_daily_report', 'created_by', 'name', 'created_at')
    search_fields = ('name', 'daily_report__year', 'created_by__username')
    search_help_text = "Search by employee, year, or username"
    list_filter = (
        RelatedReportYearDropdownFilter,
        ('daily_report__location', ChoicesDropdownFilter),
        ('created_by', RelatedDropdownFilter),
        ('created_at', RangeDateFilter),
    )

    def link_to_daily_report(self, obj):
        """
        Generates a secure html anchor tag linking directly 
        to the parent DailyReport change form.
        """
        if obj.daily_report:
            # Reverse lookup the admin URL path dynamically
            # Format: admin:<app_label>_<model_name>_change
            url = reverse('admin:core_dailyreport_change', args=[obj.daily_report.id])
            return format_html('<a href="{}" style="font-weight: bold; color: #15803d;">{}</a>', url, obj.daily_report)
        return "-"

    # 2. Give the column a clean display header and allow it to sort correctly
    link_to_daily_report.short_description = "Daily Report"
    link_to_daily_report.admin_order_field = "daily_report"

@admin.register(QCRecord)
class QCRecordAdmin(PremiumAdmin):
    list_display = ('link_to_daily_report', 'created_by', 'name', 'created_at')
    search_fields = ('name', 'daily_report__year', 'created_by__username')
    search_help_text = "Search by employee, year, or username"
    list_filter = (
        RelatedReportYearDropdownFilter,
        ('daily_report__location', ChoicesDropdownFilter),
        ('created_by', RelatedDropdownFilter),
        ('created_at', RangeDateFilter),
    )

    def link_to_daily_report(self, obj):
        """
        Generates a secure html anchor tag linking directly 
        to the parent DailyReport change form.
        """
        if obj.daily_report:
            # Reverse lookup the admin URL path dynamically
            # Format: admin:<app_label>_<model_name>_change
            url = reverse('admin:core_dailyreport_change', args=[obj.daily_report.id])
            return format_html('<a href="{}" style="font-weight: bold; color: #15803d;">{}</a>', url, obj.daily_report)
        return "-"

    # 2. Give the column a clean display header and allow it to sort correctly
    link_to_daily_report.short_description = "Daily Report"
    link_to_daily_report.admin_order_field = "daily_report"

@admin.register(MetadataRecord)
class MetadataRecordAdmin(PremiumAdmin):
    list_display = ('link_to_daily_report', 'created_by', 'name', 'created_at')
    search_fields =('name', 'daily_report__year', 'created_by__username')
    search_help_text = "Search by employee, year, or username"
    list_filter = (
        RelatedReportYearDropdownFilter,
        ('daily_report__location', ChoicesDropdownFilter),
        ('created_by', RelatedDropdownFilter),
        ('created_at', RangeDateFilter),
    )

    def link_to_daily_report(self, obj):
        """
        Generates a secure html anchor tag linking directly 
        to the parent DailyReport change form.
        """
        if obj.daily_report:
            # Reverse lookup the admin URL path dynamically
            # Format: admin:<app_label>_<model_name>_change
            url = reverse('admin:core_dailyreport_change', args=[obj.daily_report.id])
            return format_html('<a href="{}" style="font-weight: bold; color: #15803d;">{}</a>', url, obj.daily_report)
        return "-"

    # 2. Give the column a clean display header and allow it to sort correctly
    link_to_daily_report.short_description = "Daily Report"
    link_to_daily_report.admin_order_field = "daily_report"