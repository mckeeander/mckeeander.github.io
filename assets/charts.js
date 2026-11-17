// Dark theme for every Altair / Vega-Lite chart on the site.
// Categorical colours are the dark steps of a palette checked for colour-blind
// separation and 3:1 contrast against the chart card (#1a1d23). Use them in order.
(() => {
  const CATEGORY = ["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#008300", "#9085e9", "#e66767"];
  const SEQUENTIAL = ["#184f95", "#1c5cab", "#256abf", "#2a78d6", "#3987e5", "#5598e7", "#6da7ec", "#86b6ef", "#9ec5f4", "#b7d3f6"];
  const DIVERGING = ["#d95926", "#a0644c", "#5b606b", "#4f78b3", "#3987e5"];

  const INK = "#e8e9ec", INK_2 = "#a9adb8", MUTED = "#747a87", GRID = "#252932", DOMAIN = "#3a3f4a";
  const SANS = "Hanken Grotesk, ui-sans-serif, system-ui, sans-serif";
  const MONO = "JetBrains Mono, ui-monospace, monospace";

  const theme = {
    background: null,
    padding: { left: 4, right: 12, top: 8, bottom: 4 },
    font: SANS,
    view: { stroke: null },
    title: { color: INK, font: SANS, fontSize: 15, fontWeight: 600, anchor: "start", offset: 14, subtitleColor: INK_2, subtitleFontSize: 13, subtitleFontWeight: 400 },
    axis: {
      domainColor: DOMAIN, tickColor: DOMAIN, gridColor: GRID, gridWidth: 1,
      labelColor: INK_2, labelFont: MONO, labelFontSize: 11, labelPadding: 6,
      titleColor: INK_2, titleFont: SANS, titleFontSize: 12, titleFontWeight: 500, titlePadding: 10,
    },
    axisX: { grid: false, tickSize: 4 },
    axisY: { domain: false, ticks: false, labelPadding: 8, labelLimit: 200 },
    axisBand: { grid: false },
    legend: {
      labelColor: INK_2, labelFont: SANS, labelFontSize: 12, titleColor: INK_2, titleFont: SANS,
      titleFontSize: 12, titleFontWeight: 500, symbolType: "circle", symbolSize: 90, orient: "top", direction: "horizontal", labelLimit: 280, columns: 0,
    },
    header: { labelColor: INK_2, titleColor: INK, labelFont: SANS, titleFont: SANS },
    range: { category: CATEGORY, ramp: SEQUENTIAL, heatmap: SEQUENTIAL, diverging: DIVERGING },
    mark: { color: CATEGORY[0], tooltip: { content: "encoding" } },
    bar: { color: CATEGORY[0], cornerRadiusEnd: 4, stroke: "#1a1d23", strokeWidth: 0 },
    rect: { cornerRadius: 2 },
    arc: { stroke: "#1a1d23", strokeWidth: 2 },
    line: { color: CATEGORY[0], strokeWidth: 2, strokeCap: "round", strokeJoin: "round" },
    area: { color: CATEGORY[0], opacity: 0.85, line: false },
    point: { color: CATEGORY[0], size: 64, filled: true, stroke: "#1a1d23", strokeWidth: 1.5 },
    circle: { size: 64, stroke: "#1a1d23", strokeWidth: 1.5 },
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
    const spec = JSON.parse(el.querySelector("script").textContent);
    liftTitle(el, spec);
    if (fitsWidth(spec)) {
      spec.width = "container";
      spec.autosize = { type: "fit-x", contains: "padding" };
    }
    vegaEmbed(el, spec, { config: sized(el.clientWidth), actions: false, renderer: "svg", tooltip: { theme: "dark" } })
      .catch((err) => { el.textContent = "Chart failed to load."; console.error(err); });
  };

  const start = () => document.querySelectorAll("[data-chart]").forEach(draw);
  if (window.vegaEmbed) start(); else addEventListener("load", start);
})();
