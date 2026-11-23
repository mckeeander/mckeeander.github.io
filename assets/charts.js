// Paper theme for every Altair / Vega-Lite chart on the site (Basel: ink and one spot green).
// Categorical order: the site's green, then ink, then hues checked for colour-blind separation
// against the green on the chart surface. Orange is left out on purpose: next to this green it
// fails the red-green check. Slots 4-5 sit below 3:1 on paper, so give those series labels.
(() => {
  const GREEN = "#00934f", INK = "#0c0c0c";
  const CATEGORY = [GREEN, INK, "#1d5bff", "#eda100", "#e87ba4", "#6250d6", "#e34948"];
  // One-hue green ramp, light to dark, for magnitude.
  const SEQUENTIAL = ["#dcf1e5", "#bfe6d1", "#9fd9bb", "#7ccda4", "#58bf8b", "#2fae70", "#00934f", "#007f44", "#006b3a", "#00572f", "#004425"];
  const DIVERGING = ["#1d5bff", "#8ea6ec", "#c9c6bd", "#7ccda4", GREEN];

  const INK_2 = "#33322e", MUTED = "#66645e", GRID = "#dedbd2", DOMAIN = INK, PANEL = "#efede6";
  const SANS = "Archivo, ui-sans-serif, system-ui, sans-serif";
  const MONO = "JetBrains Mono, ui-monospace, monospace";

  // Notebooks written for the earlier dark and cobalt themes hard-code their colours.
  // Map them onto this theme so those charts stay consistent. New charts can leave colour to the theme.
  const RECOLOR = {
    // dark theme
    "#3987e5": GREEN, "#d95926": INK, "#199e70": CATEGORY[2], "#c98500": CATEGORY[3],
    "#d55181": CATEGORY[4], "#0ca30c": CATEGORY[2], "#9085e9": CATEGORY[5], "#e66767": CATEGORY[6],
    "#86b6ef": "#7ccda4", "#5598e7": "#2fae70", "#2a78d6": GREEN, "#1c5cab": "#006b3a",
    "#e8e9ec": INK, "#dfe3ea": INK, "#a9adb8": INK_2, "#747a87": MUTED, "#5b606b": MUTED,
    "#3a3f4a": DOMAIN, "#252932": GRID, "#1a1d23": PANEL, "#121419": PANEL, "#15171c": PANEL,
    // cobalt theme
    "#2340ff": GREEN, "#eb6834": INK, "#1baf7a": CATEGORY[2], "#008300": CATEGORY[2],
    "#6a7cff": "#2fae70", "#a3aeff": "#7ccda4", "#d3d8ff": "#bfe6d1", "#b9b6ad": "#b5b1a6",
    "#111111": INK, "#3d3c39": INK_2, "#6b6a66": MUTED, "#fbfaf8": PANEL, "#e2e0da": GRID,
  };
  const recolor = (v) => {
    if (typeof v === "string") return RECOLOR[v.toLowerCase()] || v;
    if (Array.isArray(v)) return v.map(recolor);
    if (v && typeof v === "object") { for (const k in v) v[k] = recolor(v[k]); }
    return v;
  };

  const theme = {
    background: null,
    padding: { left: 4, right: 12, top: 8, bottom: 4 },
    font: SANS,
    view: { stroke: null },
    title: { color: INK, font: SANS, fontSize: 16, fontWeight: 800, anchor: "start", offset: 14, subtitleColor: INK_2, subtitleFontSize: 14, subtitleFontWeight: 400 },
    axis: {
      domainColor: DOMAIN, domainWidth: 1.5, tickColor: DOMAIN, gridColor: GRID, gridWidth: 1,
      labelColor: INK_2, labelFont: MONO, labelFontSize: 11, labelPadding: 6,
      titleColor: INK, titleFont: SANS, titleFontSize: 12, titleFontWeight: 700, titlePadding: 10,
    },
    axisX: { grid: false, tickSize: 4 },
    axisY: { domain: false, ticks: false, labelPadding: 8, labelLimit: 200 },
    axisBand: { grid: false },
    legend: {
      labelColor: INK_2, labelFont: SANS, labelFontSize: 12, titleColor: INK, titleFont: SANS,
      titleFontSize: 12, titleFontWeight: 700, symbolType: "square", symbolSize: 90, orient: "top", direction: "horizontal", labelLimit: 280, columns: 0,
    },
    header: { labelColor: INK_2, titleColor: INK, labelFont: SANS, titleFont: SANS },
    range: { category: CATEGORY, ramp: SEQUENTIAL, heatmap: SEQUENTIAL, diverging: DIVERGING },
    mark: { color: CATEGORY[0], tooltip: { content: "encoding" } },
    bar: { color: CATEGORY[0], cornerRadiusEnd: 0, stroke: PANEL, strokeWidth: 0 },
    rect: { cornerRadius: 0 },
    arc: { stroke: PANEL, strokeWidth: 2 },
    line: { color: CATEGORY[0], strokeWidth: 2, strokeCap: "round", strokeJoin: "round" },
    area: { color: CATEGORY[0], opacity: 0.85, line: false },
    point: { color: CATEGORY[0], size: 64, filled: true, stroke: PANEL, strokeWidth: 1.5 },
    circle: { size: 64, stroke: PANEL, strokeWidth: 1.5 },
    rule: { color: MUTED },
    text: { color: INK_2, font: SANS, fontSize: 12 },
  };

  // A simple chart fills its card's width; facets and concatenations keep their own sizes.
  const fitsWidth = (s) => !(s.facet || s.hconcat || s.vconcat || s.concat || s.repeat) && (s.width === undefined || s.width === "container");

  // Chart titles become page text so they wrap on narrow screens.
  const liftTitle = (el, spec) => {
    const t = spec.title;
    if (!t) return;
    const text = typeof t === "string" || Array.isArray(t) ? t : t.text;
    const sub = typeof t === "object" && !Array.isArray(t) ? t.subtitle : null;
    const h = document.createElement("div");
    h.className = "chart-title";
    h.textContent = [].concat(text).join(" ");
    if (sub) { const s = document.createElement("div"); s.className = "chart-subtitle"; s.textContent = [].concat(sub).join(" "); h.append(s); }
    el.before(h);
    delete spec.title;
  };

  // Label room scales with the card, so phone charts keep a usable plot area.
  const sized = (w) => ({
    ...theme,
    axis: { ...theme.axis, titleLimit: Math.max(120, w - 48) },
    axisY: { ...theme.axisY, labelLimit: Math.round(Math.min(200, w * 0.36)) },
    legend: { ...theme.legend, labelLimit: Math.round(w * 0.85), columns: w < 520 ? 1 : 0 },
  });

  const draw = (el) => {
    const spec = recolor(JSON.parse(el.querySelector("script").textContent));
    liftTitle(el, spec);
    if (fitsWidth(spec)) {
      spec.width = "container";
      spec.autosize = { type: "fit-x", contains: "padding" };
    }
    vegaEmbed(el, spec, { config: sized(el.clientWidth), actions: false, renderer: "svg", tooltip: { theme: "light" } })
      .catch((err) => { el.textContent = "Chart failed to load."; console.error(err); });
  };

  // Touch screens: a tapped tooltip would otherwise stay put. Hide it on scroll or a tap elsewhere.
  const hideTip = () => {
    const tip = document.getElementById("vg-tooltip-element");
    if (tip) tip.classList.remove("visible");
  };
  addEventListener("scroll", hideTip, { passive: true });
  document.addEventListener("pointerdown", (e) => { if (!e.target.closest(".chart")) hideTip(); });

  // Page-specific dashboards (e.g. projects/vegas-gaming/dashboard) draw their own specs
  // with the same look: window.siteChart.config(width) is this theme sized to a container.
  window.siteChart = { config: (w) => sized(w), recolor };

  const start = () => document.querySelectorAll("[data-chart]").forEach(draw);
  if (window.vegaEmbed) start(); else addEventListener("load", start);
})();
