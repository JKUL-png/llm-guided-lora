/* Interactive figures for part 2. Plain HTML bars, so they reflow on a phone. Same helpers and look as the part 1 blog.
   Every number comes from window.BLOG (data/data.js), which build_blog.py writes from the CSVs. */
(function () {
  const B = window.BLOG;
  const $ = (id) => document.getElementById(id);
  const n1 = (v) => {   // one decimal, exact halves to even, as in the paper
    const x = Math.round(Math.abs(v) * 1e6) / 1e6, s = x * 10, f = Math.floor(s);
    const r = Math.abs(s - f - 0.5) < 1e-9 ? (f % 2 ? f + 1 : f) : Math.round(s);
    return (v < 0 && r !== 0 ? "−" : "") + (r / 10).toFixed(1);
  };
  const sg = (v) => { const t = n1(v); return t.startsWith("−") || t === "0.0" ? t : "+" + t; };
  const pc = (v) => n1(v) + "%";
  const int = (v) => Math.round(v).toLocaleString("en-US");
  const h = (tag, cls, html) => { const e = document.createElement(tag); if (cls) e.className = cls; if (html !== undefined) e.innerHTML = html; return e; };
  const COL = { a: "c-full", b: "c-opus", f: "c-opus", c: "c-auto", d: "c-auto", e: "c-auto", N: "c-orig", T: "c-orig", P: "c-edit" };
  const short = (k) => ({ N: "thinking off", T: "thinking on", P: "p50c" }[k] || `(${k})`);
  const READ = { solid: "solid", indication: "indication", no: "not distinguishable from zero" };

  function tabs(root, label, options, onPick) {
    const g = h("div", "seg"); g.setAttribute("role", "group"); g.setAttribute("aria-label", label);
    const set = (value) => { g.querySelectorAll("button").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.v === value))); onPick(value); };
    options.forEach(([value, text]) => { const b = h("button", "", text); b.type = "button"; b.dataset.v = value; b.addEventListener("click", () => set(value)); g.append(b); });
    root.append(g);
    return set;
  }

  function table(root, head, rows) {
    const d = h("details", "data"); d.append(h("summary", "", "Data table"));
    const w = h("div", "table-wrap"), t = h("table");
    t.innerHTML = `<thead><tr>${head.map((c) => `<th>${c}</th>`).join("")}</tr></thead><tbody>${rows.map((r) => `<tr>${r.map((c) => `<td>${c}</td>`).join("")}</tr>`).join("")}</tbody>`;
    w.append(t); d.append(w); root.append(d);
    return d;
  }

  // Selectable rows: a click (or Enter) shows the row's sentence in the readout under the figure.
  function selectable(el, read, text) {
    el.tabIndex = 0; el.setAttribute("role", "button");
    const pick = () => { el.parentNode.querySelectorAll(".on").forEach((x) => x.classList.remove("on")); el.classList.add("on"); read.innerHTML = text; };
    el.addEventListener("click", pick);
    el.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); pick(); } });
  }

  // rows: {key, label, value, lo, hi, text, side, ghost}
  function bars(box, read, rows, max) {
    box.textContent = "";
    rows.forEach((r) => {
      const row = h("div", "bar-row");
      const top = h("div", "bar-top");
      top.append(h("span", "bar-name", r.label), h("span", "bar-val", r.text));
      const tr = h("div", "bar-track");
      const fill = h("div", `bar-fill ${r.cls}`); fill.style.width = `${(r.value / max) * 100}%`; tr.append(fill);
      if (r.lo !== undefined) { const ci = h("div", "bar-ci"); ci.style.left = `${(r.lo / max) * 100}%`; ci.style.width = `${((r.hi - r.lo) / max) * 100}%`; tr.append(ci); }
      if (r.ghost !== undefined) { const gh = h("div", "bar-ghost"); gh.style.left = `${(r.ghost / max) * 100}%`; tr.append(gh); }
      row.append(top, tr);
      if (r.side) row.append(h("div", "bar-side", r.side));
      if (r.read) selectable(row, read, r.read);
      box.append(row);
    });
    const ax = h("div", "bar-axis");
    [0, 0.25, 0.5, 0.75, 1].forEach((f) => { const t = h("span", "", String(Math.round(max * f))); t.style.left = `${f * 100}%`; ax.append(t); });
    box.append(ax);
  }

  /* Figure: the design (which layers each adapter trains) */
  (function () {
    const root = $("figDesign"); if (!root) return;
    const grid = h("div", "lgrid"), read = h("p", "read", "Tap a row to see that adapter's layers and results.");
    const head = h("div", "lgrid-row lgrid-head");
    head.append(h("span", "lgrid-name", ""));
    const cells = h("span", "lgrid-cells");
    for (let k = 0; k < B.nLayers; k++) cells.append(h("span", "lgrid-num", k % 5 === 0 || k === B.nLayers - 1 ? String(k) : ""));
    head.append(cells); grid.append(head);
    let prev = null;
    B.design.forEach((r) => {
      const row = h("div", `lgrid-row${prev !== r.arm ? " first" : ""}`);
      row.append(h("span", "lgrid-name", prev !== r.arm ? B.names[r.arm] : ""));
      const cs = h("span", "lgrid-cells");
      for (let k = 0; k < B.nLayers; k++) {
        const c = h("span", `lgrid-cell${r.layers.includes(k) ? " " + COL[r.arm] : ""}${B.mitLayers.includes(k) ? " mit" : ""}`);
        cs.append(c);
      }
      row.append(cs);
      selectable(row, read, `<strong>${B.names[r.arm]}, seed ${r.seed}:</strong> ${r.layers.length === B.nLayers ? "all layers" : "layers " + r.layers.join(", ")}. On MATH it answered ${r.correct} of ${B.nProblems} correctly, and ${r.clean} of its ${B.nProblems} responses were clean (one close of thinking, under the limit).`);
      grid.append(row);
      prev = r.arm;
    });
    root.append(grid, read);
    table(root, ["Arm", "Seed", "Layers", `MATH correct (of ${B.nProblems})`, `Clean (of ${B.nProblems})`],
      B.design.map((r) => [B.names[r.arm], r.seed, r.layers.length === B.nLayers ? "all" : r.layers.join(" "), r.correct, r.clean]));
  })();

  /* Figure: accuracy per model */
  (function () {
    const root = $("figAcc"); if (!root) return;
    const box = h("div", "div-bars"), read = h("p", "read", "Tap a bar to see its numbers.");
    const TASK = { math: "MATH-500", gsm8k: "GSM8K", ifeval: "IFEval" };
    let tbl = null;
    const show = (t) => {
      const rows = B.acc[t], N = rows.find((r) => r.key === "N").acc;
      bars(box, read, rows.map((r) => ({
        label: B.names[r.key], value: r.acc, lo: r.lo, hi: r.hi, cls: COL[r.key], ghost: N, text: pc(r.acc),
        side: `${pc(r.limit)} at the limit · ${int(r.tokens)} tokens per response`,
        read: `<strong>${B.names[r.key]}, ${TASK[t]}:</strong> ${pc(r.acc)} correct (95% interval ${n1(r.lo)}–${n1(r.hi)}); seeds ${r.seeds.join(" / ")} of ${B.nProblems}. ${pc(r.limit)} of responses hit the token limit; ${int(r.tokens)} tokens per response on average.`,
      })), 100);
      read.textContent = "Tap a bar to see its numbers.";
      if (tbl) tbl.remove();
      tbl = table(root, ["Model", "Correct %", "95% interval", "At limit %", "Tokens", "Per seed"],
        rows.map((r) => [B.names[r.key], n1(r.acc), `${n1(r.lo)}–${n1(r.hi)}`, n1(r.limit), int(r.tokens), r.seeds.join(" / ")]));
    };
    const set = tabs(root, "Benchmark", [["math", "MATH-500"], ["gsm8k", "GSM8K"], ["ifeval", "IFEval"]], show);
    root.append(box, read);
    set("math");
  })();

  /* Figure: differences, with the two intervals */
  (function () {
    const root = $("figDiff"); if (!root) return;
    const box = h("div", "dv"), read = h("p", "read", "Tap a row to see its tests.");
    let tbl = null;
    const show = (g) => {
      const rows = B.diff[g];
      const ext = Math.max(10, ...rows.map((r) => Math.max(Math.abs(r.lo), Math.abs(r.hi))));
      const lim = Math.ceil(ext / 5) * 5, X = (v) => ((v + lim) / (2 * lim)) * 100;
      box.textContent = "";
      rows.forEach((r) => {
        const row = h("div", `dv-row ${r.read}`);
        const top = h("div", "bar-top");
        top.append(h("span", "bar-name", `${short(r.x)} − ${short(r.y)}`), h("span", "bar-val", `${sg(r.dif)} [${sg(r.lo)}, ${sg(r.hi)}]`));
        const tr = h("div", "dv-track");
        const band = h("div", `dv-band ${COL[r.x]}`); band.style.left = `${X(r.lo)}%`; band.style.width = `${X(r.hi) - X(r.lo)}%`;
        const line = h("div", `dv-line ${COL[r.x]}`); line.style.left = `${X(r.plo)}%`; line.style.width = `${X(r.phi) - X(r.plo)}%`;
        const dot = h("div", `dv-dot ${COL[r.x]}`); dot.style.left = `${X(r.dif)}%`;
        const z = h("div", "zero"); z.style.left = `${X(0)}%`;
        tr.append(band, line, z, dot);
        row.append(top, tr, h("div", "bar-side", `${r.status} · ${READ[r.read]}`));
        selectable(row, read, `<strong>${short(r.x)} − ${short(r.y)}:</strong> ${sg(r.dif)} points. 95% interval over problems and adapters ${sg(r.lo)} to ${sg(r.hi)}; over problems only ${sg(r.plo)} to ${sg(r.phi)}. Permutation p = ${r.p}; Holm-corrected ${r.holm} (family of ${r.famsize}). ${r.status[0].toUpperCase() + r.status.slice(1)}; reading: ${READ[r.read]}.`);
        box.append(row);
      });
      const ax = h("div", "bar-axis");
      [-lim, -lim / 2, 0, lim / 2, lim].forEach((v) => { const t = h("span", "", v > 0 ? "+" + v : v < 0 ? "−" + -v : "0"); t.style.left = `${X(v)}%`; ax.append(t); });
      box.append(ax);
      read.textContent = "Tap a row to see its tests.";
      if (tbl) tbl.remove();
      tbl = table(root, ["Comparison", "Difference", "95% interval", "Per problem", "p", "Holm", "Status", "Reading"],
        rows.map((r) => [`${short(r.x)} − ${short(r.y)}`, sg(r.dif), `${sg(r.lo)} to ${sg(r.hi)}`, `${sg(r.plo)} to ${sg(r.phi)}`, r.p, r.holm, r.status, READ[r.read]]));
    };
    const set = tabs(root, "Comparison", [["main", "Main test"], ["nothink", "vs thinking off"], ["p50c", "vs p50c"], ["gsm8k", "GSM8K"], ["ifeval", "IFEval"], ["explore", "Exploratory"]], show);
    root.append(box, read);
    const lg = h("div", "legend");
    lg.innerHTML = '<span class="lg"><span class="sw sw-band"></span>95% interval, problems and adapters (main)</span><span class="lg"><span class="sw sw-line"></span>problems only (robustness)</span>';
    root.append(lg);
    set("main");
  })();

  /* Figure: clean responses (exploratory) */
  (function () {
    const root = $("figClean"); if (!root) return;
    const box = h("div", "div-bars"), read = h("p", "read", "Tap a bar to see its numbers.");
    let tbl = null;
    const groups = (k) => (k === "c" ? " · seeds use layers " + Object.values(B.placeboLayers).map((l) => l.join(" ")).join(" / ") : "");
    const show = (v) => {
      if (v === "share") {
        bars(box, read, B.clean.map((r) => ({
          label: B.names[r.key], value: r.pct, lo: r.lo, hi: r.hi, cls: COL[r.key], text: pc(r.pct), side: `per seed ${r.seeds.join(" / ")}`,
          read: `<strong>${B.names[r.key]}:</strong> ${pc(r.pct)} of responses close their thinking exactly once and stay under the limit (95% interval ${n1(r.lo)}–${n1(r.hi)}). Per seed: ${r.seeds.join(" / ")} of ${B.nProblems}${groups(r.key)}.`,
        })), 100);
      } else {
        const rows = [];
        B.clean.forEach((r) => {
          rows.push({ label: `${B.names[r.key]} · clean`, value: r.accclean, cls: COL[r.key], text: pc(r.accclean) });
          rows.push({ label: `${B.names[r.key]} · more than one close`, value: r.accmulti, cls: `${COL[r.key]} hatch`, text: pc(r.accmulti) });
        });
        bars(box, read, rows, 100);
      }
      read.textContent = "Tap a bar to see its numbers.";
      if (tbl) tbl.remove();
      tbl = table(root, ["Model", "Clean %", "95% interval", "Per seed", "Correct if clean %", "Correct if >1 close %"],
        B.clean.map((r) => [B.names[r.key], n1(r.pct), `${n1(r.lo)}–${n1(r.hi)}`, r.seeds.join(" / "), n1(r.accclean), n1(r.accmulti)]));
    };
    const set = tabs(root, "View", [["share", "Share of clean responses"], ["acc", "Accuracy by response type"]], show);
    root.append(box, read);
    set("share");
  })();

  /* Copy citation */
  const copy = $("copy");
  if (copy && navigator.clipboard) copy.addEventListener("click", () => navigator.clipboard.writeText($("bibtex").textContent).then(() => { copy.textContent = "Copied"; }));
})();
