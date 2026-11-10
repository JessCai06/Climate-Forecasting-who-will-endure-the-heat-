// Charts for the deck, drawn from window.DECK_DATA (presentation/data/deck_data.js, made by
// code/export_deck_data.py from the policy analysis outputs). Colours carry one meaning across every slide:
// see COLOR and REGION_COLOR below, and the legend on each chart.
(function () {
  const D = window.DECK_DATA;
  const tip = document.getElementById("tip");

  // ---------------------------------------------------------------- one palette for the whole deck
  const COLOR = {
    days: "#f77f00",      // cooling-required days (high >= 95 F)
    nights: "#1d3557",    // hot nights (low >= 75 F)
    cdd: "#e9a21b",       // cooling degree days
    hottest: "#9e2a2b",   // hottest day of the year
    demand: "#0077b6",    // electricity demand / use
    price: "#2a9d8f",     // electricity price
    over: "#e63946",      // over the affordable bar; city in need because of the cost of cooling
    under: "#8d99ae",     // under the bar
    noac: "#6a4c93",      // city in need because many homes have no AC
    ink: "#000", grid: "#e7e7e7", muted: "#9a9a9a",
  };
  const REGION_COLOR = {
    TEX: "#c44e52", FLA: "#f28e2b", CAL: "#edc948", SW: "#b07aa1", SE: "#ff9da7", CAR: "#9c755f", TEN: "#76716b",
    MIDA: "#4e79a7", MIDW: "#76b7b2", CENT: "#59a14f", NY: "#17becf", NE: "#1f3a93", NW: "#8c564b",
  };
  const REGION_NAME = {
    TEX: "Texas (ERCOT)", FLA: "Florida", CAL: "California", SW: "Southwest", SE: "Southeast", CAR: "Carolinas", TEN: "Tennessee",
    MIDA: "Mid-Atlantic (PJM)", MIDW: "Midwest (MISO)", CENT: "Central (SPP)", NY: "New York", NE: "New England", NW: "Northwest",
  };
  const METRIC = {
    days: { label: "Cooling-required days", unit: "days a year, high ≥ 95 °F", fmt: d3.format(".1f") },
    nights: { label: "Hot nights", unit: "nights a year, low ≥ 75 °F", fmt: d3.format(".1f") },
    cdd: { label: "Cooling degree days", unit: "°F-days a year", fmt: d3.format(",.0f") },
    hottest: { label: "Hottest day", unit: "°F, hottest day of the year", fmt: d3.format(".1f") },
  };

  // ---------------------------------------------------------------- helpers
  function showTip(ev, text) {
    tip.textContent = text;
    tip.hidden = false;
    tip.style.left = Math.min(ev.clientX + 14, window.innerWidth - tip.offsetWidth - 8) + "px";
    tip.style.top = Math.min(ev.clientY + 14, window.innerHeight - tip.offsetHeight - 8) + "px";
  }
  function hideTip() { tip.hidden = true; }
  function svgFor(el, label) {
    const w = el.clientWidth, h = el.clientHeight;
    return d3.select(el).append("svg").attr("viewBox", `0 0 ${w} ${h}`).attr("role", "img").attr("aria-label", label);
  }
  function axis(g) { g.selectAll("text").style("font-size", "15px").style("fill", "#555"); g.selectAll("path,line").style("stroke", "#9a9a9a"); return g; }
  function title(svg, x, y, text, sub) {
    svg.append("text").attr("x", x).attr("y", y).style("font-size", "20px").style("font-weight", 600).style("fill", "#000").text(text);
    if (sub) svg.append("text").attr("x", x).attr("y", y + 22).style("font-size", "14px").style("fill", "#555").text(sub);
  }
  function legend(svg, x, y, items, gap = 26) {   // items: [{label, color, shape: "dot"|"line"|"ring"|"dash"}]
    let cx = x;
    const g = svg.append("g").attr("transform", `translate(0,${y})`);
    items.forEach((it) => {
      const gi = g.append("g").attr("transform", `translate(${cx},0)`);
      if (it.shape === "line" || it.shape === "dash") gi.append("line").attr("x1", 0).attr("x2", 18).attr("y1", -4).attr("y2", -4).attr("stroke", it.color).attr("stroke-width", 3).attr("stroke-dasharray", it.shape === "dash" ? "4 3" : null);
      else gi.append("circle").attr("cx", 7).attr("cy", -4).attr("r", 6).attr("fill", it.shape === "ring" ? "#fff" : it.color).attr("stroke", it.shape === "ring" ? it.color : "none").attr("stroke-width", 1.5);
      const t = gi.append("text").attr("x", 24).attr("y", 1).style("font-size", "16px").style("fill", "#222").text(it.label);
      cx += 24 + t.node().getComputedTextLength() + gap;
    });
    return g;
  }
  function source(svg, x, y, text, anchor = "start") {
    svg.append("text").attr("x", x).attr("y", y).attr("text-anchor", anchor).style("font-size", "14px").style("fill", "#888").text(text);
  }
  const STATE_TILES = [["ME",11,0],["VT",10,1],["NH",11,1],["WA",1,2],["ID",2,2],["MT",3,2],["ND",4,2],["MN",5,2],["IL",6,2],["WI",7,2],["MI",8,2],["NY",9,2],["RI",10,2],["MA",11,2],
    ["OR",1,3],["NV",2,3],["WY",3,3],["SD",4,3],["IA",5,3],["IN",6,3],["OH",7,3],["PA",8,3],["NJ",9,3],["CT",10,3],
    ["CA",1,4],["UT",2,4],["CO",3,4],["NE",4,4],["MO",5,4],["KY",6,4],["WV",7,4],["VA",8,4],["MD",9,4],["DE",10,4],
    ["AZ",2,5],["NM",3,5],["KS",4,5],["AR",5,5],["TN",6,5],["NC",7,5],["SC",8,5],["DC",9,5],
    ["OK",4,6],["LA",5,6],["MS",6,6],["AL",7,6],["GA",8,6],["TX",4,7],["FL",9,7]];

  // ---------------------------------------------------------------- charts
  const CHARTS = {
    // Slide 1: every challenge city, sized by households; colour = why it is in need.
    cityCluster(el) {
      const w = el.clientWidth, h = el.clientHeight;
      const svg = svgFor(el, "U.S. challenge cities sized by households, coloured by whether they are in need of cooling help");
      // challenge names run words together ("SanDiego", "DallasFortWorth") or are upper case ("EUGENE")
      const pretty = (s) => (s === s.toUpperCase() ? s[0] + s.slice(1).toLowerCase() : s.replace(/([a-z])([A-Z])/g, "$1 $2"));
      const nodes = D.cities.map((c) => ({ ...c, name: pretty(c.name) }));
      const size = d3.scaleSqrt([0, d3.max(nodes, (d) => d.households)], [4, 40]);
      nodes.forEach((d) => (d.r = size(d.households || 0)));
      const sim = d3.forceSimulation(nodes).force("x", d3.forceX(w / 2).strength(0.05)).force("y", d3.forceY(h / 2 - 20).strength(0.05))
        .force("charge", d3.forceManyBody().strength(-4)).force("collide", d3.forceCollide((d) => d.r + 2.5)).stop();
      for (let i = 0; i < 300; i++) sim.tick();
      const fill = (d) => (d.need === "no AC" ? COLOR.noac : d.need ? COLOR.over : "#fff");
      svg.append("g").selectAll("circle").data(nodes).join("circle")
        .attr("cx", (d) => d.x).attr("cy", (d) => d.y).attr("r", (d) => d.r)
        .attr("fill", fill).attr("stroke", (d) => (d.need ? "none" : "#555")).attr("stroke-width", 1).style("cursor", "pointer")
        .on("pointermove", (ev, d) => showTip(ev, `${d.name}, ${d.state} · ${d.need ? "in need (" + d.need + ")" : "not in need"}` +
          ` · ${d3.format(",")(d.households)} households · homes without AC ${d.no_ac}% · cooling-required days ${d.days_base} → ${d.days_fc} a year` +
          (d.x_bar_4 != null ? ` · low-income family bill ${d.x_bar_4}× the bar` : "")))
        .on("pointerleave", hideTip);
      legend(svg, 14, h - 14, [{ label: "In need: many homes without AC", color: COLOR.noac }, { label: "In need: cost of cooling", color: COLOR.over },
        { label: "Not in need", color: "#555", shape: "ring" }]);
      const list = document.querySelector('[data-list="cityNeed"]');
      if (list) {
        nodes.filter((d) => d.need).sort((a, b) => b.households - a.households).slice(0, 6).forEach((d) => {
          const li = document.createElement("li");
          li.style.color = d.need === "no AC" ? COLOR.noac : COLOR.over;
          li.innerHTML = "";
          const span = document.createElement("span"); span.style.color = "#000"; span.textContent = `${d.name}, ${d.state} (${d.need})`;
          li.appendChild(span); list.appendChild(li);
        });
      }
      const n = nodes.filter((d) => d.need).length, nac = nodes.filter((d) => d.need === "no AC").length;
      document.querySelectorAll('[data-fill="needShort"]').forEach((e) => (e.textContent = `${n} of ${nodes.length}`));
      document.querySelectorAll('[data-fill="needCount"]').forEach((e) => (e.textContent = `${n} of ${nodes.length} cities are in need: ${nac} because many homes have no AC, ${n - nac} because running the AC costs low-income families more than the affordable share.`));
    },

    // Slide 2: small charts in the corners of the definition.
    miniArea(el) {
      const w = el.clientWidth, h = el.clientHeight, key = el.dataset.series;
      const svg = svgFor(el, el.dataset.label || key);
      let xs, v, color;
      if (key === "afford") {
        xs = D.afford.years; v = xs.map((_, i) => d3.median(D.afford.states, (s) => s.x1[i])); color = COLOR.over;
      } else {
        xs = D.weather.years; v = D.weather.series.US[key]; color = COLOR[key];
      }
      const x = d3.scaleLinear(d3.extent(xs), [0, w]);
      const y = d3.scaleLinear([Math.min(0, d3.min(v)), d3.max(v) * 1.1], [h, 4]);
      const ok = (d) => d != null;
      svg.append("path").attr("d", d3.area().defined(ok).x((_, i) => x(xs[i])).y0(h).y1((d) => y(d))(v)).attr("fill", color).attr("fill-opacity", 0.35);
      svg.append("path").attr("d", d3.line().defined(ok).x((_, i) => x(xs[i])).y((d) => y(d))(v)).attr("fill", "none").attr("stroke", color).attr("stroke-width", 1.5);
      if (key === "afford") svg.append("line").attr("x1", 0).attr("x2", w).attr("y1", y(1)).attr("y2", y(1)).attr("stroke", "#000").attr("stroke-dasharray", "3 2");
      const k = v.length - 1;
      svg.append("circle").attr("cx", x(xs[k])).attr("cy", y(v[k])).attr("r", 3).attr("fill", "#000");
      svg.append("text").attr("x", w).attr("y", -6).attr("text-anchor", "end").style("font-size", "13px").style("font-weight", 600).style("fill", "#000")
        .text(key === "afford" ? `${v[k].toFixed(2)}× in ${xs[k]}` : `${METRIC[key].fmt(v[k])} in ${xs[k]}`);
    },

    // Slide 3a: one measure at a time (tabs), U.S. average plus each region, 1976-2025.
    weatherArea(el) {
      const w = el.clientWidth, h = el.clientHeight, m = { t: 60, r: 70, b: 70, l: 20 };
      const svg = svgFor(el, "Heat measures by year, U.S. average and regions, 1976 to 2025");
      const W = D.weather, years = W.years, x = d3.scaleLinear([1976, 2025], [m.l, w - m.r]);
      const body = svg.append("g");
      let current = "days";
      const tabs = Object.keys(METRIC);
      const tabG = svg.append("g");
      function draw() {
        body.selectAll("*").remove();
        const color = COLOR[current], all = Object.values(W.series).flatMap((s) => s[current]).filter((v) => v != null);
        const y = d3.scaleLinear([current === "hottest" ? d3.min(all) - 2 : 0, d3.max(all) * 1.05], [h - m.b, m.t]).nice();
        body.append("line").attr("x1", x(2018.5)).attr("x2", x(2018.5)).attr("y1", m.t).attr("y2", h - m.b).attr("stroke", "#121212").attr("stroke-dasharray", "2 4");
        body.append("text").attr("x", x(2018.5) + 8).attr("y", m.t + 18).style("font-size", "15px").style("font-weight", 600).style("fill", "#121212").text("our forecast →");
        body.append("text").attr("x", x(2018.5) - 8).attr("y", m.t + 18).attr("text-anchor", "end").style("font-size", "15px").style("fill", "#666").text("← observed");
        body.append("g").attr("class", "grid").selectAll("line").data(y.ticks(5)).join("line").attr("x1", m.l).attr("x2", w - m.r).attr("y1", y).attr("y2", y).attr("stroke", COLOR.grid);
        const line = d3.line().defined((d) => d != null).x((_, i) => x(years[i])).y((d) => y(d));
        const regions = Object.keys(W.series).filter((k) => k !== "US");
        body.append("g").selectAll("path").data(regions).join("path").attr("d", (k) => line(W.series[k][current]))
          .attr("fill", "none").attr("stroke", (k) => REGION_COLOR[k]).attr("stroke-width", 1.2).attr("stroke-opacity", 0.45).style("cursor", "pointer")
          .on("pointerenter", function () { d3.select(this).raise().attr("stroke-opacity", 1).attr("stroke-width", 2.5); })
          .on("pointermove", (ev, k) => { const s = W.series[k][current]; showTip(ev, `${REGION_NAME[k]}: ${METRIC[current].fmt(d3.mean(s.slice(0, 30).filter((v) => v != null)))} (1976–2005) → ${METRIC[current].fmt(d3.mean(s.slice(43)))} (forecast 2019–2025)`); })
          .on("pointerleave", function () { d3.select(this).attr("stroke-opacity", 0.45).attr("stroke-width", 1.2); hideTip(); });
        const us = W.series.US[current];
        body.append("path").attr("d", d3.area().defined((d) => d != null).x((_, i) => x(years[i])).y0(y(y.domain()[0])).y1((d) => y(d))(us)).attr("fill", color).attr("fill-opacity", 0.18);
        body.append("path").attr("d", line(us)).attr("fill", "none").attr("stroke", color).attr("stroke-width", 3);
        const base = d3.mean(us.slice(0, 30)), fc = d3.mean(us.slice(43));
        [[1976, 2005, base], [2019, 2025, fc]].forEach(([a, b, v]) => {
          body.append("line").attr("x1", x(a)).attr("x2", x(b)).attr("y1", y(v)).attr("y2", y(v)).attr("stroke", "#000").attr("stroke-width", 1.5).attr("stroke-dasharray", "5 3");
        });
        const halo = (t) => t.attr("paint-order", "stroke").attr("stroke", "#fff").attr("stroke-width", 4).attr("stroke-linejoin", "round");
        halo(body.append("text").attr("x", x(1976) + 4).attr("y", y(base) - 8).style("font-size", "15px").style("font-weight", 600).style("fill", "#000").text(`1976–2005 average: ${METRIC[current].fmt(base)}`));
        halo(body.append("text").attr("x", x(2025) - 2).attr("text-anchor", "end").attr("y", y(fc) - 10).style("font-size", "15px").style("font-weight", 600).style("fill", color).text(`2019–2025: ${METRIC[current].fmt(fc)}`));
        axis(body.append("g").attr("transform", `translate(0,${h - m.b})`).call(d3.axisBottom(x).tickFormat(d3.format("d")).ticks(10)));
        axis(body.append("g").attr("transform", `translate(${w - m.r},0)`).call(d3.axisRight(y).ticks(5)));
        body.append("text").attr("x", m.l).attr("y", 24).style("font-size", "22px").style("font-weight", 600).style("fill", "#121212").text(METRIC[current].label);
        body.append("text").attr("x", m.l).attr("y", 48).style("font-size", "16px").style("fill", "#555").text(`${METRIC[current].unit}; mean of challenge cities`);
        legend(body, w - m.r - 540, 30, [{ label: "U.S. average", color, shape: "line" }, { label: "Regions (roll over)", color: "#9a9a9a", shape: "line" }, { label: "Period average", color: "#000", shape: "dash" }]);
        tabG.selectAll("text").style("fill", (k) => (k === current ? COLOR[k] : "#999")).style("text-decoration", (k) => (k === current ? "underline" : "none"));
      }
      tabG.selectAll("text").data(tabs).join("text").attr("x", (_, i) => m.l + i * (w - m.l - m.r) / 4).attr("y", h - 12)
        .style("font-size", "15px").style("font-weight", 700).style("letter-spacing", ".08em").style("cursor", "pointer")
        .text((k) => METRIC[k].label.toUpperCase()).attr("tabindex", 0).attr("role", "button")
        .on("click", (ev, k) => { current = k; draw(); })
        .on("keydown", (ev, k) => { if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); ev.stopPropagation(); current = k; draw(); } });
      draw();
    },

    // Slide 3b: summer peak demand by daily high, one line per region (EIA-930, 2015-2018).
    regionLines(el) {
      const w = el.clientWidth, h = el.clientHeight, m = { t: 110, r: 150, b: 56, l: 70 };
      const svg = svgFor(el, "Summer daily peak demand against the daily high, by region, 2015 to 2018");
      source(svg, m.l, h - 4, "Daily peak as % of the region's average summer peak (100 = average), by 2 °F bins of the day's high. EIA-930, June–September 2015–2018.");
      const R = D.regions;
      const x = d3.scaleLinear(d3.extent(R.flatMap((r) => r.pts), (p) => p[0]), [m.l, w - m.r]).nice();
      const y = d3.scaleLinear(d3.extent(R.flatMap((r) => r.pts), (p) => p[1]), [h - m.b, m.t]).nice();
      svg.append("g").selectAll("line").data(y.ticks(6)).join("line").attr("x1", m.l).attr("x2", w - m.r).attr("y1", y).attr("y2", y).attr("stroke", COLOR.grid);
      svg.append("line").attr("x1", m.l).attr("x2", w - m.r).attr("y1", y(100)).attr("y2", y(100)).attr("stroke", "#000").attr("stroke-dasharray", "4 3");
      axis(svg.append("g").attr("transform", `translate(0,${h - m.b})`).call(d3.axisBottom(x).ticks(10).tickFormat((d) => d + " °F")));
      axis(svg.append("g").attr("transform", `translate(${m.l},0)`).call(d3.axisLeft(y).ticks(6)));
      const line = d3.line().x((p) => x(p[0])).y((p) => y(p[1]));
      const lines = svg.append("g").selectAll("path").data(R).join("path").attr("d", (r) => line(r.pts)).attr("fill", "none")
        .attr("stroke", (r) => REGION_COLOR[r.region]).attr("stroke-width", 2).attr("stroke-opacity", 0.75).style("cursor", "pointer");
      const label = svg.append("text").style("font-weight", 700).style("font-size", "17px");
      function focus(reg) {
        lines.attr("stroke-opacity", (r) => (!reg || r.region === reg ? 1 : 0.12)).attr("stroke-width", (r) => (r.region === reg ? 4 : 2));
        if (reg) { const r = R.find((q) => q.region === reg), p = r.pts[r.pts.length - 1]; label.attr("x", x(p[0]) + 6).attr("y", y(p[1]) + 4).style("fill", REGION_COLOR[reg]).text(REGION_NAME[reg]); }
        else label.text("");
      }
      lines.on("pointerenter", (ev, r) => focus(r.region))
        .on("pointermove", (ev, r) => showTip(ev, `${REGION_NAME[r.region]}: +${r.pct_per_F}% of peak per °F (fit R² ${r.r2})`))
        .on("pointerleave", () => { focus(null); hideTip(); });
      // legend: regions sorted by sensitivity
      const sorted = [...R].sort((a, b) => b.pct_per_F - a.pct_per_F);
      const lg = svg.append("g").attr("transform", `translate(${m.l},${m.t - 78})`);
      sorted.forEach((r, i) => {
        const g = lg.append("g").attr("transform", `translate(${(i % 5) * 186},${Math.floor(i / 5) * 24})`).style("cursor", "pointer")
          .on("pointerenter", () => focus(r.region)).on("pointerleave", () => focus(null));
        g.append("rect").attr("x", 0).attr("y", -11).attr("width", 13).attr("height", 13).attr("rx", 3).attr("fill", REGION_COLOR[r.region]);
        g.append("text").attr("x", 19).attr("y", 0).style("font-size", "15px").style("fill", "#222").text(`${r.region} +${r.pct_per_F.toFixed(1)}% per °F`);
      });
    },

    // Slide 3c: low-income bill / affordable bar by state, 2002-2018, toggle household size.
    affordLines(el) {
      const w = el.clientWidth, h = el.clientHeight, m = { t: 96, r: 70, b: 56, l: 70 };
      const svg = svgFor(el, "Low-income electricity bill as a multiple of the affordable bar, by state, 2002 to 2018");
      source(svg, m.l, h - 4, "Low-income bill ÷ affordable bar. Real price each year × 2015 low-income use (RECS); bar = 6% of the 2018 poverty line × the state's electricity share. 2018 dollars.");
      const A = D.afford, years = A.years;
      const x = d3.scaleLinear([2002, 2018], [m.l, w - m.r]);
      const body = svg.append("g");
      let size = "x1";
      const btns = svg.append("g").attr("transform", `translate(${m.l},4)`);
      [["x1", "1 person, income < $20k"], ["x4", "4 people, income < $40k"]].forEach(([k, txt], i) => {
        const g = btns.append("g").attr("transform", `translate(${i * 250},0)`).style("cursor", "pointer").attr("tabindex", 0).attr("role", "button")
          .on("click", () => { size = k; draw(); }).on("keydown", (ev) => { if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); ev.stopPropagation(); size = k; draw(); } });
        g.append("rect").attr("class", "btn").attr("data-k", k).attr("width", 236).attr("height", 34).attr("rx", 17).attr("fill", "#fff").attr("stroke", "#c8c8c8");
        g.append("text").attr("class", "btnt").attr("data-k", k).attr("x", 118).attr("y", 22).attr("text-anchor", "middle").style("font-size", "15px").style("font-weight", 600).text(txt);
      });
      function draw() {
        body.selectAll("*").remove();
        btns.selectAll(".btn").attr("fill", function () { return this.dataset.k === size ? "#121212" : "#fff"; }).attr("stroke", function () { return this.dataset.k === size ? "#121212" : "#c8c8c8"; });
        btns.selectAll(".btnt").style("fill", function () { return this.dataset.k === size ? "#fff" : "#000"; });
        const S = A.states, vals = S.flatMap((s) => s[size]).filter((v) => v != null);
        const y = d3.scaleLinear([Math.min(0.4, d3.min(vals)), d3.max(vals) * 1.05], [h - m.b, m.t]).nice();
        body.append("g").selectAll("line").data(y.ticks(6)).join("line").attr("x1", m.l).attr("x2", w - m.r).attr("y1", y).attr("y2", y).attr("stroke", COLOR.grid);
        axis(body.append("g").attr("transform", `translate(0,${h - m.b})`).call(d3.axisBottom(x).tickFormat(d3.format("d")).ticks(8)));
        axis(body.append("g").attr("transform", `translate(${m.l},0)`).call(d3.axisLeft(y).ticks(6).tickFormat((d) => d + "×")));
        const last = (s) => s[size][s[size].length - 1];
        const col = (s) => (last(s) > 1 ? COLOR.over : COLOR.under);
        const line = d3.line().defined((d) => d != null).x((_, i) => x(years[i])).y((d) => y(d));
        body.append("g").selectAll("path").data(S).join("path").attr("d", (s) => line(s[size])).attr("fill", "none")
          .attr("stroke", col).attr("stroke-opacity", 0.35).attr("stroke-width", 1.4).style("cursor", "pointer")
          .on("pointerenter", function () { d3.select(this).raise().attr("stroke-opacity", 1).attr("stroke-width", 3); })
          .on("pointermove", (ev, s) => showTip(ev, `${s.state}: ${s[size][0]}× the bar in 2002, ${last(s)}× in 2018`))
          .on("pointerleave", function () { d3.select(this).attr("stroke-opacity", 0.35).attr("stroke-width", 1.4); hideTip(); });
        body.append("line").attr("x1", m.l).attr("x2", w - m.r).attr("y1", y(1)).attr("y2", y(1)).attr("stroke", "#000").attr("stroke-width", 2.5);
        body.append("text").attr("x", w - m.r + 8).attr("y", y(1) + 5).style("font-size", "15px").style("font-weight", 600).style("fill", "#000").text("bar");
        body.append("g").selectAll("circle").data(S).join("circle").attr("cx", x(2018)).attr("cy", (s) => y(last(s))).attr("r", 4).attr("fill", col);
        const over = S.filter((s) => last(s) > 1).length;
        legend(body, m.l + 530, 26, [{ label: `Over the bar in 2018 (${over})`, color: COLOR.over }, { label: `Under (${S.length - over})`, color: COLOR.under }, { label: "Affordable bar", color: "#000", shape: "line" }]);
      }
      draw();
    },

    // Slide 3d (combined view, 2002-2018) and slide 4a (projected numbers, extended to 2025 with data-range="projected"):
    // weather, use and price on one time axis, U.S.
    threePanels(el) {
      const projected = el.dataset.range === "projected";
      const w = el.clientWidth, h = el.clientHeight, m = { t: 20, r: 70, b: 40, l: 230 };
      const svg = svgFor(el, `Cooling degree days, residential use per customer and real price, U.S., 2002 to ${projected ? 2025 : 2018}`);
      const N = D.national, P = N.projected, last = projected ? 2025 : 2018;
      const x = d3.scaleLinear([2002, last], [m.l, w - m.r]);
      const panels = [
        { key: "cdd", name: "Weather", sub: "cooling degree days (mean of cities)", color: COLOR.cdd, fmt: d3.format(",.0f"), how: "our forecast" },
        { key: "kwh", name: "Energy use", sub: "kWh per residential customer", color: COLOR.demand, fmt: d3.format(",.0f"), how: "trend + forecast heat" },
        { key: "price", name: "Affordability", sub: "real price, 2018 cents/kWh", color: COLOR.price, fmt: d3.format(".2f"), how: "held at 2018" },
      ];
      const ph = (h - m.t - m.b) / 3;
      const hist = (k) => N.years.map((yr, i) => ({ y: yr, v: N[k][i] }));
      const proj = (k) => [{ y: 2018, v: N[k][N[k].length - 1], lo: N[k][N[k].length - 1], hi: N[k][N[k].length - 1] }]
        .concat(P.years.map((yr, i) => ({ y: yr, v: P[k][i], lo: P[k + "_lo"] ? P[k + "_lo"][i] : P[k][i], hi: P[k + "_hi"] ? P[k + "_hi"][i] : P[k][i] })));
      if (projected) {
        svg.append("line").attr("x1", x(2018.5)).attr("x2", x(2018.5)).attr("y1", m.t).attr("y2", h - m.b).attr("stroke", "#121212").attr("stroke-dasharray", "2 4");
        svg.append("text").attr("x", x(2018.5) + 8).attr("y", m.t + 6).style("font-size", "15px").style("font-weight", 600).style("fill", "#121212").text("projected →");
        svg.append("text").attr("x", x(2018.5) - 8).attr("y", m.t + 6).attr("text-anchor", "end").style("font-size", "15px").style("fill", "#666").text("← observed");
      }
      panels.forEach((p, k) => {
        const top = m.t + k * ph, H = hist(p.key), F = projected ? proj(p.key) : [];
        const all = H.map((d) => d.v).concat(F.flatMap((d) => [d.lo, d.hi]));
        const ext = d3.extent(all), pad = (ext[1] - ext[0]) * 0.25;
        const y = d3.scaleLinear([ext[0] - pad, ext[1] + pad], [top + ph - 26, top + 22]);
        svg.append("text").attr("x", 0).attr("y", top + ph / 2 - 8).style("font-size", "24px").style("fill", p.color).style("font-weight", 600).text(p.name);
        svg.append("text").attr("x", 0).attr("y", top + ph / 2 + 18).style("font-size", "16px").style("fill", "#555").text(p.sub);
        axis(svg.append("g").attr("transform", `translate(${w - m.r},0)`).call(d3.axisRight(y).ticks(3).tickFormat(p.fmt)));
        svg.append("path").attr("d", d3.area().x((d) => x(d.y)).y0(y(y.domain()[0])).y1((d) => y(d.v))(H)).attr("fill", p.color).attr("fill-opacity", 0.15);
        svg.append("path").attr("d", d3.line().x((d) => x(d.y)).y((d) => y(d.v))(H)).attr("fill", "none").attr("stroke", p.color).attr("stroke-width", 2.5);
        if (projected) {
          if (p.key !== "cdd") svg.append("path").attr("d", d3.area().x((d) => x(d.y)).y0((d) => y(d.lo)).y1((d) => y(d.hi))(F)).attr("fill", p.color).attr("fill-opacity", 0.12);
          svg.append("path").attr("d", d3.line().x((d) => x(d.y)).y((d) => y(d.v))(F)).attr("fill", "none").attr("stroke", p.color).attr("stroke-width", 2.5).attr("stroke-dasharray", "7 5");
          const e = F[F.length - 1];
          svg.append("text").attr("x", x(2025) - 14).attr("y", y(e.hi) - 10).attr("text-anchor", "end").style("font-size", "14px").style("fill", p.color).style("font-weight", 600)
            .attr("paint-order", "stroke").attr("stroke", "#fff").attr("stroke-width", 4).text(`${p.how}: ${p.fmt(e.v)}`);
        }
        const pts = H.concat(F.slice(1).map((d) => ({ ...d, f: true })));
        svg.append("g").selectAll("circle").data(pts).join("circle").attr("cx", (d) => x(d.y)).attr("cy", (d) => y(d.v)).attr("r", 3.5)
          .attr("fill", (d) => (d.f ? "#fff" : p.color)).attr("stroke", p.color).attr("stroke-width", 1.5)
          .on("pointermove", (ev, d) => showTip(ev, `${p.name}, ${d.y}: ${p.fmt(d.v)} (${p.sub})` + (d.f ? ` · projected, ${p.how}` + (d.lo !== d.hi ? `; range ${p.fmt(d.lo)}–${p.fmt(d.hi)}` : "") : "")))
          .on("pointerleave", hideTip);
      });
      if (!projected) ["2006", "2011", "2012"].forEach((yr) => svg.append("line").attr("x1", x(+yr)).attr("x2", x(+yr)).attr("y1", m.t).attr("y2", h - m.b).attr("stroke", "#000").attr("stroke-opacity", 0.12));
      axis(svg.append("g").attr("transform", `translate(0,${h - m.b})`).call(d3.axisBottom(x).tickFormat(d3.format("d")).ticks(projected ? 12 : 9)));
      source(svg, m.l, h - 4, projected
        ? "Data up to 2018 only. Weather: our cdd forecast. Use: 2002–2018 fit on trend and cdd, band ≈ 80% range. Price: held at 2018, band = typical yearly swings."
        : "Weather: challenge data (valid years). Use and price: EIA-861, all states, BLS CPI-U. Faint lines: 2006, 2011 and 2012.");
    },

    // Slide 4: two state grid maps.
    tileMap(el) {
      const w = el.clientWidth, h = el.clientHeight, key = el.dataset.field;
      const svg = svgFor(el, key === "days_fc" ? "Forecast cooling-required days by state" : "Low-income family bill over the bar by state");
      const byS = Object.fromEntries(D.states.map((s) => [s.state, s]));
      const color = key === "days_fc"
        ? d3.scaleSequential([0, d3.max(D.states, (s) => s.days_fc)], d3.interpolateRgb("#fff3e6", COLOR.days))
        : d3.scaleDiverging([0.6, 1, 1.9], (t) => (t < 0.5 ? d3.interpolateRgb(COLOR.price, "#ffffff")(t * 2) : d3.interpolateRgb("#ffffff", COLOR.over)((t - 0.5) * 2)));
      const c = Math.min(w / 12, (h - 30) / 8), g = svg.append("g").attr("transform", `translate(${(w - c * 12) / 2},0)`);
      const cells = g.selectAll("g").data(STATE_TILES).join("g").attr("transform", ([, col, row]) => `translate(${col * c},${row * c})`)
        .on("pointermove", (ev, [s]) => { const d = byS[s]; showTip(ev, d ? (key === "days_fc" ? `${s}: ${d.days_fc} cooling-required days a year (forecast); ${d.nights_fc} hot nights` : `${s}: low-income family of four ${d.x4}× the bar; single person ${d.x1}×`) : `${s}: no challenge city`); })
        .on("pointerleave", hideTip);
      cells.append("rect").attr("width", c - 3).attr("height", c - 3).attr("rx", 4).attr("fill", ([s]) => (byS[s] ? color(byS[s][key]) : "#fff")).attr("stroke", ([s]) => (byS[s] ? "none" : "#ddd"));
      cells.append("text").attr("x", (c - 3) / 2).attr("y", (c - 3) / 2 + 5).attr("text-anchor", "middle").style("font-size", "13px").style("font-weight", 600)
        .style("fill", ([s]) => { const d = byS[s]; if (!d) return "#999"; const k = d3.color(color(d[key])); return (0.299 * k.r + 0.587 * k.g + 0.114 * k.b) < 140 ? "#fff" : "#000"; }).text(([s]) => s);
      const lg = svg.append("g").attr("transform", `translate(${(w - c * 12) / 2},${h - 14})`);
      const stops = key === "days_fc" ? [0, 0.5, 1].map((t) => t * d3.max(D.states, (s) => s.days_fc)) : [0.6, 1, 1.9];
      const lw = 160, id = `grad-${key}`;
      const grad = svg.append("defs").append("linearGradient").attr("id", id);
      d3.range(0, 1.01, 0.1).forEach((t) => grad.append("stop").attr("offset", t).attr("stop-color", color(stops[0] + t * (stops[2] - stops[0]))));
      lg.append("rect").attr("width", lw).attr("height", 10).attr("y", -10).attr("rx", 5).attr("fill", `url(#${id})`);
      lg.append("text").attr("x", 0).attr("y", 12).style("font-size", "12px").text(key === "days_fc" ? "0 days" : "0.6×");
      lg.append("text").attr("x", lw).attr("y", 12).attr("text-anchor", "end").style("font-size", "12px").text(key === "days_fc" ? `${Math.round(stops[2])} days` : "1.9×");
      if (key !== "days_fc") lg.append("text").attr("x", lw * (0.4 / 1.3)).attr("y", 12).attr("text-anchor", "middle").style("font-size", "12px").text("bar");
    },

    // Slide 4: heat exposure vs affordability, by state.
    scatter(el) {
      const w = el.clientWidth, h = el.clientHeight, m = { t: 20, r: 20, b: 60, l: 70 };
      const svg = svgFor(el, "Forecast cooling-required days against the low-income family bill over the bar, by state");
      const P = D.states.filter((s) => s.days_fc != null && s.x4 != null);
      const x = d3.scaleLinear([0, d3.max(P, (d) => d.days_fc) * 1.05], [m.l, w - m.r]).nice();
      const y = d3.scaleLinear([Math.min(0.6, d3.min(P, (d) => d.x4)), d3.max(P, (d) => d.x4) * 1.05], [h - m.b, m.t]).nice();
      svg.append("g").selectAll("line").data(y.ticks(5)).join("line").attr("x1", m.l).attr("x2", w - m.r).attr("y1", y).attr("y2", y).attr("stroke", "#dcdcdc");
      svg.append("line").attr("x1", m.l).attr("x2", w - m.r).attr("y1", y(1)).attr("y2", y(1)).attr("stroke", "#000").attr("stroke-width", 2);
      svg.append("text").attr("x", w - m.r).attr("y", y(1) - 6).attr("text-anchor", "end").style("font-size", "13px").style("font-weight", 600).style("fill", "#000").text("affordable bar");
      axis(svg.append("g").attr("transform", `translate(0,${h - m.b})`).call(d3.axisBottom(x).ticks(7)));
      axis(svg.append("g").attr("transform", `translate(${m.l},0)`).call(d3.axisLeft(y).ticks(5).tickFormat((d) => d + "×")));
      svg.append("text").attr("x", (m.l + w - m.r) / 2).attr("y", h - 12).attr("text-anchor", "middle").style("font-size", "17px").style("font-weight", 600).style("fill", COLOR.days).text("Cooling-required days a year (forecast 2019–2025)");
      svg.append("text").attr("transform", `translate(18,${(m.t + h - m.b) / 2}) rotate(-90)`).attr("text-anchor", "middle").style("font-size", "18px").style("font-weight", 600).style("fill", "#333").text("Low-income family bill ÷ bar");
      const mx = d3.mean(P, (d) => d.days_fc), my = d3.mean(P, (d) => d.x4);
      const sxy = d3.sum(P, (d) => (d.days_fc - mx) * (d.x4 - my)), sxx = d3.sum(P, (d) => (d.days_fc - mx) ** 2), syy = d3.sum(P, (d) => (d.x4 - my) ** 2);
      const b = sxy / sxx, rr = sxy / Math.sqrt(sxx * syy);
      svg.append("line").attr("x1", x(0)).attr("x2", x(x.domain()[1])).attr("y1", y(my - b * mx)).attr("y2", y(my + b * (x.domain()[1] - mx))).attr("stroke", "#999").attr("stroke-width", 2).attr("stroke-dasharray", "6 4");
      svg.append("g").selectAll("circle").data(P).join("circle").attr("cx", (d) => x(d.days_fc)).attr("cy", (d) => y(d.x4)).attr("r", 7)
        .attr("fill", (d) => (d.x4 > 1 ? COLOR.over : COLOR.under)).attr("fill-opacity", 0.85).attr("stroke", "#fff")
        .on("pointermove", (ev, d) => showTip(ev, `${d.state}: ${d.days_fc} cooling-required days a year; family of four ${d.x4}× the bar; homes without AC ${d.no_ac}%`)).on("pointerleave", hideTip);
      svg.append("g").selectAll("text").data(P.filter((d) => d.days_fc > 45 || d.state === "CA" || d.x4 < 0.75)).join("text")
        .attr("x", (d) => x(d.days_fc) + 10).attr("y", (d) => y(d.x4) + 5).style("font-size", "14px").style("fill", "#333").text((d) => d.state);
      svg.append("text").attr("x", w - m.r - 10).attr("y", h - m.b - 16).attr("text-anchor", "end").style("font-size", "26px").style("font-weight", 700).style("fill", "#aaa").text(`r = ${rr.toFixed(2)}`);
      legend(svg, m.l + 10, m.t + 6, [{ label: "Over the bar", color: COLOR.over }, { label: "Under", color: COLOR.under }]);
      document.querySelectorAll('[data-fill="scatterR"]').forEach((e) => (e.textContent = `r = ${rr.toFixed(2)}`));
    },
  };

  if (!D) {
    document.querySelectorAll("[data-chart]").forEach((el) => (el.textContent = "Data file missing: run python code/export_deck_data.py"));
    return;
  }
  document.querySelectorAll("[data-chart]").forEach((el) => { const f = CHARTS[el.dataset.chart]; if (f) f(el); });
})();
