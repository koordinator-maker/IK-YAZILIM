from django.urls import path
from . import views

# Online modülü: önce views_oline.py, yoksa views_online.py
try:
    from . import views_oline as online
except Exception:
    try:
        from . import views_online as online
    except Exception:
        online = None

# Görsel plan view'ı (bu turda YENİ DOSYA olarak ekledik)
try:
    from .views_visual_plan import visual_plan
except Exception:
    visual_plan = None

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

# Online eğitim rotaları (hem tireli hem alt-çizgili isimleri destekle)
if online is not None:
    urlpatterns += [
        # Liste
        path("online/", online.online_list, name="online"),
        path("online/", online.online_list, name="online-list"),

        # İzleme
        path("online/<int:pk>/", online.online_watch, name="online_watch"),
        path("online/<int:pk>/", online.online_watch, name="online-watch"),

        # İlerleme (AJAX POST)
        path("online/<int:pk>/progress/", online.online_progress, name="online_progress"),
        path("online/<int:pk>/progress/", online.online_progress, name="online-progress"),
    ]

# Plan sayfaları
# /plans/ → HTML plan panosu (mevcutta vardır; core.urls içinde de olabilir)
# Burada sadece görsel planı ekliyoruz; plans_page zaten başka yerde tanımlı.
if visual_plan is not None:
    urlpatterns += [
        path("plans/visual/", visual_plan, name="visual_plan"),
    ]
