// trainings/static/trainings/admin/assignment_requirements.js
(function () {
  function onChange(e) {
    var sel = e.target;
    if (!sel || !sel.classList.contains('comp-select')) return;
    var tid = sel.getAttribute('data-tid');
    var wrap = document.querySelector('.comp-date-wrap[data-for="' + tid + '"]');
    var placeholder = document.querySelector('.comp-date-placeholder[data-for="' + tid + '"]');
    if (sel.value === 'yes') {
      if (wrap) wrap.style.display = '';
      if (placeholder) placeholder.style.display = 'none';
    } else {
      if (wrap) wrap.style.display = 'none';
      if (placeholder) placeholder.style.display = '';
    }
  }

  function init() {
    document.querySelectorAll('.comp-select').forEach(function (el) {
      el.addEventListener('change', onChange);
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
