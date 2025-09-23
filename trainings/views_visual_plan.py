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
