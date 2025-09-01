# trainings/bootreport.py
from __future__ import annotations

import json
import os
import platform
import sys
import hashlib
from datetime import datetime
from typing import Any, Dict, List

import django
from django.conf import settings
from django.apps import apps as dj_apps
from django.urls import get_resolver, URLPattern, URLResolver
from django.contrib.auth import get_user_model
from pathlib import Path


# -----------------------------
# Public entrypoint
# -----------------------------
def safe_write_boot_report() -> None:
    """
    Uygulama açılışında çağrılır. Hata üretmeden güvenli şekilde rapor yazar.
    Yazım hedefi sırayla:
      1) HRLMS_BOOTREPORT_DIR (env var)
      2) BASE_DIR/var
      3) CWD/var
    Başarılı olursa stdout'a kesin dosya yollarını yazar.
    """
    try:
        data = _collect_boot_data()
        paths = _write_files_resilient(data)
        # Konsola net çıktı
        print(
            f"[bootreport] OK\n"
            f"  JSON: {paths['json']}\n"
            f"  TXT : {paths['txt']}\n",
            flush=True,
        )
    except Exception as e:
        # Uygulamayı düşürmeyelim; sadece kısaca log basalım
        print(f"[bootreport] failed: {e}", flush=True)


# -----------------------------
# Collectors
# -----------------------------
def _collect_boot_data() -> Dict[str, Any]:
    now = datetime.now()

    # BASE_DIR güvenli çözüm
    base_dir = None
    try:
        base_dir = Path(getattr(settings, "BASE_DIR")).resolve()
    except Exception:
        base_dir = Path(__file__).resolve().parents[2]  # trainings/ -> app root -> project root tahmini

    info: Dict[str, Any] = {
        "generated_at": now.isoformat(timespec="seconds"),
        "tz": str(getattr(settings, "TIME_ZONE", "")),
        "python": {
            "version": sys.version,
            "implementation": platform.python_implementation(),
        },
        "django": {
            "version": django.get_version(),
            "debug": bool(getattr(settings, "DEBUG", False)),
        },
        "project": {
            "base_dir": str(base_dir),
            "root_urlconf": getattr(settings, "ROOT_URLCONF", ""),
            "allowed_hosts": list(getattr(settings, "ALLOWED_HOSTS", [])),
            "secret_key_masked": _mask(getattr(settings, "SECRET_KEY", "")),
            "language_code": getattr(settings, "LANGUAGE_CODE", ""),
            "use_tz": bool(getattr(settings, "USE_TZ", True)),
        },
        "paths": {
            "static_url": getattr(settings, "STATIC_URL", ""),
            "static_root": str(getattr(settings, "STATIC_ROOT", "")),
            "staticfiles_dirs": [str(p) for p in getattr(settings, "STATICFILES_DIRS", []) or []],
            "media_url": getattr(settings, "MEDIA_URL", ""),
            "media_root": str(getattr(settings, "MEDIA_ROOT", "")),
            "template_dirs": _template_dirs(),
        },
        "apps": {
            "installed_apps": list(getattr(settings, "INSTALLED_APPS", [])),
            "middleware": list(getattr(settings, "MIDDLEWARE", [])),
            "auth_user_model": _user_model_path(),
        },
        "database": _db_summary(),
        "urls": _list_all_urls(),
        "models": _introspect_models(),
        "hr_lms_focus": _hr_lms_focus_section(),
        "signature": {},  # aşağıda dolduruluyor
    }

    signature_src = json.dumps(
        {
            "installed_apps": info["apps"]["installed_apps"],
            "middleware": info["apps"]["middleware"],
            "database": info["database"],
            "urls": [u["route"] for u in info["urls"]],
            "models": {m["model_label"]: [f["name"] for f in m["fields"]] for m in info["models"]},
        },
        ensure_ascii=False,
        sort_keys=True,
    ).encode("utf-8")
    sha = hashlib.sha256(signature_src).hexdigest()
    info["signature"] = {"sha256": sha, "short": sha[:12]}
    return info


def _mask(value: str, keep: int = 6) -> str:
    if not value:
        return ""
    if len(value) <= keep:
        return "*" * len(value)
    return value[:keep] + "*" * (len(value) - keep)


def _template_dirs() -> List[str]:
    dirs: List[str] = []
    for cfg in getattr(settings, "TEMPLATES", []):
        for d in cfg.get("DIRS", []):
            dirs.append(str(d))
    return dirs


def _db_summary() -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    dbs = getattr(settings, "DATABASES", {})
    for alias, cfg in dbs.items():
        engine = cfg.get("ENGINE", "")
        name = cfg.get("NAME", "")
        out[alias] = {"engine": engine, "name": name}
    return out


def _user_model_path() -> str:
    try:
        User = get_user_model()
        return f"{User._meta.app_label}.{User.__name__}"
    except Exception:
        return ""


def _list_all_urls() -> List[Dict[str, Any]]:
    resolver = get_resolver()
    flat: List[Dict[str, Any]] = []

    def _walk(patterns, prefix=""):
        for p in patterns:
            if isinstance(p, URLPattern):
                route = str(p.pattern)
                name = p.name
                try:
                    callback = (
                        getattr(p.callback, "__module__", "")
                        + "."
                        + getattr(p.callback, "__name__", "")
                    )
                except Exception:
                    callback = ""
                flat.append({"route": prefix + route, "name": name, "callback": callback})
            elif isinstance(p, URLResolver):
                route = str(p.pattern)
                _walk(p.url_patterns, prefix + route)
            else:
                try:
                    route = str(p.pattern)
                except Exception:
                    route = "-"
                flat.append({"route": route, "name": getattr(p, "name", None), "callback": ""})

    _walk(resolver.url_patterns)
    return flat


