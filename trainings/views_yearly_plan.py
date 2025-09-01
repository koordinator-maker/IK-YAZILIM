afrom collections import defaultdict
from datetime import datetime
from typing import Dict, List, Tuple

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import get_user_model
from django.db.models import Prefetch
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from .models import TrainingPlan, TrainingPlanAttendee

User = get_user_model()


def _week_of(dt) -> int:
    try:
        return dt.isocalendar().week
    except Exception:
        return 0


def _title(plan: TrainingPlan) -> str:
    t = getattr(plan, "training", None)
    if t:
        return getattr(t, "title", None) or getattr(t, "name", None) or str(t)
    return f"Plan #{plan.pk}"


@staff_member_required
def yearly_plan_board(request: HttpRequest) -> HttpResponse:
    """
    52 haftalık grid: sütunlar hafta(1-52), satırlar eğitim başlığı.
    Hücrede ilgili haftadaki plan(lar) etiket olarak görünür.
    Hover -> tooltip: tarih + eğitmen + katılımcılar
    Tıkla -> admin change sayfası
    """
    year = int(request.GET.get("year") or datetime.now().year)

    plans = (
        TrainingPlan.objects.select_related("training")
        .prefetch_related(
            Prefetch("plan_attendees", queryset=TrainingPlanAttendee.objects.select_related("user"))
        )
    )

    # Sadece seçili yıl
    plans = [p for p in plans if getattr(p, "start_datetime", None) and getattr(p, "start_datetime").year == year]

    # Satırlar = eğitim başlığı
    rows_order: List[str] = []
    row_map: Dict[str, Dict[int, List[TrainingPlan]]] = defaultdict(lambda: defaultdict(list))

    for p in plans:
        title = _title(p)
        week = _week_of(getattr(p, "start_datetime"))
        row_map[title][week].append(p)

    rows_order = sorted(row_map.keys(), key=lambda s: s.lower())

    ctx = {
        "year": year,
        "weeks": list(range(1, 53)),
        "rows_order": rows_order,
        "row_map": row_map,
    }
    return render(request, "trainings/plans/yearly_board.html", ctx)
