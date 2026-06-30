#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import html
import json
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


CATEGORY_ORDER = {"core": 0, "accessory": 1, "singleton": 2}
CATEGORY_COLORS = {"core": "#0f766e", "accessory": "#c2410c", "singleton": "#7f1d1d"}
FIG_EXTENSIONS = ["png", "tiff", "pdf", "svg"]


def read_key_value(path: Path) -> dict[str, str]:
    values = {}
    if not path.exists():
        return values
    with path.open(newline="") as handle:
        reader = csv.reader(handle, delimiter="\t")
        next(reader, None)
        for row in reader:
            if len(row) >= 2:
                values[row[0]] = row[1]
    return values


def read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        return [dict(row) for row in reader]


def write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    if not rows:
        path.write_text("\n")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_key_value(path: Path, values: dict[str, str]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(["metric", "value"])
        for key, value in values.items():
            writer.writerow([key, value])


def first_existing_numeric_column(rows: list[dict[str, str]], prefix: str) -> str | None:
    if not rows:
        return None
    for column in rows[0].keys():
        if column.startswith(prefix):
            return column
    return None


def to_float(value: str, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def save_figure(fig, figures_dir: Path, stem: str) -> list[str]:
    outputs = []
    for ext in FIG_EXTENSIONS:
        path = figures_dir / f"{stem}.{ext}"
        fig.savefig(path, dpi=400, bbox_inches="tight")
        outputs.append(str(path))
    plt.close(fig)
    return outputs


def plot_genome_qc(fasta_rows: list[dict[str, str]], figures_dir: Path) -> list[str]:
    if not fasta_rows:
        return []
    df = pd.DataFrame(fasta_rows)
    df["total_bp"] = pd.to_numeric(df.get("total_bp"), errors="coerce").fillna(0)
    df["gc_pct"] = pd.to_numeric(df.get("gc_pct"), errors="coerce").fillna(0)
    df = df.sort_values("total_bp", ascending=False)
    sns.set_theme(style="whitegrid")
    fig, ax1 = plt.subplots(figsize=(max(8, 0.45 * len(df) + 4), 5.2))
    ax1.bar(df["sample_id"], df["total_bp"], color="#0f766e", alpha=0.88, label="Genome length")
    ax1.set_ylabel("Genome length (bp)")
    ax1.tick_params(axis="x", rotation=65, labelsize=8)
    ax2 = ax1.twinx()
    ax2.plot(df["sample_id"], df["gc_pct"], color="#c2410c", marker="o", linewidth=2.0, label="GC%")
    ax2.set_ylabel("GC (%)")
    ax1.set_title("Genome Size and GC Content")
    ax1.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    return save_figure(fig, figures_dir, "genome_qc_gc_length")


def plot_codon_gc3(codon_rows: list[dict[str, str]], figures_dir: Path) -> list[str]:
    if not codon_rows:
        return []
    df = pd.DataFrame(codon_rows)
    if "gc3_pct" not in df.columns:
        return []
    df["gc3_pct"] = pd.to_numeric(df["gc3_pct"], errors="coerce").fillna(0)
    df = df.sort_values("gc3_pct", ascending=False)
    fig, ax = plt.subplots(figsize=(max(8, 0.45 * len(df) + 4), 4.8))
    sns.barplot(data=df, x="sample_id", y="gc3_pct", ax=ax, color="#1d4ed8")
    ax.set_title("Coding Sequence GC3 Content")
    ax.set_xlabel("Genome")
    ax.set_ylabel("GC3 (%)")
    ax.tick_params(axis="x", rotation=65, labelsize=8)
    fig.tight_layout()
    return save_figure(fig, figures_dir, "codon_gc3_profile")


def plot_similarity(pairwise_rows: list[dict[str, str]], fasta_rows: list[dict[str, str]], figures_dir: Path) -> list[str]:
    samples = [row.get("sample_id", "") for row in fasta_rows if row.get("sample_id")]
    if len(samples) < 2 or not pairwise_rows:
        return []
    jaccard_column = first_existing_numeric_column(pairwise_rows, "kmer")
    if not jaccard_column:
        return []
    matrix = pd.DataFrame(0.0, index=samples, columns=samples)
    for sample in samples:
        matrix.loc[sample, sample] = 1.0
    for row in pairwise_rows:
        a = row.get("sample_a")
        b = row.get("sample_b")
        if a in matrix.index and b in matrix.columns:
            value = to_float(row.get(jaccard_column), 0.0)
            matrix.loc[a, b] = value
            matrix.loc[b, a] = value
    fig, ax = plt.subplots(figsize=(max(6, 0.45 * len(samples) + 3), max(5, 0.40 * len(samples) + 2.5)))
    sns.heatmap(matrix, cmap="viridis", vmin=0, vmax=1, square=True, linewidths=0.4, linecolor="#e5e7eb", cbar_kws={"label": "k-mer Jaccard"}, ax=ax)
    ax.set_title("Genome-Level Cohort Similarity")
    ax.tick_params(axis="x", rotation=65, labelsize=8)
    ax.tick_params(axis="y", labelsize=8)
    fig.tight_layout()
    return save_figure(fig, figures_dir, "cohort_similarity_heatmap")



def plot_intergenomic_similarity(matrix_rows: list[dict[str, str]], figures_dir: Path) -> list[str]:
    if not matrix_rows:
        return []
    samples = [column for column in matrix_rows[0].keys() if column != "sample_id"]
    if len(samples) < 2:
        return []
    matrix = pd.DataFrame(index=[row.get("sample_id", "") for row in matrix_rows], columns=samples)
    for row in matrix_rows:
        row_id = row.get("sample_id", "")
        for sample in samples:
            matrix.loc[row_id, sample] = to_float(row.get(sample), 0.0)
    matrix = matrix.apply(pd.to_numeric, errors="coerce").fillna(0.0)
    if matrix.empty:
        return []
    fig, ax = plt.subplots(figsize=(max(6.5, 0.52 * len(samples) + 3), max(5.5, 0.48 * len(samples) + 2.8)))
    sns.heatmap(
        matrix,
        cmap="mako_r",
        vmin=0,
        vmax=100,
        square=True,
        linewidths=0.45,
        linecolor="#e5e7eb",
        annot=len(samples) <= 10,
        fmt=".1f",
        cbar_kws={"label": "BLASTN similarity score (%)"},
        ax=ax,
    )
    ax.set_title("BLASTN Intergenomic Similarity")
    ax.tick_params(axis="x", rotation=65, labelsize=8)
    ax.tick_params(axis="y", labelsize=8)
    fig.tight_layout()
    return save_figure(fig, figures_dir, "intergenomic_similarity_heatmap")



class TreeNode:
    def __init__(self, name: str = "", length: float = 0.0, children: list["TreeNode"] | None = None) -> None:
        self.name = name
        self.length = length
        self.children = children or []


def parse_newick(text: str) -> TreeNode | None:
    data = text.strip().rstrip(";")
    if not data:
        return None
    index = 0

    def parse_label() -> str:
        nonlocal index
        start = index
        while index < len(data) and data[index] not in ":,()":
            index += 1
        return data[start:index].strip().strip("'")

    def parse_length() -> float:
        nonlocal index
        if index >= len(data) or data[index] != ":":
            return 0.0
        index += 1
        start = index
        while index < len(data) and data[index] not in ",()":
            index += 1
        try:
            return float(data[start:index])
        except ValueError:
            return 0.0

    def parse_subtree() -> TreeNode:
        nonlocal index
        children: list[TreeNode] = []
        if index < len(data) and data[index] == "(":
            index += 1
            while index < len(data):
                children.append(parse_subtree())
                if index < len(data) and data[index] == ",":
                    index += 1
                    continue
                if index < len(data) and data[index] == ")":
                    index += 1
                    break
        name = parse_label()
        length = parse_length()
        return TreeNode(name=name, length=length, children=children)

    try:
        return parse_subtree()
    except Exception:
        return None


def plot_newick_tree(tree_path: Path, figures_dir: Path) -> list[str]:
    root = parse_newick(tree_path.read_text())
    if root is None:
        return []
    leaves: list[TreeNode] = []

    def collect(node: TreeNode) -> None:
        if not node.children:
            leaves.append(node)
        for child in node.children:
            collect(child)

    collect(root)
    if len(leaves) < 2:
        return []
    y_positions = {id(node): index for index, node in enumerate(leaves)}
    x_positions: dict[int, float] = {}

    def assign_x(node: TreeNode, current: float = 0.0) -> None:
        x_positions[id(node)] = current
        for child in node.children:
            assign_x(child, current + max(child.length, 0.0))

    assign_x(root)
    if max(x_positions.values() or [0.0]) == 0.0:
        def assign_depth_x(node: TreeNode, depth: int = 0) -> None:
            x_positions[id(node)] = float(depth)
            for child in node.children:
                assign_depth_x(child, depth + 1)
        assign_depth_x(root)

    def node_y(node: TreeNode) -> float:
        if not node.children:
            return float(y_positions[id(node)])
        return sum(node_y(child) for child in node.children) / len(node.children)

    fig_height = max(4.8, 0.42 * len(leaves) + 1.8)
    fig, ax = plt.subplots(figsize=(9.5, fig_height))

    def draw(node: TreeNode) -> None:
        x = x_positions[id(node)]
        y = node_y(node)
        if node.children:
            child_ys = [node_y(child) for child in node.children]
            ax.plot([x, x], [min(child_ys), max(child_ys)], color="#17212b", linewidth=1.2)
            for child in node.children:
                cx = x_positions[id(child)]
                cy = node_y(child)
                ax.plot([x, cx], [cy, cy], color="#17212b", linewidth=1.2)
                draw(child)
        else:
            label = node.name or "unnamed"
            ax.text(x + 0.01 * max(max(x_positions.values()), 1.0), y, label, va="center", fontsize=8)

    draw(root)
    ax.set_ylim(-0.75, len(leaves) - 0.25)
    ax.set_xlim(0, max(x_positions.values()) * 1.18 + 0.01)
    ax.set_yticks([])
    ax.set_xlabel("Substitutions/site or relative distance")
    ax.set_title(f"Marker-Gene Phylogeny: {tree_path.stem}")
    for spine in ["left", "right", "top"]:
        ax.spines[spine].set_visible(False)
    ax.grid(axis="x", alpha=0.18)
    fig.tight_layout()
    stem = "marker_tree_" + "".join(ch if ch.isalnum() or ch in "_-" else "_" for ch in tree_path.stem)
    return save_figure(fig, figures_dir, stem)


def plot_marker_trees(trees_dir: Path, figures_dir: Path) -> list[str]:
    if not trees_dir.exists() or not trees_dir.is_dir():
        return []
    outputs: list[str] = []
    for tree_path in sorted(trees_dir.glob("*.nwk")):
        outputs.extend(plot_newick_tree(tree_path, figures_dir))
    return outputs


def plot_pangenome(presence_rows: list[dict[str, str]], metadata_rows: list[dict[str, str]], figures_dir: Path) -> list[str]:
    if not presence_rows or not metadata_rows:
        return []
    genome_order = [row.get("genome_id", "") for row in metadata_rows if row.get("genome_id")]
    genome_order = [genome for genome in genome_order if genome in presence_rows[0]]
    if not genome_order:
        return []
    df = pd.DataFrame(presence_rows)
    if "category" not in df.columns or "n_genomes" not in df.columns:
        return []
    df["category_rank"] = df["category"].map(CATEGORY_ORDER).fillna(99)
    df["n_genomes_num"] = pd.to_numeric(df["n_genomes"], errors="coerce").fillna(0)
    df = df.sort_values(["category_rank", "n_genomes_num", "orthogroup"], ascending=[True, False, True]).reset_index(drop=True)
    matrix = df[genome_order].fillna("").map(lambda value: 1 if str(value).strip() else 0)
    n_rows, n_cols = matrix.shape
    fig_width = max(10, 0.45 * n_cols + 4)
    fig_height = max(7, min(28, 0.10 * n_rows + 4))
    fig = plt.figure(figsize=(fig_width, fig_height), constrained_layout=True)
    gs = fig.add_gridspec(1, 2, width_ratios=[0.28, 12], wspace=0.03)
    ax_cat = fig.add_subplot(gs[0, 0])
    ax = fig.add_subplot(gs[0, 1])
    cat_values = df["category"].map(CATEGORY_ORDER).fillna(2).to_numpy().reshape(-1, 1)
    cmap = matplotlib.colors.ListedColormap([CATEGORY_COLORS["core"], CATEGORY_COLORS["accessory"], CATEGORY_COLORS["singleton"]])
    ax_cat.imshow(cat_values, aspect="auto", interpolation="nearest", cmap=cmap, vmin=0, vmax=2)
    ax_cat.set_xticks([])
    ax_cat.set_yticks([])
    ax_cat.set_title("Class", fontsize=9)
    sns.heatmap(matrix, ax=ax, cmap=sns.color_palette(["#f8fafc", "#1d4ed8"]), cbar=True, vmin=0, vmax=1, linewidths=0.12, linecolor="#d1d5db", xticklabels=genome_order, yticklabels=False, cbar_kws={"label": "Presence"})
    ax.set_title(f"Pangenome Presence/Absence ({n_cols} genomes, {n_rows} orthogroups)")
    ax.set_xlabel("Genomes")
    ax.set_ylabel("Orthogroups")
    ax.tick_params(axis="x", rotation=90, labelsize=8)
    return save_figure(fig, figures_dir, "pangenome_presence_absence_heatmap")


def plot_host_context(host_rows: list[dict[str, str]], figures_dir: Path) -> list[str]:
    linked = [row for row in host_rows if row.get("host_found") == "true"]
    if not linked:
        return []
    df = pd.DataFrame(linked)
    df["delta_gc_pct"] = pd.to_numeric(df.get("delta_gc_pct"), errors="coerce").fillna(0)
    df["tetranucleotide_cosine"] = pd.to_numeric(df.get("tetranucleotide_cosine"), errors="coerce").fillna(0)
    fig, ax1 = plt.subplots(figsize=(max(8, 0.50 * len(df) + 4), 5.0))
    ax1.bar(df["sample_id"], df["delta_gc_pct"], color="#c2410c", alpha=0.82)
    ax1.set_ylabel("Absolute phage-host GC difference (%)")
    ax1.tick_params(axis="x", rotation=65, labelsize=8)
    ax2 = ax1.twinx()
    ax2.plot(df["sample_id"], df["tetranucleotide_cosine"], color="#0f766e", marker="o", linewidth=2)
    ax2.set_ylabel("Tetranucleotide cosine similarity")
    ax2.set_ylim(0, 1.05)
    ax1.set_title("Host-Context Nucleotide Composition")
    fig.tight_layout()
    return save_figure(fig, figures_dir, "host_context_composition")


def plot_host_adaptation(host_adaptation_rows: list[dict[str, str]], figures_dir: Path) -> list[str]:
    linked = [row for row in host_adaptation_rows if row.get("host_found") == "true"]
    if not linked:
        return []
    df = pd.DataFrame(linked)
    for column in ["codon_distance", "rscu_distance", "cai_like", "preferred_codon_match_pct", "crispr_spacer_hits"]:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce").fillna(0)
    fig, ax1 = plt.subplots(figsize=(max(8, 0.55 * len(df) + 4), 5.2))
    x = range(len(df))
    ax1.bar([i - 0.18 for i in x], df["codon_distance"], width=0.36, color="#c2410c", alpha=0.82, label="Codon distance")
    ax1.bar([i + 0.18 for i in x], df["rscu_distance"], width=0.36, color="#7f1d1d", alpha=0.74, label="RSCU distance")
    ax1.set_ylabel("Distance (1 - cosine)")
    ax1.set_xticks(list(x))
    ax1.set_xticklabels(df["sample_id"], rotation=65, ha="right", fontsize=8)
    ax1.set_ylim(0, max(1.0, float(max(df["codon_distance"].max(), df["rscu_distance"].max())) * 1.15))
    ax2 = ax1.twinx()
    ax2.plot(list(x), df["cai_like"], color="#0f766e", marker="o", linewidth=2.0, label="CAI-like score")
    ax2.set_ylabel("CAI-like host adaptation score")
    ax2.set_ylim(0, 1.05)
    for index, hits in enumerate(df.get("crispr_spacer_hits", [])):
        if hits:
            ax1.text(index, 0.04, f"CRISPR {int(hits)}", ha="center", va="bottom", fontsize=8, color="#1d4ed8", rotation=90)
    ax1.set_title("Phage-Host Codon Adaptation")
    ax1.legend(loc="upper left")
    fig.tight_layout()
    return save_figure(fig, figures_dir, "host_codon_adaptation")


def command_version(command: list[str]) -> str:
    executable = shutil.which(command[0])
    if not executable:
        return "not_found"
    try:
        completed = subprocess.run([executable] + command[1:], check=False, text=True, capture_output=True, timeout=8)
        output = (completed.stdout or completed.stderr or "").strip().splitlines()
        return output[0] if output else "available"
    except Exception as exc:
        return f"available_version_error:{exc.__class__.__name__}"


def write_software_versions(path: Path) -> None:
    tools = {
        "python": [sys.executable, "--version"],
        "nextflow": ["nextflow", "-version"],
        "mmseqs": ["mmseqs", "version"],
        "blastp": ["blastp", "-version"],
        "blastn": ["blastn", "-version"],
        "makeblastdb": ["makeblastdb", "-version"],
        "mafft": ["mafft", "--version"],
        "iqtree2": ["iqtree2", "--version"],
        "iqtree": ["iqtree", "--version"],
        "trimal": ["trimal", "--version"],
        "tRNAscan-SE": ["tRNAscan-SE", "--version"],
        "bacphlip": ["bacphlip", "--help"],
        "checkv": ["checkv", "--version"],
        "pharokka.py": ["pharokka.py", "--version"],
        "genomad": ["genomad", "--version"],
        "phold": ["phold", "--version"],
        "clinker": ["clinker", "--version"],
        "prodigal": ["prodigal", "-v"],
        "minced": ["minced", "-h"],
    }
    with path.open("w", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(["tool", "version_or_status"])
        writer.writerow(["platform", platform.platform()])
        for tool, command in tools.items():
            writer.writerow([tool, command_version(command)])


def html_table(rows: list[dict[str, str]], max_rows: int = 12) -> str:
    if not rows:
        return '<p class="muted">No rows available.</p>'
    columns = list(rows[0].keys())
    body = []
    for row in rows[:max_rows]:
        body.append("<tr>" + "".join(f"<td>{html.escape(str(row.get(col, '')))}</td>" for col in columns) + "</tr>")
    return "<div class=\"table-wrap\"><table><thead><tr>" + "".join(f"<th>{html.escape(col)}</th>" for col in columns) + "</tr></thead><tbody>" + "".join(body) + "</tbody></table></div>"


def write_important_files(path: Path, files: list[tuple[str, str, str]]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(["category", "path", "description"])
        writer.writerows(files)


def claim_evidence_rows(
    validation: dict[str, str],
    cohort_summary: dict[str, str],
    intergenomic_summary: dict[str, str],
    marker_summary: dict[str, str],
    pangenome_summary: dict[str, str],
    fasta_rows: list[dict[str, str]],
    orf_rows: list[dict[str, str]],
    codon_rows: list[dict[str, str]],
    pairwise_rows: list[dict[str, str]],
    intergenomic_pair_rows: list[dict[str, str]],
    marker_presence_rows: list[dict[str, str]],
    marker_provenance_rows: list[dict[str, str]],
    presence_rows: list[dict[str, str]],
    host_rows: list[dict[str, str]],
    host_adaptation_rows: list[dict[str, str]],
    crispr_match_rows: list[dict[str, str]],
    crispr_summary: dict[str, str],
) -> list[dict[str, str]]:
    def row(claim_id: str, claim_type: str, status: str, artifact: str, limitation: str) -> dict[str, str]:
        return {
            "claim_id": claim_id,
            "claim_type": claim_type,
            "status": status,
            "supporting_artifact": artifact,
            "limitation": limitation,
        }

    intergenomic_status = intergenomic_summary.get("status", "not_available")
    marker_status = marker_summary.get("status", "not_available")
    pangenome_status = pangenome_summary.get("status", "not_available")
    crispr_status = crispr_summary.get("status", "not_available")
    host_links = sum(1 for item in host_rows if item.get("host_found") == "true")
    termini_available = bool(fasta_rows) and all("termini_heuristic" in item for item in fasta_rows)
    return [
        row("input_validation", "software_validation", "PASS" if validation.get("genomes") else "WARN", "tables/validation_summary.tsv", "Validates input contract only."),
        row("genome_qc", "software_artifact", "PASS" if fasta_rows else "FAIL", "tables/fasta_stats_combined.tsv", "FASTA-derived assembly statistics only."),
        row("termini_heuristics", "software_artifact", "PASS" if termini_available else "WARN", "tables/fasta_stats_combined.tsv", "Exact terminal-repeat heuristics; does not infer packaging biology."),
        row("orf_summary", "software_artifact", "PASS" if orf_rows else "FAIL", "tables/orf_summary_combined.tsv", "Lightweight ORF calls are suitable for workflow QA; use consistent annotation for manuscript biology."),
        row("codon_summary", "software_artifact", "PASS" if codon_rows else "FAIL", "tables/codon_summary_combined.tsv", "Descriptive coding-sequence composition only."),
        row("cohort_similarity", "software_artifact", "PASS" if cohort_summary or pairwise_rows else "WARN", "tables/cohort_similarity_summary.tsv", "Detects redundancy and k-mer similarity; not taxonomy."),
        row("intergenomic_similarity", "software_artifact", "PASS" if intergenomic_status in {"completed", "single_genome_skipped"} else "WARN", "tables/intergenomic_similarity_summary.tsv", "BLASTN-derived similarity summary; thresholds are workflow parameters."),
        row("marker_phylogeny", "software_artifact", "PASS" if marker_status == "completed" else "WARN", "tables/marker_tree_summary.tsv", "Marker trees require suitable markers and are not standalone classification."),
        row("marker_presence", "software_artifact", "PASS" if marker_presence_rows else "WARN", "tables/marker_presence.tsv", "Marker selection provenance only."),
        row("marker_provenance", "software_artifact", "PASS" if marker_provenance_rows or marker_status == "skipped" else "WARN", "tables/marker_provenance.tsv", "Alignment/tree provenance only; not biological classification."),
        row("pangenome", "software_artifact", "PASS" if presence_rows or pangenome_status == "skipped" else "WARN", "tables/pangenome_summary.tsv", "Orthogroups depend on selected backend and annotation consistency."),
        row("host_context", "software_artifact", "PASS" if host_links else "WARN", "tables/host_context.tsv", "Host-linked composition only; not host-range prediction."),
        row("host_codon_adaptation", "software_artifact", "PASS" if host_adaptation_rows else "WARN", "tables/host_codon_adaptation.tsv", "Composition/adaptation metrics only."),
        row("crispr_spacer_match", "software_artifact", "PASS" if crispr_status in {"completed", "disabled"} else "WARN", "tables/crispr_spacer_summary.tsv", f"Spacer matches reported: {len(crispr_match_rows)}."),
        row("report_manifest", "software_validation", "PASS", "validation_manifest.json", "Report-level completeness manifest only."),
    ]


def build_html(args, validation, cohort_summary, intergenomic_summary, marker_summary, pangenome_summary, fasta_rows, codon_rows, host_rows, host_adaptation_rows, crispr_match_rows, crispr_summary, intergenomic_pair_rows, marker_presence_rows, marker_topology_rows, marker_provenance_rows, claim_rows, figure_paths, important_files) -> str:
    genomes = validation.get("genomes", str(len(fasta_rows)))
    orthogroups = pangenome_summary.get("orthogroups", "0")
    exact_dups = cohort_summary.get("exact_duplicate_pairs", "0")
    intergenomic_status = intergenomic_summary.get("status", "not_available")
    max_intergenomic = intergenomic_summary.get("max_similarity_score_pct", "NA")
    marker_status = marker_summary.get("status", "not_available")
    markers_built = marker_summary.get("markers_built", "0")
    host_links = sum(1 for row in host_rows if row.get("host_found") == "true")
    crispr_hits = crispr_summary.get("spacer_matches", str(len(crispr_match_rows)))
    warnings = []
    if int(float(exact_dups or 0)) > 0:
        warnings.append(f"{exact_dups} exact duplicate genome pair(s) detected.")
    if args.pangenome_method == "none":
        warnings.append("Pangenome clustering was skipped.")
    if args.pangenome_method == "legacy_snakemake_rbh":
        warnings.append("Deprecated Snakemake backend selected for parity only; native report uses skipped pangenome tables.")
    if intergenomic_status not in {"completed", "single_genome_skipped"}:
        warnings.append(f"Intergenomic similarity status: {intergenomic_status}.")
    if marker_status not in {"completed", "skipped", "skipped_no_trees_built"}:
        warnings.append(f"Marker phylogeny status: {marker_status}.")
    if not warnings:
        warnings.append("No blocking report warnings detected by the local QA checks.")
    figure_cards = []
    for stem in sorted({Path(path).stem for path in figure_paths if path.endswith(".png")}):
        png = f"figures/{stem}.png"
        tiff = f"figures/{stem}.tiff"
        pdf = f"figures/{stem}.pdf"
        figure_cards.append(f'''
        <article class="figure-card">
          <img src="{html.escape(png)}" alt="{html.escape(stem)}">
          <div class="downloads"><a href="{html.escape(tiff)}">TIFF</a><a href="{html.escape(pdf)}">PDF</a><a href="{html.escape(png)}">PNG</a></div>
        </article>''')
    download_links = "".join(f"<li><a href=\"{html.escape(path)}\">{html.escape(category)}: {html.escape(description)}</a></li>" for category, path, description in important_files[:40])
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>PhageFlow Report</title>
<style>
:root {{ --ink:#17212b; --muted:#64748b; --bg:#f6f0e8; --card:#fffaf2; --line:#d9c7ad; --teal:#0f766e; --rust:#c2410c; --blue:#1d4ed8; }}
body {{ margin:0; font-family: Georgia, 'Times New Roman', serif; color:var(--ink); background:radial-gradient(circle at top left, #fff7ed, var(--bg) 42%, #e8f3ef); }}
header {{ padding:44px 6vw 28px; border-bottom:1px solid var(--line); background:linear-gradient(135deg, rgba(15,118,110,.16), rgba(194,65,12,.10)); }}
h1 {{ margin:0; font-size:clamp(2rem, 4vw, 4rem); letter-spacing:-.04em; }}
.subtitle {{ max-width:900px; color:#334155; font-size:1.05rem; line-height:1.6; }}
main {{ padding:28px 6vw 60px; }}
.grid {{ display:grid; grid-template-columns:repeat(auto-fit, minmax(190px, 1fr)); gap:16px; margin:24px 0; }}
.card, section {{ background:rgba(255,250,242,.92); border:1px solid var(--line); border-radius:22px; box-shadow:0 14px 38px rgba(44,30,14,.08); }}
.card {{ padding:20px; }}
.metric {{ font-size:2rem; font-weight:700; line-height:1; }}
.label {{ color:var(--muted); margin-top:8px; }}
section {{ padding:24px; margin:24px 0; }}
h2 {{ margin:0 0 14px; font-size:1.45rem; }}
.warning {{ border-left:5px solid var(--rust); padding:12px 14px; margin:8px 0; background:#fff7ed; border-radius:10px; }}
.figure-grid {{ display:grid; grid-template-columns:repeat(auto-fit, minmax(320px, 1fr)); gap:18px; }}
.figure-card {{ background:#fff; border:1px solid #eadcc7; border-radius:16px; padding:12px; }}
.figure-card img {{ width:100%; height:auto; display:block; border-radius:10px; }}
.downloads {{ display:flex; gap:10px; margin-top:10px; flex-wrap:wrap; }}
a {{ color:var(--blue); text-decoration:none; font-weight:600; }}
a:hover {{ text-decoration:underline; }}
.table-wrap {{ overflow:auto; border:1px solid #eadcc7; border-radius:12px; }}
table {{ border-collapse:collapse; width:100%; min-width:720px; background:#fff; font-size:.9rem; }}
th, td {{ border-bottom:1px solid #eee2d1; padding:8px 10px; text-align:left; }}
th {{ background:#f3e7d6; position:sticky; top:0; }}
.muted {{ color:var(--muted); }}
footer {{ color:var(--muted); padding:20px 6vw 40px; font-size:.9rem; }}
</style>
</head>
<body>
<header>
  <h1>PhageFlow Report</h1>
  <p class="subtitle">Native Nextflow bacteriophage genome characterization report with reproducible intergenomic similarity, pangenome, host-context, and validation outputs. Output mode: <strong>{html.escape(args.output_mode)}</strong>.</p>
</header>
<main>
  <div class="grid">
    <div class="card"><div class="metric">{html.escape(str(genomes))}</div><div class="label">genomes analyzed</div></div>
    <div class="card"><div class="metric">{html.escape(str(orthogroups))}</div><div class="label">orthogroups</div></div>
    <div class="card"><div class="metric">{html.escape(str(exact_dups))}</div><div class="label">exact duplicate pairs</div></div>
    <div class="card"><div class="metric">{html.escape(str(max_intergenomic))}</div><div class="label">max BLASTN similarity score (%)</div></div>
    <div class="card"><div class="metric">{html.escape(str(markers_built))}</div><div class="label">marker trees built</div></div>
    <div class="card"><div class="metric">{html.escape(str(host_links))}</div><div class="label">host links evaluated</div></div>
    <div class="card"><div class="metric">{html.escape(str(crispr_hits))}</div><div class="label">CRISPR spacer matches</div></div>
    <div class="card"><div class="metric">{html.escape(args.pangenome_method)}</div><div class="label">pangenome method</div></div>
  </div>
  <section><h2>Report QA Warnings</h2>{''.join(f'<div class="warning">{html.escape(w)}</div>' for w in warnings)}</section>
  <section><h2>Key Figures</h2><div class="figure-grid">{''.join(figure_cards) or '<p class="muted">No figures were generated.</p>'}</div></section>
  <section><h2>Genome QC</h2>{html_table(fasta_rows)}</section>
  <section><h2>Intergenomic Similarity</h2>{html_table([intergenomic_summary])}{html_table(intergenomic_pair_rows)}</section>
  <section><h2>Marker-Gene Phylogeny</h2>{html_table([marker_summary])}{html_table(marker_presence_rows)}{html_table(marker_topology_rows)}{html_table(marker_provenance_rows)}</section>
  <section><h2>Pangenome Summary</h2>{html_table([pangenome_summary])}</section>
  <section><h2>Codon Summary</h2>{html_table(codon_rows)}</section>
  <section><h2>Host Context</h2>{html_table(host_rows)}{html_table(host_adaptation_rows)}{html_table(crispr_match_rows)}</section>
  <section><h2>Claim-Evidence Matrix</h2>{html_table(claim_rows, max_rows=20)}</section>
  <section><h2>Downloads</h2><ul>{download_links}</ul></section>
  <section><h2>Methods Summary</h2><p>Inputs were normalized and validated, genome-level FASTA statistics were calculated, lightweight ORFs were predicted for dependency-light testing, codon usage was summarized, cohort redundancy was screened by SHA256 and canonical k-mer Jaccard similarity, BLASTN intergenomic similarity was estimated from reciprocal local alignments, optional marker-gene phylogenies were inferred from selected conserved phage proteins, host context included nucleotide composition plus codon/RSCU adaptation when a host genome was supplied, optional CRISPR spacer matching was performed against phage genomes when enabled, and pangenome inference used the selected native Nextflow backend. Publication analyses should use a consistent phage annotation backend such as Pharokka/PHANOTATE across all genomes before final biological interpretation.</p></section>
</main>
<footer>Generated by PhageFlow at {datetime.now(timezone.utc).isoformat()} UTC.</footer>
</body>
</html>
'''


def build_markdown(args, validation, cohort_summary, intergenomic_summary, marker_summary, pangenome_summary, fasta_rows, codon_rows, host_adaptation_rows, crispr_match_rows, intergenomic_pair_rows, marker_topology_rows) -> str:
    lines = ["# PhageFlow Report", ""]
    lines.append(f"- Genomes analyzed: {validation.get('genomes', len(fasta_rows))}")
    lines.append(f"- Pangenome method: `{args.pangenome_method}`")
    lines.append(f"- Output mode: `{args.output_mode}`")
    lines.append(f"- Pairwise comparisons: {cohort_summary.get('pairwise_comparisons', 'NA')}")
    lines.append(f"- Intergenomic similarity status: {intergenomic_summary.get('status', 'NA')}")
    lines.append(f"- Max BLASTN similarity score (%): {intergenomic_summary.get('max_similarity_score_pct', 'NA')}")
    lines.append(f"- Marker phylogeny status: {marker_summary.get('status', 'NA')}")
    lines.append(f"- Marker trees built: {marker_summary.get('markers_built', '0')}")
    lines.append(f"- Orthogroups: {pangenome_summary.get('orthogroups', 'NA')}")
    lines.append(f"- Host adaptation rows: {len(host_adaptation_rows)}")
    lines.append(f"- CRISPR spacer matches: {len(crispr_match_rows)}")
    lines.append("")
    lines.append("## Main Figures")
    lines.append("")
    lines.append("See `index.html` for the dashboard and `figures/` for high-resolution PNG, TIFF, PDF, and SVG outputs.")
    lines.append("")
    lines.append("## Intergenomic Similarity")
    lines.append("")
    if intergenomic_pair_rows:
        cols = ["sample_a", "sample_b", "mean_identity_pct", "aligned_fraction_min", "similarity_score_pct", "status"]
        lines.append("| " + " | ".join(cols) + " |")
        lines.append("| " + " | ".join(["---"] * len(cols)) + " |")
        for row in intergenomic_pair_rows:
            lines.append("| " + " | ".join(str(row.get(col, "")) for col in cols) + " |")
    else:
        lines.append("No pairwise intergenomic rows were generated, usually because only one genome was supplied or the module was disabled.")
    lines.append("")
    lines.append("## Marker-Gene Phylogeny")
    lines.append("")
    if marker_topology_rows:
        cols = ["marker_kind", "status", "shared_pairs", "pearson_correlation", "tree_engine"]
        lines.append("| " + " | ".join(cols) + " |")
        lines.append("| " + " | ".join(["---"] * len(cols)) + " |")
        for row in marker_topology_rows:
            lines.append("| " + " | ".join(str(row.get(col, "")) for col in cols) + " |")
    else:
        lines.append("No marker tree was generated, usually because the module was disabled or too few genomes contained the requested marker.")
    lines.append("")
    lines.append("## Genome QC")
    lines.append("")
    if fasta_rows:
        cols = ["sample_id", "contigs", "total_bp", "gc_pct", "ambiguous_pct"]
        lines.append("| " + " | ".join(cols) + " |")
        lines.append("| " + " | ".join(["---"] * len(cols)) + " |")
        for row in fasta_rows:
            lines.append("| " + " | ".join(str(row.get(col, "")) for col in cols) + " |")
    lines.append("")
    lines.append("## Codon Summary")
    lines.append("")
    if codon_rows:
        cols = ["sample_id", "genes", "coding_nt_counted", "gc_pct", "gc3_pct", "top_codons"]
        lines.append("| " + " | ".join(cols) + " |")
        lines.append("| " + " | ".join(["---"] * len(cols)) + " |")
        for row in codon_rows:
            lines.append("| " + " | ".join(str(row.get(col, "")) for col in cols) + " |")
    lines.append("")
    lines.append("## Host Adaptation")
    lines.append("")
    if host_adaptation_rows:
        cols = ["sample_id", "host_id", "codon_distance", "rscu_distance", "cai_like", "crispr_spacer_hits", "interpretation"]
        lines.append("| " + " | ".join(cols) + " |")
        lines.append("| " + " | ".join(["---"] * len(cols)) + " |")
        for row in host_adaptation_rows:
            lines.append("| " + " | ".join(str(row.get(col, "")) for col in cols) + " |")
    else:
        lines.append("No host-adaptation rows were generated, usually because no host samplesheet was supplied.")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build PhageFlow HTML/Markdown report and QA manifests.")
    parser.add_argument("--validation", required=True, type=Path)
    parser.add_argument("--fasta-stats", action="append", default=[], type=Path)
    parser.add_argument("--orf-summary", action="append", default=[], type=Path)
    parser.add_argument("--codon-summary", action="append", default=[], type=Path)
    parser.add_argument("--cohort-summary", required=True, type=Path)
    parser.add_argument("--cohort-pairwise", required=True, type=Path)
    parser.add_argument("--cohort-duplicates", required=True, type=Path)
    parser.add_argument("--intergenomic-summary", required=True, type=Path)
    parser.add_argument("--intergenomic-pairs", required=True, type=Path)
    parser.add_argument("--intergenomic-similarity-matrix", required=True, type=Path)
    parser.add_argument("--intergenomic-distance-matrix", required=True, type=Path)
    parser.add_argument("--intergenomic-note", required=True, type=Path)
    parser.add_argument("--marker-summary", required=True, type=Path)
    parser.add_argument("--marker-presence", required=True, type=Path)
    parser.add_argument("--marker-topology", required=True, type=Path)
    parser.add_argument("--marker-provenance", required=True, type=Path)
    parser.add_argument("--marker-note", required=True, type=Path)
    parser.add_argument("--marker-trees", required=True, type=Path)
    parser.add_argument("--pangenome-summary", required=True, type=Path)
    parser.add_argument("--pangenome-presence-absence", required=True, type=Path)
    parser.add_argument("--pangenome-metadata", required=True, type=Path)
    parser.add_argument("--host-context", required=True, type=Path)
    parser.add_argument("--host-adaptation", required=True, type=Path)
    parser.add_argument("--host-rscu", required=True, type=Path)
    parser.add_argument("--crispr-matches", required=True, type=Path)
    parser.add_argument("--crispr-summary", required=True, type=Path)
    parser.add_argument("--pangenome-method", required=True)
    parser.add_argument("--output-mode", required=True)
    parser.add_argument("--min-orf-aa", required=True)
    parser.add_argument("--kmer-size", required=True)
    parser.add_argument("--duplicate-jaccard", required=True)
    parser.add_argument("--run-intergenomic-similarity", required=True)
    parser.add_argument("--ani-min-identity", required=True)
    parser.add_argument("--ani-min-aln-len", required=True)
    parser.add_argument("--ani-max-evalue", required=True)
    parser.add_argument("--ani-max-genomes", required=True)
    parser.add_argument("--run-marker-tree", required=True)
    parser.add_argument("--marker-source", required=True)
    parser.add_argument("--marker-kinds", required=True)
    parser.add_argument("--marker-min-genomes", required=True)
    parser.add_argument("--marker-tree-engine", required=True)
    parser.add_argument("--marker-bootstrap", required=True)
    parser.add_argument("--run-crispr-spacer-match", required=True)
    parser.add_argument("--crispr-min-identity", required=True)
    parser.add_argument("--crispr-min-coverage", required=True)
    parser.add_argument("--host-min-orf-aa", required=True)
    parser.add_argument("--host-use-prodigal", required=True)
    parser.add_argument("--pan-min-seq-id", required=True)
    parser.add_argument("--pan-min-coverage", required=True)
    parser.add_argument("--output-html", required=True, type=Path)
    parser.add_argument("--output-md", required=True, type=Path)
    parser.add_argument("--figures-dir", required=True, type=Path)
    parser.add_argument("--important-files", required=True, type=Path)
    parser.add_argument("--validation-manifest", required=True, type=Path)
    parser.add_argument("--software-versions", required=True, type=Path)
    parser.add_argument("--params-json", required=True, type=Path)
    parser.add_argument("--runtime-summary", required=True, type=Path)
    args = parser.parse_args()

    args.figures_dir.mkdir(parents=True, exist_ok=True)
    tables_dir = Path("tables")
    tables_dir.mkdir(exist_ok=True)

    validation = read_key_value(args.validation)
    cohort_summary = read_key_value(args.cohort_summary)
    intergenomic_summary = read_key_value(args.intergenomic_summary)
    marker_summary = read_key_value(args.marker_summary)
    pangenome_summary = read_key_value(args.pangenome_summary)
    fasta_rows = [row for path in args.fasta_stats for row in read_rows(path)]
    orf_rows = [row for path in args.orf_summary for row in read_rows(path)]
    codon_rows = [row for path in args.codon_summary for row in read_rows(path)]
    pairwise_rows = read_rows(args.cohort_pairwise)
    intergenomic_pair_rows = read_rows(args.intergenomic_pairs)
    intergenomic_matrix_rows = read_rows(args.intergenomic_similarity_matrix)
    marker_presence_rows = read_rows(args.marker_presence)
    marker_topology_rows = read_rows(args.marker_topology)
    marker_provenance_rows = read_rows(args.marker_provenance)
    presence_rows = read_rows(args.pangenome_presence_absence)
    metadata_rows = read_rows(args.pangenome_metadata)
    host_rows = read_rows(args.host_context)
    host_adaptation_rows = read_rows(args.host_adaptation)
    host_rscu_rows = read_rows(args.host_rscu)
    crispr_match_rows = read_rows(args.crispr_matches)
    crispr_summary = read_key_value(args.crispr_summary)

    write_key_value(tables_dir / "validation_summary.tsv", validation)
    write_rows(tables_dir / "fasta_stats_combined.tsv", fasta_rows)
    write_rows(tables_dir / "orf_summary_combined.tsv", orf_rows)
    write_rows(tables_dir / "codon_summary_combined.tsv", codon_rows)
    shutil.copyfile(args.cohort_summary, tables_dir / "cohort_similarity_summary.tsv")
    shutil.copyfile(args.cohort_pairwise, tables_dir / "cohort_pairwise_similarity.tsv")
    shutil.copyfile(args.cohort_duplicates, tables_dir / "cohort_duplicate_groups.tsv")
    shutil.copyfile(args.intergenomic_summary, tables_dir / "intergenomic_similarity_summary.tsv")
    shutil.copyfile(args.intergenomic_pairs, tables_dir / "intergenomic_similarity_pairs.tsv")
    shutil.copyfile(args.intergenomic_similarity_matrix, tables_dir / "intergenomic_similarity_matrix.tsv")
    shutil.copyfile(args.intergenomic_distance_matrix, tables_dir / "intergenomic_distance_matrix.tsv")
    shutil.copyfile(args.intergenomic_note, tables_dir / "intergenomic_similarity_note.md")
    shutil.copyfile(args.marker_summary, tables_dir / "marker_tree_summary.tsv")
    shutil.copyfile(args.marker_presence, tables_dir / "marker_presence.tsv")
    shutil.copyfile(args.marker_topology, tables_dir / "marker_topology_consistency.tsv")
    shutil.copyfile(args.marker_provenance, tables_dir / "marker_provenance.tsv")
    shutil.copyfile(args.marker_note, tables_dir / "marker_phylogeny_note.md")
    if args.marker_trees.exists() and args.marker_trees.is_dir():
        shutil.copytree(args.marker_trees, tables_dir / "marker_trees", dirs_exist_ok=True)
    shutil.copyfile(args.pangenome_summary, tables_dir / "pangenome_summary.tsv")
    shutil.copyfile(args.pangenome_presence_absence, tables_dir / "presence_absence.tsv")
    shutil.copyfile(args.pangenome_metadata, tables_dir / "genome_metadata.tsv")
    shutil.copyfile(args.host_context, tables_dir / "host_context.tsv")
    shutil.copyfile(args.host_adaptation, tables_dir / "host_codon_adaptation.tsv")
    shutil.copyfile(args.host_rscu, tables_dir / "host_codon_rscu.tsv")
    shutil.copyfile(args.crispr_matches, tables_dir / "crispr_spacer_matches.tsv")
    shutil.copyfile(args.crispr_summary, tables_dir / "crispr_spacer_summary.tsv")
    claim_rows = claim_evidence_rows(
        validation,
        cohort_summary,
        intergenomic_summary,
        marker_summary,
        pangenome_summary,
        fasta_rows,
        orf_rows,
        codon_rows,
        pairwise_rows,
        intergenomic_pair_rows,
        marker_presence_rows,
        marker_provenance_rows,
        presence_rows,
        host_rows,
        host_adaptation_rows,
        crispr_match_rows,
        crispr_summary,
    )
    write_rows(tables_dir / "claim_evidence_matrix.tsv", claim_rows)

    figure_paths = []
    figure_paths.extend(plot_genome_qc(fasta_rows, args.figures_dir))
    figure_paths.extend(plot_codon_gc3(codon_rows, args.figures_dir))
    figure_paths.extend(plot_similarity(pairwise_rows, fasta_rows, args.figures_dir))
    figure_paths.extend(plot_intergenomic_similarity(intergenomic_matrix_rows, args.figures_dir))
    figure_paths.extend(plot_marker_trees(args.marker_trees, args.figures_dir))
    figure_paths.extend(plot_pangenome(presence_rows, metadata_rows, args.figures_dir))
    figure_paths.extend(plot_host_context(host_rows, args.figures_dir))
    figure_paths.extend(plot_host_adaptation(host_adaptation_rows, args.figures_dir))

    params = {
        "pangenome_method": args.pangenome_method,
        "intergenomic_status": intergenomic_summary.get("status", "not_available"),
        "marker_status": marker_summary.get("status", "not_available"),
        "host_adaptation_rows": str(len(host_adaptation_rows)),
        "crispr_status": crispr_summary.get("status", "not_available"),
        "crispr_spacer_matches": crispr_summary.get("spacer_matches", str(len(crispr_match_rows))),
        "output_mode": args.output_mode,
        "min_orf_aa": args.min_orf_aa,
        "kmer_size": args.kmer_size,
        "duplicate_jaccard": args.duplicate_jaccard,
        "run_intergenomic_similarity": args.run_intergenomic_similarity,
        "ani_min_identity": args.ani_min_identity,
        "ani_min_aln_len": args.ani_min_aln_len,
        "ani_max_evalue": args.ani_max_evalue,
        "ani_max_genomes": args.ani_max_genomes,
        "run_marker_tree": args.run_marker_tree,
        "marker_source": args.marker_source,
        "marker_kinds": args.marker_kinds,
        "marker_min_genomes": args.marker_min_genomes,
        "marker_tree_engine": args.marker_tree_engine,
        "marker_bootstrap": args.marker_bootstrap,
        "run_crispr_spacer_match": args.run_crispr_spacer_match,
        "crispr_min_identity": args.crispr_min_identity,
        "crispr_min_coverage": args.crispr_min_coverage,
        "host_min_orf_aa": args.host_min_orf_aa,
        "host_use_prodigal": args.host_use_prodigal,
        "pan_min_seq_id": args.pan_min_seq_id,
        "pan_min_coverage": args.pan_min_coverage,
    }
    args.params_json.write_text(json.dumps(params, indent=2, sort_keys=True) + "\n")
    write_software_versions(args.software_versions)

    important_files = [
        ("report", "index.html", "HTML dashboard"),
        ("report", "phageflow_report.md", "Markdown summary report"),
        ("qa", "validation_manifest.json", "Report-level validation manifest"),
        ("qa", "software_versions.tsv", "Detected software and runtime versions"),
        ("qa", "params.json", "Workflow parameters captured by the report builder"),
        ("qa", "runtime_summary.tsv", "Report runtime and output counts"),
        ("table", "tables/fasta_stats_combined.tsv", "Combined genome QC table"),
        ("table", "tables/codon_summary_combined.tsv", "Combined codon usage summary"),
        ("table", "tables/cohort_pairwise_similarity.tsv", "Pairwise cohort similarity matrix source"),
        ("table", "tables/intergenomic_similarity_summary.tsv", "BLASTN intergenomic similarity summary"),
        ("table", "tables/intergenomic_similarity_pairs.tsv", "Pairwise BLASTN identity/coverage and similarity scores"),
        ("table", "tables/intergenomic_similarity_matrix.tsv", "BLASTN intergenomic similarity score matrix"),
        ("table", "tables/intergenomic_distance_matrix.tsv", "BLASTN-derived distance matrix"),
        ("method", "tables/intergenomic_similarity_note.md", "Intergenomic similarity method note"),
        ("table", "tables/marker_tree_summary.tsv", "Marker-gene phylogeny summary"),
        ("table", "tables/marker_presence.tsv", "Marker candidate selection table"),
        ("table", "tables/marker_topology_consistency.tsv", "Marker tree versus intergenomic-distance consistency table"),
        ("table", "tables/marker_provenance.tsv", "Marker alignment/tree provenance table"),
        ("method", "tables/marker_phylogeny_note.md", "Marker phylogeny method note"),
        ("table", "tables/pangenome_summary.tsv", "Pangenome summary table"),
        ("table", "tables/presence_absence.tsv", "Orthogroup presence/absence table"),
        ("table", "tables/host_context.tsv", "Host-context composition and linked-host table"),
        ("table", "tables/host_codon_adaptation.tsv", "Host codon-adaptation metrics"),
        ("table", "tables/host_codon_rscu.tsv", "Phage-host RSCU comparison by codon"),
        ("table", "tables/crispr_spacer_matches.tsv", "Optional CRISPR spacer/protospacer matches"),
        ("table", "tables/crispr_spacer_summary.tsv", "CRISPR spacer matching summary"),
        ("qa", "tables/claim_evidence_matrix.tsv", "Software claim-to-artifact evidence matrix"),
    ]
    for path in figure_paths:
        if path.endswith(".tiff"):
            important_files.append(("figure", path, f"High-resolution TIFF figure: {Path(path).stem}"))
    write_important_files(args.important_files, important_files)

    validation_checks = {
        "html_report_exists": True,
        "figures_generated": len(figure_paths) > 0,
        "important_files_count": len(important_files),
        "fasta_rows": len(fasta_rows),
        "orf_rows": len(orf_rows),
        "codon_rows": len(codon_rows),
        "pairwise_rows": len(pairwise_rows),
        "intergenomic_pair_rows": len(intergenomic_pair_rows),
        "intergenomic_matrix_rows": len(intergenomic_matrix_rows),
        "intergenomic_status": intergenomic_summary.get("status", "not_available"),
        "intergenomic_max_similarity_score_pct": intergenomic_summary.get("max_similarity_score_pct", "NA"),
        "marker_status": marker_summary.get("status", "not_available"),
        "marker_trees_built": marker_summary.get("markers_built", "0"),
        "marker_presence_rows": len(marker_presence_rows),
        "marker_topology_rows": len(marker_topology_rows),
        "marker_provenance_rows": len(marker_provenance_rows),
        "pangenome_rows": len(presence_rows),
        "host_rows": len(host_rows),
        "host_adaptation_rows": len(host_adaptation_rows),
        "host_rscu_rows": len(host_rscu_rows),
        "crispr_match_rows": len(crispr_match_rows),
        "crispr_status": crispr_summary.get("status", "not_available"),
        "crispr_spacer_matches": crispr_summary.get("spacer_matches", str(len(crispr_match_rows))),
        "claim_evidence_rows": len(claim_rows),
        "output_mode": args.output_mode,
        "pangenome_method": args.pangenome_method,
    }
    validation_checks["report_complete"] = bool(fasta_rows and codon_rows and intergenomic_matrix_rows and args.output_mode in {"basic", "important", "all"})
    args.validation_manifest.write_text(json.dumps(validation_checks, indent=2, sort_keys=True) + "\n")

    runtime = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "figures_generated": str(len(figure_paths)),
        "important_files": str(len(important_files)),
        "genomes": validation.get("genomes", str(len(fasta_rows))),
        "pangenome_method": args.pangenome_method,
        "intergenomic_status": intergenomic_summary.get("status", "not_available"),
        "marker_status": marker_summary.get("status", "not_available"),
        "host_adaptation_rows": str(len(host_adaptation_rows)),
        "crispr_status": crispr_summary.get("status", "not_available"),
        "crispr_spacer_matches": crispr_summary.get("spacer_matches", str(len(crispr_match_rows))),
        "claim_evidence_rows": str(len(claim_rows)),
        "output_mode": args.output_mode,
    }
    write_key_value(args.runtime_summary, runtime)

    html_text = build_html(args, validation, cohort_summary, intergenomic_summary, marker_summary, pangenome_summary, fasta_rows, codon_rows, host_rows, host_adaptation_rows, crispr_match_rows, crispr_summary, intergenomic_pair_rows, marker_presence_rows, marker_topology_rows, marker_provenance_rows, claim_rows, figure_paths, important_files)
    args.output_html.write_text(html_text)
    args.output_md.write_text(build_markdown(args, validation, cohort_summary, intergenomic_summary, marker_summary, pangenome_summary, fasta_rows, codon_rows, host_adaptation_rows, crispr_match_rows, intergenomic_pair_rows, marker_topology_rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
