from django.contrib import admin
from django.apps import apps
from django.utils.html import format_html, format_html_join
from django.utils.text import Truncator
from django.contrib import messages
from django.db.models import Q, Exists, OuterRef
from django.utils import timezone
from datetime import datetime
from django.shortcuts import redirect
from django.urls import reverse

from django import forms
from django.contrib.auth import get_user_model


# ===== Yardımcılar =====
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
    """
    'model' içindeki, 'related_model'e many-to-one FK alan adını bulur.
    Bulamazsa candidates listesindeki isimlerden var olanı döner.
    """
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


# --- Modeller
Training = M("Training")
Enrollment = M("Enrollment")
Certificate = M("Certificate")
JobRole = M("JobRole")
TrainingRequirement = M("TrainingRequirement")
JobRoleAssignment = M("JobRoleAssignment")
TrainingNeed = M("TrainingNeed")
TrainingPlan = M("TrainingPlan")
TrainingPlanAttendee = M("TrainingPlanAttendee")
OnlineVideo = M("OnlineVideo")
VideoProgress = M("VideoProgress")


# =========================================
# PROXY MODELLER (sol menü kısayolları)
# (migrasyon gerektirmez)
# =========================================
if JobRoleAssignment:
    class JobRoleAssignmentQuickAdd(JobRoleAssignment):
        class Meta:
            proxy = True
            app_label = "trainings"
            verbose_name = "Kullanıcıya Görev Atama"
            verbose_name_plural = "Kullanıcıya Görev Atama"

    class JobRoleAssignmentListed(JobRoleAssignment):
        class Meta:
            proxy = True
            app_label = "trainings"
            verbose_name = "Kullanıcılara Atanmış Görevler"
            verbose_name_plural = "Kullanıcılara Atanmış Görevler"


# ========== Training ==========
if Training:
    @admin.register(Training)
    class TrainingAdmin(admin.ModelAdmin):
        list_display = ("title", "code", "is_active", "duration_hours", "created_at")
        list_filter = ("is_active",)
        search_fields = ("title", "code", "description")
        ordering = ("title",)
        readonly_fields = tuple(f for f in ("created_at", "updated_at") if has_field(Training, f))


# ========== JobRole & Requirements (inline) ==========
if JobRole and TrainingRequirement:

    TR_ROLE_FK = fk_name_to(TrainingRequirement, JobRole)

    class TrainingRequirementInline(admin.TabularInline):
        model = TrainingRequirement
        extra = 0
        autocomplete_fields = ("training",) if has_field(TrainingRequirement, "training") else ()
        fields = ["training"]
        if has_field(TrainingRequirement, "is_mandatory"):
            fields.append("is_mandatory")

        def formfield_for_foreignkey(self, db_field, request, **kwargs):
            formfield = super().formfield_for_foreignkey(db_field, request, **kwargs)
            if db_field.name == "training":
                w = formfield.widget
                for attr, val in {
                    "can_add_related": False,
                    "can_change_related": False,
                    "can_delete_related": False,
                    "can_view_related": True,
                }.items():
                    try:
                        setattr(w, attr, val)
                    except Exception:
                        pass
            return formfield

        def save_formset(self, request, form, formset, change):
            instances = formset.save(commit=False)
            seen = set()
            role_fk = TR_ROLE_FK or "role"
            for obj in instances:
                if getattr(obj, "_should_delete", False):
                    continue
                role_id = getattr(obj, f"{role_fk}_id", None)
                training_id = getattr(obj, "training_id", None)
                if not role_id or not training_id:
                    continue
                key = (role_id, training_id)
                exists = self.model.objects.filter(**{f"{role_fk}_id": role_id, "training_id": training_id}).exists()
                if key in seen or exists:
                    continue
                obj.save()
                seen.add(key)

            for obj in formset.deleted_objects:
                obj.delete()

        class Media:
            js = ("trainings/admin/requirement_inline.js",)
            css = {"all": ("trainings/admin/requirement_inline.css",)}

    @admin.register(JobRole)
    class JobRoleAdmin(admin.ModelAdmin):
        list_display = ("name", "created_at") if has_field(JobRole, "created_at") else ("name",)
        search_fields = ("name",)
        inlines = [TrainingRequirementInline]


