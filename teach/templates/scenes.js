/* scenes.js — shared runtime for teach visual lessons.
   Workspace: copy to ./assets/scenes.js; lesson HTML links ../assets/scenes.js.
   Vanilla JS on purpose: the runtime is ~80 lines; jQuery/Lodash would only add weight. */
(function () {
  "use strict";

  var root = document.querySelector("[data-scenes]");
  if (!root) return;

  /* 1. Scene captions from <script type="application/json" id="scene-data"> */
  var dataEl = document.getElementById("scene-data");
  var scenes = [];
  if (dataEl) {
    try { scenes = JSON.parse(dataEl.textContent); } catch (e) { scenes = []; }
  }
  var whyLabel = root.getAttribute("data-scn-why-label") || "Why it matters:";

  /* 2. Step-tagged visual elements */
  var stepEls = Array.prototype.slice.call(root.querySelectorAll("[data-step]"));
  var maxStep = stepEls.reduce(function (m, el) {
    var s = parseInt(el.getAttribute("data-step"), 10);
    return isNaN(s) ? m : Math.max(m, s);
  }, 0);
  var total = Math.max(scenes.length, maxStep);
  if (total < 1) return;

  /* 3. Caption container — one comprehensive item per scene; only the active one is shown */
  var captionBox = root.querySelector("[data-scn-captions]");
  var scrollBox = root.querySelector("[data-scn-scroll]");
  var captionItems = [];
  if (captionBox) {
    for (var i = 0; i < total; i++) {
      var s = scenes[i] || {};
      if (s.text && !s.paragraphs) s.paragraphs = [s.text]; /* legacy single-paragraph fallback */
      var item = document.createElement("div");
      item.className = "scn-caption-item";
      var html = "";
      if (s.title) html += '<h2 class="scn-caption-title">' + esc(s.title) + "</h2>";
      if (Array.isArray(s.paragraphs) && s.paragraphs.length) {
        var paras = "";
        for (var p = 0; p < s.paragraphs.length; p++) paras += "<p>" + esc(s.paragraphs[p]) + "</p>";
        html += '<div class="scn-caption-text">' + paras + "</div>";
      }
      if (Array.isArray(s.points) && s.points.length) {
        var lis = "";
        for (var q = 0; q < s.points.length; q++) lis += "<li>" + esc(s.points[q]) + "</li>";
        html += '<ul class="scn-caption-points">' + lis + "</ul>";
      }
      if (s.code) html += '<pre class="scn-caption-code"><code>' + esc(s.code) + "</code></pre>";
      if (s.why) html += '<p class="scn-caption-why"><span class="scn-why-label">' + esc(whyLabel) + "</span> " + esc(s.why) + "</p>";
      item.innerHTML = html;
      captionBox.appendChild(item);
      captionItems.push(item);
    }
  }

  /* 4. Controls: prev, next, dots, counter */
  var prevBtn = root.querySelector("[data-scn-prev]");
  var nextBtn = root.querySelector("[data-scn-next]");
  var dotsWrap = root.querySelector("[data-scn-dots]");
  var counter = root.querySelector("[data-scn-counter]");
  var dots = [];

  if (dotsWrap) {
    for (var d = 0; d < total; d++) {
      (function (idx) {
        var dot = document.createElement("button");
        dot.type = "button";
        dot.className = "scn-dot";
        dot.setAttribute("aria-label", "Scene " + (idx + 1));
        dot.addEventListener("click", function () { go(idx + 1); });
        dotsWrap.appendChild(dot);
        dots.push(dot);
      })(d);
    }
  }
  if (prevBtn) prevBtn.addEventListener("click", function () { go(current - 1); });
  if (nextBtn) nextBtn.addEventListener("click", function () { go(current + 1); });
  document.addEventListener("keydown", function (e) {
    if (e.key === "ArrowRight") go(current + 1);
    else if (e.key === "ArrowLeft") go(current - 1);
  });

  var current = 1;

  function go(n) {
    if (n < 1 || n > total || n === current) return;
    current = n;
    render();
    /* fixed-viewport layout: reset the right explanation pane to the top */
    if (scrollBox) {
      if (scrollBox.scrollTo) scrollBox.scrollTo({ top: 0, behavior: "smooth" });
      else scrollBox.scrollTop = 0;
    }
  }

  function render() {
    /* stage: reveal elements up to the current scene; ring the newest one */
    for (var i = 0; i < stepEls.length; i++) {
      var el = stepEls[i];
      var s = parseInt(el.getAttribute("data-step"), 10);
      if (isNaN(s)) continue;
      if (s < current) { el.classList.add("scn-on"); el.classList.remove("scn-hot"); }
      else if (s === current) { el.classList.add("scn-on", "scn-hot"); }
      else { el.classList.remove("scn-on", "scn-hot"); }
    }
    /* captions */
    for (var c = 0; c < captionItems.length; c++) {
      captionItems[c].classList.toggle("scn-on", c === current - 1);
    }
    /* dots + counter + buttons */
    for (var k = 0; k < dots.length; k++) {
      dots[k].classList.toggle("scn-dot-on", k === current - 1);
      dots[k].setAttribute("aria-current", k === current - 1 ? "step" : "false");
    }
    if (counter) counter.textContent = current + " / " + total;
    if (prevBtn) prevBtn.disabled = current === 1;
    if (nextBtn) nextBtn.disabled = current === total;
  }

  function esc(t) {
    var d = document.createElement("div");
    d.textContent = t;
    return d.innerHTML;
  }

  render();
})();