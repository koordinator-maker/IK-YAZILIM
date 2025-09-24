# Rev: 2025-09-24 13:55 r1
from __future__ import annotations
from datetime import date, datetime
from typing import Any, List

from django.http import JsonResponse, HttpRequest, Http404
from django.db.models import Q
from django.utils.timezone import is_aware

# ⬇️ MODEL ADI: TrainingPlan
# Admin ekranında gördüğünüz "Eğitim Planları" modelinin adı büyük ihtimalle budur.
# Farklıysa sadece bu import satırını düzeltin.
from trainings.models import TrainingPlan  # type: ignore


def _to_iso(d: Any) -> str:
    """date/datetime → 'YYYY-MM-DD' (sadece gün hassasiyeti yeterli)."""
    if isinstance(d, datetime):
        # aware ise naive'a çevirip sadece date al
        if is_aware(d):
            d = d.astimezone().replace(tzinfo=None)
        d = d.date()
    if isinstance(d, date):
        return d.isoformat()
    return str(d)


def _plan_dict(p: TrainingPlan) -> dict:
    t = getattr(p, "training", None)
    title = getattr(t, "name", None) or getattr(t, "title", None) or (str(t) if t else str(p))

    code = getattr(t, "code", "") or ""
    start = getattr(p, "start", None) or getattr(p, "start_date", None)
    end = getattr(p, "end", None) or getattr(p, "end_date", None) or start

    location = getattr(p, "location", "") or getattr(p, "place", "") or ""
    capacity = getattr(p, "capacity", None) or getattr(p, "quota", None) or 0

    # Katılımcılar (alan adı projeden projeye değişebilir)
    parts: List[str] = []
    if hasattr(p, "participants"):
        for u in getattr(p, "participants").all():
            fn = getattr(u, "get_full_name", None)
            parts.append(fn() if callable(fn) and fn() else getattr(u, "username", str(u)))
    elif hasattr(p, "attendees"):
        for u in getattr(p, "attendees").all():
            fn = getattr(u, "get_full_name", None)
            parts.append(fn() if callable(fn) and fn() else getattr(u, "username", str(u)))

    return {
        "id": p.pk,
        "title": title,
        "code": code,
        "start": _to_iso(start),
        "end": _to_iso(end),
        "location": location,
        "capacity": capacity,
        "participants": parts,
    }


def plans_api(request: HttpRequest) -> JsonResponse:
    """GET /api/plans/?year=YYYY  → {results:[...] }"""
    year_str = request.GET.get("year")
    qs = TrainingPlan.objects.all().select_related("training")
    if year_str and year_str.isdigit():
        y = int(year_str)
        qs = qs.filter(Q(start__year=y) | Q(end__year=y))
    data = [_plan_dict(p) for p in qs.order_by("start", "end", "pk")]
    return JsonResponse({"results": data})


def plan_detail_api(request: HttpRequest, pk: int) -> JsonResponse:
    """GET /api/plans/<id>/ → tek plan + katılımcılar"""
    try:
        p = TrainingPlan.objects.select_related("training").get(pk=pk)
    except TrainingPlan.DoesNotExist as e:
        raise Http404(str(e))
    return JsonResponse(_plan_dict(p))


def plan_search_api(request: HttpRequest) -> JsonResponse:
    """GET /api/plan-search/?q=metin"""
    q = request.GET.get("q", "").strip()
    qs = TrainingPlan.objects.all().select_related("training")
    if q:
        qs = qs.filter(
            Q(training__name__icontains=q) |
            Q(training__title__icontains=q) |
            Q(training__code__icontains=q)
        )
    data = [_plan_dict(p) for p in qs.order_by("start", "end", "pk")[:50]]
    return JsonResponse({"results": data})


def calendar_year_api(request: HttpRequest) -> JsonResponse:
    """GET /api/calendar-year/?year=YYYY → yıl/ay bazında toplam adet (isteğe bağlı)"""
    y = int(request.GET.get("year", "0") or 0)
    if not y:
        return JsonResponse({"year": y, "months": {str(i): [] for i in range(1, 13)}, "total": 0})

    qs = TrainingPlan.objects.filter(Q(start__year=y) | Q(end__year=y)).order_by("start")
    months: dict[str, list] = {str(i): [] for i in range(1, 13)}
    total = 0
    for p in qs:
        d = _plan_dict(p)
        # hangi ayda başlıyorsa oraya koy (basit toplama)
        try:
            m = int(d["start"].split("-")[1])
        except Exception:
            m = 1
        months[str(m)].append(d)
        total += 1
    return JsonResponse({"year": y, "months": months, "total": total})
