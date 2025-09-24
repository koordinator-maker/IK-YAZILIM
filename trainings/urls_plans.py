# Rev: 2025-09-24 13:55 r1
from django.urls import path
from . import api_plans

urlpatterns = [
    path("plans/", api_plans.plans_api, name="plans_api"),
    path("plans/<int:pk>/", api_plans.plan_detail_api, name="plan_detail_api"),
    path("plan-search/", api_plans.plan_search_api, name="plan_search_api"),
    path("calendar-year/", api_plans.calendar_year_api, name="calendar_year_api"),
]
