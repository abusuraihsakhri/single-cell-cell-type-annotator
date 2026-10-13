"""Deterministic marker-overlap cell-type annotation.

Input reference signatures and universe are supplied by the user; no atlas
database, expression normalization, or learned classifier is bundled.
"""
from __future__ import annotations

import math
from collections.abc import Iterable, Mapping


def _genes(values: Iterable[str], field: str) -> set[str]:
    if isinstance(values, (str, bytes)):
        raise ValueError(f"{field} must be an iterable of gene identifiers")
    try:
        result = {str(g).strip().upper() for g in values}
    except TypeError as exc:
        raise ValueError(f"{field} must be an iterable") from exc
    if not result or "" in result:
        raise ValueError(f"{field} must contain non-empty gene identifiers")
    return result


def _signatures(values: Mapping[str, Iterable[str]], field: str) -> dict[str, set[str]]:
    if not isinstance(values, Mapping) or not values:
        raise ValueError(f"{field} must be a non-empty mapping")
    output = {}
    for name, genes in values.items():
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"{field} contains an empty label")
        if name.strip() in output:
            raise ValueError(f"{field} contains duplicate labels")
        output[name.strip()] = _genes(genes, f"{field}[{name}]")
    return output


def hypergeom_survival(population: int, successes: int, draws: int, overlap: int) -> float:
    """P(X >= overlap) for sampling without replacement, using log-sum-exp."""
    if not (0 <= successes <= population and 0 <= draws <= population):
        raise ValueError("Invalid hypergeometric population or subset size")
    low = max(0, draws - (population - successes))
    high = min(successes, draws)
    if not (low <= overlap <= high):
        if overlap <= low:
            return 1.0
        raise ValueError("Observed overlap exceeds its possible maximum")
    if overlap == low:
        return 1.0

    def logchoose(n: int, k: int) -> float:
        return math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)

    denominator = logchoose(population, draws)
    terms = [
        logchoose(successes, i) + logchoose(population - successes, draws - i) - denominator
        for i in range(overlap, high + 1)
    ]
    maximum = max(terms)
    return min(1.0, math.exp(maximum) * math.fsum(math.exp(t - maximum) for t in terms))


def adjust_bh(p_values: list[float]) -> list[float]:
    """Benjamini-Hochberg FDR adjustment; preserves input order."""
    size = len(p_values)
    adjusted = [1.0] * size
    running = 1.0
    for rank in range(size, 0, -1):
        i = sorted(range(size), key=lambda index: (p_values[index], index))[rank - 1]
        running = min(running, p_values[i] * size / rank)
        adjusted[i] = min(1.0, running)
    return adjusted


def annotate_clusters(
    cluster_markers: Mapping[str, Iterable[str]],
    references: Mapping[str, Iterable[str]],
    universe: Iterable[str],
    *,
    alpha: float = 0.05,
    min_overlap: int = 1,
) -> list[dict]:
    """Compare each cluster against all user-supplied reference cell types.

    Apply BH adjustment independently within each cluster over all references.
    Return one row per cluster/reference, with the best significant hit labeled.
    """
    if not math.isfinite(alpha) or not (0 < alpha <= 1):
        raise ValueError("alpha must be in (0, 1]")
    if isinstance(min_overlap, bool) or not isinstance(min_overlap, int) or min_overlap < 1:
        raise ValueError("min_overlap must be a positive integer")
    background = _genes(universe, "universe")
    clusters = _signatures(cluster_markers, "cluster_markers")
    signatures = _signatures(references, "references")
    for group, data in (("cluster_markers", clusters), ("references", signatures)):
        for label, genes in data.items():
            extra = genes - background
            if extra:
                raise ValueError(f"{group}[{label}] has {len(extra)} gene(s) absent from universe: " +
                                 ", ".join(sorted(extra)[:5]))
    n = len(background)
    rows: list[dict] = []
    for cluster, markers in clusters.items():
        group_rows = []
        for cell_type, signature in signatures.items():
            shared = sorted(markers & signature)
            p = hypergeom_survival(n, len(signature), len(markers), len(shared))
            group_rows.append({
                "cluster": cluster, "cell_type": cell_type, "overlap": len(shared),
                "cluster_size": len(markers), "reference_size": len(signature),
                "universe_size": n, "shared_genes": ";".join(shared),
                "p_value": p,
            })
        q_values = adjust_bh([r["p_value"] for r in group_rows])
        for row, q in zip(group_rows, q_values):
            row["q_value"] = q
        group_rows.sort(key=lambda r: (r["q_value"], r["p_value"], -r["overlap"], r["cell_type"]))
        winner = next((r for r in group_rows
                       if r["q_value"] <= alpha and r["overlap"] >= min_overlap), None)
        for row in group_rows:
            row["assignment"] = winner["cell_type"] if winner else "Unassigned"
            row["is_best_match"] = row is winner
        rows.extend(group_rows)
    return rows
