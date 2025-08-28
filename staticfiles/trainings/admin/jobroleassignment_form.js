// trainings/static/trainings/admin/jobroleassignment_form.js
(function () {
  function hideRelatedLinksFor(selectorIds) {
    selectorIds.forEach(function (id) {
      var wrap = document.querySelector('#' + id)?.closest('.related-widget-wrapper');
      if (!wrap) return;
      wrap.querySelectorAll('.related-widget-wrapper-link').forEach(function (a) {
        var title = (a.getAttribute('title') || '').toLowerCase();
        // default add/view/delete linklerini gizle
        if (title.includes('add') || title.includes('ekle')) a.style.display = 'none';
        if (title.includes('view') || title.includes('görüntüle')) a.style.display = 'none';
        if (title.includes('delete') || title.includes('sil')) a.style.display = 'none';
        // change kalsın
      });
    });
  }

  function addCustomAddRoleButton(roleFieldId, addUrlBase) {
    var roleWrap = document.querySelector('#' + roleFieldId)?.closest('.related-widget-wrapper, .form-row');
    var userIdInput = document.querySelector('#id_user'); // autocomplete hidden input da bu id'yi taşır
    if (!roleWrap || !userIdInput) return;
    var uid = userIdInput.value;
    if (!uid) return;

    // varsa tekrar ekleme
    if (roleWrap.querySelector('.add-role-for-person')) return;

    var btn = document.createElement('a');
    btn.className = 'button add-role-for-person';
    btn.style.marginLeft = '8px';
    btn.textContent = 'add another role for this person';
    btn.href = addUrlBase + '?user=' + encodeURIComponent(uid);

    // role alanının hemen sağına ekle
    var target = roleWrap.querySelector('select, input');
    (target?.parentNode || roleWrap).appendChild(btn);
  }

  function init() {
    // user alanı: add/view/delete gizle (change kalsın)
    hideRelatedLinksFor(['id_user']);
    // role alanı: add/view/delete gizle, özel buton ekle
    // role alanının gerçek id'si şablondan data-attr ile gelecekse daha sağlam olurdu;
    // pratikte autocomplete/select id'si "id_<alanadi>"
    var roleFieldCandidates = ['id_role', 'id_job_role', 'id_jobrole', 'id_position', 'id_job'];
    var roleId = roleFieldCandidates.find(function (i) { return document.getElementById(i); });
    if (roleId) {
      hideRelatedLinksFor([roleId.replace('#', '')]);
      addCustomAddRoleButton(roleId, '/admin/trainings/jobroleassignment/add/');
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
