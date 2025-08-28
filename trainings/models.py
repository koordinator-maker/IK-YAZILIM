from django.conf import settings
from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator  # (OnlineVideo için)

# =========================================================
# 1) TRAINING (Eğitim) & İLGİLİ MODELLER
# =========================================================

class Training(models.Model):
    title = models.CharField("Başlık", max_length=200)
    code = models.CharField("Kod", max_length=50, blank=True, null=True)
    description = models.TextField("Açıklama", blank=True)
    duration_hours = models.PositiveIntegerField("Süre (saat)", blank=True, null=True)
    is_active = models.BooleanField("Aktif mi?", default=True)
    created_at = models.DateTimeField("Oluşturulma", default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Eğitim"
        verbose_name_plural = "Eğitimler"
        ordering = ["title"]
        indexes = [models.Index(fields=["is_active"])]

    def __str__(self):
        return self.title or f"Training #{self.pk}"


class Enrollment(models.Model):
    STATUS_CHOICES = (
        ("enrolled", "Kayıtlı"),
        ("completed", "Tamamlandı"),
        ("cancelled", "İptal"),
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="enrollments",
        verbose_name="Kullanıcı",
    )
    training = models.ForeignKey(
        "trainings.Training",
        on_delete=models.CASCADE,
        related_name="enrollments",
        verbose_name="Eğitim",
    )
    status = models.CharField("Durum", max_length=12, choices=STATUS_CHOICES, default="enrolled")
    is_passed = models.BooleanField("Başarılı mı?", default=False)
    completed_at = models.DateTimeField("Tamamlanma", null=True, blank=True)

    created_at = models.DateTimeField("Oluşturulma", default=timezone.now)

    class Meta:
        verbose_name = "Katılım"
        verbose_name_plural = "Katılımlar"
        indexes = [
            models.Index(fields=["user", "training"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"{self.user} → {self.training} ({self.get_status_display()})"


def cert_upload_to(instance, filename):
    return f"certificates/{instance.user_id}/{timezone.now():%Y%m%d%H%M%S}-{filename}"

class Certificate(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="certificates",
        verbose_name="Kullanıcı",
    )
    training = models.ForeignKey(
        "trainings.Training",
        on_delete=models.CASCADE,
        related_name="certificates",
        verbose_name="Eğitim",
    )
    file = models.FileField("Dosya (PDF)", upload_to=cert_upload_to, blank=True, null=True)
    serial = models.CharField("Seri", max_length=50, blank=True, null=True)
    issued_at = models.DateTimeField("Düzenlenme", default=timezone.now)
    expires_at = models.DateTimeField("Geçerlilik Bitiş", null=True, blank=True)

    created_at = models.DateTimeField("Oluşturulma", default=timezone.now)

    class Meta:
        verbose_name = "Sertifika"
        verbose_name_plural = "Sertifikalar"
        indexes = [
            models.Index(fields=["user", "training"]),
            models.Index(fields=["issued_at"]),
        ]

    def __str__(self):
        return f"Cert #{self.pk} - {self.user} / {self.training}"

# =========================================================
# 2) GÖREV BAZLI MODELLER
# =========================================================

class JobRole(models.Model):
    name = models.CharField("Görev Adı", max_length=150, unique=True)
    code = models.CharField("Kod", max_length=50, unique=True, blank=True, null=True)
    description = models.TextField("Açıklama", blank=True)

    is_active = models.BooleanField("Aktif mi?", default=True)
    created_at = models.DateTimeField("Oluşturulma", default=timezone.now)

    class Meta:
        verbose_name = "Görev Tanımı"
        verbose_name_plural = "Görev Tanımları"
        ordering = ["name"]

    def __str__(self):
        return self.name


class TrainingRequirement(models.Model):
    MANDATORY_CHOICES = (
        ("required", "Zorunlu"),
        ("optional", "Önerilen"),
    )

    job_role = models.ForeignKey(
        "trainings.JobRole",
        on_delete=models.CASCADE,
        related_name="requirements",
        verbose_name="Görev"
    )
    training = models.ForeignKey(
        "trainings.Training",
        on_delete=models.PROTECT,
        related_name="role_requirements",
        verbose_name="Eğitim"
    )
    requirement_type = models.CharField(
        "Tür",
        max_length=10,
        choices=MANDATORY_CHOICES,
        default="required"
    )
    validity_months = models.PositiveIntegerField(
        "Geçerlilik (ay)",
        null=True, blank=True,
        help_text="Boş veya 0 = süresiz/tekrarsız."
    )

    notes = models.TextField("Notlar", blank=True)
    is_active = models.BooleanField("Aktif mi?", default=True)
    created_at = models.DateTimeField("Oluşturulma", default=timezone.now)

    class Meta:
        verbose_name = "Görev Eğitim Gerekliliği"
        verbose_name_plural = "Görev Eğitim Gereklilikleri"
        constraints = [
            models.UniqueConstraint(
                fields=["job_role", "training"],
                name="uq_jobrole_training_unique"
            ),
            models.CheckConstraint(
                name="ck_validity_nonnegative",
                check=models.Q(validity_months__gte=0) | models.Q(validity_months__isnull=True),
            ),
        ]

    def __str__(self):
        return f"{self.job_role} → {self.training} ({self.get_requirement_type_display()})"


class JobRoleAssignment(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="job_assignments",
        verbose_name="Kullanıcı"
    )
    job_role = models.ForeignKey(
        "trainings.JobRole",
        on_delete=models.PROTECT,
        related_name="assignments",
        verbose_name="Görev"
    )
    effective_from = models.DateField("Başlangıç", default=timezone.now)
    effective_to = models.DateField("Bitiş", null=True, blank=True)

    is_active = models.BooleanField("Aktif mi?", default=True)
    created_at = models.DateTimeField("Oluşturulma", default=timezone.now)

    class Meta:
        verbose_name = "Kullanıcı Görev Ataması"
        verbose_name_plural = "Kullanıcı Görev Atamaları"
        indexes = [
            models.Index(fields=["user", "is_active"]),
            models.Index(fields=["job_role", "is_active"]),
        ]
        constraints = [
            models.CheckConstraint(
                name="ck_effective_dates",
                check=models.Q(effective_to__isnull=True) | models.Q(effective_to__gte=models.F("effective_from"))
            ),
        ]

    def __str__(self):
        status = "Aktif" if self.is_active else "Pasif"
        return f"{self.user} → {self.job_role} ({status})"


# =========================================================
# 3) TRAINING NEED
# =========================================================

class TrainingNeed(models.Model):
    SOURCE_CHOICES = (
        ("role_auto", "Rol Otomatik"),
        ("manager", "Yönetici Talebi"),
        ("career", "Kariyer Gelişim Talebi"),
        ("customer", "Müşteri Talebi"),
        ("manual", "Manuel"),
    )
    STATUS_CHOICES = (
        ("pending", "Beklemede"),
        ("approved", "Onaylandı"),
        ("rejected", "Reddedildi"),
        ("planned", "Planlandı"),
        ("done", "Tamamlandı"),
        ("cancelled", "İptal"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="training_needs", verbose_name="Kullanıcı"
    )
    training = models.ForeignKey(
        "trainings.Training", on_delete=models.PROTECT,
        related_name="training_needs", verbose_name="Eğitim"
    )

    source = models.CharField("Kaynak", max_length=20, choices=SOURCE_CHOICES, default="role_auto")
    status = models.CharField("Durum", max_length=12, choices=STATUS_CHOICES, default="pending")
    priority = models.PositiveSmallIntegerField("Öncelik", default=3, help_text="1=En yüksek, 5=En düşük")

    job_role = models.ForeignKey(
        "trainings.JobRole", on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name="Görev", related_name="training_needs"
    )
    assignment = models.ForeignKey(
        "trainings.JobRoleAssignment", on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name="Görev Ataması", related_name="training_needs"
    )

    due_date = models.DateField("Hedef Tarih", null=True, blank=True)

    is_open = models.BooleanField("Açık Kayıt", default=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="created_training_needs", verbose_name="Oluşturan"
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="approved_training_needs", verbose_name="Onaylayan"
    )

    created_at = models.DateTimeField("Oluşturulma", default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Eğitim İhtiyacı"
        verbose_name_plural = "Eğitim İhtiyaçları"
        indexes = [
            models.Index(fields=["user", "is_open"]),
            models.Index(fields=["training", "status"]),
            models.Index(fields=["source"]),
        ]
        constraints = [
            models.UniqueConstraint(fields=["user", "training", "is_open"], name="uq_open_need_per_user_training"),
        ]

    def __str__(self):
        return f"{self.user} → {self.training} [{self.get_status_display()}]"


# =========================================================
# 4) TRAINING PLAN
# =========================================================

class TrainingPlan(models.Model):
    DELIVERY_CHOICES = (
        ("onsite", "Sınıf/Onsite"),
        ("online", "Online"),
        ("hybrid", "Hibrit"),
    )
    STATUS_CHOICES = (
        ("planned", "Planlandı"),
        ("scheduled", "Takvimlendi"),
        ("completed", "Tamamlandı"),
        ("cancelled", "İptal"),
    )

    training = models.ForeignKey(
        "trainings.Training",
        on_delete=models.PROTECT,
        related_name="plans",
        verbose_name="Eğitim",
    )
    need = models.ForeignKey(
        "trainings.TrainingNeed",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="plans",
        verbose_name="Kaynak İhtiyaç",
    )

    start_datetime = models.DateTimeField("Başlangıç")
    end_datetime = models.DateTimeField("Bitiş")

    capacity = models.PositiveIntegerField("Kontenjan", null=True, blank=True)
    location = models.CharField("Lokasyon", max_length=200, blank=True)
    instructor_name = models.CharField("Eğitmen", max_length=150, blank=True)

    delivery = models.CharField("Sunum Türü", max_length=10, choices=DELIVERY_CHOICES, default="online")
    status = models.CharField("Durum", max_length=10, choices=STATUS_CHOICES, default="planned")

    notes = models.TextField("Notlar", blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="created_training_plans",
        verbose_name="Oluşturan",
    )
    created_at = models.DateTimeField("Oluşturulma", default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Eğitim Planı"
        verbose_name_plural = "Eğitim Planları"
        ordering = ["-start_datetime"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["start_datetime"]),
        ]

    def __str__(self):
        return f"{self.training} @ {self.start_datetime:%Y-%m-%d %H:%M}"


# ---------- YENİ: Plan Katılımcısı ----------
class TrainingPlanAttendee(models.Model):
    plan = models.ForeignKey(
        "trainings.TrainingPlan",
        on_delete=models.CASCADE,
        related_name="plan_attendees",
        verbose_name="Plan",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="training_plan_attendances",
        verbose_name="Kullanıcı",
    )
    created_at = models.DateTimeField("Oluşturulma", default=timezone.now)

    class Meta:
        verbose_name = "Plan Katılımcısı"
        verbose_name_plural = "Plan Katılımcıları"
        unique_together = [("plan", "user")]
        indexes = [models.Index(fields=["plan", "user"])]

    def __str__(self):
        return f"{self.user} @ {self.plan_id}"


# =========================================================
# 5) ONLINE VIDEO ve İLERLEME
# =========================================================

class OnlineVideo(models.Model):
    training = models.OneToOneField(
        "trainings.Training",
        on_delete=models.PROTECT,
        related_name="online_video",
        verbose_name="Eğitim",
    )
    title = models.CharField("Başlık", max_length=200, blank=True)
    description = models.TextField("Açıklama", blank=True)
    video = models.FileField("Video (MP4)", upload_to="videos/")
    thumbnail = models.ImageField("Küçük Resim", upload_to="thumbnails/", null=True, blank=True)
    duration_seconds = models.PositiveIntegerField("Süre (sn)", validators=[MinValueValidator(1)])
    is_active = models.BooleanField("Aktif mi?", default=True)

    created_at = models.DateTimeField("Oluşturulma", default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Online Video"
        verbose_name_plural = "Online Videolar"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["is_active"])]

    def __str__(self):
        return self.title or f"{self.training.title} (Online)"

    @property
    def duration_hours_display(self):
        s = int(self.duration_seconds)
        h, rem = divmod(s, 3600)
        m, _ = divmod(rem, 60)
        if h:
            return f"{h}s {m}d"
        return f"{m}d"


class VideoProgress(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="video_progress")
    video = models.ForeignKey("trainings.OnlineVideo", on_delete=models.CASCADE, related_name="progress")
    last_position_seconds = models.FloatField("Son Konum (sn)", default=0.0)
    max_position_seconds = models.FloatField("Maks Konum (sn)", default=0.0)
    completed = models.BooleanField("Tamamlandı", default=False)
    completed_at = models.DateTimeField("Tamamlanma", null=True, blank=True)
    created_at = models.DateTimeField("Oluşturulma", default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("user", "video")]
        verbose_name = "Video İlerleme"
        verbose_name_plural = "Video İlerlemeleri"
        indexes = [
            models.Index(fields=["user", "video"]),
            models.Index(fields=["completed"]),
        ]

    def __str__(self):
        return f"{self.user} / {self.video}"

    def percent(self) -> int:
        if not self.video_id or not self.video.duration_seconds:
            return 0
        p = int((self.max_position_seconds / float(self.video.duration_seconds)) * 100)
        return max(0, min(100, p))
