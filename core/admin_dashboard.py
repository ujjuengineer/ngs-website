"""Admin dashboard data for Plotly charts on /admin/."""

from datetime import timedelta

from django.db.models import Count, Sum
from django.utils import timezone

from .models import CompanyCertificate, ContactMessage, DailyReport


def _fmt_int(value):
    return f"{value:,}" if value is not None else "0"


def _top_n_with_other(rows, label_key, value_key, n=6, other_label="Other"):
    """Keep top N slices; fold the rest into Other for cleaner pies."""
    top = rows[:n]
    rest = rows[n:]
    labels = [row[label_key] for row in top]
    values = [row[value_key] for row in top]
    if rest:
        labels.append(other_label)
        values.append(sum(row[value_key] for row in rest))
    return labels, values


def dashboard_callback(request, context):
    reports = DailyReport.objects.all()

    total_reports = reports.count()
    agg = reports.aggregate(
        pages=Sum("num_of_page"),
        deeds=Sum("num_of_deed"),
    )
    total_pages = agg["pages"] or 0
    total_deeds = agg["deeds"] or 0

    # Workflow completion rates (not raw counts that make Scanning dominate)
    workflow_stages = [
        ("PDF", reports.filter(pdf_deed=True).count()),
        ("Indexing", reports.filter(indexing=True).count()),
        ("Uploading", reports.filter(uploading=True).count()),
        ("QC", reports.filter(QC=True).count()),
        ("Metadata", reports.filter(metadata=True).count()),
        ("Pending", reports.filter(pdf_deed=False).count()),
    ]

    district_labels = dict(DailyReport.DISTRICT_CHOICES)
    district_rows = list(
        reports.exclude(district="")
        .values("district")
        .annotate(count=Count("id"))
        .order_by("-count")
    )
    chart_districts = {
        "labels": [
            district_labels.get(row["district"], row["district"].title())
            for row in district_rows
        ],
        "counts": [row["count"] for row in district_rows],
    }

    thirty_days_ago = timezone.localdate() - timedelta(days=29)
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

    employee_rows = [
        {
            "label": (row["name"] or "").title(),
            "pages": row["pages"] or 0,
        }
        for row in reports.exclude(name="")
        .values("name")
        .annotate(pages=Sum("num_of_page"))
        .order_by("-pages")[:12]
    ]
    emp_labels, emp_pages = _top_n_with_other(employee_rows, "label", "pages", n=6)
    chart_employees = {"labels": emp_labels, "pages": emp_pages}

    year_rows = list(
        reports.exclude(year="")
        .values("year")
        .annotate(count=Count("id"), pages=Sum("num_of_page"))
        .order_by("year")[:10]
    )
    chart_years = {
        "labels": [row["year"] for row in year_rows],
        "counts": [row["count"] for row in year_rows],
        "pages": [row["pages"] or 0 for row in year_rows],
    }

    unread_messages = ContactMessage.objects.filter(is_read=False).count()
    total_certificates = CompanyCertificate.objects.count()
    active_districts = reports.exclude(district="").values("district").distinct().count()
    done_meta = reports.filter(metadata=True).count()
    completion_pct = round((done_meta / total_reports) * 100) if total_reports else 0

    context.update(
        {
            "dashboard_kpis": [
                {
                    "label": "Reports",
                    "value": _fmt_int(total_reports),
                    "hint": "volumes",
                    "icon": "description",
                },
                {
                    "label": "Pages",
                    "value": _fmt_int(total_pages),
                    "hint": "processed",
                    "icon": "menu_book",
                },
                {
                    "label": "Deeds",
                    "value": _fmt_int(total_deeds),
                    "hint": "recorded",
                    "icon": "folder_open",
                },
                {
                    "label": "Districts",
                    "value": _fmt_int(active_districts),
                    "hint": "active",
                    "icon": "location_on",
                },
                {
                    "label": "Complete",
                    "value": f"{completion_pct}%",
                    "hint": "to metadata",
                    "icon": "task_alt",
                },
                {
                    "label": "Inbox",
                    "value": _fmt_int(unread_messages),
                    "hint": f"{total_certificates} certs",
                    "icon": "mail",
                },
            ],
            "chart_workflow": {
                "labels": [stage for stage, _ in workflow_stages],
                "values": [count for _, count in workflow_stages],
            },
            "chart_districts": chart_districts,
            "chart_timeline": chart_timeline,
            "chart_employees": chart_employees,
            "chart_years": chart_years,
        }
    )
    return context
