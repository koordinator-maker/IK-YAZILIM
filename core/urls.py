# core/urls.py
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse

# Plan sayfası ve JSON API uçları trainings uygulamasında
from trainings.views_plans import (
    plans_page,      # /plans/ (HTML pano)
    plan_list,       # /api/plans/
    plan_detail,     # /api/plans/<pk>/
    plan_search,     # /api/plan-search/
    calendar_year,   # /api/calendar-year/?year=YYYY
)

# Board (staff-only) görsel planlama view'ları
from trainings.views_planning_board import (
    planning_board,
    plan_assign_participant,
    plan_remove_participant,
    plan_set_trainer_name,
)

urlpatterns = [
    # GEÇİCİ TEST - doğru dosyayı düzenlediğimizi teyit için:
    path("ping-board/", lambda r: HttpResponse("OK"), name="ping_board"),

    # Ana site akışı (/, /mine/, eğitim liste/kayıt vb.)
    # NOT: trainings/public_urls mevcut; public akış buradan geliyor.
    path("", include("trainings.public_urls")),

    # Admin
    path("admin/", admin.site.urls),

    # Kimlik
    path(
        "login/",
        auth_views.LoginView.as_view(template_name="registration/login.html"),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),

    # Vekalet matrisi modülü
    path(
        "delegations/",
        include(("delegations.urls", "delegations"), namespace="delegations"),
    ),

    # Plan sayfası ve API uçları
    path("plans/", plans_page, name="plans_page"),
    path("api/plans/", plan_list, name="api_plan_list"),
    path("api/plans/<int:pk>/", plan_detail, name="api_plan_detail"),
    path("api/plan-search/", plan_search, name="api_plan_search"),
    path("api/calendar-year/", calendar_year, name="api_calendar_year"),

    # --- YENİ: Staff-only Görsel Planlama Board ---
    path("plans/board/", planning_board, name="plans_board"),
    path("plans/<int:plan_id>/assign/", plan_assign_participant, name="plan_assign_participant"),
    path("plans/<int:plan_id>/remove/", plan_remove_participant, name="plan_remove_participant"),
    path("plans/<int:plan_id>/set-trainer/", plan_set_trainer_name, name="plan_set_trainer_name"),
]

# Geliştirmede static & media servis etmek
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
