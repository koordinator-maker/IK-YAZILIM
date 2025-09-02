from collections import defaultdict
from datetime import datetime
from typing import Dict, List

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import get_user_model
from django.db.models import Prefetch
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from .models import TrainingPlan, TrainingPlanAttendee

User = get_user_model()


def _week_of(dt) -> int:
    """
    ISO haftası. 53. hafta gelirse 52'ye sabitleriz ki grid 1..52 kalsın.
    """
    try:
        w = dt.isocalendar().week
        return 52 if w == 53 else w
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
    Hücrede o haftadaki plan(lar) küçük birer etiket olarak görünür.
    Hover: tarih + eğitmen + katılımcılar
    Tıkla: admin change sayfasına gider.
    """
    year = int(request.GET.get("year") or datetime.now().year)

    plans_qs = (
        TrainingPlan.objects.select_related("training")
        .prefetch_related(
            Prefetch(
                "plan_attendees",
                queryset=TrainingPlanAttendee.objects.select_related("user"),
            )
        )
    )

    # Sadece seçilen yıl
    plans = [
        p for p in plans_qs
        if getattr(p, "start_datetime", None) and getattr(p, "start_datetime").year == year
    ]

    # row_map[title][week] -> List[plan_dict]
    row_map: Dict[str, Dict[int, List[dict]]] = defaultdict(lambda: defaultdict(list))

    for p in plans:
        title = _title(p)
        week = _week_of(getattr(p, "start_datetime"))
        # Tarih metni
        when = ""
        try:
            sd = getattr(p, "start_datetime")
            ed = getattr(p, "end_datetime")
            if sd and ed:
                when = f"{sd} → {ed}"
            elif sd:
                when = f"{sd}"
        except Exception:
            pass

        # Eğitmen
        trainer = getattr(p, "instructor_name", None) or "-"

        # Katılımcılar
        attendees: List[str] = []
        for a in p.plan_attendees.all():
            u = a.user
            if not u:
                continue
            try:
                display = u.get_full_name() or u.username
            except Exception:
                display = getattr(u, "username", None) or str(u)
            attendees.append(display)
        attendees_txt = ", ".join(attendees) if attendees else "-"

        row_map[title][week].append(
            {
                "id": p.id,
                "when": when,
                "trainer": trainer,
                "attendees_txt": attendees_txt,
                "admin_link": f"/admin/trainings/trainingplan/{p.id}/change/",
            }
        )

    # Template dostu yapı:
    # rows = [ { "title": str, "cells": [ List[plan_dict], ... 52 eleman ] }, ... ]
    rows: List[dict] = []
    for title in sorted(row_map.keys(), key=lambda s: s.lower()):
        week_plans = row_map[title]
        cells: List[List[dict]] = [week_plans.get(w, []) for w in range(1, 53)]
        rows.append({"title": title, "cells": cells})

    ctx = {
        "year": year,
        "weeks": list(range(1, 53)),
        "rows": rows,
    }
    return render(request, "trainings/plans/yearly_board.html", ctx)
