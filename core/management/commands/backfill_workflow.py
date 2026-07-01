from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from core.models import DailyReport
from core.utils import sync_workflow_records # Imported from utils.py now!

User = get_user_model()

class Command(BaseCommand):
    help = "One-time backfill to sync historical workflow checkboxes to new sub-models with a specific user fallback"

    def handle(self, *args, **options):
        all_reports = DailyReport.objects.all()
        total = all_reports.count()
        
        # 1. Look for the user 'RINKI' as our primary fallback
        rinki_user = User.objects.filter(username__iexact="RINKI").first()
        
        # 2. Ultimate safety fallback (in case 'RINKI' doesn't exist in a local/test database)
        system_admin = User.objects.filter(is_superuser=True).first()
        ultimate_fallback = rinki_user if rinki_user else system_admin

        self.stdout.write(self.style.WARNING(f"Starting backfill for {total} reports..."))

        for index, report in enumerate(all_reports, start=1):
            assigned_user = ultimate_fallback
            
            # If the report has an author name string, try to find an exact match
            if report.name:
                matched_user = User.objects.filter(username__iexact=report.name).first()
                if matched_user:
                    assigned_user = matched_user
            
            # 3. Synchronize records using our core utility function
            sync_workflow_records(report, assigned_user)
            
            # 4. Retain original text name string if it was uniquely written
            if report.name:
                if report.pdf_deed: report.pdf_records.update(name=report.name)
                if report.indexing: report.indexing_records.update(name=report.name)
                if report.uploading: report.uploading_records.update(name=report.name)
                if report.QC: report.qc_records.update(name=report.name)
                if report.metadata: report.metadata_records.update(name=report.name)

            # 5. Handle empty timestamps safely
            report_timestamp = report.created_at if report.created_at else timezone.now()
            if report.pdf_deed: report.pdf_records.update(created_at=report_timestamp)
            if report.indexing: report.indexing_records.update(created_at=report_timestamp)
            if report.uploading: report.uploading_records.update(created_at=report_timestamp)
            if report.QC: report.qc_records.update(created_at=report_timestamp)
            if report.metadata: report.metadata_records.update(created_at=report_timestamp)

            if index % 50 == 0 or index == total:
                self.stdout.write(f"Processed {index}/{total} records...")

        self.stdout.write(self.style.SUCCESS(f"Backfill complete! Handled missing items with fallback user: {ultimate_fallback}"))