# ========== Yardımcı: tamamlanma bilgisi ==========
def _completion_info(user, training):
    if not user or not training or Enrollment is None:
        return False, None
    completed_filter = Q()
    if has_field(Enrollment, "status"):
        completed_filter |= Q(status="completed")
    if has_field(Enrollment, "is_passed"):
        completed_filter |= Q(is_passed=True)
    if has_field(Enrollment, "completed_at"):
        completed_filter |= Q(completed_at__isnull=False)
    if completed_filter:
        qs = Enrollment.objects.filter(user=user, training=training).filter(completed_filter)
        if qs.exists():
            dt = None
            if has_field(Enrollment, "completed_at"):
                row = qs.exclude(completed_at__isnull=True).order_by("-completed_at").first()
                if row and getattr(row, "completed_at", None):
                    dt = row.completed_at
            if dt is None and has_field(Enrollment, "created_at"):
                row2 = qs.order_by("-created_at").first()
                if row2 and getattr(row2, "created_at", None):
                    dt = row2.created_at
            return True, dt
    return False, None

def _parse_dt_local(val):
    if not val:
        return None
    try:
        dt = datetime.strptime(val, "%Y-%m-%dT%H:%M")
    except Exception:
        return None
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.get_current_timezone())
    return dt

def _ensure_completed_enrollment(user, training, dt=None):
    if Enrollment is None:
        return
    obj, _created = Enrollment.objects.get_or_create(user=user, training=training)
    if has_field(Enrollment, "status"):
        obj.status = "completed"
    if has_field(Enrollment, "is_passed"):
        obj.is_passed = True
    if has_field(Enrollment, "completed_at"):
        obj.completed_at = dt or getattr(obj, "completed_at", None) or timezone.now()
    if has_field(Enrollment, "created_at") and not getattr(obj, "created_at", None):
        obj.created_at = timezone.now()
    obj.save()


