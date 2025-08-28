from __future__ import annotations

from django import forms
from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone


def M(name: str):
    try:
        return apps.get_model("trainings", name)
    except Exception:
        return None


Training = M("Training")
TrainingPlan = M("TrainingPlan")
TrainingPlanAttendee = M("TrainingPlanAttendee")
TrainingNeed = M("TrainingNeed")
Enrollment = M("Enrollment")

User = get_user_model()


# -----------------------------
# Yardımcı
# -----------------------------
def _ensure_enrollment(user, training):
    """Kullanıcı için ilgili eğitime Enrollment yoksa oluşturur."""
    if not (Enrollment and user and training):
        return
    Enrollment.objects.get_or_create(
        user=user,
        training=training,
        defaults={"status": "enrolled"},
    )


# -----------------------------
# PLAN FORMU
# -----------------------------
class TrainingPlanForm(forms.ModelForm):
    """
    - participants: çoklu kullanıcı seçimi (mevcutlara EKLENİR)
    - remove: mevcut listedekilerden kaldırmak için checkbox’lar (template tarafı)
    - tarih/kapasite doğrulamaları
    """
    participants = forms.ModelMultipleChoiceField(
        label="Katılımcı seçimi (mevcutlara eklenir)",
        queryset=User.objects.none(),  # __init__'te set edilir
        required=False,
        help_text="Seçtikleriniz mevcut listeye EKLENİR. Kaldırmak için yukarıdaki listeden işaretleyip kaydedin.",
        widget=forms.SelectMultiple(attrs={"size": 12}),
    )

    class Meta:
        model = TrainingPlan
        fields = [
            "training",
            "need",
            "start_datetime",
            "end_datetime",
            "delivery",
            "status",
            "capacity",
            "location",
            "instructor_name",
            "notes",
        ]
        widgets = {
            "start_datetime": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "end_datetime": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Katılımcı queryset
        self.fields["participants"].queryset = User.objects.order_by("username")

        # Güvenli queryset'ler
        if Training and "training" in self.fields:
            self.fields["training"].queryset = Training.objects.filter(is_active=True).order_by("title")
        if TrainingNeed and "need" in self.fields:
            self.fields["need"].queryset = TrainingNeed.objects.order_by("-created_at")

        # Bilgi: mevcut seçimi initial olarak göstermiyoruz (yanıltmasın);
        # liste üstte ayrı bir “Katılımcılar” panelinde görünüyor.

    # ---- Doğrulamalar ----
    def clean(self):
        cleaned = super().clean()

        start = cleaned.get("start_datetime")
        end = cleaned.get("end_datetime")
        cap = cleaned.get("capacity")

        # tarih
        if start and end and end <= start:
            raise ValidationError("Bitiş tarihi, başlangıç tarihinden sonra olmalı.")
        if start and start < timezone.now() and (not self.instance or not self.instance.pk):
            raise ValidationError("Başlangıç tarihi geçmiş olamaz.")

        # kapasite: toplam sonrası (mevcut + eklenecek - kaldırılacak)
        if cap is not None and cap < 0:
            self.add_error("capacity", "Kontenjan negatif olamaz.")

        # Mevcut/eklenecek/kaldırılacakları toplayıp kapasiteyi aşmayalım
        existing_ids = set()
        if self.instance and getattr(self.instance, "pk", None) and TrainingPlanAttendee:
            existing_ids = set(
                TrainingPlanAttendee.objects.filter(plan=self.instance).values_list("user_id", flat=True)
            )

        selected_users = cleaned.get("participants") or []
        selected_ids = set(u.id for u in selected_users)

        # template’ten remove[]=<uid> olarak gelir
        remove_ids = set()
        try:
            remove_ids = {int(x) for x in self.data.getlist("remove")}
        except Exception:
            remove_ids = set()

        total_after = len((existing_ids | selected_ids) - remove_ids)
        if cap and total_after > cap:
            self.add_error(
                "participants",
                f"Toplam katılımcı sayısı ({total_after}) kapasiteyi ({cap}) aşıyor.",
            )

        return cleaned

    # ---- Kaydetme ----
    def save(self, commit=True):
        """
        - Plan kaydını yapar
        - Seçilen katılımcıları _selected_participants olarak tutar
        - commit=True ise katılımcı senkronunu hemen yapar (MEVCUT + EKLE - KALDIR mantığı)
        """
        plan = super().save(commit=commit)

        self._selected_participants = list(self.cleaned_data.get("participants") or [])

        if commit:
            self.save_participants(plan)

        return plan

    def save_participants(self, plan):
        """
        Plan kaydedildikten sonra katılımcı senkronu + Enrollment aç.
        Mevcutlara EKLE, işaretlileri KALDIR.
        """
        if not plan or not getattr(plan, "pk", None) or TrainingPlanAttendee is None:
            return

        # Post’tan kaldırılacaklar
        try:
            remove_ids = {int(x) for x in self.data.getlist("remove")}
        except Exception:
            remove_ids = set()

        # Mevcut
        existing_ids = set(
            TrainingPlanAttendee.objects.filter(plan=plan).values_list("user_id", flat=True)
        )

        # Eklenecekler (formdan gelen)
        selected_ids = set(u.id for u in getattr(self, "_selected_participants", []))

        # Nihai durum
        keep_ids = (existing_ids | selected_ids) - remove_ids

        # Silinmesi gerekenler
        to_delete = existing_ids - keep_ids
        if to_delete:
            TrainingPlanAttendee.objects.filter(plan=plan, user_id__in=to_delete).delete()

        # Eklenmesi gerekenler
        to_add = keep_ids - existing_ids
        if to_add:
            TrainingPlanAttendee.objects.bulk_create(
                [TrainingPlanAttendee(plan=plan, user_id=uid) for uid in to_add],
                ignore_conflicts=True,
            )

        # Enrollment
        if Training and plan.training_id and keep_ids:
            training = plan.training
            for uid in keep_ids:
                try:
                    u = User.objects.get(pk=uid)
                except User.DoesNotExist:
                    continue
                _ensure_enrollment(u, training)


def get_training_plan_form():
    """Dışa verdiğimiz fabrika fonksiyonu."""
    return TrainingPlanForm


# -----------------------------
# EĞİTİM İHTİYACI (MANUEL) FORM FABRİKASI
# -----------------------------
def TrainingNeedManualFormFactory():
    """
    Manuel eğitim ihtiyacı oluşturma formu.
    """
    class _Form(forms.Form):
        training = forms.ModelChoiceField(
            label="Eğitim",
            queryset=Training.objects.filter(is_active=True).order_by("title") if Training else Training.objects.none(),
        )
        users = forms.ModelMultipleChoiceField(
            label="Kullanıcılar",
            queryset=User.objects.order_by("username"),
            widget=forms.SelectMultiple(attrs={"size": 12}),
        )
        note = forms.CharField(
            label="Not", required=False, widget=forms.Textarea(attrs={"rows": 3})
        )
        due_date = forms.DateField(
            label="Hedef Tarih", required=False, widget=forms.DateInput(attrs={"type": "date"})
        )

    return _Form
