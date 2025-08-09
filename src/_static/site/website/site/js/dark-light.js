(function () {
  "use strict";
  const root = document.getElementsByTagName('html')[0];
  if ( !root ) { return; }

  let rootMode = root.getAttribute('data-bs-theme');
  let mode = window.localStorage.getItem('mode') ?? rootMode ?? 'dark';
  root.setAttribute('data-bs-theme', mode );

  var t, e, r, a, n, o;
  null !== (e = document.querySelector('[data-bs-toggle="mode"]')) &&
  ((t = e.querySelector("#theme-mode-btn")),
    "light" === mode ? (root.setAttribute("data-bs-theme", "light"), (t.checked = !0)) : (root.removeAttribute("data-bs-theme", "light"), (t.checked = !1)),
    e.addEventListener("click", function (e) {
      t.checked ? (root.setAttribute("data-bs-theme", "light"), window.localStorage.setItem("mode", "light")) : (root.removeAttribute("data-bs-theme", "light"), window.localStorage.setItem("mode", "dark"));
    }))
})(jQuery);
