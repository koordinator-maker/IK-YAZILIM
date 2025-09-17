from .settings import *

# Yerel geliþtirme ayarlarý
DEBUG = True
ALLOWED_HOSTS = ["127.0.0.1", "localhost"]

# Örnek: SQLite varsayýlaný kullanýyorsan DATABASES dokunmana gerek yok.
# Eðer özel DB kullanacaksan burayý açýp düzenle:
# DATABASES["default"] = {
#     "ENGINE": "django.db.backends.postgresql",
#     "NAME": "hrlms",
#     "USER": "postgres",
#     "PASSWORD": "postgres",
#     "HOST": "127.0.0.1",
#     "PORT": "5432",
# }