def _introspect_models() -> List[Dict[str, Any]]:
    models_info: List[Dict[str, Any]] = []
    for model in dj_apps.get_models():
        try:
            fields = []
            for f in model._meta.get_fields():
                info = {
                    "name": f.name,
                    "type": f.__class__.__name__,
                    "is_relation": getattr(f, "is_relation", False),
                    "many_to_many": getattr(f, "many_to_many", False),
                    "related_model": f.related_model._meta.label if getattr(f, "related_model", None) else None,
                }
                for attr in ("null", "blank", "db_index", "primary_key", "unique", "choices"):
                    if hasattr(f, attr):
                        val = getattr(f, attr)
                        if attr == "choices" and val:
                            try:
                                val = [str(c[0]) for c in val]
                            except Exception:
                                val = str(val)
                        info[attr] = val
                fields.append(info)

            models_info.append(
                {
                    "app_label": model._meta.app_label,
                    "model_name": model.__name__,
                    "model_label": model._meta.label,
                    "db_table": model._meta.db_table,
                    "fields": fields,
                }
            )
        except Exception:
            continue
    models_info.sort(key=lambda m: m["model_label"])
    return models_info


def _hr_lms_focus_section() -> Dict[str, Any]:
    out: Dict[str, Any] = {"training_plan": None, "training_plan_attendee": None}
    try:
        TP = dj_apps.get_model("trainings", "TrainingPlan")
    except Exception:
        TP = None
    if TP:
        out["training_plan"] = {
            "model_label": TP._meta.label,
            "fields": [f.name for f in TP._meta.get_fields()],
        }
    try:
        TPA = dj_apps.get_model("trainings", "TrainingPlanAttendee")
    except Exception:
        TPA = None
    if TPA:
        out["training_plan_attendee"] = {
            "model_label": TPA._meta.label,
            "fields": [f.name for f in TPA._meta.get_fields()],
        }
    return out


# -----------------------------
# Writers (resilient)
# -----------------------------
def _write_files_resilient(data: Dict[str, Any]) -> Dict[str, str]:
    """
    Yazılacak dizini seç ve dosyaları kaydet. Başarısız olursa alternatif
    dizinleri dener. Sonunda {"json": path, "txt": path} döner.
    """
    targets = []

    # 1) Ortam değişkeni
    env_dir = os.environ.get("HRLMS_BOOTREPORT_DIR")
    if env_dir:
        targets.append(Path(env_dir).expanduser())

    # 2) BASE_DIR/var
    try:
        base_dir = Path(getattr(settings, "BASE_DIR")).resolve()
    except Exception:
        base_dir = Path(__file__).resolve().parents[2]
    targets.append(base_dir / "var")

    # 3) CWD/var
    targets.append(Path.cwd() / "var")

    last_err = None
    for tdir in targets:
        try:
            tdir.mkdir(parents=True, exist_ok=True)
            json_path = tdir / "bootreport.json"
            txt_path = tdir / "bootreport.txt"

            # JSON
            json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

            # TXT
            txt_path.write_text(_summarize(data), encoding="utf-8")

            return {"json": str(json_path.resolve()), "txt": str(txt_path.resolve())}
        except Exception as e:
            last_err = e
            continue

    raise RuntimeError(f"Tüm konumlara yazma başarısız: {last_err}")


def _summarize(d: Dict[str, Any]) -> str:
    lines: List[str] = []
    push = lines.append

    push(f"Generated: {d.get('generated_at')}  TZ={d.get('tz')}")
    push(f"Python: {d['python']['implementation']} {d['python']['version'].split()[0]}")
    push(f"Django: {d['django']['version']}  DEBUG={d['django']['debug']}")
    proj = d["project"]
    push(f"Project: BASE_DIR={proj['base_dir']}  ROOT_URLCONF={proj['root_urlconf']}")
    push(f"Paths: STATIC_ROOT={d['paths']['static_root']}  MEDIA_ROOT={d['paths']['media_root']}")
    push(f"Templates: {', '.join(d['paths']['template_dirs']) or '-'}")
    push(f"Auth User Model: {d['apps']['auth_user_model']}")
    push(f"Installed Apps: {len(d['apps']['installed_apps'])} items")
    push(f"Middleware   : {len(d['apps']['middleware'])} items")
    push("Databases:")
    for alias, cfg in d["database"].items():
        push(f"  - {alias}: {cfg['engine']}  name={cfg['name']}")
    push(f"URL Patterns: {len(d['urls'])} items")
    for u in d["urls"][:50]:
        nm = u["name"] or "-"
        push(f"  - {u['route']}  (name={nm})")

    hl = d.get("hr_lms_focus", {})
    tp = hl.get("training_plan")
    tpa = hl.get("training_plan_attendee")
    push("HR-LMS Focus:")
    if tp:
        push(f"  TrainingPlan: {tp['model_label']}  fields={', '.join(tp['fields'])}")
    else:
        push("  TrainingPlan: -")
    if tpa:
        push(f"  TrainingPlanAttendee: {tpa['model_label']}  fields={', '.join(tpa['fields'])}")
    else:
        push("  TrainingPlanAttendee: -")

    sig = d.get("signature", {})
    push(f"Signature: sha256={sig.get('sha256','')[:12]}…  short={sig.get('short','')}")
    return "\n".join(lines)
