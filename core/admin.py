from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin, GroupAdmin as BaseGroupAdmin
from django.contrib.auth.models import User, Group
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
from django.urls import reverse
from django.utils.html import format_html

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
    list_display = (
        'id',
        'year',
        'volume_num',
        'location',
        'name',
        'pdf_deed',
        'indexing',
        'uploading',
        'QC',
        'metadata',
        'created_at',
        'edit_button',
    )
    list_display_links = ('id', 'name')
    list_filter = (
        ('location', ChoicesDropdownFilter),
        ReportYearDropdownFilter,
        'pdf_deed',
        'indexing',
        'uploading',
        'QC',
        'metadata',
    )
    search_fields = ('name', 'year', 'volume_num')
    search_help_text = "Search by employee, year, or volume number"

    
    # Embed the inline tables nicely at the bottom of the edit layout
    inlines = [PDFRecordInline, IndexingRecordInline, UploadingRecordInline, QCRecordInline, MetadataRecordInline]

    def edit_button(self, obj):
        """Visible Edit button so admins can fix typos / spelling mistakes."""
        url = reverse('admin:core_dailyreport_change', args=[obj.pk])
        return format_html(
            '<a href="{}" style="display:inline-block;background:#15803d;color:#fff;'
            'padding:4px 12px;border-radius:6px;font-size:12px;font-weight:600;'
            'text-decoration:none;white-space:nowrap;">Edit</a>',
            url,
        )
    edit_button.short_description = "Edit"

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