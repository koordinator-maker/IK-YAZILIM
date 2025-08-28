from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, Http404, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import OnlineVideo, VideoProgress, Enrollment


def _progress_maps(user, videos):
    """
    Kullanıcının ilerleme haritaları:
      - pct_map: {video_id: yüzde_int}
      - sec_map: {video_id: max_position_seconds_float}
    """
    pct_map, sec_map = {}, {}
    if not user.is_authenticated:
        return pct_map, sec_map
    qs = VideoProgress.objects.filter(user=user, video__in=videos).values(
        "video_id", "max_position_seconds", "video__duration_seconds"
    )
    for row in qs:
        dur = float(row["video__duration_seconds"] or 1.0)
        secs = float(row["max_position_seconds"] or 0.0)
        pct = int((secs / dur) * 100)
        pct_map[row["video_id"]] = max(0, min(100, pct))
        sec_map[row["video_id"]] = max(0.0, secs)
    return pct_map, sec_map


def online_list(request):
    """
    Online videolar listesi. Kartların altında:
      - İlerleme: %X
      - İzlenen: H:M:S
      - Toplam süre (video.duration_hours_display)
    """
    videos = OnlineVideo.objects.filter(is_active=True).select_related("training").order_by("-created_at")
    pct_map, sec_map = _progress_maps(request.user, videos)
    for v in videos:
        v.progress_percent = pct_map.get(v.id, 0)
        v.progress_seconds = int(sec_map.get(v.id, 0))
    return render(request, "trainings/online_list.html", {"videos": videos})


@login_required
def online_watch(request, pk: int):
    """Video izleme sayfası + kaldığı yerden devam bilgisi."""
    video = get_object_or_404(OnlineVideo.objects.select_related("training"), pk=pk, is_active=True)
    vp, _ = VideoProgress.objects.get_or_create(user=request.user, video=video)

    allowed_max = float(vp.max_position_seconds or 0.0)
    dur = float(video.duration_seconds or 1.0)
    saved_percent = int((allowed_max / dur) * 100)

    ctx = {
        "video": video,
        "vp": vp,
        "allowed_max": int(allowed_max),
        "saved_percent": saved_percent,
    }
    return render(request, "trainings/online_watch.html", ctx)


@login_required
@require_POST
def online_progress(request, pk: int):
    """
    İstemciden { position: saniye } alır.
    İleri sarma kısıtı: max + 5 saniye.
    %90 eşiğinde tamamlandı sayar ve Enrollment'ı tamamlar.
    """
    video = get_object_or_404(OnlineVideo.objects.select_related("training"), pk=pk, is_active=True)
    try:
        position = float(request.POST.get("position", "0"))
    except (TypeError, ValueError):
        return HttpResponseBadRequest("bad position")
    if position < 0:
        position = 0.0

    vp, _ = VideoProgress.objects.get_or_create(user=request.user, video=video)

    prev_max = float(vp.max_position_seconds or 0.0)
    allowed_new_max = min(position, prev_max + 5.0)  # en fazla +5 sn ilerleme
    new_max = max(prev_max, allowed_new_max)

    vp.max_position_seconds = new_max
    vp.last_position_seconds = min(position, new_max)

    dur = float(video.duration_seconds or 1)
    threshold = 0.90 * dur

    just_completed = False
    if (not vp.completed) and (new_max >= threshold):
        vp.completed = True
        vp.completed_at = timezone.now()
        just_completed = True

        # Enrollment güncelle
        if video.training_id:
            enr, _ = Enrollment.objects.get_or_create(
                user=request.user,
                training=video.training,
                defaults={"status": "enrolled"},
            )
            enr.status = "completed"
            enr.is_passed = True
            if not enr.completed_at:
                enr.completed_at = timezone.now()
            enr.save(update_fields=["status", "is_passed", "completed_at"])

    vp.save(update_fields=[
        "max_position_seconds", "last_position_seconds",
        "completed", "completed_at", "updated_at"
    ])

    return JsonResponse({
        "ok": True,
        "allowed_max": new_max,
        "completed": vp.completed,
        "just_completed": just_completed,
        "percent": int((new_max / dur) * 100),
        "watched_seconds": int(new_max),
    })
