from django.db import models
import uuid
from django.utils import timezone
from django.contrib.auth.models import User

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
    LOCATION_CHOICES = [
        ('SHERGHATI', 'Sherghati'),
        ('TEKARI', 'Tekari'),
        ('AURANGABAD', 'Aurangabad'),
        ('JAHANABAD', 'Jahanabad'),
        ('NAWADA', 'Nawada'),
        ('NALANDA', 'Nalanda'),
        ('HILSA', 'Hilsa'),
        ('ROSARA', 'Rosara'),
        ('KISHANPUR', 'Kishanpur'),
        ('DARBHANGA', 'Darbhanga'),
        ('BAHERA', 'Bahera'),
        ('DALSINGHSARAI','Dalsinghsarai'),
        ('BENIPATTI', 'Benipatti'),
        ('PHULPARAS', 'Phulparas'),
        ('JHANJHARPUR', 'Jhanjharpur'),
        ('JAINAGAR', 'Jainagar'),
        ('SAMASTIPUR', 'Samastipur'),
        ('KAMTAUL', 'Kamtaul'),
        ('KHAJAULI', 'Khajauli')
    ]

    date = models.DateField(default=timezone.now, verbose_name="Report Date")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At', null=True, blank=True)
    location = models.CharField(max_length=50, choices=LOCATION_CHOICES, verbose_name="Location")
    name = models.CharField(max_length=255, verbose_name="Employee Name")
    year = models.CharField(max_length=9, verbose_name="Year")
    volume_num = models.CharField(max_length=100, verbose_name="Volume Number")
    
    num_of_page = models.IntegerField(verbose_name="Number of Pages")

    # MADE THIS FIELD OPTIONAL
    num_of_deed = models.IntegerField(verbose_name="Number of Deeds", null=True, blank=True)

    # Workflow progress boolean fields
    scanning = models.BooleanField(default=True, verbose_name="Scanning")
    pdf_deed = models.BooleanField(default=False, verbose_name="PDF (Deed)")
    indexing = models.BooleanField(default=False, verbose_name="Indexing")
    uploading = models.BooleanField(default=False, verbose_name="Uploading")
    QC = models.BooleanField(default=False, verbose_name="QC")
    metadata = models.BooleanField(default=False, verbose_name="Meta Data")
    
    # The presence of a related record below now implies the task is done.

    class Meta:
        verbose_name = "Daily Report"
        verbose_name_plural = "Daily Reports"
        ordering = ['-date', 'location']

    def save(self, *args, **kwargs):
        if self.name:
            self.name = self.name.upper()
        if not self.pk: 
            self.scanning = True
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.year} - {self.volume_num} ({self.location})"



# WORKFLOW STEP MODELS

class PDFRecord(models.Model):
    daily_report = models.ForeignKey(
        DailyReport, 
        on_delete=models.CASCADE, 
        related_name='pdf_records',
        verbose_name="Daily Report"
    )
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        verbose_name="Created By"
    )
    name = models.CharField(max_length=255, verbose_name="Employee Name")
    created_at = models.DateTimeField(
        default=timezone.now, 
        verbose_name="Created At"
    )

    class Meta:
        verbose_name = "PDF Record"
        verbose_name_plural = "PDF Records"

    def save(self, *args, **kwargs):
        if self.name:
            self.name = self.name.upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"PDF for Report #{self.daily_report.id} - By: {self.created_by}"


class IndexingRecord(models.Model):
    daily_report = models.ForeignKey(
        DailyReport, 
        on_delete=models.CASCADE, 
        related_name='indexing_records',
        verbose_name="Daily Report"
    )
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        verbose_name="Indexed By"
    )
    name = models.CharField(max_length=255, verbose_name="Employee Name")
    created_at = models.DateTimeField(
        default=timezone.now, 
        verbose_name="Indexed At"
    )

    class Meta:
        verbose_name = "Indexing Record"
        verbose_name_plural = "Indexing Records"

    def save(self, *args, **kwargs):
        if self.name:
            self.name = self.name.upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Indexing for Report #{self.daily_report.id} - By: {self.created_by}"


