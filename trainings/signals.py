# trainings/signals.py
from django.db.models.signals import post_save, post_migrate
from django.dispatch import receiver
from django.apps import apps
import logging

logger = logging.getLogger(__name__)

def M(name: str):
    try:
        return apps.get_model("trainings", name)
    except Exception:
        return None

def has_field(model, fname: str) -> bool:
    try:
        model._meta.get_field(fname)
        return True
    except Exception:
        return False

def fk_name_to(model, related_model, candidates=("role", "job_role", "jobrole", "position", "job")):
    if not model or not related_model:
        return None
    try:
        for f in model._meta.get_fields():
            if getattr(f, "is_relation", False) and getattr(f, "many_to_one", False):
                if getattr(f, "related_model", None) == related_model:
                    return f.name
    except Exception:
        pass
    for cand in candidates:
        if has_field(model, cand):
            return cand
    return None

JobRoleAssignment = M("JobRoleAssignment")
TrainingRequirement = M("TrainingRequirement")
JobRole = M("JobRole")

# create_needs fonksiyonu
try:
    from .utils.needs import create_needs_for_assignment
except Exception as e:
    create_needs_for_assignment = None
    logger.exception("utils.needs.create_needs_for_assignment import edilemedi: %s", e)


def _run_create_needs(assignment, reason="unknown"):
    if not (assignment and create_needs_for_assignment):
        return
    try:
        cnt = create_needs_for_assignment(assignment)
        logger.info("[needs] %s -> %s adet TrainingNeed (assignment id=%s)", reason, cnt, getattr(assignment, "pk", None))
    except Exception as e:
        logger.exception("[needs] %s -> HATA (assignment id=%s): %s", reason, getattr(assignment, "pk", None), e)


# 1) Kullanıcıya görev atanınca/aktif edilince
if JobRoleAssignment:
    @receiver(post_save, sender=JobRoleAssignment)
    def on_job_role_assignment_saved(sender, instance, created, **kwargs):
        try:
            active_ok = True
            if has_field(JobRoleAssignment, "is_active"):
                active_ok = bool(getattr(instance, "is_active", False))
            if created or active_ok:
                _run_create_needs(instance, reason="JobRoleAssignment.save")
        except Exception as e:
            logger.exception("JobRoleAssignment post_save hata: %s", e)


# 2) Role yeni gereklilik eklenince → o role sahip herkes için
if TrainingRequirement and JobRoleAssignment and JobRole:
    @receiver(post_save, sender=TrainingRequirement)
    def on_training_requirement_saved(sender, instance, created, **kwargs):
        try:
            tr_role_fk = fk_name_to(TrainingRequirement, JobRole) or "role"
            role_obj = getattr(instance, tr_role_fk, None)
            if not role_obj:
                return
            jra_role_fk = fk_name_to(JobRoleAssignment, JobRole) or "role"
            qs = JobRoleAssignment.objects.filter(**{jra_role_fk: role_obj})
            if has_field(JobRoleAssignment, "is_active"):
                qs = qs.filter(is_active=True)
            for a in qs:
                _run_create_needs(a, reason="TrainingRequirement.save")
        except Exception as e:
            logger.exception("TrainingRequirement post_save hata: %s", e)


# 3) Migrasyonlardan sonra güvenli backfill (ilk kurulumda boş kalmasın)
@receiver(post_migrate)
def on_post_migrate(sender, app_config, **kwargs):
    try:
        if getattr(app_config, "label", "") != "trainings":
            return
        if not JobRoleAssignment:
            return
        qs = JobRoleAssignment.objects.all()
        if has_field(JobRoleAssignment, "is_active"):
            qs = qs.filter(is_active=True)
        for a in qs:
            _run_create_needs(a, reason="post_migrate")
    except Exception as e:
        logger.exception("post_migrate needs backfill hata: %s", e)
