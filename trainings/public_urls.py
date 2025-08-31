from django.urls import path
from . import views

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
