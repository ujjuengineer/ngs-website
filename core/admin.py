from django.contrib import admin
from .models import ContactMessage, CompanyCertificate, DailyReport

@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'phone', 'subject', 'created_at', 'is_read')
    list_filter = ('is_read', 'created_at')
    search_fields = ('name', 'email', 'subject')
    readonly_fields = ('created_at',)
    actions = ['mark_as_read']

    def mark_as_read(self, request, queryset):
        queryset.update(is_read=True)
    mark_as_read.short_description = "Mark selected as read"



@admin.register(CompanyCertificate)
class CompanyCertificateAdmin(admin.ModelAdmin):
    # Removed 'expiry_date' from the end of this list
    list_display = ('certificate_number', 'recipient_name', 'certificate_name', 'issue_date')
    
    list_display_links = ('certificate_number', 'recipient_name')
    search_fields = ('recipient_name', 'certificate_number', 'certificate_name')
    list_filter = ('issue_date', 'certificate_name')
    
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

@admin.register(DailyReport)
class DailyReportAdmin(admin.ModelAdmin):
    # readonly_fields = ('created_at',)
    
    # What columns to show in the list view table
    list_display = ('date', 'created_at', 'location', 'name', 'year', 'volume_num', 'num_of_deed', 'num_of_page')
    
    # What fields can be clicked to open the edit page
    list_display_links = ('date', 'name')
    
    # Right sidebar filters
    list_filter = ('date', 'location', 'pdf_deed', 'indexing', 'uploading', 'metadata')
    
    # Search bar configuration (case-insensitive search)
    search_fields = ('name', 'volume_num', 'year')
    
    # Keeps records ordered with the newest reports on top
    ordering = ('-date',)
    
    # Layout optimization using Fieldsets to group quantitative stats and process checks
    fieldsets = (
        ('Basic Information', {
            'fields': ('date', 'created_at', 'location', 'name')
        }),
        ('Book details', {
            'fields': ('year', 'volume_num', 'num_of_deed', 'num_of_page')
        }),
        ('Status Checklists', {
            'fields': ('pdf_deed', 'indexing', 'uploading', 'metadata'),
            'description': 'Mark operations as true once completed.'
        }),
    )