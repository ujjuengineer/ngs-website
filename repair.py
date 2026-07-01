import os
import django

# Setup Django environment manually for an external script
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ngs_website.settings') # Verify your settings path match
django.setup()

from django.contrib.auth import get_user_model
from core.models import PDFRecord, IndexingRecord, UploadingRecord, QCRecord, MetadataRecord

User = get_user_model()

rinki_user = User.objects.filter(username__iexact="RINKI").first()
ujjwal_user = User.objects.filter(username__iexact="ujjwalkumar").first()
admin_fallback = User.objects.filter(is_superuser=True).first()
default_fallback = rinki_user if rinki_user else admin_fallback

sub_models = [PDFRecord, IndexingRecord, UploadingRecord, QCRecord, MetadataRecord]

print("Starting repair for empty created_by fields...")

for Model in sub_models:
    empty_records = Model.objects.filter(created_by__isnull=True)
    count = empty_records.count()
    print(f"Fixing {count} empty rows inside {Model.__name__}...")
    
    for record in empty_records:
        emp_name = (record.name or "").upper()
        
        if "RINKI" in emp_name:
            record.created_by = rinki_user if rinki_user else default_fallback
        elif "UJJWAL" in emp_name:
            record.created_by = ujjwal_user if ujjwal_user else default_fallback
        else:
            record.created_by = default_fallback
            
        record.save()

print("Repair complete! Refresh your admin panel page.")