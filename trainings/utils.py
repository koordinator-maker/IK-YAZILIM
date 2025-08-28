from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from django.conf import settings

def generate_certificate_pdf(user_fullname, training_title, date_str, outfile_name):
    outdir = Path(settings.MEDIA_ROOT) / "certificates"
    outdir.mkdir(parents=True, exist_ok=True)
    outpath = outdir / outfile_name

    c = canvas.Canvas(str(outpath), pagesize=A4)
    w, h = A4

    c.setFont("Helvetica-Bold", 22)
    c.drawCentredString(w/2, h-150, "KATILIM SERTİFİKASI")

    c.setFont("Helvetica", 14)
    c.drawCentredString(w/2, h-220, f"Sayın {user_fullname},")
    c.drawCentredString(w/2, h-260, f"'{training_title}' eğitimini başarıyla tamamlamıştır.")
    c.drawCentredString(w/2, h-300, f"Tarih: {date_str}")

    c.setFont("Helvetica-Oblique", 10)
    c.drawCentredString(w/2, 80, "Bu belge otomatik olarak oluşturulmuştur.")
    c.showPage()
    c.save()

    return str(outpath)
