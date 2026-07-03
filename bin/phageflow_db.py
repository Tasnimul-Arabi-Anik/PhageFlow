#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import time
import urllib.request
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


TOOL_ORDER = ["checkv", "pharokka", "genomad", "phold", "iphop", "phabox"]
GROUPS = {
    "publication": ["checkv", "pharokka", "genomad"],
    "structure": ["phold"],
    "host-prediction": ["iphop"],
    "host_prediction": ["iphop"],
    "integrated": ["phabox"],
    "phabox2": ["phabox"],
    "all": TOOL_ORDER,
}
PHABOX_DB_URL = "https://github.com/KennthShang/PhaBOX/releases/download/v2/phabox_db_v2_2.zip"
IPHOP_DEFAULT_DB_VERSION = "iPHoP.latest_rw"


@dataclass(frozen=True)
class DbSpec:
    name: str
    run_flag: str
    path_param: str
    source: str
    notes: str


SPECS = {
    "checkv": DbSpec(
        name="checkv",
        run_flag="--run_checkv",
        path_param="--checkv_db",
        source="checkv download_database",
        notes="CheckV genome quality database.",
    ),
    "pharokka": DbSpec(
        name="pharokka",
        run_flag="--run_pharokka",
        path_param="--pharokka_db",
        source="install_databases.py",
        notes="Pharokka annotation database.",
    ),
    "genomad": DbSpec(
        name="genomad",
        run_flag="--run_genomad",
        path_param="--genomad_db",
        source="genomad download-database",
        notes="geNomad marker/classification database.",
    ),
    "phold": DbSpec(
        name="phold",
        run_flag="--run_phold",
        path_param="--phold_db",
        source="phold install",
        notes="Phold structure-search database. Also requires Pharokka output.",
    ),
    "iphop": DbSpec(
        name="iphop",
        run_flag="--run_iphop",
        path_param="--iphop_db",
        source="iphop download",
        notes="iPHoP host-prediction database.",
    ),
    "phabox": DbSpec(
        name="phabox",
        run_flag="--run_phabox",
        path_param="--phabox_db",
        source=PHABOX_DB_URL,
        notes="PhaBOX2 integrated classification/host/lifestyle database.",
    ),
}


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_tool_list(raw: str | None) -> list[str]:
    if not raw:
        return list(TOOL_ORDER)
    selected: list[str] = []
    for token in raw.replace(";", ",").split(","):
        token = token.strip().lower()
        if not token:
            continue
        members = GROUPS.get(token, [token])
        for member in members:
            if member not in SPECS:
                valid = ", ".join([*TOOL_ORDER, *sorted(GROUPS)])
                raise SystemExit(f"ERROR: unknown database tool or group '{token}'. Valid values: {valid}")
            if member not in selected:
                selected.append(member)
    return selected


def resolve_db_root(raw: str | None) -> Path:
    root = raw or os.environ.get("PHAGEFLOW_DB_ROOT")
    if not root:
        raise SystemExit("ERROR: provide --db-root PATH or set PHAGEFLOW_DB_ROOT.")
    return Path(root).expanduser().resolve()


def manifest_path(db_root: Path) -> Path:
    return db_root / "phageflow_db_manifest.json"


def load_manifest(db_root: Path) -> dict:
    path = manifest_path(db_root)
    if not path.exists():
        return {"created_by": "phageflow db", "entries": {}}
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError:
        return {"created_by": "phageflow db", "entries": {}}
    if "entries" not in data or not isinstance(data["entries"], dict):
        data["entries"] = {}
    return data


def write_manifest(db_root: Path, data: dict) -> None:
    db_root.mkdir(parents=True, exist_ok=True)
    data["updated_at_utc"] = utc_now()
    manifest_path(db_root).write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def path_is_nonempty_dir(path: Path) -> bool:
    return path.is_dir() and any(path.iterdir())


def candidate_paths(db_root: Path, tool: str) -> list[Path]:
    tool_root = db_root / tool
    candidates = [tool_root / "current"]
    if tool_root.exists():
        candidates.extend(
            p
            for p in sorted(tool_root.iterdir())
            if p.name not in {"current", "staging"} and p.is_dir()
        )
    return candidates


