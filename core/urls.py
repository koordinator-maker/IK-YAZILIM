from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse

# Trainings pano/servis görünümleri
from trainings.views_plans import (
    plans_page,      # /plans/ (HTML pano)
    plan_list,       # /api/plans/
    plan_detail,     # /api/plans/<pk>/
    plan_search,     # /api/plan-search/
    calendar_year,   # /api/calendar-year/?year=YYYY
)
from trainings.views_yearly_plan import yearly_plan_board  # /plans/yearly/

urlpatterns = [
    # Ana site (/, /mine/, enroll, cert, online vs.) -> trainings.public_urls
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

    # Sağlık kontrolü (geçici)
    path("ping-board/", lambda r: HttpResponse("OK")),

    # Vekalet matrisi modülü
    path(
        "delegations/",
        include(("delegations.urls", "delegations"), namespace="delegations"),
    ),

    # Plan sayfası ve API uçları
    path("plans/", plans_page, name="plans_page"),
    path("plans/yearly/", yearly_plan_board, name="yearly_plan"),
    path("api/plans/", plan_list, name="api_plan_list"),
    path("api/plans/<int:pk>/", plan_detail, name="api_plan_detail"),
    path("api/plan-search/", plan_search, name="api_plan_search"),
    path("api/calendar-year/", calendar_year, name="api_calendar_year"),
]

# Opsiyonel: dms uygulaması varsa API'sini ekle
try:
    import importlib.util as _ilus
    if _ilus.find_spec("dms") is not None:
        urlpatterns.append(path("v1/", include("dms.urls")))
except Exception:
    # Eksik bağımlılık vb. durumlarda düşmeyelim
    pass

# Geliştirmede static & media servis et
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
