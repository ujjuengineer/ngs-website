from django.db import migrations


LOCATION_TO_DISTRICT = {
    "SHERGHATI": "GAYA", "TEKARI": "GAYA", "AURANGABAD": "GAYA",
    "JAHANABAD": "GAYA", "NAWADA": "GAYA",
    "NALANDA": "NALANDA", "HILSA": "NALANDA",
    "DARBHANGA": "DARBHANGA", "BAHERA": "DARBHANGA", "KAMTAUL": "DARBHANGA",
    "BENIPATTI": "DARBHANGA", "PHULPARAS": "DARBHANGA",
    "JHANJHARPUR": "DARBHANGA", "JAINAGAR": "DARBHANGA", "KHAJAULI": "DARBHANGA",
    "SAMASTIPUR": "DARBHANGA", "ROSARA": "DARBHANGA",
    "DALSINGHSARAI": "DARBHANGA", "KISHANPUR": "DARBHANGA",
}


def forwards(apps, schema_editor):
    DailyReport = apps.get_model("core", "DailyReport")
    for report in DailyReport.objects.all():
        mapped = LOCATION_TO_DISTRICT.get(report.location, "")
        if mapped and report.district != mapped:
            report.district = mapped
            report.save(update_fields=["district"])


def backwards(apps, schema_editor):
    DailyReport = apps.get_model("core", "DailyReport")
    DailyReport.objects.update(district="")


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0017_dailyreport_district"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
