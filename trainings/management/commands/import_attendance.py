# trainings/management/commands/import_attendance.py
from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from trainings.utils.attendance_ocr import (
    ocr_pdf_to_texts,
    extract_name_candidates,
    match_names_to_users,
    add_attendees_to_plan,
)

class Command(BaseCommand):
    help = "El yazısı katılım listesini (PDF) OCR ile okuyup bir plana katılımcı olarak ekler."

    def add_arguments(self, parser):
        parser.add_argument("--plan", type=int, required=True, help="TrainingPlan ID")
        parser.add_argument("--file", type=str, required=True, help="Katılım listesi PDF yolu")
        parser.add_argument("--min-score", type=float, default=0.78, help="Eşleşme alt skoru (0-1)")
        parser.add_argument("--lang", type=str, default="tur+eng", help="Tesseract OCR dil kodu")

    def handle(self, *args, **opts):
        plan_id = opts["plan"]
        pdf_path = opts["file"]
        min_score = opts["min_score"]
        lang = opts["lang"]

        try:
            texts = ocr_pdf_to_texts(pdf_path, lang=lang)
        except RuntimeError as e:
            raise CommandError(str(e))

        cands = extract_name_candidates(texts)
        self.stdout.write(self.style.WARNING(f"Aday isim satırı: {len(cands)}"))

        matches = match_names_to_users(cands, min_score=min_score)

        ok = [m for m in matches if m.user is not None]
        no = [m for m in matches if m.user is None]

        self.stdout.write(self.style.SUCCESS(f"Eşleşen: {len(ok)}  | Eşleşmeyen: {len(no)}"))

        # Eşleşmeyenleri göster
        if no:
            self.stdout.write("Eşleşmeyen örnekler:")
            for m in no[:10]:
                self.stdout.write(f"  - '{m.extracted}' (skor={m.score:.2f})")

        added, skipped = add_attendees_to_plan(plan_id, ok)
        self.stdout.write(self.style.SUCCESS(f"Eklendi: {added} | Zaten vardı: {skipped}"))

        self.stdout.write(self.style.SUCCESS("Bitti."))
