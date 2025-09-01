from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import get_user_model
from django.db.models import Prefetch, Q
from django.http import Http404, HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET, require_POST

from .models import Training, TrainingPlan, TrainingPlanAttendee

User = get_user_model()


def _is_staff(user) -> bool:
    return user.is_staff or user.is_superuser


# -----------------------------
# Plan listesi (kart görünümü)
# -----------------------------
@login_required
def plans_page(request: HttpRequest) -> HttpResponse:
    q = (request.GET.get("q") or "").strip()
    year = request.GET.get("year")
    qs = (
        TrainingPlan.objects.select_related("training")
        .prefetch_related("attendees")
        .order_by("start_time")
    )
    if year and year.isdigit():
        qs = qs.filter(start_time__year=int(year))
    if q:
        qs = qs.filter(
            Q(training__title__icontains=q)
            | Q(training__code__icontains=q)
            | Q(trainer__icontains=q)
            | Q(room__icontains=q)
        )

    plans: List[TrainingPlan] = list(qs[:200])
    return render(request, "trainings/plans_page.html", {"plans": plans})


# -----------------------------
# Görsel plan (takvim 12 ay)
# -----------------------------
@login_required
def visual_plan(request: HttpRequest) -> HttpResponse:
    year = int(request.GET.get("year") or datetime.now().year)
    return render(request, "trainings/visual_plan.html", {"year": year})


# -----------------------------
# Basit JSON API’ler (liste/arama)
# -----------------------------
@require_GET
@login_required
def api_plan_list(request: HttpRequest) -> JsonResponse:
    qs = (
        TrainingPlan.objects.select_related("training")
        .order_by("-start_time")[:200]
    )
    data = [
        {
            "id": p.id,
            "title": p.training.title if p.training_id else "",
            "code": p.training.code if p.training_id else "",
            "start": p.start_time.isoformat() if p.start_time else None,
            "duration_hours": p.duration_hours,
            "capacity": p.capacity,
            "trainer": p.trainer,
            "room": p.room,
            "attendee_count": p.attendees.count(),
        }
        for p in qs
    ]
    return JsonResponse({"results": data})


@require_GET
@login_required
def api_plan_detail(request: HttpRequest, pk: int) -> JsonResponse:
    p = get_object_or_404(
        TrainingPlan.objects.select_related("training").prefetch_related("attendees"),
        pk=pk,
    )
    return JsonResponse(
        {
            "id": p.id,
            "title": p.training.title if p.training_id else "",
            "code": p.training.code if p.training_id else "",
            "start": p.start_time.isoformat() if p.start_time else None,
            "duration_hours": p.duration_hours,
            "capacity": p.capacity,
            "trainer": p.trainer,
            "room": p.room,
            "attendees": [
                {"id": u.id, "username": u.get_username(), "full_name": u.get_full_name() or u.get_username()}
                for u in p.attendees.all()
            ],
        }
    )


@require_GET
@login_required
def api_plan_search(request: HttpRequest) -> JsonResponse:
    q = (request.GET.get("q") or "").strip()
    qs = (
        TrainingPlan.objects.select_related("training")
        .order_by("-start_time")
    )
    if q:
        qs = qs.filter(
            Q(training__title__icontains=q)
            | Q(training__code__icontains=q)
            | Q(trainer__icontains=q)
            | Q(room__icontains=q)
        )
    data = [
        {
            "id": p.id,
            "title": p.training.title if p.training_id else "",
            "code": p.training.code if p.training_id else "",
            "start": p.start_time.isoformat() if p.start_time else None,
        }
        for p in qs[:50]
    ]
    return JsonResponse({"results": data})


@require_GET
@login_required
def api_calendar_year(request: HttpRequest) -> JsonResponse:
    year = int(request.GET.get("year") or datetime.now().year)
    qs = (
        TrainingPlan.objects.filter(start_time__year=year)
        .select_related("training")
        .order_by("start_time")
    )
    buckets: Dict[int, List[Dict[str, Any]]] = {m: [] for m in range(1, 13)}
    for p in qs:
        m = p.start_time.month if p.start_time else 1
        buckets[m].append(
            {
                "id": p.id,
                "title": p.training.title if p.training_id else "",
                "code": p.training.code if p.training_id else "",
                "day": p.start_time.day if p.start_time else None,
                "time": p.start_time.strftime("%H:%M") if p.start_time else "",
            }
        )
    return JsonResponse({"year": year, "months": buckets})


# ------------------------------------------------
# Katılımcı yönetimi (Admin ve /plans/ için ortak)
# ------------------------------------------------
@require_GET
@login_required
def api_plan_attendees(request: HttpRequest, pk: int) -> JsonResponse:
    """Seçili plan için mevcut katılımcılar ve öneri listesi döner."""
    plan = get_object_or_404(
        TrainingPlan.objects.prefetch_related("attendees"),
        pk=pk,
    )
    attendees = [
        {"id": u.id, "username": u.get_username(), "full_name": u.get_full_name() or u.get_username()}
        for u in plan.attendees.all().order_by("username")
    ]
    # basit bir öneri: tüm kullanıcılar (ilk 100) – gerçek hayatta burada arama parametresi kullanırsın
    users = [
        {"id": u.id, "username": u.get_username(), "full_name": u.get_full_name() or u.get_username()}
        for u in User.objects.order_by("username")[:100]
    ]
    return JsonResponse({"attendees": attendees, "users": users})


@require_POST
@login_required
def api_plan_attendee_add(request: HttpRequest, pk: int) -> JsonResponse:
    plan = get_object_or_404(TrainingPlan, pk=pk)
    try:
        user_id = int(request.POST.get("user_id"))
    except (TypeError, ValueError):
        return JsonResponse({"ok": False, "error": "bad user_id"}, status=400)
    user = get_object_or_404(User, pk=user_id)
    TrainingPlanAttendee.objects.get_or_create(plan=plan, user=user)
    return JsonResponse({"ok": True})


@require_POST
@login_required
def api_plan_attendee_remove(request: HttpRequest, pk: int) -> JsonResponse:
    plan = get_object_or_404(TrainingPlan, pk=pk)
    try:
        user_id = int(request.POST.get("user_id"))
    except (TypeError, ValueError):
        return JsonResponse({"ok": False, "error": "bad user_id"}, status=400)
    TrainingPlanAttendee.objects.filter(plan=plan, user_id=user_id).delete()
    return JsonResponse({"ok": True})
