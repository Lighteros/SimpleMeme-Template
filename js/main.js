(function () {
  var S = window.SITE || {};
  var $ = function (id) { return document.getElementById(id); };
  var root = document.documentElement.style;
  if (S.bg) root.setProperty("--bg", S.bg);
  if (S.accent) root.setProperty("--accent", S.accent);

  var name = S.name || "TOKEN";
  document.title = S.ticker ? name + " (" + S.ticker + ")" : name;
  $("name").textContent = name;
  $("ticker").textContent = S.ticker || "";

  var logo = $("logo");
  logo.alt = name + " logo";
  if (S.logo) logo.src = S.logo;
  logo.onerror = function () { logo.onerror = null; logo.src = "img/logo.svg"; };

  var ca = S.ca || "TBA";
  $("ca-text").textContent = ca;
  $("ca").setAttribute("aria-label", "Copy contract address " + ca);

  var x = $("x");
  if (S.xUrl && S.xUrl !== "#") { x.href = S.xUrl; }
  else { x.classList.add("pending"); x.setAttribute("aria-disabled", "true"); x.removeAttribute("href"); }

  var btn = $("ca"), status = $("copy-status"), t;
  function done(ok) {
    btn.classList.toggle("copied", ok);
    status.textContent = ok ? "Copied!" : "Copy failed - long-press to select";
    clearTimeout(t);
    t = setTimeout(function () { status.textContent = ""; btn.classList.remove("copied"); }, 1600);
  }
  function fallback() {
    var ta = document.createElement("textarea");
    ta.value = ca; ta.setAttribute("readonly", ""); ta.style.position = "fixed"; ta.style.opacity = "0";
    document.body.appendChild(ta); ta.select();
    var ok = false; try { ok = document.execCommand("copy"); } catch (e) {}
    document.body.removeChild(ta); done(ok);
  }
  btn.addEventListener("click", function () {
    if (navigator.clipboard && window.isSecureContext) {
      navigator.clipboard.writeText(ca).then(function () { done(true); }, fallback);
    } else fallback();
  });
})();
