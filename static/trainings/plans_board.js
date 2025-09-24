(function () {
  const qs = (s, el = document) => el.querySelector(s);
  const ce = (t) => document.createElement(t);
  const params = new URLSearchParams(location.search);
  const year = parseInt(params.get('year') || new Date().getFullYear(), 10);
  const weeksInYear = (y) => {
    // ISO haftaları: 4 Ocak'ın haftası 1, yıl sonu hafta sayısı:
    const d = new Date(Date.UTC(y, 11, 28)); // 28 Aralık her zaman son haftada
    return isoWeek(d);
  };

  function isoWeek(d) {
    const date = new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate()));
    // Perşembe hilesi
    const dayNum = (date.getUTCDay() + 6) % 7;
    date.setUTCDate(date.getUTCDate() - dayNum + 3);
    const firstThursday = new Date(Date.UTC(date.getUTCFullYear(), 0, 4));
    const diff = (date - firstThursday) / 86400000;
    return 1 + Math.floor(diff / 7);
  }
  function isoYear(d) {
    const date = new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate()));
    const dayNum = (date.getUTCDay() + 6) % 7;
    date.setUTCDate(date.getUTCDate() - dayNum + 3);
    return date.getUTCFullYear();
  }

  /* ---------- Yıl navigasyonu ---------- */
  qs('#lblYear').textContent = year;
  qs('#btnPrev').onclick = () => location.assign(`/plans/?year=${year - 1}`);
  qs('#btnNext').onclick = () => location.assign(`/plans/?year=${year + 1}`);
  qs('#btnThis').onclick = () => location.assign(`/plans/?year=${new Date().getFullYear()}`);

  /* ---------- Başlık: Aylar + Haftalar ---------- */
  const monthNames = ['Ocak','Şubat','Mart','Nisan','Mayıs','Haziran','Temmuz','Ağustos','Eylül','Ekim','Kasım','Aralık'];
  const wiy = weeksInYear(year);
  const monthsEl = qs('#months');
  const weeksEl  = qs('#weeks');

  // 1..52/53 haftalar için ay blokları
  // Ay bloğu: o ayın kapsadığı ISO hafta sayısı
  function monthWeekSpans(y){
    const spans = [];
    for (let m=0; m<12; m++){
      const first = new Date(Date.UTC(y, m, 1));
      const last  = new Date(Date.UTC(y, m+1, 0));
      // Ay içindeki tüm günlerin ISO haftaları
      const seen = new Set();
      for (let d = new Date(first); d <= last; d.setUTCDate(d.getUTCDate()+1)){
        if (isoYear(d) !== y) continue; // başka yıla düşen günleri at
        seen.add(isoWeek(d));
      }
      spans.push([...seen].sort((a,b)=>a-b));
    }
    return spans.map(weeks => ({ weeks, count: weeks.length }));
  }
  const spans = monthWeekSpans(year);
  monthsEl.style.gridTemplateColumns = `repeat(${wiy}, var(--weekW))`;
  weeksEl.style.gridTemplateColumns  = `repeat(${wiy}, var(--weekW))`;

  // Ay hücreleri
  spans.forEach((sp, idx) => {
    if (sp.count === 0) return;
    const m = ce('div');
    m.className = 'month';
    // grid-column: ilk haftadan başla, haftalar kadar uzat
    const start = sp.weeks[0];
    m.style.gridColumn = `${start} / span ${sp.count}`;
    m.textContent = monthNames[idx];
    monthsEl.appendChild(m);
  });

  // Hafta numaraları
  for (let w=1; w<=wiy; w++){
    const el = ce('div');
    el.className = 'week';
    el.textContent = w;
    weeksEl.appendChild(el);
  }

  /* ---------- Satırlar (planlar) ---------- */
  const rowsEl = qs('#rows');
  const tip = qs('#tip');
  const tTitle = qs('.t-title', tip);
  const tSub   = qs('.t-sub',   tip);
  const tBody  = qs('.t-body',  tip);
  const tAdmin = qs('#tAdmin',  tip);

  function clamp(n, min, max){ return Math.max(min, Math.min(max, n)); }

  function planRow(p){
    // tarihleri parse et
    const s = new Date(p.start + 'T00:00:00Z');
    const e = new Date(p.end   + 'T00:00:00Z');

    // Bu yıl ile kesişen kısmı al
    let sw = isoWeek(s), ew = isoWeek(e);
    let sy = isoYear(s),  ey = isoYear(e);

    // farklı yıllara taşma: bu sayfada sadece [1..wiy]
    let startW = (sy < year) ? 1 : sw;
    let endW   = (ey > year) ? wiy : ew;
    startW = clamp(startW, 1, wiy);
    endW   = clamp(endW,   1, wiy);
    const span = Math.max(1, endW - startW + 1);

    // satır
    const row = ce('div'); row.className = 'row';

    const left = ce('div'); left.className = 'left sticky';
    const t1 = ce('div'); t1.className = 'training-title'; t1.textContent = p.title;
    const t2 = ce('div'); t2.className = 'training-sub';
    t2.textContent = `Kod: ${p.code} • ${p.start} – ${p.end}`;
    left.append(t1, t2);

    const grid = ce('div'); grid.className = 'grid';

    const block = ce('div'); block.className = 'block';
    block.style.gridColumn = `${startW} / span ${span}`;
    const code = ce('span'); code.className = 'code'; code.textContent = p.code;
    const title = ce('span'); title.textContent = ''; // kodun yanında kısa görünüm
    block.append(code, title);

    // hover → tooltip (katılımcıları plandan çeker)
    block.addEventListener('mouseenter', async (ev) => {
      tTitle.textContent = p.title;
      tSub.textContent   = `${p.start} – ${p.end} • ${p.location || '—'} • Kapasite: ${p.capacity ?? '—'}`;
      tBody.innerHTML    = 'Yükleniyor…';
      tAdmin.href = `/admin/trainings/trainingplan/${p.id}/change/`;
      tip.hidden = false;

      // konum
      const r = ev.currentTarget.getBoundingClientRect();
      tip.style.left = `${Math.min(window.innerWidth - 360, r.left + 10)}px`;
      tip.style.top  = `${r.bottom + 8}px`;

      try{
        const res = await fetch(`/api/plans/${p.id}/`);
        if (!res.ok) throw 0;
        const j = await res.json();
        const names = (j.attendees || []).map(a => a.full_name || a.username);
        tBody.innerHTML = names.length ? ('<ul style="margin:0;padding-left:18px">' + names.map(n=>`<li>${n}</li>`).join('') + '</ul>')
                                       : 'Katılımcı yok.';
      }catch{
        tBody.textContent = 'Detay okunamadı.';
      }
    });
    block.addEventListener('mouseleave', () => { tip.hidden = true; });

    grid.appendChild(block);
    row.append(left, grid);
    return row;
  }

  async function loadPlans(){
    const res = await fetch('/api/plans/');
    const j = await res.json();
    const plans = (j.results || []).filter(p => {
      // bu yıl ile kesişen planları göster
      const s = new Date(p.start+'T00:00:00Z');
      const e = new Date(p.end  +'T00:00:00Z');
      const sy = isoYear(s), ey = isoYear(e);
      return !(ey < year || sy > year);
    });
    if (!plans.length){
      rowsEl.innerHTML = '<div style="padding:18px;color:#6b7280">Bu yılda plan yok.</div>';
      return;
    }
    plans.sort((a,b)=> (a.start < b.start ? -1:1));
    plans.forEach(p => rowsEl.appendChild(planRow(p)));
  }

  loadPlans();
})();