# ========== JobRoleAssignment (ORİJİNAL) ==========
if JobRoleAssignment:
    ROLE_FNAME = fk_name_to(JobRoleAssignment, JobRole)

    @admin.action(description="Görev tanımı ihtiyaçlarını oluştur/güncelle")
    def generate_role_needs(modeladmin, request, queryset):
        from .utils.needs import create_needs_for_assignment
        processed = 0
        for a in queryset:
            try:
                create_needs_for_assignment(a)
                processed += 1
            except Exception:
                pass
        messages.success(request, f"{processed} atama işlendi.")

    @admin.register(JobRoleAssignment)
    class JobRoleAssignmentAdmin(admin.ModelAdmin):
        change_form_template = "admin/trainings/jobroleassignment/change_form.html"

        list_display = ["user"]
        if ROLE_FNAME:
            list_display.append(ROLE_FNAME)
        for cand in ("is_active", "start_date", "end_date", "created_at"):
            if has_field(JobRoleAssignment, cand):
                list_display.append(cand)
        list_display = tuple(list_display)

        list_filter = tuple([f for f in ("is_active",) if has_field(JobRoleAssignment, f)])

        search_fields = ["user__username"]
        if ROLE_FNAME:
            search_fields.append(f"{ROLE_FNAME}__name")
        search_fields = tuple(search_fields)

        ac = ["user"]
        if ROLE_FNAME:
            ac.append(ROLE_FNAME)
        autocomplete_fields = tuple(ac)

        actions = (generate_role_needs,)

        def formfield_for_foreignkey(self, db_field, request, **kwargs):
            formfield = super().formfield_for_foreignkey(db_field, request, **kwargs)
            if db_field.name in ("user", ROLE_FNAME):
                w = formfield.widget
                for attr, val in {
                    "can_add_related": False,
                    "can_delete_related": False,
                    "can_view_related": False,
                    "can_change_related": True,
                }.items():
                    try:
                        setattr(w, attr, val)
                    except Exception:
                        pass
            return formfield

        def get_changeform_initial_data(self, request):
            initial = super().get_changeform_initial_data(request)
            u = request.GET.get("user")
            if u and has_field(JobRoleAssignment, "user"):
                initial["user"] = u
            return initial

        def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
            extra_context = extra_context or {}
            rows = []
            add_role_url = None
            if object_id and TrainingRequirement and Training and ROLE_FNAME:
                obj = self.get_object(request, object_id)
                if obj is not None:
                    user = getattr(obj, "user", None)
                    if user:
                        add_role_url = f"/admin/trainings/jobroleassignment/add/?user={user.pk}"

                    role_list = []
                    qs_assign = JobRoleAssignment.objects.filter(user=user)
                    if has_field(JobRoleAssignment, "is_active"):
                        qs_assign = qs_assign.filter(is_active=True)
                    for a in qs_assign:
                        role = getattr(a, ROLE_FNAME, None)
                        if role:
                            role_list.append(role)

                    role_fk = fk_name_to(TrainingRequirement, JobRole) or "role"
                    req_qs = TrainingRequirement.objects.filter(**{f"{role_fk}__in": role_list}).select_related("training")
                    by_training = {}
                    for req in req_qs:
                        tr = getattr(req, "training", None)
                        if not tr:
                            continue
                        tid = tr.pk
                        mand = getattr(req, "is_mandatory", True) if has_field(TrainingRequirement, "is_mandatory") else None
                        if tid not in by_training:
                            by_training[tid] = {"training": tr, "is_mandatory": mand}
                        else:
                            prev = by_training[tid]["is_mandatory"]
                            by_training[tid]["is_mandatory"] = (prev or mand) if prev is not None else mand

                    for tid, item in by_training.items():
                        tr = item["training"]
                        completed, dt = _completion_info(user, tr)
                        rows.append({
                            "training": tr,
                            "is_mandatory": item["is_mandatory"],
                            "completed": completed,
                            "completed_date": dt,
                        })

            extra_context["requirement_rows"] = rows
            extra_context["add_role_url"] = add_role_url
            extra_context["role_field_name"] = ROLE_FNAME
            return super().changeform_view(request, object_id, form_url, extra_context)

        def save_model(self, request, obj, form, change):
            super().save_model(request, obj, form, change)
            try:
                user = getattr(obj, "user", None)
                if not user or Training is None:
                    return
                for key, val in request.POST.items():
                    if not key.startswith("comp_"):
                        continue
                    tid = key.split("_", 1)[1]
                    try:
                        tr = Training.objects.get(pk=tid)
                    except Exception:
                        continue
                    if val == "yes":
                        dt = _parse_dt_local(request.POST.get(f"compdt_{tid}"))
                        _ensure_completed_enrollment(user, tr, dt)
            except Exception:
                pass

        # Orijinali MENÜDE GİZLE
        def get_model_perms(self, request):
            return {}

        class Media:
            js = (
                "trainings/admin/jobroleassignment_form.js",
                "trainings/admin/assignment_requirements.js",
            )


# ========== Proxy Admin: "Kullanıcıya Görev Atama" ==========
if JobRoleAssignment and 'JobRoleAssignmentQuickAdd' in globals():
    @admin.register(JobRoleAssignmentQuickAdd)
    class JobRoleAssignmentQuickAddAdmin(JobRoleAssignmentAdmin):
        """Sol menüde görünen kısa yol. Changelist -> direkt Add sayfası."""
        # Menüde GÖRÜNSÜN
        def get_model_perms(self, request):
            return {"view": True}

        # Listeye tıklanınca Add ekranına yönlendir
        def changelist_view(self, request, extra_context=None):
            url = reverse("admin:trainings_jobroleassignment_add")
            return redirect(url)


# ========== Proxy Admin: "Kullanıcılara Atanmış Görevler" ==========
if JobRoleAssignment and 'JobRoleAssignmentListed' in globals():
    @admin.register(JobRoleAssignmentListed)
    class JobRoleAssignmentListedAdmin(JobRoleAssignmentAdmin):
        """Sol menüde liste ekranı olarak görünsün."""
        def get_model_perms(self, request):
            return {"view": True}


# ========== Enrollment ==========
if Enrollment:
    @admin.register(Enrollment)
    class EnrollmentAdmin(admin.ModelAdmin):
        list_display = (
            "user",
            "training",
            "status" if has_field(Enrollment, "status") else None,
            "is_passed" if has_field(Enrollment, "is_passed") else None,
            "created_at" if has_field(Enrollment, "created_at") else None,
            "completed_at" if has_field(Enrollment, "completed_at") else None,
        )
        list_display = tuple([f for f in list_display if f])
        list_filter = tuple([f for f in ("status", "is_passed") if has_field(Enrollment, f)])
        date_hierarchy = "created_at" if has_field(Enrollment, "created_at") else None
        search_fields = ("user__username", "training__title", "training__code")
        autocomplete_fields = ("user", "training")


