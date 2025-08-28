# trainings/views_needs.py
from django.apps import apps
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Q
from django.shortcuts import redirect, render

from .forms import TrainingNeedManualFormFactory


def M(name: str):
    try:
        return apps.get_model("trainings", name)
    except Exception:
        return None


Training = M("Training")
TrainingNeed = M("TrainingNeed")


def _model_has_field(model, fname: str) -> bool:
    try:
        model._meta.get_field(fname)
        return True
    except Exception:
        return False


@login_required
def needs_list(request):
    """
    Eğitim İhtiyaçları listesi (OKUMA).
    - Kullanıcı staff değilse: yalnızca kendi ihtiyaçlarını görür (modelde 'user' alanı varsa).
    - Admin/staff tüm kayıtları görür.
    - Bu view'da değişiklik yok; düzenleme/admin işlemleri /admin/ üzerinden yapılır.
    """
    if TrainingNeed is None:
        messages.error(request, "TrainingNeed modeli bulunamadı.")
        return render(request, "trainings/needs_list.html", {"rows": [], "q": "", "count": 0})

    q = (request.GET.get("q") or "").strip()

    qs = TrainingNeed.objects.all()

    # Staff değilse yalnızca kendi kayıtlarını görsün (modelde user alanı varsa)
    if _model_has_field(TrainingNeed, "user") and not request.user.is_staff:
        qs = qs.filter(user=request.user)

    # Basit arama
    if q:
        q_filter = Q()
        if _model_has_field(TrainingNeed, "note"):
            q_filter |= Q(note__icontains=q)
        if _model_has_field(TrainingNeed, "source"):
            q_filter |= Q(source__icontains=q)
        if _model_has_field(TrainingNeed, "status"):
            q_filter |= Q(status__icontains=q)
        if _model_has_field(TrainingNeed, "description"):
            q_filter |= Q(description__icontains=q)
        if _model_has_field(TrainingNeed, "training") and Training:
            q_filter |= Q(training__title__icontains=q) | Q(training__code__icontains=q)
        qs = qs.filter(q_filter)

    qs = qs.select_related("training").order_by("-id")

    rows = []
    for it in qs:
        rows.append({
            "id": getattr(it, "id", None),
            "training_title": getattr(getattr(it, "training", None), "title", "(Eğitim yok)"),
            "training_code": getattr(getattr(it, "training", None), "code", ""),
            "user_str": str(getattr(it, "user", "")) if _model_has_field(TrainingNeed, "user") else "",
            "source": getattr(it, "source", "") if _model_has_field(TrainingNeed, "source") else "",
            "status": getattr(it, "status", "") if _model_has_field(TrainingNeed, "status") else "",
            "is_resolved": getattr(it, "is_resolved", None) if _model_has_field(TrainingNeed, "is_resolved") else None,
            "created_at": getattr(it, "created_at", None) if _model_has_field(TrainingNeed, "created_at") else None,
            "due_date": getattr(it, "due_date", None) if _model_has_field(TrainingNeed, "due_date") else None,
            "note": getattr(it, "note", "") if _model_has_field(TrainingNeed, "note") else getattr(it, "description", ""),
        })

    return render(request, "trainings/needs_list.html", {
        "rows": rows,
        "q": q,
        "count": len(rows),
    })


@staff_member_required  # ✅ Sadece admin/staff giriş yapmış kullanıcı erişir
def need_add_manual(request):
    """
    Manuel eğitim ihtiyacı ekleme (YALNIZCA STAFF).
    Normal kullanıcılar bu sayfaya erişemez.
    """
    if TrainingNeed is None or Training is None:
        messages.error(request, "TrainingNeed/Training modeli bulunamadı.")
        return redirect("needs-list")

    include_user = _model_has_field(TrainingNeed, "user")
    FormCls = TrainingNeedManualFormFactory(include_user=include_user)

    if request.method == "POST":
        form = FormCls(request.POST)
        if form.is_valid():
            cleaned = form.cleaned_data
            training = cleaned.get("training")
            target_user = cleaned.get("user") if include_user else request.user
            note = cleaned.get("note")
            due_date = cleaned.get("due_date")

            fields = {f.name for f in TrainingNeed._meta.get_fields() if hasattr(f, "attname")}
            data = {}

            if "training" in fields:
                data["training"] = training
            if "user" in fields:
                data["user"] = target_user
            if "note" in fields:
                data["note"] = note
            elif "description" in fields:
                data["description"] = note
            if "due_date" in fields:
                data["due_date"] = due_date
            if "source" in fields:
                data["source"] = "manual"
            if "status" in fields and not data.get("status"):
                try:
                    data["status"] = "open"
                except Exception:
                    pass
            if "created_by" in fields:
                data["created_by"] = request.user

            TrainingNeed.objects.create(**data)
            messages.success(request, "Eğitim ihtiyacı eklendi.")
            return redirect("needs-list")
    else:
        form = FormCls()

    return render(request, "trainings/need_add.html", {"form": form})
