#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from argparse import Namespace
from pathlib import Path
import tempfile


REPO = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = REPO / "bin" / "validate_phageflow_run.py"


def load_validator():
    spec = importlib.util.spec_from_file_location("validate_phageflow_run", VALIDATOR_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {VALIDATOR_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def default_args(**overrides):
    values = {
        "expect_optional": [],
        "expect_lite_optionals": False,
        "expect_publication_optionals": False,
    }
    for module in ["trnascan", "bacphlip", "checkv", "abricate", "pharokka", "genomad", "phold", "clinker", "iphop", "phabox"]:
        values[f"expect_{module}"] = False
    values.update(overrides)
    return Namespace(**values)


def run_expectation_regression() -> None:
    validator = load_validator()

    assert validator.expected_optional_modules(default_args(expect_phabox=True)) == ["phabox"]
    assert validator.expected_optional_modules(default_args(expect_optional=["integrated"])) == ["phabox"]
    assert "phabox" in validator.expected_optional_modules(default_args(expect_optional=["all"]))
    assert "iphop" in validator.expected_optional_modules(default_args(expect_iphop=True))


def run_phabox_contract_regression(tmp_path: Path) -> None:
    validator = load_validator()

    outdir = tmp_path / "run"
    phabox_dir = outdir / "05_optional" / "phabox"
    (phabox_dir / "sample_a.phabox").mkdir(parents=True)
    (phabox_dir / "sample_a.phabox" / "phabox_prediction.tsv").write_text("id\tscore\ncontig1\t0.9\n")
    (phabox_dir / "sample_a.phabox.log").write_text("completed\n")

    rows: list[dict[str, str]] = []
    versions = {"phabox2": "phabox2 help"}
    assert validator.check_optional_module(rows, outdir, "phabox", 1, versions)
    checks = {row["check"] for row in rows}
    assert "optional_tool_available:phabox2" in checks
    assert "optional_output:phabox_dirs" in checks
    assert "optional_output:phabox_logs" in checks


def main() -> int:
    run_expectation_regression()
    with tempfile.TemporaryDirectory() as tmp:
        run_phabox_contract_regression(Path(tmp))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