# ========== Certificate ==========
if Certificate:
    @admin.register(Certificate)
    class CertificateAdmin(admin.ModelAdmin):
        list_display = (
            "user",
            "training",
            "serial" if has_field(Certificate, "serial") else None,
            "issued_at" if has_field(Certificate, "issued_at") else None,
            "expires_at" if has_field(Certificate, "expires_at") else None,
        )
        list_display = tuple([f for f in list_display if f])
        search_fields = ("user__username", "training__title", "serial")
        autocomplete_fields = ("user", "training")


# ========== TrainingNeed (ÖNE ALINDI: TrainingPlan’den ÖNCE KAYDET) ==========
def _has_completed(user, training) -> bool:
    ok, _ = _completion_info(user, training)
    return ok

if TrainingNeed:
    class SourceFilter(admin.SimpleListFilter):
        title = "Kaynak"
        parameter_name = "src"

        def lookups(self, request, model_admin):
            return (
                ("manual", "Manuel"),
                ("role", "Görev Gereği"),
                ("other", "Diğer/Bilinmeyen"),
            )

        def queryset(self, request, queryset):
            val = self.value()
            if not val:
                return queryset
            if has_field(TrainingNeed, "source"):
                if val == "manual":
                    return queryset.filter(source__iexact="manual")
                if val == "role":
                    return queryset.filter(source__iexact="role")
                if val == "other":
                    return queryset.exclude(source__in=["manual", "role"]) | queryset.filter(source__isnull=True)
            note_q = {}
            if has_field(TrainingNeed, "note"):
                note_q["note__istartswith"] = "Görev tanımı:"
            elif has_field(TrainingNeed, "description"):
                note_q["description__istartswith"] = "Görev tanımı:"
            if val == "role" and note_q:
                return queryset.filter(**note_q)
            if val == "manual" and note_q:
                return queryset.exclude(**note_q)
            return queryset

    @admin.action(description="Seçili ihtiyaçları KAPAT (çözüldü)")
    def mark_resolved(modeladmin, request, queryset):
        changed = 0
        if has_field(TrainingNeed, "is_resolved"):
            changed = queryset.update(is_resolved=True)
        elif has_field(TrainingNeed, "status"):
            changed = queryset.update(status="closed")
        messages.success(request, f"{changed} kayıt güncellendi.")

    @admin.action(description="Seçili ihtiyaçları AÇIK işaretle")
    def mark_open(modeladmin, request, queryset):
        changed = 0
        if has_field(TrainingNeed, "is_resolved"):
            changed = queryset.update(is_resolved=False)
        elif has_field(TrainingNeed, "status"):
            changed = queryset.update(status="open")
        messages.success(request, f"{changed} kayıt güncellendi.")

    @admin.register(TrainingNeed)
    class TrainingNeedAdmin(admin.ModelAdmin):
        list_display = (
            "training",
            "user" if has_field(TrainingNeed, "user") else None,
            "source_badge",
            "already_completed",
            "status" if has_field(TrainingNeed, "status") else None,
            "is_resolved" if has_field(TrainingNeed, "is_resolved") else None,
            "due_date" if has_field(TrainingNeed, "due_date") else None,
            "created_at" if has_field(TrainingNeed, "created_at") else None,
            "short_note",
        )
        list_display = tuple([f for f in list_display if f])

        list_filter = (SourceFilter,)
        if has_field(TrainingNeed, "status"):
            list_filter += ("status",)
        if has_field(TrainingNeed, "is_resolved"):
            list_filter += ("is_resolved",)
        if has_field(TrainingNeed, "due_date"):
            list_filter += ("due_date",)

        search_fields = ("training__title", "training__code")
        if has_field(TrainingNeed, "note"):
            search_fields += ("note",)
        if has_field(TrainingNeed, "description"):
            search_fields += ("description",)
        if has_field(TrainingNeed, "user"):
            search_fields += ("user__username",)

        list_select_related = ("training", "user") if has_field(TrainingNeed, "user") else ("training",)
        date_hierarchy = "created_at" if has_field(TrainingNeed, "created_at") else None
        ordering = ("-id",)
        actions = (mark_resolved, mark_open)

        readonly_fields = tuple([f for f in ("created_at",) if has_field(TrainingNeed, f)])
        autocomplete_fields = tuple([f for f in ("training", "user") if has_field(TrainingNeed, f)])

        def get_queryset(self, request):
            qs = super().get_queryset(request)
            if not (Enrollment and has_field(TrainingNeed, "user")):
                return qs
            done = Q()
            if has_field(Enrollment, "status"):
                done |= Q(status="completed")
            if has_field(Enrollment, "is_passed"):
                done |= Q(is_passed=True)
            if has_field(Enrollment, "completed_at"):
                done |= Q(completed_at__isnull=False)
            if not done:
                return qs
            completed_exists = Exists(
                Enrollment.objects.filter(
                    user=OuterRef("user"),
                    training=OuterRef("training"),
                ).filter(done)
            )
            return qs.annotate(_c=completed_exists).filter(_c=False)

        def short_note(self, obj):
            text = ""
            if has_field(TrainingNeed, "note"):
                text = getattr(obj, "note", "") or ""
            elif has_field(TrainingNeed, "description"):
                text = getattr(obj, "description", "") or ""
            return Truncator(text).chars(60)
        short_note.short_description = "Not"

        def source_badge(self, obj):
            src = ""
            if has_field(TrainingNeed, "source"):
                src = (getattr(obj, "source", "") or "").lower()
            else:
                text = ""
                if has_field(TrainingNeed, "note"):
                    text = getattr(obj, "note", "") or ""
                elif has_field(TrainingNeed, "description"):
                    text = getattr(obj, "description", "") or ""
                if text.lower().startswith("görev tanımı:"):
                    src = "role"
                else:
                    src = "manual"

            if src == "manual":
                cls = "tn-badge tn-badge-manual"; label = "Manuel"
            elif src == "role":
                cls = "tn-badge tn-badge-role"; label = "Görev Gereği"
            else:
                cls = "tn-badge tn-badge-other"; label = (src or "Bilinmiyor").capitalize()
            return format_html('<span class="{}">{}</span>', cls, label)
        source_badge.short_description = "Kaynak"

        def already_completed(self, obj):
            if not has_field(TrainingNeed, "user"):
                return False
            ok, _ = _completion_info(getattr(obj, "user", None), getattr(obj, "training", None))
            return ok
        already_completed.boolean = True
        already_completed.short_description = "Alınmış mı?"

        class Media:
            css = {"all": ("trainings/admin/trainingneed_list.css",)}
            js = ("trainings/admin/trainingneed_list.js",)