class UploadingRecord(models.Model):
    daily_report = models.ForeignKey(
        DailyReport, 
        on_delete=models.CASCADE, 
        related_name='uploading_records',
        verbose_name="Daily Report"
    )
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        verbose_name="Uploaded By"
    )
    name = models.CharField(max_length=255, verbose_name="Employee Name")
    created_at = models.DateTimeField(
        default=timezone.now, 
        verbose_name="Uploaded At"
    )

    class Meta:
        verbose_name = "Uploading Record"
        verbose_name_plural = "Uploading Records"

    def save(self, *args, **kwargs):
        if self.name:
            self.name = self.name.upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Upload for Report #{self.daily_report.id} - By: {self.created_by}"


class QCRecord(models.Model):
    daily_report = models.ForeignKey(
        DailyReport, 
        on_delete=models.CASCADE, 
        related_name='qc_records',
        verbose_name="Daily Report"
    )
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        verbose_name="QC Verified By"
    )
    name = models.CharField(max_length=255, verbose_name="Employee Name")
    created_at = models.DateTimeField(
        default=timezone.now, 
        verbose_name="QC Verified At"
    )

    class Meta:
        verbose_name = "QC Record"
        verbose_name_plural = "QC Records"

    def save(self, *args, **kwargs):
        if self.name:
            self.name = self.name.upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"QC for Report #{self.daily_report.id} - By: {self.created_by}"


class MetadataRecord(models.Model):
    daily_report = models.ForeignKey(
        DailyReport, 
        on_delete=models.CASCADE, 
        related_name='metadata_records',
        verbose_name="Daily Report"
    )
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        verbose_name="Metadata Entered By"
    )
    name = models.CharField(max_length=255, verbose_name="Employee Name")
    created_at = models.DateTimeField(
        default=timezone.now, 
        verbose_name="Metadata Entered At"
    )

    class Meta:
        verbose_name = "Metadata Record"
        verbose_name_plural = "Metadata Records"

    def save(self, *args, **kwargs):
        if self.name:
            self.name = self.name.upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Metadata for Report #{self.daily_report.id} - By: {self.created_by}"

# class DailyReport(models.Model):
    # Location choices
    # LOCATION_CHOICES = [
    #     ('SHERGHATI', 'Sherghati'),
    #     ('TEKARI', 'Tekari'),
    #     ('AURANGABAD', 'Aurangabad'),
    #     ('JAHANABAD', 'Jahanabad'),
    #     ('NAWADA', 'Nawada'),

    #     ('NALANDA', 'Nalanda'),
    #     ('HILSA', 'Hilsa'),
    # ]

    # # Date field - auto sets to current date
    # date = models.DateField(default=timezone.now, verbose_name="Report Date")
    # created_at = models.DateTimeField(
    #     # null=True,
    #     # blank=True,
    #     auto_now_add=True,
    #     verbose_name='Created At'
    # )

    # # Location drop-down selection
    # location = models.CharField(
    #     max_length=50, 
    #     choices=LOCATION_CHOICES, 
    #     verbose_name="Location"
    # )
    
    # # Name - character field (will auto-capitalize on save)
    # name = models.CharField(max_length=255, verbose_name="Employee Name")
    
    # # Year and Volume fields
    # year = models.CharField(max_length=9, verbose_name="Year")
    # volume_num = models.CharField(max_length=100, verbose_name="Volume Number")
    
    # # Quantitative tracking fields
    # num_of_deed = models.IntegerField(verbose_name="Number of Deeds")
    # num_of_page = models.IntegerField(verbose_name="Number of Pages")
    
    # # Status / Workflow progress boolean fields
    # pdf_deed = models.BooleanField(default=False, verbose_name="PDF (Deed)")
    # indexing = models.BooleanField(default=False, verbose_name="Indexing")
    # uploading = models.BooleanField(default=False, verbose_name="Uploading")
    # QC = models.BooleanField(default=False, verbose_name="QC")
    # metadata = models.BooleanField(default=False, verbose_name="Meta Data")

    # class Meta:
    #     verbose_name = "Daily Report"
    #     verbose_name_plural = "Daily Reports"
    #     ordering = ['-date', 'location']

    # def save(self, *args, **kwargs):
    #     # Automatically capitalize the name field before writing to database
    #     if self.name:
    #         self.name = self.name.upper()
    #     super().save(*args, **kwargs)

    # def __str__(self):
    #     return f"{self.date} - {self.name} ({self.location})"
    
    # # redeploying