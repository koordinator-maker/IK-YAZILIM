from django.urls import path
from .views import DelegationMatrixView, toggle_delegation, update_meta, reset_all

app_name = "delegations"

urlpatterns = [
    path("matrix/", DelegationMatrixView.as_view(), name="matrix"),
    path("toggle/", toggle_delegation, name="toggle"),
    path("update-meta/", update_meta, name="update_meta"),
    path("reset-all/", reset_all, name="reset_all"),
]