# ========== TrainingPlan (Katılımcı Ekle/Çıkar butonlu) ==========
class TrainingPlanAdminForm(forms.ModelForm):
    bulk_users_add = forms.ModelMultipleChoiceField(
        label="Katılımcı Ekle (çoklu seç)",
        queryset=get_user_model().objects.none(),
        required=False,
        widget=forms.SelectMultiple(attrs={"size": "12", "style": "min-width:260px;"}),
        help_text="Ctrl/Shift ile birden fazla kullanıcı seçip ‘Ekle’ye tıklayın."
    )
    bulk_users_remove = forms.ModelMultipleChoiceField(
        label="Katılımcı Çıkar (mevcutlardan seç)",
        queryset=get_user_model().objects.none(),
        required=False,
        widget=forms.SelectMultiple(attrs={"size": "10", "style": "min-width:260px;"}),
        help_text="Mevcut katılımcılardan birden fazla seçip ‘Çıkar’a tıklayın."
    )

    class Meta:
        model = TrainingPlan
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        User = get_user_model()
        # Ekle alanı: aktif tüm kullanıcılar
        self.fields["bulk_users_add"].queryset = User.objects.filter(is_active=True).order_by("first_name", "last_name", "username")
        # Çıkar alanı: sadece mevcut katılımcılar
        existing_ids = []
        if self.instance and getattr(self.instance, "pk", None) and TrainingPlanAttendee:
            existing_ids = list(
                TrainingPlanAttendee.objects.filter(plan=self.instance).values_list("user_id", flat=True)
            )
        self.fields["bulk_users_remove"].queryset = User.objects.filter(id__in=existing_ids).order_by("first_name", "last_name", "username")


