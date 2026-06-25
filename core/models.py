from django.db import models
import uuid

class ContactMessage(models.Model):
    name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    subject = models.CharField(max_length=300)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} - {self.subject}"

    class Meta:
        ordering = ['-created_at']

class CompanyCertificate(models.Model):
    # The name of the recipient
    recipient_name = models.CharField(max_length=255, verbose_name="Recipient Name")
    
    # The title of the certificate
    certificate_name = models.CharField(
        max_length=255, 
        verbose_name="Certificate Title", 
        default="Certificate of Achievement"
    )
    
    # Certificate Number - unique to prevent duplication
    certificate_number = models.CharField(
        max_length=100, 
        unique=True, 
        verbose_name="Certificate Number"
    )
    
    # Issue Date
    issue_date = models.DateField(verbose_name="Issue Date")
    
    # Metadata fields to track database records
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Company Certificate"
        verbose_name_plural = "Company Certificates"
        ordering = ['-issue_date']

    def __str__(self):
        return f"{self.certificate_number} - {self.recipient_name}"
    
# hellow workd