def current_db_path(db_root: Path, tool: str) -> Path | None:
    for path in candidate_paths(db_root, tool):
        if path_is_nonempty_dir(path):
            return path.resolve()
    return None


def count_files_and_bytes(path: Path | None) -> tuple[int, int]:
    if path is None or not path.exists():
        return 0, 0
    file_count = 0
    total_bytes = 0
    for item in path.rglob("*"):
        if item.is_file():
            file_count += 1
            total_bytes += item.stat().st_size
    return file_count, total_bytes


def status_rows(db_root: Path, tools: list[str]) -> list[dict[str, str | int]]:
    rows: list[dict[str, str | int]] = []
    manifest = load_manifest(db_root)
    entries = manifest.get("entries", {})
    for tool in tools:
        path = current_db_path(db_root, tool)
        files, bytes_ = count_files_and_bytes(path)
        entry = entries.get(tool, {})
        rows.append(
            {
                "tool": tool,
                "status": "available" if path else "missing",
                "path": str(path) if path else "",
                "files": files,
                "bytes": bytes_,
                "prepared_at_utc": entry.get("prepared_at_utc", ""),
                "source": entry.get("source", SPECS[tool].source),
                "note": SPECS[tool].notes,
            }
        )
    return rows


def print_status(rows: list[dict[str, str | int]], as_json: bool) -> None:
    if as_json:
        print(json.dumps({"databases": rows}, indent=2))
        return
    header = ["tool", "status", "path", "files", "bytes", "prepared_at_utc", "source", "note"]
    print("\t".join(header))
    for row in rows:
        print("\t".join(str(row.get(col, "")) for col in header))


def run_command(command: list[str], dry_run: bool) -> None:
    if dry_run:
        print("DRY_RUN\t" + " ".join(shlex_quote(part) for part in command))
        return
    subprocess.run(command, check=True)


def shlex_quote(value: str) -> str:
    if not value:
        return "''"
    safe = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_@%+=:,./-")
    if all(ch in safe for ch in value):
        return value
    return "'" + value.replace("'", "'\"'\"'") + "'"


def staging_root(db_root: Path, tool: str) -> Path:
    return db_root / tool / "staging"


def stage_dir(db_root: Path, tool: str) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return staging_root(db_root, tool) / f"{stamp}_{os.getpid()}"


def latest_stage_dir(db_root: Path, tool: str) -> Path | None:
    root = staging_root(db_root, tool)
    if not root.exists():
        return None
    candidates = [p for p in root.iterdir() if p.is_dir()]
    if not candidates:
        return None
    return max(candidates, key=lambda p: (p.stat().st_mtime, p.name))


def should_resume_staging(tool: str, args: argparse.Namespace) -> bool:
    return bool(
        tool == "iphop"
        and getattr(args, "resume_staging", False)
        and getattr(args, "iphop_split", False)
    )


def prepare_stage_dir(db_root: Path, tool: str, args: argparse.Namespace) -> Path:
    if should_resume_staging(tool, args):
        stage = latest_stage_dir(db_root, tool)
        if stage:
            if args.dry_run:
                print(f"DRY_RUN\treuse staging {shlex_quote(str(stage))}")
            return stage

    stage = stage_dir(db_root, tool)
    if args.dry_run:
        print(f"DRY_RUN\tmkdir -p {shlex_quote(str(stage))}")
    else:
        stage.mkdir(parents=True, exist_ok=False)
    return stage


def choose_promote_candidate(stage: Path, preferred: str | None = None) -> Path:
    if preferred:
        candidate = stage / preferred
        if path_is_nonempty_dir(candidate):
            return candidate
    children = [p for p in stage.iterdir() if p.is_dir() and path_is_nonempty_dir(p)]
    if len(children) == 1:
        return children[0]
    if path_is_nonempty_dir(stage):
        return stage
    raise RuntimeError(f"No populated database directory found under staging directory: {stage}")


