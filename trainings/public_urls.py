from django.urls import path
from . import views
from .views_online import online_list, online_watch, online_progress
from .views_plans import (
    plans_page,
    visual_plan,
    api_plan_list,
    api_plan_detail,
    api_plan_search,
    api_calendar_year,
    api_plan_attendees,       # NEW
    api_plan_attendee_add,    # NEW
    api_plan_attendee_remove, # NEW
)

urlpatterns = [
    path("", views.home, name="home"),
    path("mine/", views.my_trainings, name="mine"),
    path("enroll/<int:pk>/", views.enroll, name="enroll"),
    path("certs/<int:pk>/", views.download_certificate, name="download_certificate"),
    path("certs/<int:pk>/", views.download_certificate, name="cert-download"),
    path("whoami/", views.whoami, name="whoami"),

    # Online eğitimler
    path("online/", online_list, name="online"),
    path("online/", online_list, name="online-list"),
    path("online/<int:pk>/", online_watch, name="online_watch"),
    path("online/<int:pk>/", online_watch, name="online-watch"),
    path("online/<int:pk>/progress/", online_progress, name="online_progress"),
    path("online/<int:pk>/progress/", online_progress, name="online-progress"),

    # Eğitim Planları
    path("plans/", plans_page, name="plans_page"),
    path("plans/visual/", visual_plan, name="visual_plan"),

    # Plan API’leri
    path("api/plans/", api_plan_list, name="api_plan_list"),
    path("api/plans/<int:pk>/", api_plan_detail, name="api_plan_detail"),
    path("api/plan-search/", api_plan_search, name="api_plan_search"),
    path("api/calendar-year/", api_calendar_year, name="api_calendar_year"),

    # Katılımcı yönetimi (AJAX)
    path("api/plans/<int:pk>/attendees/", api_plan_attendees, name="api_plan_attendees"),
    path("api/plans/<int:pk>/attendees/add/", api_plan_attendee_add, name="api_plan_attendee_add"),
    path("api/plans/<int:pk>/attendees/remove/", api_plan_attendee_remove, name="api_plan_attendee_remove"),
]
