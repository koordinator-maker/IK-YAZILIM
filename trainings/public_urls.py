# trainings/public_urls.py
from django.urls import path
from . import views

# Online modülünü esnek import et:
# Öncelik: views_oline.py  → sonra views_online.py  → yoksa None
try:
    from . import views_oline as online_views
except Exception:
    try:
        from . import views_online as online_views
    except Exception:
        online_views = None

urlpatterns = [
    # Katalog ana sayfası (/)
    path("", views.trainings_list, name="home"),

    # Benim eğitimlerim (/mine/)
    path("mine/", views.my_trainings, name="mine"),

    # Self-enroll
    path("enroll/<int:pk>/", views.enroll, name="enroll"),

    # Sertifika indirme — mevcut şablon ikisini de kullanabildiği için iki isimle de çözümlensin
    path("certs/<int:pk>/", views.download_certificate, name="download_certificate"),
    path("certs/<int:pk>/", views.download_certificate, name="cert-download"),

    # Tanı sayfası
    path("whoami/", views.whoami, name="whoami"),
]

# Online eğitim rotaları (modül varsa eklenir)
if online_views is not None:
    urlpatterns += [
        path("online/", online_views.online_list, name="online_list"),
        path("online/<int:pk>/", online_views.online_watch, name="online_watch"),
        path("online/<int:pk>/progress/", online_views.online_progress, name="online_progress"),
    ]
