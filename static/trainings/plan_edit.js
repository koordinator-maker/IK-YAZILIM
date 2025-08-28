// plan_edit.js
(function () {
  // Hata varsa participants alanı görünür olsun
  const err = document.querySelector('.err[data-field="participants"]') || null;
  const details = document.querySelector('.picker');
  if (details && err) details.open = true;

  // Chip’teki “×” alanına tıklanınca checkbox’ı toggle’la
  document.querySelectorAll('.chip .rm').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
      const chip = btn.closest('.chip');
      const cb = chip.querySelector('input[type="checkbox"]');
      cb.checked = !cb.checked;
      // görsel feedback için label’a tık davranışı:
      chip.classList.toggle('to-remove', cb.checked);
    });
  });
})();
