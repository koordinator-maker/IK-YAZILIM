# Rev: 2025-09-24 18:35 r3 – start_datetime/end_datetime uyumu + plan_attendees

from __future__ import annotations
from datetime import date, datetime
from typing import Any, Dict, List

from django.http import JsonResponse, HttpRequest
from django.shortcuts import render, get_object_or_404
from django.db.models import Q
from django.utils.timezone import is_aware

# Model sınıfı: /admin/trainings/trainingplan/<id>/change/ ekranından geliyor
from trainings.models import TrainingPlan


# ---------------- yardımcılar ----------------
def _to_iso(d: Any) -> str:
    """date/datetime -> 'YYYY-MM-DD' (sadece gün)."""
    if isinstance(d, datetime):
        if is_aware(d):
            d = d.astimezone().replace(tzinfo=None)
        d = d.date()
    if isinstance(d, date):
        return d.isoformat()
    return ""


# Modeldeki alan adlarını dinamik tespit et
START_FIELD = (
    "start_datetime"
    if hasattr(TrainingPlan, "start_datetime")
    else ("start_date" if hasattr(TrainingPlan, "start_date") else "start")
)
END_FIELD = (
    "end_datetime"
    if hasattr(TrainingPlan, "end_datetime")
    else ("end_date" if hasattr(TrainingPlan, "end_date") else "end")
)


def _title_and_code(p: TrainingPlan) -> (str, str):
    t = getattr(p, "training", None)
    title = (
        getattr(t, "name", None)
        or getattr(t, "title", None)
        or (str(t) if t is not None else str(p))
    )
    code = getattr(t, "code", "") or ""
    return title, code


def _participants_list(p: TrainingPlan) -> List[str]:
    out: List[str] = []
    rel = None
    # projene göre farklı isimler olabilir:
    if hasattr(p, "plan_attendees"):
        rel = getattr(p, "plan_attendees")
    elif hasattr(p, "participants"):
        rel = getattr(p, "participants")
    elif hasattr(p, "attendees"):
        rel = getattr(p, "attendees")
    if rel:
        for u in rel.all():
            fn = getattr(u, "get_full_name", None)
            name = fn() if callable(fn) and fn() else getattr(u, "username", str(u))
            out.append(name)
    return out


def _serialize_plan(p: TrainingPlan) -> Dict[str, Any]:
    title, code = _title_and_code(p)
    start = getattr(p, START_FIELD, None)
    end = getattr(p, END_FIELD, None) or start
    location = getattr(p, "location", "") or getattr(p, "place", "") or ""
    capacity = getattr(p, "capacity", None) or getattr(p, "quota", None) or 0

    return {
        "id": p.pk,
        "title": title,
        "code": code,
        "start": _to_iso(start),
        "end": _to_iso(end),
        "location": location,
        "capacity": capacity,
        "participants": _participants_list(p),
    }


# ---------------- HTML ----------------
def plans_page(request: HttpRequest):
    """GET /plans/ → yıllık matris HTML"""
    return render(request, "trainings/plans_page.html")


# ---------------- JSON APIs ----------------
def plan_list(request: HttpRequest) -> JsonResponse:
    """GET /api/plans/?year=YYYY → {results:[...]} (DB’den)"""
    year = request.GET.get("year")
    qs = TrainingPlan.objects.all().select_related("training")

    if year and year.isdigit():
        y = int(year)
        start_lookup = f"{START_FIELD}__year"
        end_lookup = f"{END_FIELD}__year"
        if hasattr(TrainingPlan, START_FIELD) and hasattr(TrainingPlan, END_FIELD):
            qs = qs.filter(Q(**{start_lookup: y}) | Q(**{end_lookup: y}))
        else:
            # son çare: hiç filtreleme yapma
            pass

    # mevcut alana göre sıralama
    try:
        qs = qs.order_by(START_FIELD, END_FIELD, "pk")
    except Exception:
        qs = qs.order_by("pk")

    data = [_serialize_plan(p) for p in qs]
    return JsonResponse({"results": data})


def plan_detail(request: HttpRequest, pk: int) -> JsonResponse:
    """GET /api/plans/<id>/"""
    p = get_object_or_404(TrainingPlan.objects.select_related("training"), pk=pk)
    return JsonResponse(_serialize_plan(p))


def plan_search(request: HttpRequest) -> JsonResponse:
    """GET /api/plan-search/?q=metin"""
    q = (request.GET.get("q") or "").strip()
    qs = TrainingPlan.objects.all().select_related("training")
    if q:
        qs = qs.filter(
            Q(training__name__icontains=q)
            | Q(training__title__icontains=q)
            | Q(training__code__icontains=q)
        )
    try:
        qs = qs.order_by(START_FIELD, END_FIELD, "pk")
    except Exception:
        qs = qs.order_by("pk")
    data = [_serialize_plan(p) for p in qs[:50]]
    return JsonResponse({"results": data})


def calendar_year(request: HttpRequest) -> JsonResponse:
    """GET /api/calendar-year/?year=YYYY → aylık dağılım (opsiyonel)"""
    y = int(request.GET.get("year", "0") or 0)
    if not y:
        return JsonResponse(
            {"year": y, "months": {str(i): [] for i in range(1, 13)}, "total": 0}
        )

    start_lookup = f"{START_FIELD}__year"
    end_lookup = f"{END_FIELD}__year"
    qs = TrainingPlan.objects.filter(Q(**{start_lookup: y}) | Q(**{end_lookup: y}))
    try:
        qs = qs.order_by(START_FIELD, END_FIELD, "pk")
    except Exception:
        qs = qs.order_by("pk")

    months: Dict[str, list] = {str(i): [] for i in range(1, 13)}
    total = 0
    for p in qs:
        d = _serialize_plan(p)
        try:
            m = int((d["start"] or "0000-01-01").split("-")[1])
        except Exception:
            m = 1
        months[str(m)].append(d)
        total += 1
    return JsonResponse({"year": y, "months": months, "total": total})
