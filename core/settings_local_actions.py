from .settings import *

# Yerel geli�tirme ayarlar�
DEBUG = True
ALLOWED_HOSTS = ["127.0.0.1", "localhost"]

# �rnek: SQLite varsay�lan� kullan�yorsan DATABASES dokunmana gerek yok.
# E�er �zel DB kullanacaksan buray� a��p d�zenle:
# DATABASES["default"] = {
#     "ENGINE": "django.db.backends.postgresql",
#     "NAME": "hrlms",
#     "USER": "postgres",
#     "PASSWORD": "postgres",
#     "HOST": "127.0.0.1",
#     "PORT": "5432",
# }
