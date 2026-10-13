# Single-cell Cell Type Annotator

A reproducible **marker-overlap annotation tool** for single-cell RNA-seq cluster marker lists. Compare user-provided cluster markers against user-provided reference cell-type signatures using the exact one-sided hypergeometric tail; report Benjamini–Hochberg (BH) adjusted p-values separately for each cluster.

This is an exploratory statistical annotator. It does **not** download curated atlases, infer expression-based cell identities, run CellTypist, or estimate calibrated classification probabilities.

## Use in the browser

Open `web/index.html` locally, or serve it with:

```bash
python -m http.server 8001 --directory web
```

Then open `http://localhost:8001/`. The standalone browser app has no server dependency and works without Pyodide. It does not upload files or make outbound network requests; calculation and export remain in your browser.

Supply three inputs:

1. **Cluster markers:** CSV columns `cluster,gene`, with one marker per row.
2. **Reference signatures:** CSV columns `cell_type,gene`, one reference gene per row.
3. **Background universe:** TXT/CSV containing all genes eligible for testing, separated by lines, commas, or whitespace; this must not be restricted to observed hits.

Gene symbols are normalized to uppercase; duplicate symbols within each group are removed. Every cluster/reference gene must be present in the supplied universe. Choose your own FDR cutoff (default 0.05) and minimum overlap (default 1). The highest-ranked BH-significant reference becomes the assignment; otherwise a cluster is `Unassigned`. Download the full per-cluster/per-reference comparison table as CSV. Use **Load synthetic example** to check the interface.

## Python CLI

Requires Python 3.9 or later.

```bash
python -m pip install -e ".[dev]"
single-cell-cell-type-annotator annotate \
  --markers markers.csv \
  --references reference.csv \
  --universe universe.txt \
  --alpha 0.05 \
  --min-overlap 1 \
  -o annotations.csv
```

The module also exposes `annotate_clusters()`, `hypergeom_survival()`, and `adjust_bh()` in `celltype_annotator.annotation` for programmatic use. The CLI and browser calculate the same hypergeometric test with distinct numerically stable implementations.

## API and legacy utilities

Start the FastAPI service from a repository checkout:

```bash
python cli.py serve --host 127.0.0.1 --port 8000
```

- `GET /`: local browser interface (when web files are present).
- `GET /health`: API status.
- `POST /api/annotate`: accepts `cluster_markers` and `references` maps of label to gene-list, plus `universe`, `alpha`, and `min_overlap`; returns `results`.
- `POST /api/audit`, `POST /api/chat`, `GET /api/audit/logs`, `GET /metrics`: the preserved **legacy generic task-evaluation endpoints**, not biological annotation.

The legacy `audit`, `batch`, `chat`, and `verify-audit` commands remain accessible through `python cli.py`. Legacy numeric thresholds are not cell-type biological standards, and mock chat does not perform clinical or scientific assessment.

The audit logger holds records in process memory and signs them with HMAC-SHA256. Set a strong `AUDIT_SECRET_KEY` when persistent verification across restarts is required; if unset, an ephemeral random key is used and logs cannot be verified across restarts. This is not a replacement for persisted, access-controlled audit logging. PHI pattern checking is heuristic and **does not guarantee HIPAA de-identification**; do not submit identifiable patient data.

## Interpretation and limitations

A hypergeometric overlap p-value assesses enrichment relative to the **specified gene universe**, assuming genes are exchangeable under the null. The BH q-value controls a multiple-testing procedure over the submitted references within each cluster. The smallest q-value is not a posterior probability, and a significant result does not independently establish cell identity. Marker selection bias, correlated genes, tissue context, incomplete references, and choice of gene universe can affect results. Confirm assignments with independent gene-expression evidence, differential-expression analysis, and biological expertise.

No built-in HCA/PanglaoDB reference data are shipped or queried. The synthetic example is illustrative, not a validated biological dataset.

## Development and tests

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
node --test tests/browser.test.js
node --check web/annotator.js
```

The `web/` directory is a static deployable site for GitHub Pages. `.github/workflows/pages.yml` deploys that directory on changes to `master`, provided Pages is enabled and GitHub Actions has sufficient deployment permissions. The application is fully client-side; no Python-to-WebAssembly runtime is required.

## License

MIT. See [LICENSE](LICENSE).
