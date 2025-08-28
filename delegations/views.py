from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import JsonResponse, HttpResponseBadRequest
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST
from django.views.generic import TemplateView
from django.utils.dateparse import parse_date

from .models import RoleDelegation, DelegationDocument
from trainings.models import JobRole


def staff_required(user):
    return user.is_staff or user.is_superuser


@method_decorator(ensure_csrf_cookie, name='dispatch')
class DelegationMatrixView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'delegations/matrix.html'

    def test_func(self):
        return staff_required(self.request.user)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        roles = JobRole.objects.filter(is_active=True).order_by('name')

        # Aktif vekaletler için "from_to" anahtarları
        qs = RoleDelegation.objects.filter(is_active=True).values_list('from_role_id', 'to_role_id')
        pair_keys = [f"{a}_{b}" for a, b in qs]

        ctx['roles'] = roles
        ctx['pair_keys'] = pair_keys
        ctx['has_any'] = len(pair_keys) > 0  # varsa "Hepsini Temizle" göster
        ctx['meta'] = DelegationDocument.singleton()
        return ctx


@login_required
@user_passes_test(staff_required)
@require_POST
def toggle_delegation(request):
    """Hücre tıklandığında vekaleti aç/kapat. Body: from_id, to_id"""
    try:
        from_id = int(request.POST.get('from_id'))
        to_id = int(request.POST.get('to_id'))
    except (TypeError, ValueError):
        return HttpResponseBadRequest("bad ids")

    if from_id == to_id:
        return JsonResponse({'ok': False, 'reason': 'self'}, status=400)

    obj, created = RoleDelegation.objects.get_or_create(
        from_role_id=from_id, to_role_id=to_id, defaults={'is_active': True}
    )
    if not created:
        obj.is_active = not obj.is_active
        obj.save(update_fields=['is_active', 'updated_at'])

    # Güncel listeyi döndürmek istersek:
    qs = RoleDelegation.objects.filter(is_active=True).values_list('from_role_id', 'to_role_id')
    pair_keys = [f"{a}_{b}" for a, b in qs]

    return JsonResponse({
        'ok': True,
        'active': obj.is_active,
        'pair_key': f"{from_id}_{to_id}",
        'pair_keys': pair_keys,
    })


@login_required
@user_passes_test(staff_required)
@require_POST
def update_meta(request):
    """Üst-bilgi (Form No, Revizyon, Güncelleme) güncellemesi."""
    meta = DelegationDocument.singleton()
    meta.form_no = (request.POST.get('form_no') or '').strip()

    rev = request.POST.get('revizyon_tarihi') or None
    gun = request.POST.get('guncelleme_tarihi') or None
    meta.revizyon_tarihi = parse_date(rev) if rev else None
    meta.guncelleme_tarihi = parse_date(gun) if gun else None

    meta.save()
    return JsonResponse({
        'ok': True,
        'form_no': meta.form_no,
        'revizyon_tarihi': str(meta.revizyon_tarihi) if meta.revizyon_tarihi else '',
        'guncelleme_tarihi': str(meta.guncelleme_tarihi) if meta.guncelleme_tarihi else '',
    })


@login_required
@user_passes_test(staff_required)
@require_POST
def reset_all(request):
    """Tüm vekalet kayıtlarını sil (matrisi boşalt)."""
    RoleDelegation.objects.all().delete()
    return JsonResponse({'ok': True})
