#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from pathlib import Path


PAIR_FIELDS = [
    "query_id",
    "reference_id",
    "same_sequence_sha256",
    "kmer_jaccard",
    "kmer_interpretation",
    "blastn_similarity_score_pct",
    "blastn_mean_identity_pct",
    "blastn_aligned_fraction_min",
    "blastn_status",
    "duplicate_flag",
    "ranking_metric",
    "limitation",
]

NEAREST_FIELDS = [
    "query_id",
    "nearest_reference_id",
    "rank",
    "same_sequence_sha256",
    "kmer_jaccard",
    "blastn_similarity_score_pct",
    "duplicate_flag",
    "ranking_metric",
    "limitation",
]

LIMITATION = "Nearest local reference by PhageFlow software metrics only; not taxonomy or biological classification."


def read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    with path.open(newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle, delimiter="\t")]


def read_key_values(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    with path.open(newline="") as handle:
        reader = csv.reader(handle, delimiter="\t")
        next(reader, None)
        for row in reader:
            if len(row) >= 2:
                values[row[0]] = row[1]
    return values


def write_rows(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_key_values(path: Path, values: dict[str, str]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(["metric", "value"])
        for key, value in values.items():
            writer.writerow([key, value])


def pair_key(left: str, right: str) -> tuple[str, str]:
    return tuple(sorted((left, right)))


def to_float(value: str, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def find_kmer_column(rows: list[dict[str, str]]) -> str:
    if not rows:
        return ""
    for column in rows[0]:
        if column.startswith("kmer") and column.endswith("_jaccard"):
            return column
    return ""


def index_cohort_pairs(rows: list[dict[str, str]]) -> tuple[dict[tuple[str, str], dict[str, str]], str]:
    kmer_column = find_kmer_column(rows)
    indexed = {}
    for row in rows:
        left = row.get("sample_a", "")
        right = row.get("sample_b", "")
        if left and right:
            indexed[pair_key(left, right)] = row
    return indexed, kmer_column


def index_blastn_pairs(rows: list[dict[str, str]]) -> dict[tuple[str, str], dict[str, str]]:
    indexed = {}
    for row in rows:
        left = row.get("sample_a", "")
        right = row.get("sample_b", "")
        if left and right:
            indexed[pair_key(left, right)] = row
    return indexed


def role_is_reference(row: dict[str, str]) -> bool:
    return (row.get("role") or "").strip().lower() == "reference"


def ranking_value(pair: dict[str, str]) -> tuple[float, float]:
    blastn = pair.get("blastn_similarity_score_pct", "")
    kmer = pair.get("kmer_jaccard", "")
    if blastn:
        return to_float(blastn), to_float(kmer)
    return -1.0, to_float(kmer)


def ranking_metric(pair: dict[str, str]) -> str:
    return "blastn_similarity_score_pct_then_kmer_jaccard" if pair.get("blastn_similarity_score_pct") else "kmer_jaccard_only"


def build_reference_rows(
    samples: list[dict[str, str]],
    cohort_pairs: list[dict[str, str]],
    blastn_pairs: list[dict[str, str]],
    intergenomic_summary: dict[str, str],
) -> tuple[list[dict[str, str]], list[dict[str, str]], dict[str, str]]:
    queries = [row for row in samples if not role_is_reference(row)]
    references = [row for row in samples if role_is_reference(row)]
    cohort_index, kmer_column = index_cohort_pairs(cohort_pairs)
    blastn_index = index_blastn_pairs(blastn_pairs)

    pair_rows: list[dict[str, str]] = []
    for query in queries:
        query_id = query.get("sample_id", "")
        for reference in references:
            reference_id = reference.get("sample_id", "")
            if not query_id or not reference_id or query_id == reference_id:
                continue
            key = pair_key(query_id, reference_id)
            cohort = cohort_index.get(key, {})
            blastn = blastn_index.get(key, {})
            kmer_jaccard = cohort.get(kmer_column, "") if kmer_column else ""
            kmer_interpretation = cohort.get("interpretation", "")
            duplicate_flag = "true" if kmer_interpretation in {"exact_duplicate", "near_duplicate"} else "false"
            pair = {
                "query_id": query_id,
                "reference_id": reference_id,
                "same_sequence_sha256": cohort.get("same_sequence_sha256", ""),
                "kmer_jaccard": kmer_jaccard,
                "kmer_interpretation": kmer_interpretation,
                "blastn_similarity_score_pct": blastn.get("similarity_score_pct", ""),
                "blastn_mean_identity_pct": blastn.get("mean_identity_pct", ""),
                "blastn_aligned_fraction_min": blastn.get("aligned_fraction_min", ""),
                "blastn_status": blastn.get("status", ""),
                "duplicate_flag": duplicate_flag,
                "ranking_metric": "",
                "limitation": LIMITATION,
            }
            pair["ranking_metric"] = ranking_metric(pair)
            pair_rows.append(pair)

    nearest_rows: list[dict[str, str]] = []
    for query in queries:
        query_id = query.get("sample_id", "")
        candidates = [row for row in pair_rows if row["query_id"] == query_id]
        candidates.sort(key=ranking_value, reverse=True)
        for rank, row in enumerate(candidates[:1], start=1):
            nearest_rows.append(
                {
                    "query_id": query_id,
                    "nearest_reference_id": row["reference_id"],
                    "rank": str(rank),
                    "same_sequence_sha256": row["same_sequence_sha256"],
                    "kmer_jaccard": row["kmer_jaccard"],
                    "blastn_similarity_score_pct": row["blastn_similarity_score_pct"],
                    "duplicate_flag": row["duplicate_flag"],
                    "ranking_metric": row["ranking_metric"],
                    "limitation": LIMITATION,
                }
            )

    if not references:
        status = "skipped_no_references"
    elif not queries:
        status = "skipped_no_queries"
    elif not pair_rows:
        status = "skipped_no_query_reference_pairs"
    else:
        status = "completed"

    summary = {
        "method": "local_reference_context",
        "status": status,
        "queries": str(len(queries)),
        "references": str(len(references)),
        "query_reference_pairs": str(len(pair_rows)),
        "nearest_reference_rows": str(len(nearest_rows)),
        "intergenomic_status": intergenomic_summary.get("status", "not_available"),
        "ranking": "blastn_similarity_score_pct_then_kmer_jaccard",
        "limitation": LIMITATION,
    }
    return pair_rows, nearest_rows, summary


def write_note(path: Path) -> None:
    path.write_text(
        "# Local Reference Context\n\n"
        "PhageFlow compares non-reference genomes against genomes marked `role=reference` "
        "in the normalized samplesheet. Rankings use existing PhageFlow software metrics: "
        "BLASTN intergenomic similarity when available, with k-mer Jaccard as a tie-breaker "
        "or fallback. These tables provide local reference context only and are not taxonomy, "
        "host-range evidence, or biological classification.\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize local query/reference context from completed PhageFlow comparison tables.")
    parser.add_argument("--samplesheet", required=True, type=Path)
    parser.add_argument("--cohort-pairwise", required=True, type=Path)
    parser.add_argument("--intergenomic-pairs", required=True, type=Path)
    parser.add_argument("--intergenomic-summary", required=True, type=Path)
    parser.add_argument("--pairs", required=True, type=Path)
    parser.add_argument("--nearest", required=True, type=Path)
    parser.add_argument("--summary", required=True, type=Path)
    parser.add_argument("--note", required=True, type=Path)
    args = parser.parse_args()

    samples = read_rows(args.samplesheet)
    cohort_pairs = read_rows(args.cohort_pairwise)
    blastn_pairs = read_rows(args.intergenomic_pairs)
    intergenomic_summary = read_key_values(args.intergenomic_summary)
    pair_rows, nearest_rows, summary = build_reference_rows(samples, cohort_pairs, blastn_pairs, intergenomic_summary)

    write_rows(args.pairs, pair_rows, PAIR_FIELDS)
    write_rows(args.nearest, nearest_rows, NEAREST_FIELDS)
    write_key_values(args.summary, summary)
    write_note(args.note)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
