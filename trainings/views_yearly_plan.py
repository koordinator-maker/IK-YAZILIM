from collections import defaultdict
from datetime import date
import calendar

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
    """Plan katılımcılarını virgül ile birleştirir (M2M ya da ara tabloya uyumlu)."""
    try:
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


def _month_bands(year: int, weeks: list[int]):
    """
    Verilen yıl + hafta listesi için ardışık haftaları aya göre grupla.
    Dönen yapı: [{"name":"OCA","span":5,"color":"#eef2ff"}, ...]
    """
    # Türkçe kısa ay adları
    TR_ABBR = ["", "OCA", "ŞUB", "MAR", "NİS", "MAY", "HAZ", "TEM", "AĞU", "EYL", "EKİ", "KAS", "ARA"]
    COLORS = [
        "#eff6ff", "#f5f3ff", "#ecfeff", "#f0fdf4", "#fff7ed", "#fef2f2",
        "#fdf4ff", "#f0f9ff", "#faf5ff", "#f1f5f9", "#fefce8", "#f5f5f4",
    ]

    bands = []
    cur_month = None
    cur_span = 0
    cur_color = COLORS[0]
    ci = 0

    for w in weeks:
        # ISO haftasının pazartesi tarihi -> ay
        try:
            m = date.fromisocalendar(year, w, 1).month
        except Exception:
            # bazı yıllarda 53. hafta olmayabilir; yakın haftadan türet
            try:
                m = date.fromisocalendar(year, max(1, w - 1), 1).month
            except Exception:
                m = 1
        if cur_month is None:
            cur_month = m
            cur_span = 1
            cur_color = COLORS[ci % len(COLORS)]
        elif m == cur_month:
            cur_span += 1
        else:
            bands.append({"name": TR_ABBR[cur_month], "span": cur_span, "color": cur_color})
            ci += 1
            cur_month = m
            cur_span = 1
            cur_color = COLORS[ci % len(COLORS)]
    if cur_month is not None:
        bands.append({"name": TR_ABBR[cur_month], "span": cur_span, "color": cur_color})
    return bands


@staff_member_required
def yearly_plan_board(request):
    current_year = date.today().year
    weeks = list(range(1, 53))
    month_bands = _month_bands(current_year, weeks)

    # Bu yılın planları
    plans = []
    if TrainingPlan:
        qs = TrainingPlan.objects.all()
        if hasattr(TrainingPlan, "start_datetime"):
            qs = qs.exclude(start_datetime__isnull=True).filter(start_datetime__year=current_year)
        plans = list(qs.select_related("training"))

    # Satır başlıkları: Training.title + planlarda görünen eğitim adları (unique)
    titles_set = set()
    if Training:
        try:
            for t in Training.objects.order_by("title").values_list("title", flat=True):
                if t:
                    titles_set.add(str(t))
        except Exception:
            pass
    for p in plans:
        tr = getattr(p, "training", None)
        t = getattr(tr, "title", "") if tr else ""
        if t:
            titles_set.add(str(t))

    titles = sorted(titles_set, key=lambda s: s.upper())
    titles += [""] * 5  # altta 5 boş satır

    # title -> hafta -> [plan, ...]
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
        rows.append({"title": t or "—", "week_plans": week_plans})

    ctx = {
        "page_title": f"Yıllık Eğitim Planı — {current_year}",
        "weeks": weeks,
        "month_bands": month_bands,
        "rows": rows,
    }
    return render(request, "trainings/plans/yearly_board.html", ctx)
