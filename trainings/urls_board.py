# trainings/urls_board.py
from django.urls import path
from .views_planning_board import (
    planning_board,
    plan_assign_participant,
    plan_remove_participant,
    plan_set_trainer_name,
)

urlpatterns = [
    # Staff-only görsel planlama board
    path("plans/board/", planning_board, name="plans_board"),
    path("plans/<int:plan_id>/assign/", plan_assign_participant, name="plan_assign_participant"),
    path("plans/<int:plan_id>/remove/", plan_remove_participant, name="plan_remove_participant"),
    path("plans/<int:plan_id>/set-trainer/", plan_set_trainer_name, name="plan_set_trainer_name"),
]