if TrainingPlan:
    @admin.register(TrainingPlan)
    class TrainingPlanAdmin(admin.ModelAdmin):
        form = TrainingPlanAdminForm

        list_display = (
            "training",
            "start_datetime" if has_field(TrainingPlan, "start_datetime") else None,
            "end_datetime" if has_field(TrainingPlan, "end_datetime") else None,
            "status" if has_field(TrainingPlan, "status") else None,
            "need" if has_field(TrainingPlan, "need") else None,
            "created_by" if has_field(TrainingPlan, "created_by") else None,
        )
        list_display = tuple([f for f in list_display if f])
        list_filter = tuple([f for f in ("status",) if has_field(TrainingPlan, f)])
        search_fields = ("training__title", "training__code")

        # autocomplete_fields dinamik: model alanı var ve admin’e kayıtlı ise ekle
        ac = []
        for fname, model_cls in (("training", Training), ("need", TrainingNeed), ("created_by", get_user_model())):
            if has_field(TrainingPlan, fname) and model_cls is not None:
                try:
                    if model_cls in admin.site._registry:  # kayıtlı mı?
                        ac.append(fname)
                except Exception:
                    # _registry erişilemez ise en azından training’i ekleyelim
                    if fname == "training":
                        ac.append(fname)
        autocomplete_fields = tuple(ac)

        readonly_fields = (
            "participants_readonly",
            "op_buttons_add",
            "op_buttons_remove",
        ) + tuple([f for f in ("created_at", "updated_at", "created_by") if has_field(TrainingPlan, f)])

        def get_fieldsets(self, request, obj=None):
            """
            SOL: Katılımcılar (salt okunur)
            SAĞ: Çoklu seçim + BUTON (Ekle/Çıkar)
            """
            base = [
                ("", {
                    "fields": (
                        "training",
                        "need" if has_field(TrainingPlan, "need") else None,
                    )
                }),
                ("Plan", {
                    "fields": (
                        ("start_datetime", "end_datetime") if has_field(TrainingPlan, "start_datetime") else ("end_datetime",),
                        ("delivery", "status") if has_field(TrainingPlan, "status") else ("delivery",),
                        ("capacity", "location"),
                        "instructor_name" if has_field(TrainingPlan, "instructor_name") else None,
                        "notes" if has_field(TrainingPlan, "notes") else None,
                    )
                }),
                ("Katılımcı Yönetimi", {
                    "fields": (
                        ("participants_readonly", "bulk_users_add", "op_buttons_add"),
                        ("bulk_users_remove", "op_buttons_remove"),
                    )
                }),
            ]
            # None’ları temizle
            cleaned = []
            for title, opts in base:
                fields = tuple([f for f in opts["fields"] if f])
                cleaned.append((title, {"fields": fields}))
            # Sistem alanları en sona (varsa)
            tail = []
            if has_field(TrainingPlan, "created_by"):
                tail.append("created_by")
            if has_field(TrainingPlan, "created_at"):
                tail.append("created_at")
            if has_field(TrainingPlan, "updated_at"):
                tail.append("updated_at")
            if tail:
                cleaned.append(("Sistem", {"fields": tuple(tail)}))
            return cleaned

        # --- SAĞDAKİ BUTONLAR (gerçek submit düğmeleri) ---------------------

        @admin.display(description=" ")
        def op_buttons_add(self, obj):
            return format_html(
                "<div style='display:flex;flex-direction:column;gap:6px;min-width:140px'>"
                "  <button name='_apply_add' value='1' type='submit' class='default' "
                "          style='padding:6px 10px;border-radius:8px;border:1px solid #e5e7eb;cursor:pointer;'>Ekle</button>"
                "  <button name='_apply_add_stay' value='1' type='submit' "
                "          style='padding:6px 10px;border-radius:8px;border:1px solid #e5e7eb;cursor:pointer;'>Ekle ve sayfada kal</button>"
                "</div>"
            )

        @admin.display(description=" ")
        def op_buttons_remove(self, obj):
            return format_html(
                "<div style='display:flex;flex-direction:column;gap:6px;min-width:140px'>"
                "  <button name='_apply_remove' value='1' type='submit' "
                "          style='padding:6px 10px;border-radius:8px;border:1px solid #e5e7eb;cursor:pointer;'>Çıkar</button>"
                "  <button name='_apply_remove_stay' value='1' type='submit' "
                "          style='padding:6px 10px;border-radius:8px;border:1px solid #e5e7eb;cursor:pointer;'>Çıkar ve sayfada kal</button>"
                "</div>"
            )

        # --- Salt okunur katılımcı listesi (solda) --------------------------

        def participants_readonly(self, obj):
            """Planın katılımcılarını pastel chip şeklinde göster (salt okunur)."""
            if not obj or not getattr(obj, "pk", None) or TrainingPlanAttendee is None:
                return format_html("<span style='color:#6b7280'>Bu plana henüz katılımcı eklenmemiş.</span>")
            rows = (
                TrainingPlanAttendee.objects
                .select_related("user")
                .filter(plan=obj)
                .order_by("user__username")
            )
            if not rows.exists():
                return format_html("<span style='color:#6b7280'>Bu plana henüz katılımcı eklenmemiş.</span>")
            chip_css = (
                "display:inline-block;margin:3px 6px 0 0;padding:4px 8px;"
                "border:1px solid #e0e7ff;border-radius:999px;"
                "background:#eef2ff;color:#1f2937;font-size:12px;line-height:1;"
            )
            items = []
            for r in rows:
                u = getattr(r, "user", None)
                if not u:
                    continue
                try:
                    full = u.get_full_name()
                except Exception:
                    full = ""
                label = full or getattr(u, "username", "") or str(u)
                items.append((format_html('<span style="{}">{}</span>', chip_css, label),))
            return format_html_join("", "{}", items)
        participants_readonly.short_description = "Katılımcılar (salt okunur)"

        # --- Kayıt kaydedilirken toplu ekleme/çıkarma -----------------------

        def save_model(self, request, obj, form, change):
            """
            Sağdaki çoklu seçimlerden ekleme/çıkarma işlemlerini uygular.
            Butonlar: _apply_add, _apply_add_stay, _apply_remove, _apply_remove_stay
            """
            super().save_model(request, obj, form, change)
            if not TrainingPlanAttendee or not getattr(obj, "pk", None):
                return

            want_add = "_apply_add" in request.POST or "_apply_add_stay" in request.POST
            want_remove = "_apply_remove" in request.POST or "_apply_remove_stay" in request.POST

            # Eğer kullanıcı standart "Kaydet"e bastıysa, her iki listeyi de uygula
            if not (want_add or want_remove):
                want_add = True
                want_remove = True

            if want_add:
                add_ids = request.POST.getlist("bulk_users_add")
                for uid in add_ids:
                    try:
                        TrainingPlanAttendee.objects.get_or_create(plan=obj, user_id=int(uid))
                    except Exception:
                        pass

            if want_remove:
                rem_ids = request.POST.getlist("bulk_users_remove")
                if rem_ids:
                    try:
                        TrainingPlanAttendee.objects.filter(plan=obj, user_id__in=[int(x) for x in rem_ids]).delete()
                    except Exception:
                        pass

        class Media:
            css = {"all": ("trainings/admin/trainingplan_form.css",)}


# ========== OnlineVideo / VideoProgress ==========
if OnlineVideo:
    @admin.register(OnlineVideo)
    class OnlineVideoAdmin(admin.ModelAdmin):
        list_display = ("training", "duration_display", "is_active", "created_at")
        list_filter = ("is_active",)
        search_fields = ("training__title", "training__code", "title")
        list_select_related = ("training",)
        autocomplete_fields = ("training",)
        readonly_fields = tuple(f for f in ("created_at", "updated_at") if has_field(OnlineVideo, f))

        def duration_display(self, obj):
            try:
                return obj.duration_hours_display
            except Exception:
                return getattr(obj, "duration_seconds", None)
        duration_display.short_description = "Süre"

if VideoProgress:
    @admin.register(VideoProgress)
    class VideoProgressAdmin(admin.ModelAdmin):
        list_display = ("user", "video", "max_position_seconds", "completed", "completed_at", "updated_at")
        list_filter = ("completed",)
        search_fields = ("user__username", "video__training__title", "video__title")
        list_select_related = ("user", "video", "video__training")
        readonly_fields = ("user", "video", "last_position_seconds", "max_position_seconds", "completed", "completed_at", "created_at", "updated_at")
