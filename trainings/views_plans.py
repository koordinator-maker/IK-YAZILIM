# trainings/views_plans.py
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List

from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse, Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET

# İleride Plan modeli eklenecekse buradan import edilecek.
# Şimdilik minimal bir mock/örnek veri katmanı ile çalışıyoruz.
# Mevcut yapıyı bozmamak adına fonksiyon imzaları ve URL adları sabit tutuldu.

__all__ = [
    "plans_page",
    "plan_list",
    "plan_detail",
    "plan_search",
    "calendar_year",
]

# -------------------------------------------------------------------
# Yardımcı: sadece staff/superuser plan API'lerini görsün isterseniz:
def _is_staff(u) -> bool:
    return bool(u and (u.is_staff or u.is_superuser))


# -------------------------------------------------------------------
# HTML Sayfası
@login_required
def plans_page(request: HttpRequest) -> HttpResponse:
    """
    Eğitim Planları ana sayfası (HTML).
    Şablon yoksa geçici minimal bir placeholder render edilir.
    """
    template_candidates = [
        "trainings/plans_page.html",  # varsa proje şablonunuz
    ]
    # Şablon mevcut değilse basit gömülü HTML döndürelim:
    try:
        return render(request, template_candidates[0])
    except Exception:
        return HttpResponse(
            """
            <html><head><title>Planlar</title>
            <style>body{font-family:system-ui;padding:24px}</style>
            </head>
            <body>
              <h1>Eğitim Planları</h1>
              <p>Plan sayfası şablonu bulunamadı. <code>templates/trainings/plans_page.html</code> oluşturabilirsiniz.</p>
              <ul>
                <li><a href="/api/plans/">/api/plans/</a></li>
                <li><a href="/api/plan-search/?q=excel">/api/plan-search/?q=excel</a></li>
                <li><a href="/api/calendar-year/?year=2025">/api/calendar-year/?year=2025</a></li>
              </ul>
            </body></html>
            """,
            content_type="text/html",
            status=200,
        )


# -------------------------------------------------------------------
# JSON API'ler (min. iskelet—mevcut modeli bozmaz)
# Burada şimdilik örnek veri dönüyoruz. Model entegre olduğunda queryset'e bağlayacağız.

_EXAMPLE_PLANS: List[Dict[str, Any]] = [
    {
        "id": 1,
        "title": "Excel İleri Seviye",
        "code": "TR-EXCEL-ADV",
        "start": "2025-09-10",
        "end": "2025-09-11",
        "location": "Toplantı Odası 2",
        "capacity": 16,
        "instructor": "Ahmet Demir",
    },
    {
        "id": 2,
        "title": "İş Sağlığı ve Güvenliği",
        "code": "TR-ISG-01",
        "start": "2025-09-15",
        "end": "2025-09-15",
        "location": "Konferans Salonu",
        "capacity": 60,
        "instructor": "Dış Eğitim Kurumu",
    },
]


@login_required
@require_GET
def plan_list(request: HttpRequest) -> JsonResponse:
    """
    Tüm planların listesi (gelecekte filtre/pagination eklenebilir).
    """
    return JsonResponse({"results": _EXAMPLE_PLANS})


@login_required
@require_GET
def plan_detail(request: HttpRequest, pk: int) -> JsonResponse:
    """
    Tek planın detayı.
    """
    plan = next((p for p in _EXAMPLE_PLANS if p["id"] == pk), None)
    if not plan:
        raise Http404("Plan bulunamadı.")
    return JsonResponse(plan)


@login_required
@require_GET
def plan_search(request: HttpRequest) -> JsonResponse:
    """
    Basit başlık/kod araması: ?q=...
    """
    q = (request.GET.get("q") or "").strip().lower()
    if not q:
        return JsonResponse({"results": []})
    hits = [
        p for p in _EXAMPLE_PLANS
        if q in (p.get("title", "").lower() + " " + p.get("code", "").lower())
    ]
    return JsonResponse({"results": hits})


@login_required
@require_GET
def calendar_year(request: HttpRequest) -> JsonResponse:
    """
    Yıllık takvim görünümü için kaba bir veri üreticisi.
    Parametre: ?year=YYYY (yoksa bugünkü yıl)
    """
    try:
        year = int(request.GET.get("year") or date.today().year)
    except ValueError:
        year = date.today().year

    months: Dict[int, List[Dict[str, Any]]] = {m: [] for m in range(1, 13)}
    for p in _EXAMPLE_PLANS:
        try:
            start = datetime.fromisoformat(p["start"]).date()
        except Exception:
            continue
        if start.year == year:
            months[start.month].append(p)

    payload = {
        "year": year,
        "months": months,
        "total": sum(len(v) for v in months.values()),
    }
    return JsonResponse(payload)
