/* Offline marker-overlap annotation. No network requests or external dependencies. */
(function (root) {
  "use strict";
  const MAX_ROWS = 20000;
  const MAX_UNIVERSE = 200000;

  function parseCSV(text, first, second) {
    const rows = [];
    let row = [], field = "", quoted = false;
    text = String(text || "").replace(/^\uFEFF/, "");
    for (let i = 0; i < text.length; i++) {
      const char = text[i];
      if (char === '"') {
        if (quoted && text[i + 1] === '"') { field += '"'; i++; }
        else if (quoted) quoted = false;
        else if (!field.trim()) quoted = true;
        else throw new Error("Malformed CSV quoting");
      } else if (!quoted && (char === "," || char === "\n" || char === "\r")) {
        row.push(field.trim()); field = "";
        if (char !== ",") {
          if (row.some(v => v)) rows.push(row);
          row = [];
          if (char === "\r" && text[i + 1] === "\n") i++;
        }
      } else field += char;
    }
    if (quoted) throw new Error("Unterminated quoted CSV field");
    row.push(field.trim());
    if (row.some(v => v)) rows.push(row);
    if (!rows.length) throw new Error("CSV is empty");
    const header = rows.shift().map(x => x.toLowerCase());
    const a = header.indexOf(first), b = header.indexOf(second);
    if (a < 0 || b < 0) throw new Error("Required CSV headers: " + first + ", " + second);
    if (rows.length > MAX_ROWS) throw new Error("CSV exceeds " + MAX_ROWS + " data rows");
    const values = new Map();
    for (const [i, cells] of rows.entries()) {
      if (cells.length !== header.length) throw new Error("Incorrect CSV field count on row " + (i + 2));
      const label = cells[a].trim(), gene = cells[b].trim().toUpperCase();
      if (!label || !gene) throw new Error("Empty label or gene on row " + (i + 2));
      if (!values.has(label)) values.set(label, new Set());
      values.get(label).add(gene);
    }
    if (!values.size) throw new Error("CSV contains no marker rows");
    return values;
  }

  function parseUniverse(text) {
    const names = String(text || "").replace(/^\uFEFF/, "").split(/[\s,;]+/).filter(Boolean);
    if (names.length && names[0].toLowerCase() === "gene") names.shift();
    const genes = new Set(names.map(x => x.trim().toUpperCase()));
    if (!genes.size) throw new Error("Background universe is empty");
    if (genes.size > MAX_UNIVERSE) throw new Error("Universe exceeds " + MAX_UNIVERSE + " genes");
    return genes;
  }

  const logfact = [0];
  function logFactorial(n) {
    for (let i = logfact.length; i <= n; i++) logfact[i] = logfact[i - 1] + Math.log(i);
    return logfact[n];
  }
  function logChoose(n, k) {
    return k < 0 || k > n ? -Infinity : logFactorial(n) - logFactorial(k) - logFactorial(n - k);
  }
  function hypergeomSF(N, K, n, k) {
    if (![N, K, n, k].every(Number.isInteger) || N < 1 || K < 0 || n < 0 || K > N || n > N)
      throw new Error("Invalid hypergeometric parameters");
    const low = Math.max(0, n - (N - K)), high = Math.min(K, n);
    if (k <= low) return 1;
    if (k > high) throw new Error("Observed overlap is impossible");
    const base = logChoose(N, n);
    let max = -Infinity, sum = 0;
    for (let i = k; i <= high; i++) {
      const t = logChoose(K, i) + logChoose(N - K, n - i) - base;
      if (t > max) { sum = sum * Math.exp(max - t) + 1; max = t; }
      else sum += Math.exp(t - max);
    }
    return Math.max(0, Math.min(1, Math.exp(max) * sum));
  }
  function adjustBH(pvalues) {
    const indices = pvalues.map((_, i) => i).sort((a,b) => pvalues[a] - pvalues[b] || a - b);
    const qvalues = Array(pvalues.length).fill(1);
    let minimum = 1;
    for (let rank = indices.length; rank > 0; rank--) {
      const idx = indices[rank - 1];
      minimum = Math.min(minimum, pvalues[idx] * indices.length / rank);
      qvalues[idx] = minimum;
    }
    return qvalues;
  }
  function annotate(markers, references, background, alpha = 0.05, minOverlap = 1) {
    if (!(markers instanceof Map) || !markers.size || !(references instanceof Map) || !references.size ||
        !(background instanceof Set) || !background.size) throw new Error("Provide nonempty markers, references, and universe");
    if (!Number.isFinite(alpha) || alpha <= 0 || alpha > 1) throw new Error("FDR cutoff must be in (0, 1]");
    if (!Number.isInteger(minOverlap) || minOverlap < 1) throw new Error("Minimum overlap must be a positive integer");
    for (const [category, groups] of [["cluster", markers], ["reference", references]]) {
      for (const [label, genes] of groups) {
        if (!label || !(genes instanceof Set) || !genes.size) throw new Error("Empty " + category + " signature");
        const missing = [...genes].filter(g => !background.has(g));
        if (missing.length) throw new Error(category + " '" + label + "' has " + missing.length +
          " gene(s) outside the universe: " + missing.slice(0, 5).join(", "));
      }
    }
    const output = [];
    for (const [cluster, genes] of markers) {
      const entries = [];
      for (const [cellType, signature] of references) {
        const shared = [...genes].filter(g => signature.has(g)).sort();
        entries.push({ cluster, cell_type: cellType, overlap: shared.length,
          cluster_size: genes.size, reference_size: signature.size, universe_size: background.size,
          shared_genes: shared.join(";"), p_value: hypergeomSF(background.size, signature.size, genes.size, shared.length) });
      }
      const q = adjustBH(entries.map(x => x.p_value));
      entries.forEach((x, i) => x.q_value = q[i]);
      entries.sort((a, b) => a.q_value - b.q_value || a.p_value - b.p_value ||
        b.overlap - a.overlap || a.cell_type.localeCompare(b.cell_type));
      const best = entries.find(r => r.q_value <= alpha && r.overlap >= minOverlap);
      entries.forEach(r => { r.assignment = best ? best.cell_type : "Unassigned"; r.is_best_match = r === best; });
      output.push(...entries);
    }
    return output;
  }
  const api = {parseCSV, parseUniverse, hypergeomSF, adjustBH, annotate};
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.CellTypeAnnotation = api;

  if (typeof document === "undefined") return;
  function el(id) { return document.getElementById(id); }
  const columns = ["cluster","cell_type","overlap","cluster_size","reference_size","universe_size","p_value","q_value","assignment","is_best_match","shared_genes"];
  let lastResults = [];
  function number(v) { return typeof v === "number" && !Number.isInteger(v) ? v.toExponential(4) : String(v); }
  function render(rows) {
    const body = el("results-body");
    body.replaceChildren();
    for (const row of rows) {
      const tr = document.createElement("tr");
      if (row.is_best_match) tr.className = "best";
      for (const key of ["cluster","cell_type","overlap","p_value","q_value","assignment","shared_genes"]) {
        const td = document.createElement("td");
        td.textContent = number(row[key]); tr.append(td);
      }
      body.append(tr);
    }
    el("results-section").hidden = false;
    el("export").disabled = false;
  }
  function status(message, error = false) {
    el("status").textContent = message;
    el("status").className = error ? "status error" : "status";
  }
  el("run").addEventListener("click", () => {
    try {
      const markers = parseCSV(el("clusters").value, "cluster", "gene");
      const refs = parseCSV(el("references").value, "cell_type", "gene");
      const universe = parseUniverse(el("universe").value);
      const alpha = Number(el("alpha").value), minOverlap = Number(el("overlap").value);
      if (!el("alpha").value || !el("overlap").value) throw new Error("Specify both thresholds");
      lastResults = annotate(markers, refs, universe, alpha, minOverlap);
      render(lastResults);
      status("Analyzed " + markers.size + " cluster(s) against " + refs.size +
        " reference cell type(s), using " + universe.size + " background genes. " +
        "Assignments are exploratory marker-overlap results, not validated classifications.");
    } catch (error) {
      lastResults = [];
      el("results-section").hidden = true;
      el("export").disabled = true;
      status(error.message, true);
    }
  });
  function safeCSV(value) {
    let s = String(value);
    if (/^[\s]*[=+@-]/.test(s) && typeof value === "string") s = "'" + s;
    return '"' + s.replace(/"/g, '""') + '"';
  }
  el("export").addEventListener("click", () => {
    if (!lastResults.length) return;
    const csv = [columns.join(","), ...lastResults.map(row => columns.map(k => safeCSV(row[k])).join(","))].join("\r\n");
    const url = URL.createObjectURL(new Blob([csv], {type:"text/csv;charset=utf-8"}));
    const link = document.createElement("a");
    link.href = url; link.download = "cell-type-annotation.csv"; link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  });
  for (const [fileId, areaId] of [["cluster-file","clusters"],["reference-file","references"],["universe-file","universe"]]) {
    el(fileId).addEventListener("change", async event => {
      const file = event.target.files[0];
      if (!file) return;
      if (file.size > 2_000_000) { status("File exceeds 2 MB limit", true); return; }
      try { el(areaId).value = await file.text(); status("Loaded " + file.name + " locally"); }
      catch (error) { status("Unable to read file: " + error.message, true); }
    });
  }
  el("example").addEventListener("click", () => {
    el("clusters").value = "cluster,gene\nCluster 0,CD3D\nCluster 0,CD3E\nCluster 0,IL7R\nCluster 1,MS4A1\nCluster 1,CD79A";
    el("references").value = "cell_type,gene\nT lymphocyte,CD3D\nT lymphocyte,CD3E\nT lymphocyte,IL7R\nB lymphocyte,MS4A1\nB lymphocyte,CD79A\nB lymphocyte,CD79B";
    el("universe").value = ["CD3D","CD3E","IL7R","MS4A1","CD79A","CD79B",...Array.from({length:100},(_,i) => "BACKGROUND_"+(i+1))].join("\n");
    status("Synthetic example loaded. Press Annotate clusters to calculate results.");
  });
})(typeof window !== "undefined" ? window : globalThis);