def promote_database(db_root: Path, tool: str, candidate: Path, label: str, dry_run: bool) -> Path:
    tool_root = db_root / tool
    final = tool_root / label
    current = tool_root / "current"
    if dry_run:
        print(f"DRY_RUN\tpromote {candidate} -> {final}; current -> {final}")
        return final
    tool_root.mkdir(parents=True, exist_ok=True)
    if final.exists():
        raise RuntimeError(f"Refusing to overwrite existing database directory: {final}")
    shutil.move(str(candidate), str(final))
    tmp_link = tool_root / f".current.{os.getpid()}"
    if tmp_link.exists() or tmp_link.is_symlink():
        tmp_link.unlink()
    tmp_link.symlink_to(final, target_is_directory=True)
    tmp_link.replace(current)
    return final.resolve()


def update_manifest_entry(db_root: Path, tool: str, path: Path, source: str, command: list[str] | str) -> None:
    manifest = load_manifest(db_root)
    manifest.setdefault("entries", {})[tool] = {
        "tool": tool,
        "path": str(path),
        "source": source,
        "command": command if isinstance(command, str) else " ".join(shlex_quote(part) for part in command),
        "prepared_at_utc": utc_now(),
    }
    write_manifest(db_root, manifest)


def download_file(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url) as response, destination.open("wb") as handle:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            handle.write(chunk)


def rebuild_diamond_index(db_dir: Path, fasta_name: str, index_stem: str, dry_run: bool) -> None:
    fasta = db_dir / fasta_name
    index = db_dir / f"{index_stem}.dmnd"
    if dry_run:
        if index.exists():
            print(f"DRY_RUN\tbackup {index} -> {index}.orig")
        run_command(["diamond", "makedb", "--in", str(fasta), "-d", str(db_dir / index_stem)], dry_run=True)
        return
    if not fasta.exists():
        return
    if index.exists():
        backup = db_dir / f"{index_stem}.dmnd.orig"
        if not backup.exists():
            shutil.copy2(index, backup)
    run_command(["diamond", "makedb", "--in", str(fasta), "-d", str(db_dir / index_stem)], dry_run=False)


def prepare_one(db_root: Path, tool: str, args: argparse.Namespace) -> dict[str, str]:
    existing = current_db_path(db_root, tool)
    if existing and not args.update:
        return {"tool": tool, "status": "skipped_existing", "path": str(existing)}

    stage = prepare_stage_dir(db_root, tool, args)

    if tool == "checkv":
        command = ["checkv", "download_database", str(stage)]
        run_command(command, args.dry_run)
        candidate = stage / "downloaded_checkv_db" if args.dry_run else choose_promote_candidate(stage)
        path = promote_database(db_root, tool, candidate, "checkv_db_" + str(int(time.time())), args.dry_run)
        source = SPECS[tool].source
    elif tool == "pharokka":
        target = stage / "pharokka_db"
        command = ["install_databases.py", "-o", str(target)]
        run_command(command, args.dry_run)
        candidate = target if args.dry_run else choose_promote_candidate(stage, "pharokka_db")
        path = promote_database(db_root, tool, candidate, "pharokka_db_" + str(int(time.time())), args.dry_run)
        source = SPECS[tool].source
    elif tool == "genomad":
        command = ["genomad", "download-database", str(stage)]
        run_command(command, args.dry_run)
        candidate = stage / "genomad_db" if args.dry_run else choose_promote_candidate(stage, "genomad_db")
        path = promote_database(db_root, tool, candidate, "genomad_db_" + str(int(time.time())), args.dry_run)
        source = SPECS[tool].source
    elif tool == "phold":
        target = stage / "phold_db"
        command = ["phold", "install", "-d", str(target), "-t", str(args.threads)]
        if args.phold_foldseek_gpu:
            command.append("--foldseek_gpu")
        if args.phold_extended_db:
            command.append("--extended_db")
        run_command(command, args.dry_run)
        candidate = target if args.dry_run else choose_promote_candidate(stage, "phold_db")
        path = promote_database(db_root, tool, candidate, "phold_db_" + str(int(time.time())), args.dry_run)
        source = SPECS[tool].source
    elif tool == "iphop":
        command = ["iphop", "download", "--db_dir", str(stage), "--no_prompt"]
        if args.iphop_db_version:
            command.extend(["-dbv", args.iphop_db_version])
        if args.iphop_split:
            command.append("--split")
        run_command(command, args.dry_run)
        label = "iphop_" + args.iphop_db_version.replace("/", "_").replace(" ", "_") + "_" + str(int(time.time()))
        candidate = stage / "downloaded_iphop_db" if args.dry_run else choose_promote_candidate(stage)
        path = promote_database(db_root, tool, candidate, label, args.dry_run)
        source = SPECS[tool].source
    elif tool == "phabox":
        archive = stage / "phabox_db.zip"
        extracted = stage / "extract"
        if args.dry_run:
            print(f"DRY_RUN\tdownload {args.phabox_url} -> {archive}")
            print(f"DRY_RUN\tunzip {archive} -> {extracted}")
        else:
            download_file(args.phabox_url, archive)
            extracted.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(archive) as zip_handle:
                zip_handle.extractall(extracted)
        candidate = extracted / "phabox_db_v2_2" if args.dry_run else choose_promote_candidate(extracted, "phabox_db_v2_2")
        rebuild_diamond_index(candidate, "RefVirus.faa", "RefVirus", args.dry_run)
        rebuild_diamond_index(candidate, "contamination.fasta", "contamination", args.dry_run)
        path = promote_database(db_root, tool, candidate, "phabox_db_v2_2_" + str(int(time.time())), args.dry_run)
        command = f"download {args.phabox_url}"
        source = args.phabox_url
    else:
        raise RuntimeError(f"Unhandled tool: {tool}")

    if not args.dry_run:
        update_manifest_entry(db_root, tool, path, source, command)
    return {"tool": tool, "status": "prepared", "path": str(path)}


