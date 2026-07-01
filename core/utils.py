from .models import PDFRecord, IndexingRecord, UploadingRecord, QCRecord, MetadataRecord

def create_workflow_records_if_checked(report_instance, operator_name):
    """
    Checks the boolean flags on a DailyReport and creates the matching 
    sub-records using the actual person performing the action.
    """
    if report_instance.pdf_deed:
        PDFRecord.objects.get_or_create(daily_report=report_instance, defaults={'name': operator_name})
        
    if report_instance.indexing:
        IndexingRecord.objects.get_or_create(daily_report=report_instance, defaults={'name': operator_name})
        
    if report_instance.uploading:
        UploadingRecord.objects.get_or_create(daily_report=report_instance, defaults={'name': operator_name})
        
    if report_instance.QC:
        QCRecord.objects.get_or_create(daily_report=report_instance, defaults={'name': operator_name})
        
    if report_instance.metadata:
        MetadataRecord.objects.get_or_create(daily_report=report_instance, defaults={'name': operator_name})