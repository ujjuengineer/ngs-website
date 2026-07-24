"""Admin dashboard data for Plotly charts on /admin/."""

from datetime import timedelta

from django.db.models import Count, Sum
from django.utils import timezone

from .models import CompanyCertificate, ContactMessage, DailyReport


def _fmt_int(value):
    return f"{value:,}" if value is not None else "0"


def dashboard_callback(request, context):
    reports = DailyReport.objects.all()
    location_labels = dict(DailyReport.LOCATION_CHOICES)

    total_reports = reports.count()
    agg = reports.aggregate(
        pages=Sum("num_of_page"),
        deeds=Sum("num_of_deed"),
    )
    total_pages = agg["pages"] or 0
    total_deeds = agg["deeds"] or 0

    workflow_stages = [
        ("Scanning", total_reports),
        ("PDF Deed", reports.filter(pdf_deed=True).count()),
        ("Indexing", reports.filter(indexing=True).count()),
        ("Uploading", reports.filter(uploading=True).count()),
        ("QC", reports.filter(QC=True).count()),
        ("Metadata", reports.filter(metadata=True).count()),
    ]

    location_rows = list(
        reports.values("location")
        .annotate(count=Count("id"), pages=Sum("num_of_page"))
        .order_by("-count")
    )
    chart_locations = {
        "labels": [
            location_labels.get(row["location"], row["location"].title())
            for row in location_rows
        ],
        "counts": [row["count"] for row in location_rows],
        "pages": [row["pages"] or 0 for row in location_rows],
    }

    thirty_days_ago = timezone.localdate() - timedelta(days=30)
    timeline_rows = list(
        reports.filter(date__gte=thirty_days_ago)
        .values("date")
        .annotate(count=Count("id"), pages=Sum("num_of_page"))
        .order_by("date")
    )
    chart_timeline = {
        "labels": [row["date"].strftime("%d %b") for row in timeline_rows],
        "counts": [row["count"] for row in timeline_rows],
        "pages": [row["pages"] or 0 for row in timeline_rows],
    }

    employee_rows = list(
        reports.exclude(name="")
        .values("name")
        .annotate(pages=Sum("num_of_page"), count=Count("id"))
        .order_by("-pages")[:10]
    )
    chart_employees = {
        "labels": [row["name"].title() for row in employee_rows],
        "pages": [row["pages"] or 0 for row in employee_rows],
        "counts": [row["count"] for row in employee_rows],
    }

    year_rows = list(
        reports.exclude(year="")
        .values("year")
        .annotate(count=Count("id"), pages=Sum("num_of_page"))
        .order_by("-year")[:8]
    )
    chart_years = {
        "labels": [row["year"] for row in reversed(year_rows)],
        "counts": [row["count"] for row in reversed(year_rows)],
        "pages": [row["pages"] or 0 for row in reversed(year_rows)],
    }

    unread_messages = ContactMessage.objects.filter(is_read=False).count()
    total_certificates = CompanyCertificate.objects.count()
    active_locations = reports.values("location").distinct().count()

    context.update(
        {
            "dashboard_kpis": [
                {
                    "label": "Daily Reports",
                    "value": _fmt_int(total_reports),
                    "hint": "Total volumes logged",
                    "icon": "description",
                },
                {
                    "label": "Pages Processed",
                    "value": _fmt_int(total_pages),
                    "hint": "Across all reports",
                    "icon": "menu_book",
                },
                {
                    "label": "Deeds Recorded",
                    "value": _fmt_int(total_deeds),
                    "hint": "Where deed count is filled",
                    "icon": "folder_open",
                },
                {
                    "label": "Active Locations",
                    "value": _fmt_int(active_locations),
                    "hint": "Districts with reports",
                    "icon": "location_on",
                },
                {
                    "label": "Certificates",
                    "value": _fmt_int(total_certificates),
                    "hint": "Issued company certificates",
                    "icon": "verified",
                },
                {
                    "label": "Unread Messages",
                    "value": _fmt_int(unread_messages),
                    "hint": "Contact form inquiries",
                    "icon": "mail",
                },
            ],
            "chart_workflow": {
                "labels": [stage for stage, _ in workflow_stages],
                "values": [count for _, count in workflow_stages],
            },
            "chart_locations": chart_locations,
            "chart_timeline": chart_timeline,
            "chart_employees": chart_employees,
            "chart_years": chart_years,
        }
    )
    return context