def command_prepare(args: argparse.Namespace, update: bool = False) -> int:
    db_root = resolve_db_root(args.db_root)
    args.update = update or args.update
    tools = parse_tool_list(args.tools)
    if not args.dry_run:
        db_root.mkdir(parents=True, exist_ok=True)
    results = []
    for tool in tools:
        try:
            results.append(prepare_one(db_root, tool, args))
        except FileNotFoundError as exc:
            raise SystemExit(f"ERROR: required downloader executable was not found for {tool}: {exc.filename}") from exc
    print(json.dumps({"db_root": str(db_root), "results": results}, indent=2))
    return 0


def command_status(args: argparse.Namespace) -> int:
    db_root = resolve_db_root(args.db_root)
    print_status(status_rows(db_root, parse_tool_list(args.tools)), args.json)
    return 0


def run_arg_items(db_root: Path, tools: list[str], allow_missing: bool) -> list[str]:
    selected = list(tools)
    if "phold" in selected and "pharokka" not in selected:
        selected.insert(0, "pharokka")
    items: list[str] = []
    for tool in TOOL_ORDER:
        if tool not in selected:
            continue
        path = current_db_path(db_root, tool)
        if path is None:
            if allow_missing:
                path_text = f"/path/to/{tool}_db"
            else:
                raise SystemExit(f"ERROR: database for {tool} is missing under {db_root}. Run 'phageflow db prepare' first.")
        else:
            path_text = str(path)
        spec = SPECS[tool]
        items.extend([spec.run_flag, "true", spec.path_param, path_text])
    return items


def command_run_args(args: argparse.Namespace) -> int:
    db_root = resolve_db_root(args.db_root)
    items = run_arg_items(db_root, parse_tool_list(args.tools), args.allow_missing)
    if args.shell:
        print(" \\\n  ".join(shlex_quote(item) for item in items))
    else:
        print(" ".join(shlex_quote(item) for item in items))
    return 0


