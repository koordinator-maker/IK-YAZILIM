# core/urls.py
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static

# Site sayfaları
from trainings.views import (
    download_certificate, trainings_list, my_trainings, enroll, whoami
)

# Eğitim ihtiyaçları
from trainings.views_needs import (
    needs_list, need_add_manual
)

# Online eğitimler
from trainings.views_online import (
    online_list, online_watch, online_progress
)

# Planlama (doğrudan import)
from trainings.views_plans import (
    plan_list, plan_create, plan_edit, plan_delete, plan_copy
)

urlpatterns = [
    path("admin/", admin.site.urls),

    # Sertifika
    path("cert/<int:pk>/download/", download_certificate, name="cert-download"),

    # Site sayfaları
    path("", trainings_list, name="home"),
    path("mine/", my_trainings, name="mine"),
    path("whoami/", whoami, name="whoami"),

    # Auth
    path("login/", auth_views.LoginView.as_view(template_name="site/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(next_page="/"), name="logout"),

    # Eğitim
    path("enroll/<int:pk>/", enroll, name="enroll"),

    # Needs
    path("needs/", needs_list, name="needs-list"),
    path("needs/add/", need_add_manual, name="need-add-manual"),

    # Online Eğitimler
    path("online/", online_list, name="online-list"),
    path("online/<int:pk>/", online_watch, name="online-watch"),
    path("online/<int:pk>/progress/", online_progress, name="online-progress"),

    # Planlama (KESİN)
    path("plans/",                     plan_list,   name="plan_list"),
    path("plans/add/",                 plan_create, name="plan_create"),
    path("plans/<int:pk>/edit/",       plan_edit,   name="plan_edit"),
    path("plans/<int:pk>/delete/",     plan_delete, name="plan_delete"),
    path("plans/<int:pk>/copy/",       plan_copy,   name="plan_copy"),

    # Delegations (Vekalet Tablosu)
    path(
        "delegations/",
        include(("delegations.urls", "delegations"), namespace="delegations"),
    ),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
