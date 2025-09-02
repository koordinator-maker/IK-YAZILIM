from collections import defaultdict
from datetime import date
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from django.apps import apps
from django.urls import reverse

def M(name: str):
    try:
        return apps.get_model("trainings", name)
    except Exception:
        return None

Training = M("Training")
TrainingPlan = M("TrainingPlan")
TrainingPlanAttendee = M("TrainingPlanAttendee")

def attendees_text(plan):
    # Plan katılımcılarını virgül ile birleştir.
    try:
        # Generic: M2M ise .attendees.all(), yoksa ilişki tablosundan çek.
        if hasattr(plan, "attendees"):
            users = list(plan.attendees.all())
        elif TrainingPlanAttendee:
            rows = TrainingPlanAttendee.objects.filter(plan=plan).select_related("user")
            users = [r.user for r in rows if r.user_id]
        else:
            users = []
    except Exception:
        users = []
    out = []
    for u in users:
        try:
            full = u.get_full_name()
        except Exception:
            full = ""
        out.append(full or getattr(u, "username", "") or str(u))
    return ", ".join(out) or "-"

@staff_member_required
def yearly_plan_board(request):
    # Yıl
    current_year = date.today().year
    # 1..52/53 ISO haftaları
    weeks = list(range(1, 53))

    # Bu yılın planları (start_datetime yılına göre)
    plans = []
    if TrainingPlan:
        qs = TrainingPlan.objects.all()
        if hasattr(TrainingPlan, "start_datetime"):
            qs = qs.exclude(start_datetime__isnull=True).filter(start_datetime__year=current_year)
        plans = list(qs.select_related("training"))

    # ====== Satır başlıkları (SOL SÜTUN) ======
    # Kaynak 1: Training tablosundaki tüm başlıklar
    title_set = set()
    if Training:
        try:
            for t in Training.objects.order_by("title").values_list("title", flat=True):
                if t:
                    title_set.add(str(t))
        except Exception:
            pass
    # Kaynak 2: Planlarda geçen eğitim başlıkları
    for p in plans:
        tr = getattr(p, "training", None)
        t = getattr(tr, "title", "") if tr else ""
        if t:
            title_set.add(str(t))

    # Ekranda alfabetik + Türkçe uyumlu sıralama
    titles = sorted(title_set, key=lambda s: s.upper())

    # En alta 5 boş satır
    titles += [""] * 5

    # ====== Haftalara yerleştirme ======
    # by_title[title][week] -> [plan, plan, ...]
    by_title = defaultdict(lambda: defaultdict(list))
    for p in plans:
        tr = getattr(p, "training", None)
        title = getattr(tr, "title", "") if tr else ""
        sd = getattr(p, "start_datetime", None)
        week_no = None
        if sd:
            try:
                week_no = int(sd.isocalendar().week)
            except Exception:
                week_no = None
        if not (title and week_no):
            continue
        by_title[title][week_no].append(p)

    # Şablona gidecek satırlar
    rows = []
    for t in titles:
        week_plans = []
        for w in weeks:
            plist = []
            for p in by_title.get(t, {}).get(w, []):
                admin_link = reverse("admin:trainings_trainingplan_change", args=[p.pk])
                sd = getattr(p, "start_datetime", None)
                ed = getattr(p, "end_datetime", None)
                when_txt = ""
                if sd and ed:
                    when_txt = f"{sd:%Y-%m-%d %H:%M} – {ed:%H:%M}"
                elif sd:
                    when_txt = f"{sd:%Y-%m-%d %H:%M}"
                trainer = getattr(p, "instructor_name", "") or "-"
                label = t or getattr(getattr(p, "training", None), "title", "") or f"Plan #{p.pk}"
                plist.append({
                    "id": p.pk,
                    "label": label,
                    "admin_link": admin_link,
                    "when": when_txt,
                    "trainer": trainer,
                    "attendees_txt": attendees_text(p),
                })
            week_plans.append(plist)
        rows.append({
            "title": t or "—",
            "week_plans": week_plans,
        })

    ctx = {
        "page_title": f"Yıllık Eğitim Planı — {current_year}",
        "weeks": weeks,
        "rows": rows,
    }
    return render(request, "trainings/plans/yearly_board.html", ctx)
