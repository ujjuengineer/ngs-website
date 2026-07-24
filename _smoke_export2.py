import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ngs_website.settings")
django.setup()

from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from core.models import DailyReport

User = get_user_model()
user, _ = User.objects.get_or_create(
    username="smoke_export2",
    defaults={"is_staff": True, "is_superuser": True, "email": "smoke_export2@example.com"},
)
user.is_staff = True
user.is_superuser = True
user.set_password("smoke-pass-123")
user.save()

DailyReport.objects.create(location="SHERGHATI", name="Alice", year="2020", volume_num="V1", num_of_page=10, num_of_deed=2, pdf_deed=True)

client = Client()
client.force_login(user)

print("csv url:", reverse("admin:core_dailyreport_export_csv"))
print("xlsx url:", reverse("admin:core_dailyreport_export_xlsx"))

r = client.get("/admin/core/dailyreport/")
b = r.content.decode("utf-8", errors="replace")
print("list -> status:", r.status_code)
print("  <details class=\"ngs-dr-export\">:", "<details class=\"ngs-dr-export\">" in b)
print("  <summary class=\"ngs-dr-btn ngs-dr-btn-ghost\":", "<summary class=\"ngs-dr-btn" in b)
print("  csv link present:", "/admin/core/dailyreport/export/csv/" in b)
print("  xlsx link present:", "/admin/core/dailyreport/export/xlsx/" in b)
print("  no x-cloak on export:", "x-cloak" not in b.split("ngs-dr-export")[1].split("</details>")[0])

r_csv = client.get("/admin/core/dailyreport/export/csv/")
print("csv endpoint -> status:", r_csv.status_code, r_csv["Content-Type"])

r_xlsx = client.get("/admin/core/dailyreport/export/xlsx/")
print("xlsx endpoint -> status:", r_xlsx.status_code, r_xlsx["Content-Type"])

DailyReport.objects.filter(name="ALICE").delete()
User.objects.filter(username="smoke_export2").delete()
print("cleaned")
