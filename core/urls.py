# core/urls.py
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static

# Plan sayfası ve JSON API uçları trainings uygulamasında
from trainings.views_plans import (
    plans_page,      # HTML pano: /plans/
    plan_list,       # GET  /api/plans/
    plan_detail,     # GET  /api/plans/<pk>/
    plan_search,     # GET  /api/plan-search/
    calendar_year,   # GET  /api/calendar-year/?year=YYYY
)

urlpatterns = [
    # Ana site akışı (/, /mine/, ihtiyaç, online eğitimler vb.)
    # NOT: trainings/urls.py yok; public_urls kullanılır.
    path("", include("trainings.public_urls")),

    # Admin
    path("admin/", admin.site.urls),

    # Kimlik (LOGIN_URL = "/login/")
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
]

# Geliştirmede static & media servis etmek
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=getattr(settings, "STATIC_ROOT", None))
