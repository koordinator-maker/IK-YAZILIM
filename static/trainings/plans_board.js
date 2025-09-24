// Rev: 2025-09-24 13:55 r5
(function () {
  const qs = (s, el = document) => el.querySelector(s);
  const ce = (t) => document.createElement(t);

  const params = new URLSearchParams(location.search);
  const year = parseInt(params.get('year') || new Date().getFullYear(), 10);

  function isoWeek(d) {
    const date = new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()));
    const dayNum = (date.getUTCDay() + 6) % 7;
    date.setUTCDate(date.getUTCDate() - dayNum + 3);
    const firstThursday = new Date(Date.UTC(date.getUTCFullYear(), 0, 4));
    const dayNum2 = (firstThursday.getUTCDay() + 6) % 7;
    firstThursday.setUTCDate(firstThursday.getUTCDate() - dayNum2 + 3);
    return 1 + Math.round(((date - firstThursday) / 86400000 - 3) / 7);
  }
  function weeksInYear(y){
    const d = new Date(Date.UTC(y, 11, 28));
    return isoWeek(d);
  }
  const WIY = weeksInYear(year);
  const weekPx = () => parseInt(getComputedStyle(document.documentElement).getPropertyValue('--weekW'));

  const monthNames = ['Ocak','Şubat','Mart','Nisan','Mayıs','Haziran','Temmuz','Ağustos','Eylül','Ekim','Kasım','Aralık'];
  const monthsEl = qs('#months');
  const weeksEl  = qs('#weeks');

  function monthWeekSpans(y){
    const spans = [];
    for (let m=0; m<12; m++){
      const first = new Date(y, m, 1);
      const last  = new Date(y, m+1, 0);
      const seen = new Set();
      for (let d=new Date(first); d<=last; d.setDate(d.getDate()+1)){
        seen.add(isoWeek(d));
      }
      spans.push([...seen].sort((a,b)=>a-b));
    }
    return spans;
  }

  function buildHeader(){
    const spans = monthWeekSpans(year);
    monthsEl.innerHTML = '';
    spans.forEach((weeks, i) => {
      const m = ce('div');
      m.className = 'month';
      m.style.gridColumn = `span ${weeks.length}`;
      m.textContent = monthNames[i];
      monthsEl.appendChild(m);
    });

    weeksEl.innerHTML = '';
    for(let w=1; w<=WIY; w++){
      const wk = ce('div');
      wk.className = 'week';
      wk.textContent = `H${w}`;
      weeksEl.appendChild(wk);
    }
  }

  const rowsEl = qs('#rows');
  function weekToLeft(w){ return (w-1) * weekPx(); }

  function mkRow(plan){
    const row = ce('div'); row.className = 'row';
    const left = ce('div'); left.className = 'row-label';
    left.textContent = plan.title;

    const grid = ce('div'); grid.className = 'row-grid';
    for(let w=1; w<=WIY; w++){
      const mark = ce('div'); mark.className = 'w';
      mark.style.left = weekToLeft(w)+'px';
      grid.appendChild(mark);
    }

    const block = ce('div'); block.className = 'block';
    const sw = isoWeek(new Date(plan.start));
    const ew = isoWeek(new Date(plan.end || plan.start));
    block.style.left = weekToLeft(sw)+'px';
    block.style.width = ((ew - sw + 1) * weekPx()) + 'px';
    block.textContent = plan.title;

    block.addEventListener('click', () => {
      window.open(`/admin/trainings/trainingplan/${plan.id}/change/`, '_blank', 'noopener');
    });

    block.addEventListener('mouseenter', (e)=> showTipFor(plan, e.currentTarget));
    block.addEventListener('mouseleave', () => scheduleHideTip());

    grid.appendChild(block);
    row.append(left, grid);
    return row;
  }

  async function loadPlans(){
    const res = await fetch('/api/plans/?year=' + year);   // ⟵ yıl filtresi
    const j = await res.json();
    const plans = Array.isArray(j) ? j : j.results || [];
    rowsEl.innerHTML = '';
    plans.forEach(p => rowsEl.appendChild(mkRow(p)));
  }

  const tip    = qs('#tip');
  const tTitle = qs('.t-title');
  const tSub   = qs('.t-sub');
  const tBody  = qs('.t-body');
  const tAdmin = qs('#tAdmin');
  let hideTimer = null;
  function clearHide(){ if(hideTimer){ clearTimeout(hideTimer); hideTimer=null; } }
  function scheduleHideTip(){ clearHide(); hideTimer = setTimeout(()=> tip.hidden = true, 400); }
  tip.addEventListener('mouseenter', clearHide);
  tip.addEventListener('mouseleave', scheduleHideTip);

  async function showTipFor(plan, anchorEl){
    clearHide();
    const r = anchorEl.getBoundingClientRect();
    tip.style.left = (r.left + 8) + 'px';
    tip.style.top  = (r.top + r.height + 8) + 'px';
    tip.hidden = false;

    tTitle.textContent = plan.title;
    const subBits = [];
    if (plan.location) subBits.push(plan.location);
    if (plan.capacity) subBits.push(`Kapasite: ${plan.capacity}`);
    tSub.textContent = subBits.join(' • ');

    try{
      const dj = await (await fetch(`/api/plans/${plan.id}/`)).json();
      const parts = (dj.participants && dj.participants.length) ? dj.participants.join(', ') : 'Katılımcı yok';
      tBody.textContent = `${plan.start} → ${plan.end}\n${parts}`;
    }catch{
      tBody.textContent = `${plan.start} → ${plan.end || plan.start}`;
    }
    tAdmin.href = `/admin/trainings/trainingplan/${plan.id}/change/`;
  }

  const lblYear = qs('#lblYear');
  const btnPrev = qs('#btnPrev');
  const btnNext = qs('#btnNext');
  const btnThis = qs('#btnThis');
  function setYear(y){
    const url = new URL(location.href);
    url.searchParams.set('year', y);
    location.href = url.toString();
  }
  lblYear.textContent = year;
  btnPrev.addEventListener('click', ()=> setYear(year-1));
  btnNext.addEventListener('click', ()=> setYear(year+1));
  btnThis.addEventListener('click', ()=> setYear(new Date().getFullYear()));

  buildHeader();
  loadPlans();
})();
