# core/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views

# Plan sayfası ve JSON API uçları trainings app'indedir
from trainings.views_plans import (
    plans_page,      # HTML liste sayfası
    plan_list,       # GET /api/plans/
    plan_detail,     # GET /api/plans/<pk>/
    plan_search,     # GET /api/plan-search/
    calendar_year,   # GET /api/calendar-year/?year=YYYY
)

urlpatterns = [
    # Admin
    path("admin/", admin.site.urls),

    # Kimlik (LOGIN_URL = "/login/" ile uyumlu)
    path(
        "login/",
        auth_views.LoginView.as_view(template_nam_
