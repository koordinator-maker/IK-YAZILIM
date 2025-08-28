# trainings/utils/attendance_ocr.py
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import List, Tuple, Iterable, Optional

from django.apps import apps
from django.contrib.auth import get_user_model

User = get_user_model()

def M(name: str):
    try:
        return apps.get_model("trainings", name)
    except Exception:
        return None

TrainingPlan = M("TrainingPlan")
TrainingPlanAttendee = M("TrainingPlanAttendee")

# -------- OCR Bağımlılıklarını isteğe bağlı import (uygun hata iletisi) --------
def _require_ocr():
    try:
        from pdf2image import convert_from_path  # noqa
        import pytesseract  # noqa
        from PIL import Image, ImageFilter, ImageOps  # noqa
    except Exception as e:
        raise RuntimeError(
            "OCR için 'pytesseract', 'pdf2image' ve 'Pillow' gerekli.\n"
            "Ayrıca sistemde Tesseract kurulu olmalı (lang: tur + eng).\n"
            f"Detay: {e}"
        )

# -------- Yardımcılar --------
def _normalize(s: str) -> str:
    # Türkçe harfleri koru, boşlukları sadeleştir
    s = unicodedata.normalize("NFKC", s or "").strip()
    s = re.sub(r"[^\w\sçğıöşüÇĞİÖŞÜ.-]", " ", s, flags=re.UNICODE)
    s = re.sub(r"\s+", " ", s)
    return s

STOPWORDS = {
    "imza", "signature", "açılış", "kapanış", "opening", "closing",
    "katılımcı", "ad", "soyad", "adı", "soyadı", "name", "surname",
    "list", "liste", "attendance", "presence"
}

def _looks_like_name(line: str) -> bool:
    # 2+ kelime, sayı/puan ağırlıklı değil, stopword ağırlıklı değil
    toks = [t for t in line.split() if t]
    if len(toks) < 2:
        return False
    if sum(ch.isalpha() for ch in line) < sum(ch.isdigit() for ch in line):
        return False
    low = line.lower()
    if any(sw in low for sw in STOPWORDS):
        return False
    return True

def _split_lines(text: str) -> List[str]:
    lines = []
    for raw in (text or "").splitlines():
        s = _normalize(raw)
        s = s.strip(" -:;/|.,")
        if s:
            lines.append(s)
    return lines

# -------- OCR Çekirdeği --------
def ocr_pdf_to_texts(pdf_path: str, lang: str = "tur+eng") -> List[str]:
    """PDF'i sayfa sayfa OCR edip metin listesi döndürür."""
    _require_ocr()
    from pdf2image import convert_from_path
    import pytesseract
    from PIL import Image, ImageFilter, ImageOps

    pages = convert_from_path(pdf_path, dpi=300)
    texts = []
    for img in pages:
        # Basit ön işleme: gri, kontrast, threshold, hafif blur
        g = ImageOps.grayscale(img)
        g = g.filter(ImageFilter.MedianFilter(size=3))
        # adaptive threshold benzeri:
        g = ImageOps.autocontrast(g)
        text = pytesseract.image_to_string(g, lang=lang)
        texts.append(text or "")
    return texts

def extract_name_candidates(texts: Iterable[str]) -> List[str]:
    """OCR metinlerinden muhtemel isim satırlarını çıkarır."""
    names = []
    for t in texts:
        for line in _split_lines(t):
            if _looks_like_name(line):
                # Fazla uzun satırları kırp
                if len(line) > 80:
                    continue
                names.append(line)
    # Tekrarlı/benzer satırları kaba filtre
    uniq = []
    seen = set()
    for n in names:
        k = n.lower()
        if k not in seen:
            uniq.append(n)
            seen.add(k)
    return uniq

# -------- Eşleştirme --------
@dataclass
class MatchResult:
    extracted: str
    user: Optional[User]
    score: float

def _user_display_name(u: User) -> str:
    parts = []
    fn = getattr(u, "first_name", "") or ""
    ln = getattr(u, "last_name", "") or ""
    if fn or ln:
        parts.append(fn.strip())
        parts.append(ln.strip())
    else:
        parts.append(getattr(u, "username", "") or "")
    return _normalize(" ".join(p for p in parts if p))

def _ratio(a: str, b: str) -> float:
    # Basit difflib benzeri skor (0..1)
    from difflib import SequenceMatcher
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def match_names_to_users(candidates: List[str], min_score: float = 0.75) -> List[MatchResult]:
    users = list(User.objects.all())
    user_keys = [(_user_display_name(u), u) for u in users]

    results: List[MatchResult] = []
    for ext in candidates:
        ext_n = _normalize(ext)
        best = (None, 0.0, None)  # (user, score, key)
        for key, u in user_keys:
            if not key:
                continue
            sc = _ratio(ext_n, key)
            if sc > best[1]:
                best = (u, sc, key)
        u, sc, _ = best
        if u and sc >= min_score:
            results.append(MatchResult(extracted=ext, user=u, score=sc))
        else:
            results.append(MatchResult(extracted=ext, user=None, score=sc))
    return results

# -------- İçe Aktarma --------
def add_attendees_to_plan(plan_id: int, matches: List[MatchResult]) -> Tuple[int, int]:
    """
    Eşleşen kullanıcıları plan katılımcılarına ekler.
    Var olanları korur; tekrar eklemez.
    Dönüş: (eklenen_sayı, atlanan_sayı)
    """
    if TrainingPlan is None or TrainingPlanAttendee is None:
        raise RuntimeError("TrainingPlan/TrainingPlanAttendee modelleri bulunamadı.")

    try:
        plan = TrainingPlan.objects.get(pk=plan_id)
    except TrainingPlan.DoesNotExist:
        raise RuntimeError(f"Plan #{plan_id} bulunamadı.")

    existing = set(
        TrainingPlanAttendee.objects.filter(plan=plan).values_list("user_id", flat=True)
    )
    add, skip = 0, 0
    bulk = []
    for m in matches:
        if m.user is None:
            continue
        if m.user.id in existing:
            skip += 1
            continue
        bulk.append(TrainingPlanAttendee(plan=plan, user=m.user))
        existing.add(m.user.id)
        add += 1
    if bulk:
        TrainingPlanAttendee.objects.bulk_create(bulk, ignore_conflicts=True)
    return add, skip
