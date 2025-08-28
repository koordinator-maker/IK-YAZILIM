from django.contrib import admin
from django.shortcuts import redirect
from .models import DelegationDocument

# Proxy model: Admin'de sadece kısa yol olarak görünsün
class DelegationMatrixLink(DelegationDocument):
    class Meta:
        proxy = True
        verbose_name = "Vekalet Tablosu (Matris)"
        verbose_name_plural = "Vekalet Tablosu (Matris)"

@admin.register(DelegationMatrixLink)
class DelegationMatrixAdmin(admin.ModelAdmin):
    def changelist_view(self, request, extra_context=None):
        # Admin sol menüden tıklanınca doğrudan matrise götür
        return redirect("/delegations/matrix/")

    # Admin'de gereksiz butonları kapatalım
    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return False
