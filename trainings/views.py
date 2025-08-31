# trainings/views.py
from django.apps import apps
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import Http404, HttpResponse, FileResponse
from django.shortcuts import get_object_or_404, redirect, render

def M(name: str):
    try:
        return apps.get_model("trainings", name)
    except Exception:
        return None

Training = M("Training")
Enrollment = M("Enrollment")
Certificate = M("Certificate")


def trainings_list(request):
    q = (request.GET.get("q") or "").strip()
    qs = Training.objects.none()
    if Training:
        qs = Training.objects.all()
        # İstersen sadece aktifleri göster:
        qs = qs.filter(is_active=True)
        if q:
            qs = qs.filter(
                Q(title__icontains=q) |
                Q(code__icontains=q) |
                Q(description__icontains=q)
            )
        qs = qs.order_by("title")
    ctx = {
        "trainings": qs,
        "q": q,
        "count": qs.count() if Training else 0,
    }
    return render(request, "trainings/trainings_list.html", ctx)


@login_required
def my_trainings(request):
    qs = []
    if Enrollment:
        qs = (Enrollment.objects
              .filter(user=request.user)
              .select_related("training")
              .order_by("-id"))
    return render(request, "trainings/my_trainings.html", {"enrollments": qs})


@login_required
def enroll(request, pk):
    if not (Training and Enrollment):
        messages.error(request, "Gerekli modeller yüklenemedi (Training/Enrollment).")
        return redirect("home")
    training = get_object_or_404(Training, pk=pk)
    if Enrollment.objects.filter(user=request.user, training=training).exists():
        messages.info(request, "Bu eğitime zaten kayıtlısınız.")
    else:
        Enrollment.objects.create(user=request.user, training=training)
        messages.success(request, "Eğitime kaydınız oluşturuldu.")
    return redirect("mine")


def download_certificate(request, pk):
    if Certificate is None:
        raise Http404("Certificate modeli bulunamadı.")
    cert = get_object_or_404(Certificate, pk=pk)
    if not (request.user.is_staff or cert.user_id == getattr(request.user, "id", None)):
        raise Http404("Bu sertifikaya erişiminiz yok.")
    for cand in ("file", "pdf", "document"):
        f = getattr(cert, cand, None)
        if f:
            return FileResponse(
                f.open("rb"),
                as_attachment=True,
                filename=getattr(f, "name", f"certificate-{pk}.pdf"),
            )
    return HttpResponse(f"Sertifika #{pk} indirilemedi (dosya bulunamadı).", content_type="text/plain")


def whoami(request):
    if request.user.is_authenticated:
        return HttpResponse(
            f"Kullanıcı: {request.user.get_username()} | ID: {request.user.id}",
            content_type="text/plain",
        )
    return HttpResponse("Anonim kullanıcı", content_type="text/plain")