// Las Vegas gaming dashboard. Reads the JSON the SQL model exports (data/*.json next to this
// file) and draws four linked views with Vega-Lite, styled by the site's chart theme
// (window.siteChart from assets/charts.js). Filters: area, time range, dollars.
(() => {
  const root = document.getElementById("dashboard");
  if (!root) return;

  const BLUE = "#2340ff", ORANGE = "#eb6834", MUTED = "#6b6a66", INK = "#111111";
  const SLOTS = ["Multi-denomination slots", "Penny slots", "High-limit slots ($5+)", "Other slots"];
  const TABLES = ["Baccarat", "Blackjack", "Craps"];
  const AREA_NAME = { strip: "Las Vegas Strip", downtown: "Downtown Las Vegas", statewide: "Nevada statewide" };
  const state = { area: "strip", range: "84", dollars: "real" };
  let D = null;

  // ---------- data ----------
  const rowsOf = (j) => j.rows.map((r) => Object.fromEntries(j.columns.map((c, i) => [c, r[i]])));
  const load = (name) => fetch(`data/${name}.json`).then((r) => { if (!r.ok) throw new Error(name); return r.json(); });

  Promise.all(["area_monthly", "strip_tourism", "seasonality", "baccarat", "dash_game_mix"].map(load))
    .then(([area, tour, season, bac, mix]) => {
      D = { area: rowsOf(area), tour: rowsOf(tour), season: rowsOf(season), bac: rowsOf(bac), mix };
      bind();
      render();
    })
    .catch((e) => { root.querySelector("[data-asof]").textContent = "The dashboard data didn't load."; console.error(e); });

  // ---------- controls ----------
  function bind() {
    root.querySelectorAll(".seg").forEach((seg) => {
      seg.addEventListener("click", (e) => {
        const b = e.target.closest("button");
        if (!b) return;
        seg.querySelectorAll("button").forEach((x) => x.setAttribute("aria-checked", String(x === b)));
        state[seg.dataset.control] = b.dataset.value;
        render();
      });
    });
    let t;
    addEventListener("resize", () => { clearTimeout(t); t = setTimeout(render, 200); });
  }

  // ---------- helpers ----------
  const fmtM = (v) => `$${Math.round(v / 1e6).toLocaleString("en-US")}M`;
  const fmtB = (v) => `$${(v / 1e9).toFixed(2)}B`;
  const pct = (v, d = 1) => `${(v * 100).toFixed(d)}%`;
  const change = (v) => v == null || !isFinite(v) ? "" :
    `<span class="${v >= 0 ? "up" : "down"}">${Math.abs(v * 100).toFixed(1)}%</span>`;
  const monthName = (m) => new Date(`${m}-01T00:00:00`).toLocaleString("en-US", { month: "short", year: "numeric" });
  const val = (r) => (state.dollars === "real" ? r.real_win : r.total_win);

  // One tick per January (thinned to fit), so long ranges don't repeat a year.
  function years(data) {
    const jan = data.filter((d) => d.month.slice(5, 7) === "01").map((d) => d.month);
    const step = Math.ceil(jan.length / 9);
    return jan.filter((_, i) => i % step === 0).map((m) => new Date(`${m}T00:00:00`).getTime());
  }

  function areaRows() {
    return D.area.filter((r) => r.area_key === state.area);
  }
  function inRange(rows) {
    if (state.range === "all") return rows;
    const n = +state.range;
    return rows.slice(Math.max(0, rows.length - n));
  }

  // ---------- KPIs ----------
  function kpis() {
    const rows = areaRows().filter((r) => r.total_win != null);
    const last = rows[rows.length - 1];
    const prevYear = rows.find((r) => r.month === `${+last.month.slice(0, 4) - 1}${last.month.slice(4)}`);
    const last12 = rows.slice(-12), prior12 = rows.slice(-24, -12);
    const sum = (a, f) => a.reduce((s, r) => s + (f(r) || 0), 0);
    const withSlots = last12.filter((r) => r.slots_win != null);
    const share = sum(withSlots, (r) => r.slots_win) / sum(withSlots, (r) => r.total_win);
    const r19 = rows.filter((r) => r.month.startsWith("2019") && r.slots_win != null);
    const share19 = sum(r19, (r) => r.slots_win) / sum(r19, (r) => r.total_win);

    const t = D.tour.filter((r) => r.visitors != null);
    const tLast12 = t.slice(-12), tPrior12 = t.slice(-24, -12);
    const vis = sum(tLast12, (r) => r.visitors), visPrior = sum(tPrior12, (r) => r.visitors);

    const dollars = state.dollars === "real" ? "2025 dollars" : "then-year dollars";
    const tiles = [
      { label: `${monthName(last.month)} win`, value: fmtM(val(last)),
        sub: prevYear ? `${change(val(last) / val(prevYear) - 1)} vs ${monthName(prevYear.month)}` : "" },
      { label: "Last 12 months", value: fmtB(sum(last12, val)),
        sub: `${change(sum(last12, val) / sum(prior12, val) - 1)} vs prior 12 · ${dollars}` },
      { label: "Slot share, last 12 months", value: pct(share, 0),
        sub: isFinite(share19) ? `2019: ${pct(share19, 0)}` : "" },
      { label: "Las Vegas visitors, 12 months", value: `${(vis / 1e6).toFixed(1)}M`,
        sub: `${change(vis / visPrior - 1)} vs prior 12 · citywide` },
    ];
    root.querySelector("[data-kpis]").innerHTML = tiles.map((k) =>
      `<div class="kpi"><p class="kpi-label">${k.label}</p><p class="kpi-value">${k.value}</p><p class="kpi-sub">${k.sub}</p></div>`
    ).join("");
    root.querySelector("[data-asof]").textContent =
      `${AREA_NAME[state.area]} · data through ${monthName(last.month)} · updated monthly`;
  }

  // ---------- charts ----------
  function draw(slot, spec) {
    const el = root.querySelector(`[data-chart-slot="${slot}"]`);
    const width = el.clientWidth;
    spec.width = "container";
    spec.autosize = { type: "fit-x", contains: "padding" };
    const config = window.siteChart ? window.siteChart.config(width) : {};
    return vegaEmbed(el, spec, { config, actions: false, renderer: "svg", tooltip: { theme: "light" } })
      .catch((e) => { el.innerHTML = '<div class="dash-empty">Chart failed to load</div>'; console.error(e); });
  }

  function trend() {
    const rows = inRange(areaRows());
    const real = state.dollars === "real";
    const data = rows.map((r) => ({
      month: `${r.month}-01`,
      win_m: val(r) == null ? null : val(r) / 1e6,
      avg_m: (real ? r.real_win_12m : r.win_12m) == null ? null : (real ? r.real_win_12m : r.win_12m) / 12e6,
      yoy: r.yoy, source: r.source === "lvcva" ? "LVCVA (no NGCB report)" : "NGCB",
    }));
    const first = data[0].month, last = data[data.length - 1].month;
    const covid = [{ s: "2020-03-01", e: "2021-06-01" }].filter((c) => c.e >= first && c.s <= last);
    root.querySelector('[data-title="trend"]').textContent =
      `Win per month, ${real ? "in 2025 dollars" : "in each month's dollars"}`;
    root.querySelector('[data-note="trend"]').textContent =
      "Bars are monthly win; the line is the average of the last 12 months." + (covid.length ? " Shading marks the COVID closure and reopening." : "");
    const layers = [];
    if (covid.length) layers.push({ data: { values: covid }, mark: { type: "rect", color: MUTED, opacity: 0.12 },
      encoding: { x: { field: "s", type: "temporal" }, x2: { field: "e" } } });
    layers.push({
      data: { values: data }, mark: { type: "bar", color: BLUE, opacity: 0.45, width: { band: 0.8 } },
      encoding: {
        x: { field: "month", type: "temporal", timeUnit: "yearmonth", title: null, axis: rows.length > 30 ? { format: "%Y", labelAngle: 0, values: years(data) } : { format: "%b %Y", labelAngle: 0, tickCount: 6 } },
        y: { field: "win_m", type: "quantitative", title: "$M per month" },
        tooltip: [
          { field: "month", type: "temporal", timeUnit: "yearmonth", title: "Month", format: "%b %Y" },
          { field: "win_m", type: "quantitative", title: "Win ($M)", format: ",.0f" },
          { field: "avg_m", type: "quantitative", title: "12-month avg ($M)", format: ",.0f" },
          { field: "yoy", type: "quantitative", title: "vs a year earlier", format: "+.1%" },
          { field: "source", title: "Source" },
        ],
      },
    });
    layers.push({ data: { values: data.filter((d) => d.avg_m != null) }, mark: { type: "line", color: INK, strokeWidth: 2.2 },
      encoding: { x: { field: "month", type: "temporal", timeUnit: "yearmonth" }, y: { field: "avg_m", type: "quantitative" } } });
    return draw("trend", { height: 260, layer: layers });
  }

  function mix() {
    const m = D.mix, rows = inRange(areaRows()), months = new Set(rows.map((r) => r.month));
    const groups = m.areas[state.area] || {};
    const totals = {};
    for (const [g, arr] of Object.entries(groups)) {
      const name = SLOTS.includes(g) || TABLES.includes(g) ? g : "Other table games";
      m.months.forEach((mo, i) => { if (months.has(mo) && arr[i] != null) totals[name] = (totals[name] || 0) + arr[i]; });
    }
    const all = Object.values(totals).reduce((a, b) => a + b, 0);
    const data = Object.entries(totals).map(([g, v]) => ({ group: g, share: v / all, kind: SLOTS.includes(g) ? "Slots" : "Tables" }))
      .sort((a, b) => b.share - a.share);
    const order = data.map((d) => d.group);
    return draw("mix", {
      height: Math.max(180, data.length * 30), data: { values: data },
      layer: [
        { mark: { type: "bar", height: { band: 0.7 } },
          encoding: {
            y: { field: "group", type: "nominal", sort: order, title: null, axis: { labelLimit: 160 } },
            x: { field: "share", type: "quantitative", title: null, axis: { format: "%", tickCount: 4 } },
            color: { field: "kind", type: "nominal", title: null, scale: { domain: ["Slots", "Tables"], range: [BLUE, ORANGE] },
                     legend: { orient: "bottom", direction: "horizontal" } },
            tooltip: [{ field: "group", title: "Group" }, { field: "share", type: "quantitative", format: ".1%", title: "Share" }],
          } },
        { mark: { type: "text", align: "left", dx: 4, color: INK, fontSize: 11 },
          encoding: { y: { field: "group", type: "nominal", sort: order }, x: { field: "share", type: "quantitative" },
                      text: { field: "share", type: "quantitative", format: ".0%" } } },
      ],
    });
  }

  function season() {
    const data = D.season.filter((r) => r.area_key === state.area);
    const order = data.map((d) => d.month_name);
    return draw("season", {
      height: 200, data: { values: data },
      layer: [
        { mark: { type: "rule", strokeDash: [4, 4], color: MUTED }, encoding: { y: { datum: 1 } } },
        { mark: { type: "rule", color: MUTED, strokeWidth: 2 },
          encoding: { x: { field: "month_name", type: "nominal", sort: order, title: null, axis: { labelAngle: 0, labelExpr: "slice(datum.label, 0, 1)" } },
                      y: { field: "index_min", type: "quantitative", title: null, scale: { zero: false } }, y2: { field: "index_max" } } },
        { mark: { type: "point", filled: true, size: 70, color: BLUE },
          encoding: { x: { field: "month_name", type: "nominal", sort: order }, y: { field: "index", type: "quantitative" },
                      tooltip: [{ field: "month_name", title: "Month" }, { field: "index", type: "quantitative", format: ".2f", title: "Average" },
                                { field: "index_min", type: "quantitative", format: ".2f", title: "Lowest" },
                                { field: "index_max", type: "quantitative", format: ".2f", title: "Highest" }] } },
      ],
    });
  }

  function baccarat() {
    const months = new Set(inRange(D.area.filter((r) => r.area_key === "strip")).map((r) => r.month));
    const data = D.bac.filter((r) => months.has(r.month)).map((r) => ({
      month: `${r.month}-01`, hold: r.hold, avg: r.hold_trailing_24m, win_m: r.baccarat_win / 1e6 }));
    return draw("baccarat", {
      height: 200, data: { values: data },
      layer: [
        { mark: { type: "line", color: INK, strokeWidth: 2 },
          encoding: { x: { field: "month", type: "temporal", timeUnit: "yearmonth", title: null,
                           axis: data.length > 30 ? { format: "%Y", labelAngle: 0, values: years(data) } : { format: "%b %Y", labelAngle: 0, tickCount: 6 } },
                      y: { field: "avg", type: "quantitative", title: "Hold", axis: { format: "%" } } } },
        { mark: { type: "circle", size: data.length > 60 ? 28 : 60, color: ORANGE, opacity: 0.9 },
          encoding: { x: { field: "month", type: "temporal", timeUnit: "yearmonth" }, y: { field: "hold", type: "quantitative" },
                      tooltip: [{ field: "month", type: "temporal", timeUnit: "yearmonth", format: "%b %Y", title: "Month" },
                                { field: "hold", type: "quantitative", format: ".1%", title: "Hold" },
                                { field: "avg", type: "quantitative", format: ".1%", title: "2-year average" },
                                { field: "win_m", type: "quantitative", format: ",.0f", title: "Baccarat win ($M)" }] } },
      ],
    });
  }

  function render() {
    if (!D || !window.vegaEmbed) return;
    kpis(); trend(); mix(); season(); baccarat();
  }
  addEventListener("load", render);
})();
