from typing import Optional
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db.models import Q, Prefetch
from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .models import TrainingPlan, TrainingPlanAttendee

User = get_user_model()


def _plan_title(plan: TrainingPlan) -> str:
    t = getattr(plan, "training", None)
    if t:
        return getattr(t, "title", None) or getattr(t, "name", None) or str(t)
    return f"Plan #{plan.pk}"


def _plan_when(plan: TrainingPlan) -> str:
    start = getattr(plan, "start_datetime", None)
    end = getattr(plan, "end_datetime", None)
    if start and end:
        return f"{start} → {end}"
    if start:
        return f"{start}"
    return "Tarih: -"


def _trainer_display(plan: TrainingPlan) -> Optional[str]:
    name = getattr(plan, "instructor_name", None)
    return str(name) if name else None


def _participant_candidates(q: str = ""):
    qs = User.objects.filter(is_active=True)
    if q:
        qs = qs.filter(
            Q(first_name__icontains=q) |
            Q(last_name__icontains=q) |
            Q(username__icontains=q) |
            Q(email__icontains=q)
        )
    return qs.order_by("first_name", "last_name", "username")[:300]


def _trainer_candidates(q: str = ""):
    qs = User.objects.filter(is_active=True, is_staff=True)
    if q:
        qs = qs.filter(
            Q(first_name__icontains=q) |
            Q(last_name__icontains=q) |
            Q(username__icontains=q) |
            Q(email__icontains=q)
        )
    return qs.order_by("first_name", "last_name", "username")[:200]


@staff_member_required
def planning_board(request: HttpRequest) -> HttpResponse:
    q = (request.GET.get("q") or "").strip()
    user_q = (request.GET.get("user_q") or "").strip()
    trainer_q = (request.GET.get("trainer_q") or "").strip()

    plans_qs = (
        TrainingPlan.objects.select_related("training")
        .prefetch_related(
            Prefetch(
                "plan_attendees",
                queryset=TrainingPlanAttendee.objects.select_related("user"),
            )
        )
        .order_by("-start_datetime", "-pk")
    )
    if q:
        plans_qs = plans_qs.filter(
            Q(training__title__icontains=q) |
            Q(training__code__icontains=q) |
            Q(location__icontains=q) |
            Q(instructor_name__icontains=q)
        )

    trainer_candidates = _trainer_candidates(trainer_q)
    participant_candidates = _participant_candidates(user_q)

    cards = []
    for p in plans_qs:
        cards.append({
            "plan": p,
            "title": _plan_title(p),
            "when": _plan_when(p),
            "trainer_name": _trainer_display(p),
            "participants": [a.user for a in p.plan_attendees.all()],
        })

    ctx = {
        "cards": cards,
        "q": q,
        "user_q": user_q,
        "trainer_q": trainer_q,
        "trainer_candidates": trainer_candidates,
        "participant_candidates": participant_candidates,
    }
    return render(request, "trainings/plans/board.html", ctx)


@staff_member_required
def plan_set_trainer_name(request: HttpRequest, plan_id: int) -> HttpResponse:
    if request.method != "POST":
        return HttpResponseBadRequest("POST bekleniyor.")
    plan = get_object_or_404(TrainingPlan, pk=plan_id)
    trainer_id = request.POST.get("trainer_id")
    if not trainer_id:
        messages.error(request, "Eğitmen seçilmedi.")
        return _back_to_board(request)
    trainer = get_object_or_404(User, pk=trainer_id)
    display = trainer.get_full_name() or trainer.username
    try:
        plan.instructor_name = display  # şemayı bozmadan text alana yaz
        plan.save(update_fields=["instructor_name"])
        messages.success(request, "Eğitmen kaydedildi.")
    except Exception as e:
        messages.error(request, f"Eğitmen güncellenemedi: {e}")
    return _back_to_board(request)


@staff_member_required
def plan_assign_participant(request: HttpRequest, plan_id: int) -> HttpResponse:
    if request.method != "POST":
        return HttpResponseBadRequest("POST bekleniyor.")
    plan = get_object_or_404(TrainingPlan, pk=plan_id)
    user_id = request.POST.get("user_id")
    if not user_id:
        messages.error(request, "Katılımcı seçilmedi.")
        return _back_to_board(request)
    try:
        TrainingPlanAttendee.objects.get_or_create(plan=plan, user_id=int(user_id))
        messages.success(request, "Katılımcı eklendi.")
    except Exception as e:
        messages.error(request, f"Katılımcı eklenemedi: {e}")
    return _back_to_board(request)


@staff_member_required
def plan_remove_participant(request: HttpRequest, plan_id: int) -> HttpResponse:
    if request.method != "POST":
        return HttpResponseBadRequest("POST bekleniyor.")
    plan = get_object_or_404(TrainingPlan, pk=plan_id)
    user_id = request.POST.get("user_id")
    if not user_id:
        messages.error(request, "Silinecek katılımcı seçilmedi.")
        return _back_to_board(request)
    try:
        deleted, _ = TrainingPlanAttendee.objects.filter(plan=plan, user_id=int(user_id)).delete()
        if deleted:
            messages.success(request, "Katılımcı çıkarıldı.")
        else:
            messages.info(request, "Silinecek kayıt bulunamadı.")
    except Exception as e:
        messages.error(request, f"Katılımcı çıkarılamadı: {e}")
    return _back_to_board(request)


def _back_to_board(request: HttpRequest) -> HttpResponseRedirect:
    base = reverse("plans_board")
    params = []
    for key in ("q", "user_q", "trainer_q"):
        val = request.GET.get(key)
        if val:
            params.append(f"{key}={val}")
    if params:
        return redirect(f"{base}?{'&'.join(params)}")
    return redirect(base)
