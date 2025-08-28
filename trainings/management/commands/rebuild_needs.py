# trainings/management/commands/rebuild_needs.py
from django.core.management.base import BaseCommand
from django.apps import apps

class Command(BaseCommand):
    help = "Tüm aktif görev atamaları için görev gereği TrainingNeed kayıtlarını (tamamlanmamışlar için) yeniden oluşturur."

    def handle(self, *args, **options):
        JRA = apps.get_model("trainings", "JobRoleAssignment")
        try:
            from trainings.utils.needs import create_needs_for_assignment, fk_to_jobrole, has_field
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"imports failed: {e}"))
            return

        qs = JRA.objects.all()
        if has_field(JRA, "is_active"):
            qs = qs.filter(is_active=True)

        jra_role_fk = fk_to_jobrole(JRA)
        self.stdout.write(self.style.WARNING(f"[rebuild_needs] JobRoleAssignment role FK: {jra_role_fk or '(bulunamadı)'}"))

        processed = 0
        total_created = 0
        for a in qs:
            try:
                n = create_needs_for_assignment(a) or 0
                total_created += n
                processed += 1
            except Exception as e:
                self.stderr.write(self.style.WARNING(f"Atama id={getattr(a,'pk',None)} hata: {e}"))
        self.stdout.write(self.style.SUCCESS(f"İşlenen atama: {processed}, üretilen ihtiyaç: {total_created}"))
