"""Regenerate every table, chart and the findings file in ``outputs/``.

Usage (from the project root):

    python scripts/run_analysis.py
    python scripts/run_analysis.py --data path/to/other.csv --out other_outputs
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import matplotlib  # noqa: E402

matplotlib.use("Agg")  # render to files only, no GUI window

import matplotlib.pyplot as plt  # noqa: E402

from agri_analysis import analysis as A  # noqa: E402
from agri_analysis import plots  # noqa: E402
from agri_analysis.data import DATA_PATH, clean_data, load_data, validate_data  # noqa: E402

TABLES = {
    "data_overview": lambda df: A.data_overview(df).set_index("Item"),
    "season_summary": A.season_summary,
    "crop_summary": A.crop_summary,
    "crop_season_yield_change": A.seasonal_yield_change,
    "irrigation_summary": A.irrigation_summary,
    "rainfall_response": A.rainfall_response,
    "pest_risk_by_rainfall": A.pest_risk_by_rainfall,
    "state_summary": A.state_summary,
    "yield_drivers": A.yield_drivers,
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--data", type=Path, default=DATA_PATH, help="input CSV")
    parser.add_argument("--out", type=Path, default=ROOT / "outputs", help="output folder")
    args = parser.parse_args(argv)

    raw = load_data(args.data)
    df = clean_data(raw)
    fig_dir, tab_dir = args.out / "figures", args.out / "tables"
    fig_dir.mkdir(parents=True, exist_ok=True)
    tab_dir.mkdir(parents=True, exist_ok=True)

    validate_data(raw).to_csv(tab_dir / "data_validation.csv", index=False)
    for name, fn in TABLES.items():
        fn(df).round(4).to_csv(tab_dir / f"{name}.csv")
        print(f"  table   {name}.csv")

    for name, fn in plots.FIGURES.items():
        fig = fn(df)
        fig.savefig(fig_dir / f"{name}.png")
        plt.close(fig)
        print(f"  figure  {name}.png")

    findings = A.key_findings(df)
    lines = ["# Key findings", "", f"Generated from `{args.data.name}` ({len(df):,} farm records).", ""]
    lines += [f"{i}. {f}" for i, f in enumerate(findings, 1)]
    (args.out / "key_findings.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("  report  key_findings.md")
    print(f"Done - outputs written to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
