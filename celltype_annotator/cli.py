"""
Command-Line Interface for CellType-Marker: Reference-Based scRNA-seq Marker Overlap & Annotation Agent.
"""
import argparse
import csv
import json
import sys
from .models import FrontierPayload
from .agents import CellTypeAnnotatorCoordinator
from .annotation import annotate_clusters
from pathlib import Path

coordinator = CellTypeAnnotatorCoordinator()


def main(argv=None):
    parser = argparse.ArgumentParser(prog="single-cell-cell-type-annotator", description="CellType-Marker: Reference-Based scRNA-seq Marker Overlap & Annotation Agent")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Audit
    p_audit = subparsers.add_parser("audit", help="Run single task evaluation")
    p_audit.add_argument("--task-id", default="TASK-2026-001")
    p_audit.add_argument("--target", default="TARGET-GEN-01")
    p_audit.add_argument("--primary", type=float, default=29.4)
    p_audit.add_argument("--secondary", type=float, default=15.1)
    p_audit.add_argument("--critical", action="store_true")
    p_audit.add_argument("--status", default="DISCORDANT")

    # Chat
    p_chat = subparsers.add_parser("chat", help="System configuration query")
    p_chat.add_argument("query", nargs="+")

    # Batch
    p_batch = subparsers.add_parser("batch", help="Batch process CSV records")
    p_batch.add_argument("-i", "--input", required=True)
    p_batch.add_argument("-o", "--output", default="results.csv")

    # Serve
    p_serve = subparsers.add_parser("serve", help="Launch FastAPI REST server")
    p_serve.add_argument("--host", default="127.0.0.1")
    p_serve.add_argument("--port", type=int, default=8000)


    # Biological marker overlap annotation
    p_annotate = subparsers.add_parser("annotate", help="Annotate cluster marker genes against user-supplied reference signatures")
    p_annotate.add_argument("--markers", required=True, help="CSV columns: cluster,gene")
    p_annotate.add_argument("--references", required=True, help="CSV columns: cell_type,gene")
    p_annotate.add_argument("--universe", required=True, help="Text file of eligible background genes")
    p_annotate.add_argument("-o", "--output", default="annotations.csv")
    p_annotate.add_argument("--alpha", type=float, default=0.05)
    p_annotate.add_argument("--min-overlap", type=int, default=1)

    args = parser.parse_args(argv)


    if args.command == "annotate":
        def read_signatures(filename, label_column):
            groups = {}
            with open(filename, encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle, strict=True)
                if not {label_column, "gene"}.issubset(reader.fieldnames or []):
                    raise ValueError(f"{filename}: required headers are {label_column},gene")
                for i, row in enumerate(reader, start=2):
                    if i > 20002:
                        raise ValueError(f"{filename}: too many marker rows")
                    label, gene = row.get(label_column), row.get("gene")
                    if not label or not gene or None in row:
                        raise ValueError(f"{filename}: invalid row {i}")
                    groups.setdefault(label.strip(), []).append(gene.strip())
            return groups

        try:
            markers = read_signatures(args.markers, "cluster")
            references = read_signatures(args.references, "cell_type")
            with open(args.universe, encoding="utf-8-sig") as handle:
                genes = handle.read().replace(",", " ").split()
            if genes and genes[0].lower() == "gene":
                genes.pop(0)
            if len(genes) > 200000:
                raise ValueError("Universe exceeds 200000 genes")
            rows = annotate_clusters(markers, references, genes,
                                     alpha=args.alpha, min_overlap=args.min_overlap)
            fields = ["cluster", "cell_type", "overlap", "cluster_size", "reference_size",
                      "universe_size", "shared_genes", "p_value", "q_value",
                      "assignment", "is_best_match"]
            def safe_cell(value):
                if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
                    return "'" + value
                return value
            with open(args.output, "w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader()
                writer.writerows({key: safe_cell(row[key]) for key in fields} for row in rows)
        except (OSError, ValueError, csv.Error) as exc:
            print(f"Annotation error: {exc}", file=sys.stderr)
            return 1
        print(f"Compared {len(markers)} clusters against {len(references)} references; wrote {len(rows)} rows to {args.output}")
        return 0

    if args.command == "audit":
        payload = FrontierPayload(
            task_id=args.task_id,
            target_identifier=args.target,
            primary_metric=args.primary,
            secondary_metric=args.secondary,
            status_descriptor=args.status,
            is_critical_flag=args.critical,
        )
        dossier = coordinator.process(payload)
        print("=" * 80)
        print(f"  CELLTYPE-MARKER: REFERENCE-BASED SCRNA-SEQ MARKER OVERLAP & ANNOTATION AGENT")
        print(f"  Domain: Biomedical Scientific Discovery & Multi-Omics | Standard: Human Cell Atlas (HCA) Annotation Standards")
        print(f"  Task: {dossier['task_id']} | Status: [{dossier['overall_status']}] | Total Alerts: {dossier['total_alerts']}")
        print("=" * 80)
        for a in dossier["alerts"]:
            print(f"\n  [{a['status']}] from {a['origin_agent']}:")
            print(f"  Summary: {a['summary']}")
            print(f"  Details: {a['technical_details']}")
            print(f"  Action:  {a['actionable_remediation']}")
        print("\n" + "=" * 80)
        return 0

    if args.command == "chat":
        ans = coordinator.query_supervisory_chat(" ".join(args.query))
        print(f"\n[CellTypeAnnotatorCoordinator]:\n{ans}\n")
        return 0

    if args.command == "batch":
        try:
            with open(args.input, mode="r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                fieldnames = list(reader.fieldnames or [])
                rows = list(reader)
        except FileNotFoundError:
            print(f"Error: Input file '{args.input}' not found.", file=sys.stderr)
            return 1
        except PermissionError:
            print(f"Error: Permission denied reading '{args.input}'.", file=sys.stderr)
            return 1
        except csv.Error as e:
            print(f"Error: Malformed CSV in '{args.input}': {e}", file=sys.stderr)
            return 1

        out_fields = fieldnames + ["overall_status", "total_alerts", "critical_count", "consensus_summary"]
        out_rows = []
        skipped = 0
        for idx, r in enumerate(rows):
            try:
                payload = FrontierPayload(
                    task_id=r.get("task_id", "TASK-01"),
                    target_identifier=r.get("target_identifier", "TARGET-01"),
                    primary_metric=float(r.get("primary_metric", 15.0)),
                    secondary_metric=float(r.get("secondary_metric", 5.0)),
                    status_descriptor=r.get("status_descriptor", "NOMINAL"),
                    is_critical_flag=str(r.get("is_critical_flag", "")).lower() in ("true", "1", "yes"),
                )
            except (ValueError, TypeError) as e:
                print(f"Warning: Skipping row {idx + 1}: invalid data ({e})", file=sys.stderr)
                skipped += 1
                continue
            dossier = coordinator.process(payload)
            row_dict = dict(r)
            row_dict["overall_status"] = dossier["overall_status"]
            row_dict["total_alerts"] = dossier["total_alerts"]
            row_dict["critical_count"] = dossier["critical_count"]
            row_dict["consensus_summary"] = dossier["consensus_summary"]
            out_rows.append(row_dict)

        try:
            with open(args.output, mode="w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=out_fields)
                writer.writeheader()
                writer.writerows(out_rows)
        except PermissionError:
            print(f"Error: Permission denied writing '{args.output}'.", file=sys.stderr)
            return 1

        print(f"Processed {len(out_rows)} records -> {args.output}" + (f" ({skipped} skipped)" if skipped else ""))
        return 0

    if args.command == "serve":
        try:
            import uvicorn
            from .server import create_app
            app = create_app()
            if app:
                print(f"Starting CellType-Marker: Reference-Based scRNA-seq Marker Overlap & Annotation Agent on http://{args.host}:{args.port}")
                uvicorn.run(app, host=args.host, port=args.port)
        except ImportError:
            print("FastAPI / uvicorn not installed. Run 'pip install fastapi uvicorn'")
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
