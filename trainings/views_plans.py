# trainings/views_plans.py
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List
import math

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
    "visual_plan",  # ← BU SATIRI EKLEYİN
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
    Yıllık takvim görünümü için kaba bir veri üretici.
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


@login_required
def visual_plan(request: HttpRequest) -> HttpResponse:
    """
    52 haftalık görsel denetim planı - Timeline view
    """
    # Örnek eğitim verileri (gerçek veritabanından gelecek)
    example_trainings = [
        {
            'id': 1,
            'title': 'Excel İleri Seviye Eğitimi',
            'code': 'TR-EXCEL-ADV',
            'start_week': 36,  # 36. hafta (Eylül)
            'duration_weeks': 1,
            'start_date': '2025-09-08',
            'end_date': '2025-09-09',
            'participants': ['Ahmet Yılmaz', 'Ayşe Demir', 'Mehmet Kaya', 'Fatma Şahin'],
            'location': 'Toplantı Odası 2',
            'instructor': 'Ahmet Demir',
            'color': '#3498db'
        },
        {
            'id': 2,
            'title': 'İş Sağlığı ve Güvenliği',
            'code': 'TR-ISG-01',
            'start_week': 38,  # 38. hafta
            'duration_weeks': 1,
            'start_date': '2025-09-22',
            'end_date': '2025-09-22',
            'participants': ['Ali Veli', 'Zeynep Ak', 'Can Demir', 'Elif Yıldız', 'Burak Koç'],
            'location': 'Konferans Salonu',
            'instructor': 'Dış Eğitim Kurumu',
            'color': '#e74c3c'
        },
        {
            'id': 3,
            'title': 'Yönetici Geliştirme Programı',
            'code': 'TR-MGMT-01',
            'start_week': 40,
            'duration_weeks': 3,  # 3 hafta sürecek
            'start_date': '2025-10-06',
            'end_date': '2025-10-24',
            'participants': ['Murat Öztürk', 'Seda Yılmaz', 'Cemal Aydın'],
            'location': 'Eğitim Salonu A',
            'instructor': 'Prof. Dr. Mehmet Ak',
            'color': '#2ecc71'
        }
    ]
    
    # Mevcut haftayı hesapla
    try:
        current_week = datetime.now().isocalendar()[1]
    except:
        current_week = 36  # Fallback
    
    context = {
        'trainings': example_trainings,
        'current_year': 2025,
        'total_weeks': 52,
        'range_weeks': range(1, 53),  # 1-52 arası haftalar
        'current_week': current_week  # Mevcut hafta
    }
    
    return render(request, 'trainings/visual_plan.html', context)
@login_required
def visual_plan(request: HttpRequest) -> HttpResponse:
    """
    52 haftalık görsel denetim planı - Timeline view
    """
    # Örnek eğitim verileri
    example_trainings = [
        {
            'id': 1,
            'title': 'Excel İleri Seviye Eğitimi',
            'code': 'TR-EXCEL-ADV',
            'start_week': 36,
            'duration_weeks': 1,
            'start_date': '2025-09-08',
            'end_date': '2025-09-09',
            'participants': ['Ahmet Yılmaz', 'Ayşe Demir', 'Mehmet Kaya', 'Fatma Şahin'],
            'location': 'Toplantı Odası 2',
            'instructor': 'Ahmet Demir',
            'color': '#3498db'
        },
        {
            'id': 2,
            'title': 'İş Sağlığı ve Güvenliği',
            'code': 'TR-ISG-01', 
            'start_week': 38,
            'duration_weeks': 1,
            'start_date': '2025-09-22',
            'end_date': '2025-09-22',
            'participants': ['Ali Veli', 'Zeynep Ak', 'Can Demir', 'Elif Yıldız', 'Burak Koç'],
            'location': 'Konferans Salonu',
            'instructor': 'Dış Eğitim Kurumu',
            'color': '#e74c3c'
        }
    ]
    
    # Mevcut haftayı hesapla
    from datetime import datetime
    try:
        current_week = datetime.now().isocalendar()[1]
    except:
        current_week = 36
    
    # Direkt HTML döndür - template sorununu bypass et
    html_content = f"""
    <!DOCTYPE html>
    <html lang="tr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>📅 Görsel Denetim Planı - 2025</title>
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                margin: 0;
                padding: 20px;
            }}
            .container {{
                max-width: 1400px;
                margin: 0 auto;
                background: white;
                border-radius: 15px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.2);
                overflow: hidden;
            }}
            .header {{
                background: linear-gradient(45deg, #2c3e50, #34495e);
                color: white;
                padding: 25px;
                text-align: center;
            }}
            .header h1 {{
                font-size: 2.2em;
                margin-bottom: 10px;
            }}
            .timeline {{
                padding: 20px;
            }}
            .training-item {{
                background: #f8f9fa;
                margin: 10px 0;
                padding: 15px;
                border-radius: 8px;
                border-left: 4px solid #3498db;
            }}
            .week-grid {{
                display: grid;
                grid-template-columns: repeat(52, 1fr);
                gap: 2px;
                margin: 20px 0;
                background: #ecf0f1;
                padding: 10px;
                border-radius: 5px;
            }}
            .week-cell {{
                height: 30px;
                background: white;
                border: 1px solid #bdc3c7;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 0.7em;
            }}
            .week-active {{
                background: #3498db;
                color: white;
            }}
            .test-success {{
                background: #27ae60;
                color: white;
                padding: 20px;
                margin: 20px;
                border-radius: 10px;
                text-align: center;
                font-size: 1.2em;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>📅 Görsel Denetim Planı - 2025</h1>
                <p>52 Haftalık Timeline - Direkt HTML Çalışıyor!</p>
            </div>
            
            <div class="test-success">
                ✅ <strong>VIEW ÇALIŞIYOR!</strong> Template sorunu bypass edildi.
            </div>
            
            <div class="timeline">
                <h3>🎯 Eğitimler ({len(example_trainings)} adet)</h3>
                {"".join([f'''
                <div class="training-item">
                    <strong>{training["title"]}</strong> ({training["code"]})
                    <br>Hafta: {training["start_week"]}, Lokasyon: {training["location"]}
                    <br>Katılımcılar: {", ".join(training["participants"][:3])}{"..." if len(training["participants"]) > 3 else ""}
                </div>
                ''' for training in example_trainings])}
                
                <h3>📊 52 Haftalık Timeline (Önizleme)</h3>
                <div class="week-grid">
                    {"".join([f'<div class="week-cell {"week-active" if week in [36, 38] else ""}">{week}</div>' for week in range(1, 53)])}
                </div>
                
                <p><em>Template sorunu çözüldüğünde tam timeline görünecek.</em></p>
            </div>
        </div>
        
        <script>
            console.log("🎯 Görsel Denetim Planı yüklendi!");
            // Timeline interaktif özellikler buraya eklenecek
        </script>
    </body>
    </html>
    """
    
    return HttpResponse(html_content)