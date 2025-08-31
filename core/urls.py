# path: core\urls.py
```python
# path: core/urls.py
from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static

# ------------------------------------------------------------
# DİKKAT: Mevcut rotalarınızı koruyun. Aşağıdaki iki "alias" ve
# delegations include'u sadece NoReverseMatch'i ve matrix'i çözer.
# ------------------------------------------------------------

urlpatterns = [
    # Admin
    path("admin/", admin.site.urls),

    # Auth (varsa özel login template'inle uyumlu)
    path("accounts/login/", auth_views.LoginView.as_view(template_name="registration/login.html"), name="login"),
    path("accounts/logout/", auth_views.LogoutView.as_view(), name="logout"),

    # --- URL ADLARI İÇİN CİDDİ, MİNİMAL DOKUNUŞLAR ---
    # base.html şablonunda {% url 'home' %} ve {% url 'mine' %} çağrıları var.
    # Bu adların eksikliği 500 hatasına yol açıyor (NoReverseMatch).
    # Aşağıdaki iki alias, mevcut akışınızı bozmadan adları sağlar:
    path("home-alias/", RedirectView.as_view(url="/", permanent=False), name="home"),
    path("mine-alias/", RedirectView.as_view(url="/mine/", permanent=False), name="mine"),
    # Not:
    # - reverse('home') -> /home-alias/ (sonra /'a yönlendirir)
    # - reverse('mine') -> /mine-alias/ (sonra /mine/'a yönlendirir)
    # Böylece şablon kırılmadan çalışır. İleride trainings.urls içinde
    # doğru adlandırmalar varsa bu alias'ları kaldırabiliriz.

    # --- Vekalet Matrisi ---
    # Şablon: {% url 'delegations:matrix' %}, 'delegations:toggle', 'delegations:update_meta', 'delegations:reset_all'
    path("delegations/", include(("delegations.urls", "delegations"), namespace="delegations")),
]

# Geliştirme ortamında statik & medya servisleri
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)