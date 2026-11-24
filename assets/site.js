(() => {
  const root = document.documentElement;
  const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
  root.classList.add("js");
  // iOS Safari only shows :active (press) styles when the page listens for touches.
  document.addEventListener("touchstart", () => {}, { passive: true });

  // ---- code blocks: fold / expand ----
  const LABELS = {
    preview: (n) => `Show all ${n} lines`,
    expanded: () => "Show less",
    folded: () => "Show code",
    unfolded: () => "Hide code",
  };
  const NEXT = { preview: "expanded", expanded: "preview", folded: "unfolded", unfolded: "folded" };

  document.querySelectorAll(".code").forEach((block) => {
    const toggle = block.querySelector(".code-toggle");
    const n = block.dataset.lines;
    const paint = () => {
      const label = LABELS[block.dataset.state];
      toggle.textContent = label ? label(n) : "";
      toggle.setAttribute("aria-expanded", String(["expanded", "unfolded"].includes(block.dataset.state)));
    };
    paint();
    // A long block's bottom fade is a button that shows every line.
    if (block.dataset.state === "preview") {
      const more = document.createElement("button");
      more.type = "button";
      more.className = "code-more";
      more.innerHTML = `<span>Show all ${n} lines &darr;</span>`;
      more.addEventListener("click", () => { block.dataset.state = "expanded"; paint(); });
      block.append(more);
    }
    toggle.addEventListener("click", () => {
      const was = block.dataset.state;
      block.dataset.state = NEXT[was] || was;
      paint();
      if (was === "expanded") block.scrollIntoView({ block: "nearest", behavior: reduce ? "auto" : "smooth" });
    });

  });

  // ---- project page: reading progress, top bar edge, table of contents ----
  const bar = document.querySelector(".topbar");
  const progress = document.querySelector(".progress");
  if (bar) {
    const onScroll = () => {
      const max = root.scrollHeight - innerHeight;
      progress.style.setProperty("--p", max > 0 ? Math.min(1, scrollY / max) : 0);
    };
    addEventListener("scroll", onScroll, { passive: true });
    onScroll();
  }

  const tocLinks = [...document.querySelectorAll(".toc a")];
  if (tocLinks.length && "IntersectionObserver" in window) {
    const heads = tocLinks.map((a) => document.getElementById(decodeURIComponent(a.hash.slice(1)))).filter(Boolean);
    const spy = new IntersectionObserver(() => {
      let current = heads[0];
      for (const h of heads) if (h.getBoundingClientRect().top < innerHeight * 0.3) current = h;
      tocLinks.forEach((a) => a.classList.toggle("active", a.hash === `#${current.id}`));
    }, { rootMargin: "0px 0px -60% 0px", threshold: [0, 1] });
    heads.forEach((h) => spy.observe(h));
  }

  // ---- math (only loaded on pages that have it) ----
  addEventListener("load", () => {
    if (window.renderMathInElement) {
      renderMathInElement(document.querySelector(".proj-body"), {
        delimiters: [
          { left: "$$", right: "$$", display: true },
          { left: "\\[", right: "\\]", display: true },
          { left: "$", right: "$", display: false },
        ],
        throwOnError: false,
      });
    }
  });
})();
