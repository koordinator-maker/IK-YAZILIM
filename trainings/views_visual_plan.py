# trainings/views_visual_plan.py
from __future__ import annotations
from typing import Any, Dict
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

@login_required
def visual_plan(request: HttpRequest) -> HttpResponse:
    """
    Görsel Eğitim Planı sayfası.
    - Eğer 'templates/trainings/visual_plan.html' varsa onu render eder.
    - Yoksa base.html içinde kibar bir placeholder gösterir.
    """
    context: Dict[str, Any] = {}

    # Önce asıl şablonu dene
    try:
        return render(request, "trainings/visual_plan.html", context)
    except Exception:
        # Placeholder (şablon henüz yoksa)
        html = """
        <div style="padding:16px">
          <h1>Görsel Eğitim Planı</h1>
          <p>Şablon bulunamadı:
             <code>templates/trainings/visual_plan.html</code></p>
          <ul>
            <li><a href="/plans/">Planlar</a></li>
            <li><a href="/api/plans/">Plan API</a></li>
            <li><a href="/api/plan-search/?q=test">Plan Arama API</a></li>
          </ul>
        </div>
        """
        return render(request, "base.html", {"content": html})
# trainings/views_visual_plan.py dosyasını aç ve İÇİNE şu kodu ekle:

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from datetime import datetime

@login_required
def visual_plan(request):
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
    try:
        current_week = datetime.now().isocalendar()[1]
    except:
        current_week = 36
    
    # Direkt HTML döndür
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Görsel Denetim Planı</title>
        <style>
            body {{ font-family: Arial; padding: 20px; background: #f0f0f0; }}
            .container {{ background: white; padding: 30px; border-radius: 10px; }}
            h1 {{ color: #2c3e50; }}
            .success {{ background: #27ae60; color: white; padding: 20px; margin: 20px 0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎯 Görsel Denetim Planı - ÇALIŞIYOR!</h1>
            <div class="success">
                <h3>✅ VIEWS_VISUAL_PLAN.PY ÇALIŞIYOR!</h3>
                <p>Toplam eğitim: {len(example_trainings)}</p>
            </div>
            <h3>Eğitimler:</h3>
            <ul>
    """
    
    for training in example_trainings:
        html_content += f"<li><strong>{training['title']}</strong> - Hafta {training['start_week']}</li>"
    
    html_content += """
            </ul>
            <p><em>52 haftalık timeline burada görünecek</em></p>
        </div>
    </body>
    </html>
    """
    
    return HttpResponse(html_content)