def command_heavy_command(args: argparse.Namespace) -> int:
    db_root = resolve_db_root(args.db_root)
    items = ["nextflow", "run", "main.nf", "--input", args.input, "--outdir", args.outdir]
    items.extend(run_arg_items(db_root, parse_tool_list(args.tools), args.allow_missing))
    print(" \\\n  ".join(shlex_quote(item) for item in items))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Prepare and inspect PhageFlow heavy optional databases under a user-chosen database root."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    def add_common(p: argparse.ArgumentParser) -> None:
        p.add_argument("--db-root", help="Database root. Defaults to PHAGEFLOW_DB_ROOT.")
        p.add_argument("--tools", default="all", help="Comma-separated tools/groups. Default: all.")

    status = sub.add_parser("status", help="Report which managed databases are already available.")
    add_common(status)
    status.add_argument("--json", action="store_true", help="Write JSON instead of TSV.")
    status.set_defaults(func=command_status)

    prepare = sub.add_parser("prepare", help="Download missing databases and skip existing ones.")
    add_common(prepare)
    prepare.add_argument("--threads", type=int, default=8)
    prepare.add_argument("--dry-run", action="store_true")
    prepare.add_argument("--update", action="store_true", help="Download a fresh copy even if a current database exists.")
    prepare.add_argument("--iphop-db-version", default=IPHOP_DEFAULT_DB_VERSION)
    prepare_split = prepare.add_mutually_exclusive_group()
    prepare_split.add_argument(
        "--iphop-split",
        dest="iphop_split",
        action="store_true",
        default=True,
        help="Download iPHoP in resumable upstream chunks. Use --no-iphop-split for one archive.",
    )
    prepare_split.add_argument(
        "--no-iphop-split",
        dest="iphop_split",
        action="store_false",
        help="Download iPHoP as one upstream archive instead of resumable chunks.",
    )
    prepare.add_argument("--phabox-url", default=PHABOX_DB_URL)
    prepare.add_argument("--phold-foldseek-gpu", action="store_true")
    prepare.add_argument("--phold-extended-db", action="store_true")
    prepare_resume = prepare.add_mutually_exclusive_group()
    prepare_resume.add_argument(
        "--resume-staging",
        dest="resume_staging",
        action="store_true",
        default=True,
        help="Reuse the latest iPHoP split-download staging directory when present.",
    )
    prepare_resume.add_argument(
        "--no-resume-staging",
        dest="resume_staging",
        action="store_false",
        help="Always create a fresh staging directory.",
    )
    prepare.set_defaults(func=command_prepare)

    update = sub.add_parser("update", help="Download fresh copies and repoint the current links.")
    add_common(update)
    update.add_argument("--threads", type=int, default=8)
    update.add_argument("--dry-run", action="store_true")
    update.add_argument("--update", action="store_true", default=True)
    update.add_argument("--iphop-db-version", default=IPHOP_DEFAULT_DB_VERSION)
    update_split = update.add_mutually_exclusive_group()
    update_split.add_argument(
        "--iphop-split",
        dest="iphop_split",
        action="store_true",
        default=True,
        help="Download iPHoP in resumable upstream chunks. Use --no-iphop-split for one archive.",
    )
    update_split.add_argument(
        "--no-iphop-split",
        dest="iphop_split",
        action="store_false",
        help="Download iPHoP as one upstream archive instead of resumable chunks.",
    )
    update.add_argument("--phabox-url", default=PHABOX_DB_URL)
    update.add_argument("--phold-foldseek-gpu", action="store_true")
    update.add_argument("--phold-extended-db", action="store_true")
    update_resume = update.add_mutually_exclusive_group()
    update_resume.add_argument(
        "--resume-staging",
        dest="resume_staging",
        action="store_true",
        default=True,
        help="Reuse the latest iPHoP split-download staging directory when present.",
    )
    update_resume.add_argument(
        "--no-resume-staging",
        dest="resume_staging",
        action="store_false",
        help="Always create a fresh staging directory.",
    )
    update.set_defaults(func=lambda args: command_prepare(args, update=True))

    run_args = sub.add_parser("run-args", help="Print Nextflow flags for available managed databases.")
    add_common(run_args)
    run_args.add_argument("--allow-missing", action="store_true", help="Print placeholder paths for missing databases.")
    run_args.add_argument("--shell", action="store_true", help="Format as shell line continuations.")
    run_args.set_defaults(func=command_run_args)

    heavy = sub.add_parser("heavy-command", help="Print a complete heavy optional Nextflow command.")
    add_common(heavy)
    heavy.add_argument("--input", default="phage_samplesheet.tsv")
    heavy.add_argument("--outdir", default="results/phageflow_heavy")
    heavy.add_argument("--allow-missing", action="store_true", help="Print placeholder paths for missing databases.")
    heavy.set_defaults(func=command_heavy_command)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
