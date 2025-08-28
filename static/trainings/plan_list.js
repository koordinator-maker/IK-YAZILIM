// Silme işlemi için teyit penceresi
document.addEventListener("click", function (e) {
  const btn = e.target.closest("form.delete-form button");
  if (!btn) return;
  const form = btn.closest("form.delete-form");
  const title = form?.dataset?.title || "bu planı";
  const ok = confirm(`Kalıcı olarak silinsin mi?\n\n${title}`);
  if (!ok) e.preventDefault();
});
