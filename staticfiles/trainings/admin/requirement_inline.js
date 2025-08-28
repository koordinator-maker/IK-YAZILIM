// trainings/static/trainings/admin/requirement_inline.js
(function () {
  function ensureHeaderAddButton(group) {
    // Django tabular inline: add-row genelde <tr class="add-row"><a>...</a></tr>
    var addRowLink = group.querySelector(".add-row a");
    if (!addRowLink) return;

    // Başlık: h2 varsa onu, yoksa legend deneyelim
    var header = group.querySelector("h2, legend");
    if (!header) return;

    // Zaten oluşturduysak tekrar ekleme
    if (header.querySelector(".trq-add-btn")) return;

    // Üste yeni bir buton koy, orijinali gizli kalsın
    var wrap = document.createElement("span");
    wrap.className = "trq-add-btn";
    wrap.style.cssText = "float:right; font-weight:normal;";

    var btn = document.createElement("a");
    btn.href = "#";
    btn.className = "button";
    btn.textContent = "Başka bir Görev Eğitim Gerekliliği ekle";
    btn.addEventListener("click", function (e) {
      e.preventDefault();
      // Alttaki orijinal add butonunu tetikle
      addRowLink.click();
    });

    wrap.appendChild(btn);
    header.appendChild(wrap);
  }

  function tweakInline() {
    document.querySelectorAll(".inline-group.tabular, .inline-group").forEach(function (group) {
      ensureHeaderAddButton(group);
    });

    // İlişkili alan yanındaki change/add/delete linklerini gizle, sadece "view" kalsın
    document.querySelectorAll(".related-widget-wrapper-link").forEach(function (a) {
      var title = (a.getAttribute("title") || "").toLowerCase();
      if (title.includes("ekle") || title.includes("add")) a.style.display = "none";
      if (title.includes("değiştir") || title.includes("change")) a.style.display = "none";
      if (title.includes("sil") || title.includes("delete")) a.style.display = "none";
      // "görüntüle/view" kalsın
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () {
      tweakInline();
      // Django admin bazen formset'i sonradan enjekte eder; küçük gecikme ile tekrar dene
      setTimeout(tweakInline, 150);
    });
  } else {
    tweakInline();
    setTimeout(tweakInline, 150);
  }

  // Yeni inline satır eklendikçe tekrar uygula
  document.addEventListener("formset:added", tweakInline);
})();
