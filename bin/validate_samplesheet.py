#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import re
import sys
from pathlib import Path


FASTA_EXTENSIONS = {".fa", ".fasta", ".fna", ".fas"}
FIELDNAMES = ["sample_id", "fasta", "role", "host_id", "accession"]


def sanitize_sample_id(value: str, fallback: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip())
    cleaned = cleaned.strip("._-")
    return cleaned or fallback


def is_fasta(path: Path) -> bool:
    return path.suffix.lower() in FASTA_EXTENSIONS


def fasta_summary(path: Path) -> tuple[int, int, str]:
    records = 0
    bases = 0
    digest = hashlib.sha256()
    seen_header = False
    with path.open() as handle:
        for raw in handle:
            line = raw.strip()
            if not line:
                continue
            if line.startswith(">"):
                records += 1
                seen_header = True
                digest.update(line.encode())
                digest.update(b"\n")
            else:
                if not seen_header:
                    raise ValueError(f"{path} does not look like FASTA; sequence appears before first header")
                seq = line.upper()
                bases += len(seq)
                digest.update(seq.encode())
    if records == 0 or bases == 0:
        raise ValueError(f"{path} has no FASTA records or no sequence bases")
    return records, bases, digest.hexdigest()


def rows_from_fasta(path: Path) -> list[dict[str, str]]:
    return [
        {
            "sample_id": sanitize_sample_id(path.stem, "sample_1"),
            "fasta": str(path.resolve()),
            "role": "query",
            "host_id": "",
            "accession": "",
        }
    ]


def rows_from_directory(path: Path) -> list[dict[str, str]]:
    fasta_files = sorted(p for p in path.iterdir() if p.is_file() and is_fasta(p))
    if not fasta_files:
        raise ValueError(f"No FASTA files found in directory: {path}")
    rows = []
    for index, fasta in enumerate(fasta_files, start=1):
        rows.append(
            {
                "sample_id": sanitize_sample_id(fasta.stem, f"sample_{index}"),
                "fasta": str(fasta.resolve()),
                "role": "query",
                "host_id": "",
                "accession": "",
            }
        )
    return rows


def rows_from_table(path: Path) -> list[dict[str, str]]:
    delimiter = "," if path.suffix.lower() == ".csv" else "\t"
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle, delimiter=delimiter)
        if not reader.fieldnames:
            raise ValueError(f"Samplesheet is empty: {path}")
        missing = {"sample_id", "fasta"} - set(reader.fieldnames)
        if missing:
            raise ValueError(f"Samplesheet missing required column(s): {', '.join(sorted(missing))}")
        rows = []
        for index, row in enumerate(reader, start=1):
            raw_fasta = (row.get("fasta") or "").strip()
            if not raw_fasta:
                raise ValueError(f"Row {index} has an empty fasta path")
            fasta_path = Path(raw_fasta)
            if not fasta_path.is_absolute():
                fasta_path = path.parent / fasta_path
            rows.append(
                {
                    "sample_id": sanitize_sample_id(row.get("sample_id") or "", f"sample_{index}"),
                    "fasta": str(fasta_path.resolve()),
                    "role": (row.get("role") or "query").strip() or "query",
                    "host_id": (row.get("host_id") or "").strip(),
                    "accession": (row.get("accession") or "").strip(),
                }
            )
    return rows


def load_rows(input_path: Path) -> list[dict[str, str]]:
    if input_path.is_dir():
        return rows_from_directory(input_path)
    if is_fasta(input_path):
        return rows_from_fasta(input_path)
    return rows_from_table(input_path)


def write_normalized(rows: list[dict[str, str]], path: Path) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in FIELDNAMES})


def write_summary(rows: list[dict[str, str]], summaries: list[dict[str, str]], path: Path) -> None:
    roles = {}
    for row in rows:
        roles[row["role"]] = roles.get(row["role"], 0) + 1
    total_bases = sum(int(item["bases"]) for item in summaries)
    with path.open("w", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(["metric", "value"])
        writer.writerow(["genomes", len(rows)])
        writer.writerow(["total_bases", total_bases])
        writer.writerow(["roles", ",".join(f"{key}:{value}" for key, value in sorted(roles.items()))])
        writer.writerow(["samples", ",".join(row["sample_id"] for row in rows)])


def validate(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    seen_ids = set()
    summaries = []
    for row in rows:
        sample_id = row["sample_id"]
        if sample_id in seen_ids:
            raise ValueError(f"Duplicate sample_id after sanitization: {sample_id}")
        seen_ids.add(sample_id)
        fasta = Path(row["fasta"])
        if not fasta.exists():
            raise ValueError(f"FASTA does not exist for {sample_id}: {fasta}")
        if not fasta.is_file():
            raise ValueError(f"FASTA is not a file for {sample_id}: {fasta}")
        records, bases, digest = fasta_summary(fasta)
        summaries.append(
            {
                "sample_id": sample_id,
                "records": str(records),
                "bases": str(bases),
                "sha256": digest,
            }
        )
    return summaries


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize and validate PhageFlow inputs.")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--outdir", required=True, type=Path)
    args = parser.parse_args()

    try:
        rows = load_rows(args.input)
        summaries = validate(rows)
        args.outdir.mkdir(parents=True, exist_ok=True)
        write_normalized(rows, args.outdir / "samplesheet.normalized.tsv")
        write_summary(rows, summaries, args.outdir / "validation_summary.tsv")
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

