# trainings/utils/needs.py
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.apps import apps

def M(name: str):
    try:
        return apps.get_model("trainings", name)
    except Exception:
        return None

Training = M("Training")
Enrollment = M("Enrollment")
TrainingRequirement = M("TrainingRequirement")
JobRoleAssignment = M("JobRoleAssignment")
TrainingNeed = M("TrainingNeed")
JobRole = M("JobRole")


def has_field(model, fname: str) -> bool:
    try:
        model._meta.get_field(fname)
        return True
    except Exception:
        return False


def _fk_to_jobrole_by_name(model) -> str | None:
    """
    Alan adıyla kestirme; çoğu şemada 'job_role' veya 'role' olur.
    """
    for cand in ("job_role", "role", "jobrole", "position", "job", "gorev", "gorev_tanimi"):
        if has_field(model, cand):
            return cand
    return None


def _fk_to_jobrole_by_relation(model) -> str | None:
    """
    İlişkiden tespit; sınıf eşleşmesi sıkıntı çıkarırsa model_name bazlı bakıyoruz.
    """
    try:
        for f in model._meta.get_fields():
            if getattr(f, "is_relation", False) and getattr(f, "many_to_one", False):
                rel = getattr(f, "related_model", None)
                if not rel or not hasattr(rel, "_meta"):
                    continue
                # app_label/model_name bazlı karşılaştır
                if rel._meta.model_name in ("jobrole",) and rel._meta.app_label == "trainings":
                    return f.name
    except Exception:
        pass
    return None


def fk_to_jobrole(model) -> str | None:
    """
    JobRole FK alan adını BUL:
    1) Bilinen adlardan biri varsa onu kullan
    2) Yoksa relation’dan çöz
    3) Hiçbiri yoksa None
    """
    by_name = _fk_to_jobrole_by_name(model)
    if by_name:
        return by_name
    return _fk_to_jobrole_by_relation(model)


def is_completed(user, training) -> bool:
    """
    Kullanıcı eğitimi tamamlamış mı? (status=completed veya is_passed=True veya completed_at dolu)
    """
    if not (Enrollment and user and training):
        return False
    q = Enrollment.objects.filter(user=user, training=training)
    done = Q()
    if has_field(Enrollment, "status"):
        done |= Q(status="completed")
    if has_field(Enrollment, "is_passed"):
        done |= Q(is_passed=True)
    if has_field(Enrollment, "completed_at"):
        done |= Q(completed_at__isnull=False)
    if not done:
        return False
    return q.filter(done).exists()


@transaction.atomic
def create_needs_for_assignment(assignment) -> int:
    """
    Verilen JobRoleAssignment için (ve kullanıcının diğer aktif görevleri için)
    görev gereği olup HENÜZ ALINMAMIŞ eğitimlerden TrainingNeed üretir.
    Tamamlanmış eğitimler ve mevcut açık ihtiyaçlar atlanır.
    Kaynak alanı 'role' (Görev Gereği) olarak işaretlenir.
    """
    if not (assignment and TrainingRequirement and TrainingNeed and JobRoleAssignment):
        return 0

    user = getattr(assignment, "user", None)
    if not user:
        return 0

    # Kullanıcının tüm (tercihen aktif) görev atamaları
    qs_assign = JobRoleAssignment.objects.filter(user=user)
    if has_field(JobRoleAssignment, "is_active"):
        qs_assign = qs_assign.filter(is_active=True)

    # JobRoleAssignment içinde JobRole FK alan adını bul
    jra_role_fk = fk_to_jobrole(JobRoleAssignment)
    roles = []
    for a in qs_assign:
        role = getattr(a, jra_role_fk, None) if jra_role_fk else None
        if role:
            roles.append(role)
    if not roles:
        return 0

    # TrainingRequirement içindeki JobRole FK alanını bul
    tr_role_fk = fk_to_jobrole(TrainingRequirement)
    if not tr_role_fk:
        # Yine de en yaygın isimlerle son şans
        tr_role_fk = "job_role" if has_field(TrainingRequirement, "job_role") else "role"

    # İlgili tüm gereklilikleri çek
    tr_filter = {f"{tr_role_fk}__in": roles}
    reqs = TrainingRequirement.objects.filter(**tr_filter).select_related("training")

    created = 0
    seen = set()  # aynı eğitim birden fazla görevden gelirse tekle

    for req in reqs:
        training = getattr(req, "training", None)
        if not training:
            continue

        # Aynı eğitim tekrar işlenmesin
        t_id = getattr(training, "pk", None)
        if t_id in seen:
            continue
        seen.add(t_id)

        # 1) Tamamlanmışsa hiç ihtiyaç oluşturma
        if is_completed(user, training):
            continue

        # 2) Açık bir ihtiyaç zaten varsa tekrar oluşturma
        need_q = TrainingNeed.objects.filter(user=user, training=training)
        if has_field(TrainingNeed, "is_resolved"):
            need_q = need_q.filter(is_resolved=False)
        elif has_field(TrainingNeed, "status"):
            need_q = need_q.exclude(status="closed")
        if need_q.exists():
            continue

        # 3) İhtiyacı oluştur
        fields = {
            "user": user,
            "training": training,
        }
        if has_field(TrainingNeed, "source"):
            fields["source"] = "role"  # Görev Gereği

        # Not/description’a rol adını yaz (ilk role’den)
        role_obj = roles[0]
        role_name = getattr(role_obj, "name", "") or getattr(role_obj, "title", "") or ""
        text = f"Görev tanımı: {role_name}" if role_name else "Görev tanımı gereği"
        if has_field(TrainingNeed, "note"):
            fields["note"] = text
        elif has_field(TrainingNeed, "description"):
            fields["description"] = text

        if has_field(TrainingNeed, "created_at"):
            fields["created_at"] = timezone.now()

        TrainingNeed.objects.create(**fields)
        created += 1

    return created
