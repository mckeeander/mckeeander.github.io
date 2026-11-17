(() => {
  const root = document.documentElement;
  const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
  root.classList.add("js");

  // ---- scroll-in reveal: only what starts below the fold fades in ----
  const items = [...document.querySelectorAll(".reveal")];
  if ("IntersectionObserver" in window && !reduce) {
    const below = items.filter((el) => el.getBoundingClientRect().top > innerHeight * 0.94);
    below.forEach((el) => el.classList.add("pending"));
    const io = new IntersectionObserver((entries) => {
      for (const e of entries) {
        if (e.isIntersecting) { e.target.classList.remove("pending"); io.unobserve(e.target); }
      }
    }, { rootMargin: "0px 0px -6% 0px" });
    below.forEach((el) => io.observe(el));
  }

  // ---- card spotlight follows the pointer; a tap or click anywhere else clears it ----
  const cards = [...document.querySelectorAll(".card")];
  cards.forEach((card) => {
    const light = (e) => {
      const r = card.getBoundingClientRect();
      card.style.setProperty("--mx", `${e.clientX - r.left}px`);
      card.style.setProperty("--my", `${e.clientY - r.top}px`);
      card.classList.add("lit");
    };
    card.addEventListener("pointermove", light);
    card.addEventListener("pointerdown", light);
    card.addEventListener("pointerleave", (e) => { if (e.pointerType === "mouse") card.classList.remove("lit"); });
  });
  document.addEventListener("pointerdown", (e) => {
    cards.forEach((card) => { if (!card.contains(e.target)) card.classList.remove("lit"); });
  });
  // Coming back with the Back button restores the page as it was left; start unlit.
  addEventListener("pageshow", () => cards.forEach((card) => card.classList.remove("lit")));

  // ---- link chips: tell the border glint where each chip sits in the row ----
  const linkRow = document.querySelector(".links");
  if (linkRow) {
    const place = () => {
      const row = linkRow.getBoundingClientRect();
      const chips = [...linkRow.querySelectorAll("a")];
      const right = Math.max(...chips.map((a) => a.getBoundingClientRect().right));
      linkRow.style.setProperty("--span", `${right - row.left}px`);
      linkRow.querySelectorAll("a").forEach((a) =>
        a.style.setProperty("--off", `${a.getBoundingClientRect().left - row.left}px`));
    };
    place();
    addEventListener("resize", place);
    document.fonts && document.fonts.ready.then(place);
  }

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
      bar.classList.toggle("scrolled", scrollY > 8);
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
