from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import Http404, HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from .models import TrainingPlan


# -----------------------------------------------------------
# Yardımcılar
# -----------------------------------------------------------

def _plan_to_dict(p: TrainingPlan) -> Dict[str, Any]:
    """
    API çıktısı için TrainingPlan -> dict dönüştürücü.
    Hem ISO 'date' alanını hem de month/day eşdeğerlerini üretir.
    Frontend (visual_plan.html) iki formatı da anlayabilir.
    """
    start = p.start_datetime
    end = p.end_datetime

    # ISO formatlı tarih/saatler
    start_iso = start.isoformat() if start else None
    end_iso = end.isoformat() if end else None

    # Gün/Ay (kolon yerleşimi için)
    month = start.month if start else None
    day = start.day if start else None

    # Süre (saat) — Training.duration_hours varsa onu, yoksa yaklaşık fark (saat)
    duration_hours: Optional[int] = None
    if getattr(p.training, "duration_hours", None):
        try:
            duration_hours = int(p.training.duration_hours)
        except Exception:
            duration_hours = None
    if duration_hours is None and start and end:
        delta = end - start
        duration_hours = max(1, int(delta.total_seconds() // 3600))

    return {
        "id": p.id,
        "training_id": p.training_id,
        "training_title": getattr(p.training, "title", None),
        "training_code": getattr(p.training, "code", None),
        "title": getattr(p.training, "title", None) or f"Plan #{p.id}",
        "status": p.status,
        "delivery": p.delivery,
        "location": p.location or "",
        "trainer": p.instructor_name or "",
        "capacity": p.capacity,
        "date": start_iso,                 # ISO (frontend bunu da kullanabilir)
        "date_end": end_iso,
        "date_display": start.strftime("%d.%m.%Y %H:%M") if start else "",
        "month": month,                    # 1..12
        "day": day,                        # 1..31
        "duration_hours": duration_hours,
    }


def _year_bounds(year: int):
    """Verilen yılın başlangıç ve bitiş sınırları (timezone-aware)."""
    tz = timezone.get_current_timezone()
    start = tz.localize(datetime(year, 1, 1, 0, 0, 0))
    end = tz.localize(datetime(year + 1, 1, 1, 0, 0, 0))
    return start, end


# -----------------------------------------------------------
# HTML View'lar
# -----------------------------------------------------------

def plans_page(request: HttpRequest) -> HttpResponse:
    """
    Basit plan listesi (debug/yardım sayfası).
    Şablon yoksa kullanıcıya bilgilendirici bir mesaj gösterir.
    """
    template_name = "trainings/plans_page.html"
    try:
        return render(request, template_name, {})
    except Exception:
        # Şablon henüz yoksa, basit bir bilgi mesajı dönelim.
        return HttpResponse(
            "<h1>Eğitim Planları</h1>"
            "<p>Plan sayfası şablonu bulunamadı. "
            "<code>templates/trainings/plans_page.html</code> oluşturabilirsiniz.</p>"
            "<ul>"
            "<li><a href='/api/plans/'>/api/plans/</a></li>"
            "<li><a href='/api/plan-search/?q=excel'>/api/plan-search/?q=excel</a></li>"
            "<li><a href='/api/calendar-year/?year=2025'>/api/calendar-year/?year=2025</a></li>"
            "</ul>",
            content_type="text/html",
        )


@login_required
def visual_plan(request: HttpRequest) -> HttpResponse:
    """
    Görsel eğitim planı panosu — ay sütunları, kartlar.
    Frontend JS, /api/calendar-year/ endpoint'inden veriyi çeker.
    """
    return render(request, "trainings/visual_plan.html", {})


# -----------------------------------------------------------
# API'ler
# -----------------------------------------------------------

def api_plan_list(request: HttpRequest) -> JsonResponse:
    """
    Tüm planlar (opsiyonel filtreler):
      - ?year=YYYY   → ilgili yıl içinde
      - ?q=metin     → eğitim başlığı/kodu/lokasyon/eğitmen arama
    """
    qs = TrainingPlan.objects.select_related("training").all()

    year = request.GET.get("year")
    if year and year.isdigit():
        y = int(year)
        start, end = _year_bounds(y)
        qs = qs.filter(start_datetime__gte=start, start_datetime__lt=end)

    q = request.GET.get("q")
    if q:
        qs = qs.filter(
            Q(training__title__icontains=q)
            | Q(training__code__icontains=q)
            | Q(location__icontains=q)
            | Q(instructor_name__icontains=q)
        )

    qs = qs.order_by("start_datetime", "id")
    data = [_plan_to_dict(p) for p in qs]
    return JsonResponse(data, safe=False)


def api_plan_detail(request: HttpRequest, pk: int) -> JsonResponse:
    """Tek plan detayı."""
    p = get_object_or_404(TrainingPlan.objects.select_related("training"), pk=pk)
    return JsonResponse(_plan_to_dict(p))


def api_plan_search(request: HttpRequest) -> JsonResponse:
    """Arama kısa yolu (plan listesi ile aynı, sadece ?q zorunlu)."""
    q = (request.GET.get("q") or "").strip()
    if not q:
        return JsonResponse([], safe=False)

    qs = (
        TrainingPlan.objects.select_related("training")
        .filter(
            Q(training__title__icontains=q)
            | Q(training__code__icontains=q)
            | Q(location__icontains=q)
            | Q(instructor_name__icontains=q)
        )
        .order_by("start_datetime", "id")
    )
    return JsonResponse([_plan_to_dict(p) for p in qs], safe=False)


def api_calendar_year(request: HttpRequest) -> JsonResponse:
    """
    Yıllık takvim: /api/calendar-year/?year=2025
    Frontend ay sütunlarını bununla dolduruyor.
    DÖNÜŞ: [_plan_to_dict(...), ...]  (hem 'date' hem 'month'/'day' alanları mevcut)
    """
    year_str = request.GET.get("year")
    if not (year_str and year_str.isdigit()):
        y = timezone.localtime().year
    else:
        y = int(year_str)

    start, end = _year_bounds(y)
    qs = (
        TrainingPlan.objects.select_related("training")
        .filter(start_datetime__gte=start, start_datetime__lt=end)
        .order_by("start_datetime", "id")
    )
    data = [_plan_to_dict(p) for p in qs]
    return JsonResponse(data, safe=False)
