document.addEventListener('DOMContentLoaded', function () {
  try {
    // İçerik alanı
    var contentMain = document.querySelector('#content-main') ||
                      document.querySelector('#changelist-form')?.parentElement ||
                      document.querySelector('#changelist');
    if (!contentMain) return;

    // Sağdaki filtre kutusunu bul
    var sidebar = document.querySelector('.col-right, .sidebar');
    var filters = null;
    if (sidebar) {
      filters = sidebar.querySelector('#changelist-filter') || sidebar.querySelector('.filters');
    }
    if (!filters) {
      // Bazı temalarda filtre direkt içerikte olabilir
      filters = document.querySelector('#changelist-filter');
    }
    if (!filters) return;

    // Üste "Filtreler" pulldown ekle
    var details = document.createElement('details');
    details.className = 'tn-filter-panel';

    var summary = document.createElement('summary');
    summary.textContent = 'Filtreler';
    details.appendChild(summary);

    // Filtreleri taşımak (klon değil — linkler ve formlar bozulmasın)
    details.appendChild(filters);

    // Changelist'in üstüne yerleştir
    var changeList = document.querySelector('#changelist') || document.querySelector('#changelist-form');
    if (changeList) {
      contentMain.insertBefore(details, changeList);
    } else {
      contentMain.prepend(details);
    }

    // Artık sağ sidebar güvenle gizlenebilir
    document.body.classList.add('tn-filter-ready');
  } catch (e) {
    // Sessizce geç
    console && console.warn && console.warn('TrainingNeed filters move failed:', e);
  }
});
