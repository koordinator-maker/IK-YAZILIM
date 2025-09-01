from django.urls import path

# Mevcut sayfalar / API'ler
from .views_plans import (
    plans_page,
    plan_list,
    plan_detail,
    plan_search,
    calendar_year,
)
from .views_visual_plan import visual_plan  # mevcut görsel plan sayfası

# YENİ: Staff-only görsel planlama board
from .views_planning_board import (
    planning_board,
    plan_assign_participant,
    plan_remove_participant,
    plan_set_trainer_name,
)

urlpatterns = [
    # --------- PLAN SAYFASI (HTML) ---------
    path("plans/", plans_page, name="plans_page"),
    path("plans/visual/", visual_plan, name="visual_plan"),  # mevcut

    # --------- JSON API UÇLARI ---------
    path("api/plans/", plan_list, name="api_plan_list"),
    path("api/plans/<int:pk>/", plan_detail, name="api_plan_detail"),
    path("api/plan-search/", plan_search, name="api_plan_search"),
    path("api/calendar-year/", calendar_year, name="api_calendar_year"),

    # --------- YENİ: Staff-only Görsel Planlama Board ---------
    path("plans/board/", planning_board, name="plans_board"),
    path("plans/<int:plan_id>/assign/", plan_assign_participant, name="plan_assign_participant"),
    path("plans/<int:plan_id>/remove/", plan_remove_participant, name="plan_remove_participant"),
    path("plans/<int:plan_id>/set-trainer/", plan_set_trainer_name, name="plan_set_trainer_name"),
]
