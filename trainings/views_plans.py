# trainings/views_plans.py
from django.apps import apps
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from datetime import datetime, timedelta

from .forms import get_training_plan_form


def M(name: str):
    try:
        return apps.get_model("trainings", name)
    except Exception:
        return None

Training = M("Training")
TrainingPlan = M("TrainingPlan")
TrainingPlanAttendee = M("TrainingPlanAttendee")


def is_staff(user):
    return user.is_staff or user.is_superuser


def _parse_date(s: str):
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except Exception:
        return None


def _parse_qs_params(request):
    q = (request.GET.get("q") or "").strip()
    status_val = (request.GET.get("status") or "").strip()
    training_val = request.GET.get("training")
    try:
        training_val = int(training_val) if training_val else None
    except Exception:
        training_val = None
    from_val = (request.GET.get("from") or "").strip()
    to_val = (request.GET.get("to") or "").strip()
    return q, status_val, training_val, from_val, to_val


@login_required
@user_passes_test(is_staff)
def plan_list(request):
    if TrainingPlan is None:
        return render(request, "trainings/plan_list.html", {
            "items": [],
            "q": "", "status_val": "", "training_val": None, "from_val": "", "to_val": "",
            "trainings": Training.objects.none() if Training else [],
            "error": "TrainingPlan modeli yüklenemedi."
        })

    q, status_val, training_val, from_val, to_val = _parse_qs_params(request)

    qs = TrainingPlan.objects.select_related("training", "need").order_by("-start_datetime")

    if status_val:
        qs = qs.filter(status=status_val)

    if training_val:
        qs = qs.filter(training_id=training_val)

    fr = _parse_date(from_val)
    if fr:
        qs = qs.filter(start_datetime__date__gte=fr)

    to = _parse_date(to_val)
    if to:
        qs = qs.filter(end_datetime__date__lte=to)

    if q:
        qs = qs.filter(
            Q(training__title__icontains=q) |
            Q(training__code__icontains=q) |
            Q(location__icontains=q) |
            Q(instructor_name__icontains=q) |
            Q(notes__icontains=q)
        )

    paginator = Paginator(qs, 15)
    page_obj = paginator.get_page(request.GET.get("page"))

    t_qs = Training.objects.filter(is_active=True).order_by("title") if Training else []

    ctx = {
        "items": page_obj,
        "q": q,
        "status_val": status_val,
        "training_val": training_val,
        "from_val": from_val,
        "to_val": to_val,
        "trainings": t_qs,
    }
    return render(request, "trainings/plan_list.html", ctx)


@login_required
@user_passes_test(is_staff)
def plan_create(request):
    FormClass = get_training_plan_form()
    if FormClass is None or TrainingPlan is None:
        messages.error(request, "TrainingPlan modeli veya formu yüklenemedi.")
        return redirect(reverse("plan_list"))

    if request.method == "POST":
        form = FormClass(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            if hasattr(obj, "created_by"):
                obj.created_by = request.user
            obj.save()
            # katılımcıları senkronla (commit=False kullandık)
            form.save_participants(obj)
            messages.success(request, "Eğitim planı oluşturuldu.")
            return redirect(reverse("plan_list"))
    else:
        form = FormClass()

    return render(
        request,
        "trainings/plan_edit.html",
        {"form": form, "is_new": True, "plan": None, "attendees": []},
    )


@login_required
@user_passes_test(is_staff)
def plan_edit(request, pk):
    if TrainingPlan is None:
        messages.error(request, "TrainingPlan modeli yüklenemedi.")
        return redirect(reverse("plan_list"))

    plan = get_object_or_404(TrainingPlan, pk=pk)
    FormClass = get_training_plan_form()
    if FormClass is None:
        messages.error(request, "TrainingPlan formu yüklenemedi.")
        return redirect(reverse("plan_list"))

    if request.method == "POST":
        form = FormClass(request.POST, instance=plan)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.save()
            form.save_participants(obj)
            messages.success(request, "Eğitim planı güncellendi.")
            return redirect(reverse("plan_edit", args=[plan.id]))
    else:
        form = FormClass(instance=plan)

    attendees = []
    if TrainingPlanAttendee:
        attendees = (TrainingPlanAttendee.objects
                     .filter(plan=plan)
                     .select_related("user")
                     .order_by("user__username"))

    return render(
        request,
        "trainings/plan_edit.html",
        {"form": form, "is_new": False, "plan": plan, "attendees": attendees},
    )


@login_required
@user_passes_test(is_staff)
def plan_copy(request, pk):
    if TrainingPlan is None:
        messages.error(request, "TrainingPlan modeli yüklenemedi.")
        return redirect(reverse("plan_list"))

    src = get_object_or_404(TrainingPlan, pk=pk)
    start_dt = src.start_datetime + timedelta(days=7)
    end_dt = src.end_datetime + timedelta(days=7)

    new_obj = TrainingPlan(
        training=src.training,
        need=src.need,
        start_datetime=start_dt,
        end_datetime=end_dt,
        capacity=src.capacity,
        location=src.location,
        instructor_name=src.instructor_name,
        delivery=src.delivery,
        status="planned",
        notes=src.notes,
    )
    if hasattr(new_obj, "created_by"):
        new_obj.created_by = request.user
    new_obj.save()

    messages.success(request, f"Plan kopyalandı (yeni ID: {new_obj.id}).")
    return redirect(reverse("plan_edit", args=[new_obj.id]))


@login_required
@user_passes_test(is_staff)
def plan_delete(request, pk):
    if TrainingPlan is None:
        messages.error(request, "TrainingPlan modeli yüklenemedi.")
        return redirect(reverse("plan_list"))

    if request.method != "POST":
        messages.warning(request, "Silme işlemi yalnızca POST ile yapılabilir.")
        return redirect(reverse("plan_edit", args=[pk]))

    obj = get_object_or_404(TrainingPlan, pk=pk)
    obj.delete()
    messages.success(request, "Plan silindi.")
    return redirect(reverse("plan_list"))
