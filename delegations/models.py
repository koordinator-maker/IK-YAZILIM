from django.db import models
from django.utils import timezone

# Projedeki JobRole modeline doğrudan FK (app label + Model adı)
JOBROLE_MODEL = 'trainings.JobRole'


class DelegationDocument(models.Model):
    """
    Matris sayfasının üst-bilgi alanları (tekil kayıt).
    """
    form_no = models.CharField(max_length=50, blank=True, default='')
    revizyon_tarihi = models.DateField(null=True, blank=True)
    guncelleme_tarihi = models.DateField(null=True, blank=True)

    class Meta:
        verbose_name = "Vekalet Tablosu Üst Bilgisi"
        verbose_name_plural = "Vekalet Tablosu Üst Bilgisi"

    def save(self, *args, **kwargs):
        # Güncelleme tarihi boşsa bugünün tarihiyle doldur
        if self.guncelleme_tarihi is None:
            self.guncelleme_tarihi = timezone.localdate()
        super().save(*args, **kwargs)

    @classmethod
    def singleton(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return f"Vekalet Üst Bilgi (Form No: {self.form_no or '-'})"


class RoleDelegation(models.Model):
    """
    'from_role' -> 'to_role' vekalet izni.
    Matris hücresini temsil eder; aktif/pasif tutulur.
    """
    from_role = models.ForeignKey(
        JOBROLE_MODEL, on_delete=models.CASCADE, related_name='delegations_given'
    )
    to_role = models.ForeignKey(
        JOBROLE_MODEL, on_delete=models.CASCADE, related_name='delegations_received'
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Vekalet Tanımı"
        verbose_name_plural = "Vekalet Tanımları"
        constraints = [
            models.UniqueConstraint(
                fields=['from_role', 'to_role'],
                name='uniq_role_delegation'
            ),
            models.CheckConstraint(
                check=~models.Q(from_role=models.F('to_role')),
                name='no_self_delegation'
            ),
        ]

    def __str__(self):
        return f"{self.from_role} -> {self.to_role} ({'Aktif' if self.is_active else 'Pasif'})"
