"""Tests for scientific annotation calculations and validation."""
import math
import pytest

from celltype_annotator.annotation import annotate_clusters, adjust_bh, hypergeom_survival


def test_hypergeom_exact_tail():
    assert hypergeom_survival(20, 2, 2, 2) == pytest.approx(1 / 190)
    assert hypergeom_survival(10, 3, 2, 2) == pytest.approx(3 / 45)
    assert hypergeom_survival(10, 3, 2, 0) == 1.0


def test_hypergeom_invalid_arguments():
    with pytest.raises(ValueError):
        hypergeom_survival(10, 11, 2, 1)
    with pytest.raises(ValueError):
        hypergeom_survival(10, 2, 2, 3)


def test_bh_adjustments_monotonic_and_in_input_order():
    assert adjust_bh([0.04, 0.01, 0.03]) == pytest.approx([0.04, 0.03, 0.04])
    assert adjust_bh([]) == []


def test_annotation_selected_when_significant():
    universe = [f"G{i}" for i in range(1, 101)]
    rows = annotate_clusters(
        {"C1": ["G1", "G2", "G3"], "C2": ["G90", "G91"]},
        {"Type A": ["G1", "G2", "G3"], "Type B": ["G10", "G11"]},
        universe,
    )
    c1 = [r for r in rows if r["cluster"] == "C1"]
    a = next(r for r in c1 if r["cell_type"] == "Type A")
    assert a["overlap"] == 3
    assert a["assignment"] == "Type A"
    assert a["is_best_match"]
    assert a["q_value"] < 0.05
    assert all(r["assignment"] == "Unassigned" for r in rows if r["cluster"] == "C2")


def test_gene_case_normalization_and_duplicate_handling():
    rows = annotate_clusters({"C": ["g1", "G1"]}, {"T": ["G1"]}, ["g1", "G2"], alpha=1)
    assert rows[0]["overlap"] == 1
    assert rows[0]["cluster_size"] == 1


@pytest.mark.parametrize("clusters,refs,universe", [
    ({"C": ["G999"]}, {"T": ["G1"]}, ["G1"]),
    ({"C": ["G1"]}, {"T": ["G999"]}, ["G1"]),
    ({"C": []}, {"T": ["G1"]}, ["G1"]),
    ({}, {"T": ["G1"]}, ["G1"]),
])
def test_reject_bad_gene_universe(clusters, refs, universe):
    with pytest.raises(ValueError):
        annotate_clusters(clusters, refs, universe)


def test_no_overlap_not_assigned_even_with_permissive_alpha():
    rows = annotate_clusters({"C": ["A"]}, {"T": ["B"]}, ["A", "B"], alpha=1.0)
    assert rows[0]["assignment"] == "Unassigned"
    assert not rows[0]["is_best_match"]


def test_invalid_thresholds():
    for alpha in (0, -0.1, float("nan"), float("inf")):
        with pytest.raises(ValueError):
            annotate_clusters({"C": ["A"]}, {"T": ["A"]}, ["A"], alpha=alpha)
    with pytest.raises(ValueError):
        annotate_clusters({"C": ["A"]}, {"T": ["A"]}, ["A"], min_overlap=0)
