from datetime import timedelta
from django.core.mail import EmailMultiAlternatives
from django.core.management.base import BaseCommand
from django.template.loader import render_to_string
from django.utils import timezone

from trainings.models import Training, Enrollment

class Command(BaseCommand):
    help = "Yaklaşan eğitimler için hatırlatma e-postası gönderir (T-2 ve T-1)."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="E-posta göndermeden sadece listele")
        parser.add_argument("--days", type=int, nargs="+", default=[2, 1],
                            help="Kaç gün önceden hatırlatma yapılacağını belirt. Örn: --days 3 1")

    def handle(self, *args, **opts):
        now = timezone.now()
        today_local = now.astimezone(timezone.get_current_timezone()).date()
        days_list = opts["days"]
        dry = opts["dry_run"]

        total_sent = 0
        for d in days_list:
            # T+d günün 00:00:00 ile 23:59:59 arası
            target_start = timezone.make_aware(
                timezone.datetime.combine(today_local + timedelta(days=d), timezone.datetime.min.time()),
                timezone.get_current_timezone()
            )
            target_end = timezone.make_aware(
                timezone.datetime.combine(today_local + timedelta(days=d), timezone.datetime.max.time()),
                timezone.get_current_timezone()
            )

            trainings = Training.objects.filter(baslangic_tarihi__range=(target_start, target_end))
            for training in trainings:
                enrollments = Enrollment.objects.select_related("user").filter(
                    training=training
                ).exclude(durum="katildi")  # katılanlara tekrar mail yok

                for enr in enrollments:
                    user = enr.user
                    context = {"user": user, "training": training}
                    subject = f"[Hatırlatma] {training.baslik} - {training.baslangic_tarihi.strftime('%d.%m.%Y %H:%M')}"
                    from_email = None  # DEFAULT_FROM_EMAIL kullanılacak
                    text_body = render_to_string("emails/training_reminder.txt", context)
                    html_body = render_to_string("emails/training_reminder.html", context)

                    if dry:
                        self.stdout.write(f"DRY-RUN: {user} için e-posta hazırlanırdı: {subject}")
                    else:
                        msg = EmailMultiAlternatives(subject, text_body, from_email, [user.email or f"{user.username}@example.local"])
                        msg.attach_alternative(html_body, "text/html")
                        try:
                            msg.send()
                            total_sent += 1
                            self.stdout.write(self.style.SUCCESS(f"Gönderildi → {user} / {training}"))
                        except Exception as e:
                            self.stderr.write(f"HATA → {user} / {training}: {e}")

        if dry:
            self.stdout.write(self.style.WARNING("DRY-RUN tamamlandı (e-posta gönderilmedi)."))
        else:
            self.stdout.write(self.style.SUCCESS(f"Toplam gönderim: {total_sent}"))
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DEFAULT_FROM_EMAIL = "egitim@company.local"
TIME_ZONE = "Europe/Istanbul"
USE_TZ = True
