# Rev: 2025-09-24 14:05 r2
from __future__ import annotations
from datetime import date, datetime
from typing import Any, Dict, List

from django.http import JsonResponse, Http404, HttpRequest
from django.shortcuts import render, get_object_or_404
from django.db.models import Q
from django.utils.timezone import is_aware

# Admin URL'lerinde /admin/trainings/trainingplan/<id>/change/ gördük:
# Model sınıfı büyük olasılıkla TrainingPlan.
from trainings.models import TrainingPlan  # sende adı farklıysa bunu düzelt

# ---------------- helpers ----------------
def _to_iso(d: Any) -> str:
    if isinstance(d, datetime):
        if is_aware(d):
            d = d.astimezone().replace(tzinfo=None)
        d = d.date()
    if isinstance(d, date):
        return d.isoformat()
    return str(d or "")

def _title_and_code(p: TrainingPlan) -> (str, str):
    t = getattr(p, "training", None)
    title = ((getattr(t, "name", None) or getattr(t, "title", None)) or (str(t) if t else str(p)))
    code = getattr(t, "code", "") or ""
    return title, code

def _participants_list(p: TrainingPlan) -> List[str]:
    out: List[str] = []
    rel = None
    if hasattr(p, "participants"):
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
    start = getattr(p, "start", None) or getattr(p, "start_date", None)
    end = getattr(p, "end", None) or getattr(p, "end_date", None) or start
    location = getattr(p, "location", "") or getattr(p, "place", "") or ""
    capacity = (
        getattr(p, "capacity", None)
        or getattr(p, "quota", None)
        or getattr(getattr(p, "training", None), "capacity", None)
        or 0
    )
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
    return render(request, "trainings/plans_page.html")

# ---------------- JSON APIs ----------------
def plan_list(request: HttpRequest) -> JsonResponse:
    """GET /api/plans/?year=YYYY → {source:'db', results:[...] }"""
    year = request.GET.get("year")
    qs = TrainingPlan.objects.all().select_related("training")
    if year and year.isdigit():
        y = int(year)
        qs = qs.filter(Q(start__year=y) | Q(end__year=y))
    data = [_serialize_plan(p) for p in qs.order_by("start", "end", "pk")]
    return JsonResponse({"source": "db", "results": data})

def plan_detail(request: HttpRequest, pk: int) -> JsonResponse:
    p = get_object_or_404(TrainingPlan.objects.select_related("training"), pk=pk)
    return JsonResponse(_serialize_plan(p))

def plan_search(request: HttpRequest) -> JsonResponse:
    q = (request.GET.get("q") or "").strip()
    qs = TrainingPlan.objects.all().select_related("training")
    if q:
        qs = qs.filter(
            Q(training__name__icontains=q) |
            Q(training__title__icontains=q) |
            Q(training__code__icontains=q)
        )
    data = [_serialize_plan(p) for p in qs.order_by("start", "end", "pk")[:50]]
    return JsonResponse({"results": data})

def calendar_year(request: HttpRequest) -> JsonResponse:
    y = int(request.GET.get("year", "0") or 0)
    if not y:
        return JsonResponse({"year": y, "months": {str(i): [] for i in range(1, 13)}, "total": 0})
    qs = TrainingPlan.objects.filter(Q(start__year=y) | Q(end__year=y)).order_by("start")
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
