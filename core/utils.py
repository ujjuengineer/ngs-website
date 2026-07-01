from django.utils import timezone
from .models import PDFRecord, IndexingRecord, UploadingRecord, QCRecord, MetadataRecord

def sync_workflow_records(report_instance, user_instance):
    """
    Synchronizes the sub-records using the active User instance.
    Sets both the ForeignKey (created_by) and the string field (name).
    """
    now = timezone.now()
    
    # Generate the text string representation from user profile data
    full_name = user_instance.get_full_name().strip()
    operator_name = full_name if full_name else user_instance.username

    # --- 1. PDF Deed ---
    if report_instance.pdf_deed:
        PDFRecord.objects.get_or_create(
            daily_report=report_instance, 
            defaults={'created_by': user_instance, 'name': operator_name, 'created_at': now}
        )
    else:
        PDFRecord.objects.filter(daily_report=report_instance).delete()

    # --- 2. Indexing ---
    if report_instance.indexing:
        IndexingRecord.objects.get_or_create(
            daily_report=report_instance, 
            defaults={'created_by': user_instance, 'name': operator_name, 'created_at': now}
        )
    else:
        IndexingRecord.objects.filter(daily_report=report_instance).delete()

    # --- 3. Uploading ---
    if report_instance.uploading:
        UploadingRecord.objects.get_or_create(
            daily_report=report_instance, 
            defaults={'created_by': user_instance, 'name': operator_name, 'created_at': now}
        )
    else:
        UploadingRecord.objects.filter(daily_report=report_instance).delete()

    # --- 4. QC ---
    if report_instance.QC:
        QCRecord.objects.get_or_create(
            daily_report=report_instance, 
            defaults={'created_by': user_instance, 'name': operator_name, 'created_at': now}
        )
    else:
        QCRecord.objects.filter(daily_report=report_instance).delete()

    # --- 5. Metadata ---
    if report_instance.metadata:
        MetadataRecord.objects.get_or_create(
            daily_report=report_instance, 
            defaults={'created_by': user_instance, 'name': operator_name, 'created_at': now}
        )
    else:
        MetadataRecord.objects.filter(daily_report=report_instance).delete()