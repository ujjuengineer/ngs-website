from django.contrib import admin
from .models import ContactMessage, CompanyCertificate

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