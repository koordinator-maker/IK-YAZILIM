# dms/urls.py
from django.urls import path
from .ui_views import UiIndexView, SimpleUploadView, WhoAmIView
from .views import UploadInitView, UploadCompleteView, SearchView

urlpatterns = [
    # UI
    path("ui/", UiIndexView.as_view(), name="ui-index"),
    path("ui/upload", SimpleUploadView.as_view(), name="ui-upload"),
    path("ui/whoami", WhoAmIView.as_view(), name="ui-whoami"),

    # API
    path("docs/upload/init", UploadInitView.as_view(), name="upload-init"),
    path("docs/upload/complete", UploadCompleteView.as_view(), name="upload-complete"),
    path("search", SearchView.as_view(), name="search"),
]
