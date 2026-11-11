// Renders every <span class="math"> with the local copy of KaTeX (vendor/katex). No network access.
(function () {
  if (!window.katex) return;
  document.querySelectorAll(".math").forEach(function (el) {
    try {
      window.katex.render(el.textContent, el, { throwOnError: true, output: "html" });
    } catch (e) { /* leave the plain text in place */ }
  });
})();
