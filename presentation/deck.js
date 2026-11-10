// Deck behaviour: fit each 1728 x 1117 stage to the window, build the side navigation, move between slides.
(function () {
  const W = 1728, H = 1117;
  const deck = document.getElementById("deck");
  const slides = Array.from(document.querySelectorAll(".slide"));

  function fit() {
    const w = deck.clientWidth || window.innerWidth, h = deck.clientHeight || window.innerHeight;
    if (!w || !h) return;                       // hidden window: wait for the next resize
    document.documentElement.style.setProperty("--s", Math.min(w / W, h / H));
  }
  window.addEventListener("resize", fit);
  if ("ResizeObserver" in window) new ResizeObserver(fit).observe(deck);
  fit();

  // Sections as in the Figma side list. "target" is the slide id each entry jumps to (null = not built yet).
  const SECTIONS = [
    { n: 1, name: "Intro", target: "intro" },
    { n: 2, name: "Definitions", target: "definitions" },
    { n: 3, name: "Historical Data", target: "weather",
      sub: [{ key: "weather", name: "Weather" }, { key: "energy-use", name: "Energy Use" }, { key: "affordability", name: "Energy Affordability" },
            { key: "synthesis", name: "Combined View" }] },
    { n: 4, name: "Projections", target: "projected",
      sub: [{ key: "projected", name: "Projected Numbers" }, { key: "projections", name: "Regional Affordability" }] },
    { n: 5, name: "Policy Idea", target: "policy" },
    { n: 6, name: "Limitations", target: "limitations" },
    { n: 7, name: "Reproducibility", target: "reproducibility" },
    { n: 8, name: "Conclusion", target: "conclusion" },
  ];

  document.querySelectorAll("nav.toc").forEach((nav) => {
    const active = Number(nav.dataset.active);
    const activeSub = nav.dataset.sub || null;
    SECTIONS.forEach((sec) => {
      const a = document.createElement("a");
      a.textContent = `${sec.n}. ${sec.name}`;
      a.href = sec.target ? `#${sec.target}` : "#";
      if (!sec.target) { a.setAttribute("aria-disabled", "true"); a.addEventListener("click", (e) => e.preventDefault()); }
      if (sec.n === active) { a.classList.add("is-active"); a.setAttribute("aria-current", "true"); }
      nav.appendChild(a);
      if (sec.sub && sec.n === active) {
        const ul = document.createElement("ul");
        ul.className = "sub";
        sec.sub.forEach((sb) => {
          const li = document.createElement("li");
          const sa = document.createElement("a");
          sa.textContent = sb.name;
          sa.href = `#${sb.key}`;
          if (sb.key === activeSub) sa.classList.add("is-active");
          li.appendChild(sa);
          ul.appendChild(li);
        });
        nav.appendChild(ul);
      }
    });
  });

  // The grey bar marks the active section (and its sub-list, when open).
  function placeBars() {
    document.querySelectorAll("nav.toc").forEach((nav) => {
      const bar = nav.parentElement.querySelector(".toc-bar");
      const a = nav.querySelector("a.is-active");
      if (!bar || !a) return;
      const sub = a.nextElementSibling && a.nextElementSibling.classList.contains("sub") ? a.nextElementSibling : null;
      const bottom = sub ? sub.offsetTop + sub.offsetHeight : a.offsetTop + a.offsetHeight;
      bar.style.top = nav.offsetTop + a.offsetTop - 4 + "px";
      bar.style.height = Math.max(36, bottom - a.offsetTop + 8) + "px";
    });
  }
  placeBars();
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(placeBars);

  function current() {
    const y = deck.scrollTop + window.innerHeight / 2;
    return Math.max(0, slides.findIndex((s) => y >= s.offsetTop && y < s.offsetTop + s.offsetHeight));
  }
  function go(i) {
    const k = Math.max(0, Math.min(slides.length - 1, i));
    slides[k].scrollIntoView({ block: "start" });
    history.replaceState(null, "", `#${slides[k].id}`);
  }
  window.deckGo = go;

  document.addEventListener("keydown", (e) => {
    if (["ArrowDown", "PageDown", "ArrowRight", " "].includes(e.key)) { e.preventDefault(); go(current() + 1); }
    if (["ArrowUp", "PageUp", "ArrowLeft"].includes(e.key)) { e.preventDefault(); go(current() - 1); }
    if (e.key === "Home") { e.preventDefault(); go(0); }
    if (e.key === "End") { e.preventDefault(); go(slides.length - 1); }
  });
  document.querySelectorAll(".back").forEach((b) => b.addEventListener("click", () => go(current() - 1)));

  function fromHash() {
    const id = location.hash.slice(1);
    const i = slides.findIndex((s) => s.id === id);
    if (i >= 0) slides[i].scrollIntoView({ block: "start", behavior: "instant" });
  }
  window.addEventListener("hashchange", fromHash);
  fromHash();
})();
