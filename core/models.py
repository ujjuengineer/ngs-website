from django.db import models
import uuid
from django.utils import timezone


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
    

class DailyReport(models.Model):
    # Location choices
    LOCATION_CHOICES = [
        ('SHERGHATI', 'Sherghati'),
        ('TEKARI', 'Tekari'),
        ('AURANGABAD', 'Aurangabad'),
        ('JAHANABAD', 'Jahanabad'),
        ('NAWADA', 'Nawada'),

        ('NALANDA', 'Nalanda'),
        ('HILSA', 'Hilsa'),
    ]

    # Date field - auto sets to current date
    date = models.DateField(default=timezone.now, verbose_name="Report Date")
    
    # Location drop-down selection
    location = models.CharField(
        max_length=50, 
        choices=LOCATION_CHOICES, 
        verbose_name="Location"
    )
    
    # Name - character field (will auto-capitalize on save)
    name = models.CharField(max_length=255, verbose_name="Employee Name")
    
    # Year and Volume fields
    year = models.CharField(max_length=9, verbose_name="Year")
    volume_num = models.CharField(max_length=100, verbose_name="Volume Number")
    
    # Quantitative tracking fields
    num_of_deed = models.IntegerField(verbose_name="Number of Deeds")
    num_of_page = models.IntegerField(verbose_name="Number of Pages")
    
    # Status / Workflow progress boolean fields
    pdf_deed = models.BooleanField(default=False, verbose_name="PDF (Deed)")
    indexing = models.BooleanField(default=False, verbose_name="Indexing")
    uploading = models.BooleanField(default=False, verbose_name="Uploading")
    QC = models.BooleanField(default=False, verbose_name="QC")
    metadata = models.BooleanField(default=False, verbose_name="Meta Data")

    class Meta:
        verbose_name = "Daily Report"
        verbose_name_plural = "Daily Reports"
        ordering = ['-date', 'location']

    def save(self, *args, **kwargs):
        # Automatically capitalize the name field before writing to database
        if self.name:
            self.name = self.name.upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.date} - {self.name} ({self.location})"
    
    # redeploying