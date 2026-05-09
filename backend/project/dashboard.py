import json

from django.db.models import Count, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone


def dashboard_callback(request, context):
    from apps.courses.models import Course
    from apps.homeworks.models import Attempt
    from apps.payments.models import Payment
    from apps.users.models import User

    now = timezone.now()
    month_ago = now - timezone.timedelta(days=30)

    total_users = User.objects.count()
    total_courses = Course.objects.filter(is_deleted=False).count()
    total_revenue = Payment.objects.filter(status="success").aggregate(s=Sum("total_sum"))["s"] or 0
    pending_reviews = Attempt.objects.filter(status="submitted").count()

    registrations_qs = (
        User.objects.filter(date_joined__gte=month_ago)
        .annotate(date=TruncDate("date_joined"))
        .values("date")
        .annotate(count=Count("id"))
        .order_by("date")
    )
    reg_labels = [str(r["date"]) for r in registrations_qs]
    reg_data = [r["count"] for r in registrations_qs]

    payments_qs = (
        Payment.objects.filter(status="success", paid_at__gte=month_ago)
        .annotate(date=TruncDate("paid_at"))
        .values("date")
        .annotate(total=Sum("total_sum"))
        .order_by("date")
    )
    pay_labels = [str(p["date"]) for p in payments_qs]
    pay_data = [float(p["total"]) for p in payments_qs]

    chart_registrations = json.dumps(
        {
            "labels": reg_labels,
            "datasets": [
                {
                    "label": "Регистрации",
                    "data": reg_data,
                    "borderColor": "#0ea5e9",
                    "backgroundColor": "rgba(14,165,233,0.15)",
                    "fill": True,
                    "tension": 0.4,
                }
            ],
        }
    )

    chart_revenue = json.dumps(
        {
            "labels": pay_labels,
            "datasets": [
                {
                    "label": "Выручка ₽",
                    "data": pay_data,
                    "borderColor": "#22c55e",
                    "backgroundColor": "rgba(34,197,94,0.15)",
                    "fill": True,
                    "tension": 0.4,
                }
            ],
        }
    )

    context.update(
        {
            "kpi": [
                {
                    "title": "Пользователей",
                    "metric": str(total_users),
                    "icon": "person",
                    "footer": "всего зарегистрировано",
                },
                {
                    "title": "Курсов",
                    "metric": str(total_courses),
                    "icon": "menu_book",
                    "footer": "активных курсов",
                },
                {
                    "title": "Выручка",
                    "metric": f"{total_revenue:,.0f} ₽",
                    "icon": "payments",
                    "footer": "успешных платежей",
                },
                {
                    "title": "На проверке",
                    "metric": str(pending_reviews),
                    "icon": "rate_review",
                    "footer": "домашних заданий",
                },
            ],
            "chart_registrations": chart_registrations,
            "chart_revenue": chart_revenue,
        }
    )

    return context
