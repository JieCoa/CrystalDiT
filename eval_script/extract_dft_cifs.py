#!/usr/bin/env python3
"""
Extract DFT-relaxed structures from the second-stage evaluation output.

The DFT-relaxed structure is available in two places:

1. Embedded in `final_sun/final_evaluation_report.csv` (column `dft_structure_cif`).
   Only rows with dft_processed == True carry a non-empty value. This column is
   produced by `dft_post_processor.py` via CifWriter(AseAtomsAdaptor.get_structure(traj[-1])),
   i.e. it is the last frame of the VASP trajectory, rotated into a standard
   orientation (P1, no symmetry reduction).

2. The raw source files: `dft_un/{folder_id:06d}.traj` (ase trajectory) and
   `dft_un/{folder_id:06d}/CONTCAR`. `folder_id` comes from the `dft_folder_id`
   column of the CHGNet stage CSV.

This script materializes 1 and/or 2 as standalone .cif files plus a manifest.

Usage:
  # default: extract embedded CIF strings from one or more reports
  python eval_script/extract_dft_cifs.py \
      --report chgnet_results_XXX/final_sun/final_evaluation_report.csv \
      --out dft_cifs/

  # verify the CSV against the raw trajectories (recommended once)
  python eval_script/extract_dft_cifs.py \
      --report chgnet_results_XXX/final_sun/final_evaluation_report.csv \
      --chgnet_csv chgnet_results_XXX/chgnet_results.csv \
      --dft_dir chgnet_results_XXX \
      --source both --out dft_cifs/
"""

import argparse
import csv
import json
import re
import sys
from pathlib import Path

import numpy as np


CIF_COL = "dft_structure_cif"


def to_int_folder_id(value):
    if value is None:
        return None
    value = str(value).strip()
    if not value or value.lower() in {"nan", "none", ""}:
        return None
    try:
        return int(float(value))
    except ValueError:
        return None


def load_report(path):
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    if rows and CIF_COL not in rows[0]:
        raise KeyError(f"{path} has no column '{CIF_COL}'. Columns: {list(rows[0])}")
    return rows


def load_folder_ids(chgnet_csv):
    mapping = {}
    with open(chgnet_csv, newline="") as f:
        for row in csv.DictReader(f):
            fid = to_int_folder_id(row.get("dft_folder_id"))
            if fid is not None:
                mapping[row["filename"]] = fid
    return mapping


def find_traj(dft_dir, fid):
    """ASE trajectories may live at dft_un/<id>.traj or inside the folder."""
    candidates = [
        dft_dir / "dft_un" / f"{fid:06d}.traj",
        dft_dir / "dft_un" / f"{fid:06d}" / f"{fid:06d}.traj",
    ]
    for c in candidates:
        if c.is_file() and c.stat().st_size > 0:
            return c
    found = sorted((dft_dir / "dft_un").glob(f"**/{fid:06d}.traj"))
    return found[0] if found else None


def read_traj_structure(traj_file, index=-1):
    from ase.io import read
    from pymatgen.io.ase import AseAtomsAdaptor

    frames = read(str(traj_file), index=":")
    if not frames:
        raise ValueError(f"empty trajectory: {traj_file}")
    return AseAtomsAdaptor.get_structure(frames[index])


def read_contcar(dft_dir, fid):
    from pymatgen.io.vasp import Poscar

    contcar = dft_dir / "dft_un" / f"{fid:06d}" / "CONTCAR"
    if contcar.is_file() and contcar.stat().st_size > 0:
        return Poscar.from_file(str(contcar)).structure
    return None


def write_cif(structure, out_path, symprec=None):
    from pymatgen.io.cif import CifWriter

    if symprec is None:
        text = str(CifWriter(structure))
    else:
        text = str(CifWriter(structure, symprec=symprec))
    out_path.write_text(text)
    return text


def same_structure(a, b, ltol=1e-3, stol=1e-3):
    """Rotation-invariant comparison (lattice shape + fractional coordinates)."""
    if a is None or b is None:
        return False
    if len(a) != len(b):
        return False
    if not np.allclose(sorted(a.lattice.abc), sorted(b.lattice.abc), atol=ltol):
        return False
    if not np.allclose(sorted(a.lattice.angles), sorted(b.lattice.angles), atol=ltol):
        return False
    fa = np.sort(np.mod(a.frac_coords, 1.0), axis=0)
    fb = np.sort(np.mod(b.frac_coords, 1.0), axis=0)
    return np.allclose(fa, fb, atol=stol)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Extract DFT-relaxed CIF files from the final evaluation report",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--report", nargs="+", required=True,
                        help="one or more final_evaluation_report.csv files")
    parser.add_argument("--out", default="dft_cifs/", help="output directory for .cif files")
    parser.add_argument("--chgnet_csv", default=None,
                        help="CHGNet stage CSV, needed to map filename -> dft folder id for --source traj/both")
    parser.add_argument("--dft_dir", default=None,
                        help="directory containing dft_un/ (defaults to the report's grandparent)")
    parser.add_argument("--source", choices=["csv", "traj", "both"], default="csv",
                        help="csv = use the dft_structure_cif column; traj = rebuild from *.traj; both = also cross-check")
    parser.add_argument("--symprec", type=float, default=None,
                        help="if set, write symmetry-reduced CIF with this tolerance (default: keep P1 as-is)")
    parser.add_argument("--include-unstable", action="store_true",
                        help="by default all DFT-processed structures are kept; this flag is a no-op kept for intent")
    parser.add_argument("--only_stable", action="store_true",
                        help="keep only is_stable_dft == True")
    parser.add_argument("--only_metastable", action="store_true",
                        help="keep only is_metastable_dft == True")
    args = parser.parse_args(argv)

    from pymatgen.core import Structure

    out_root = Path(args.out)
    out_root.mkdir(parents=True, exist_ok=True)

    folder_ids = {}
    if args.chgnet_csv:
        folder_ids = load_folder_ids(args.chgnet_csv)
    elif args.source in {"traj", "both"}:
        parser.error("--source traj/both requires --chgnet_csv to resolve dft_folder_id")

    manifest = []
    summary = {"reports": [], "extracted": 0, "skipped_empty": 0,
               "failed": 0, "mismatch": 0, "duplicates": 0}

    for report in args.report:
        report = Path(report).resolve()
        rows = load_report(report)
        tag = report.parent.parent.name  # e.g. chgnet_results_CrystalDiT_mpts52
        out_dir = out_root / tag if len(args.report) > 1 else out_root
        out_dir.mkdir(parents=True, exist_ok=True)

        dft_dir = Path(args.dft_dir) if args.dft_dir else report.parent.parent
        print(f"[{tag}] rows={len(rows)}  report={report}")

        n_this = 0
        seen = set()
        for row in rows:
            filename = row["filename"]
            stem = Path(filename).stem
            processed = str(row.get("dft_processed", "")).strip().lower() == "true"
            cif_text = (row.get(CIF_COL) or "").strip()

            if not processed or not cif_text:
                summary["skipped_empty"] += 1
                continue
            if args.only_stable and str(row.get("is_stable_dft", "")).strip().lower() != "true":
                continue
            if args.only_metastable and str(row.get("is_metastable_dft", "")).strip().lower() != "true":
                continue

            try:
                struct = Structure.from_str(cif_text, fmt="cif")
            except Exception as exc:  # malformed embedded CIF
                print(f"  FAIL parse {filename}: {exc}")
                summary["failed"] += 1
                continue

            fid = folder_ids.get(filename)
            status = "ok"
            traj_struct = contcar_struct = None

            if args.source in {"traj", "both"} and fid is not None:
                traj_file = find_traj(dft_dir, fid)
                try:
                    if traj_file is None:
                        raise FileNotFoundError(f"no traj for id {fid}")
                    traj_struct = read_traj_structure(traj_file)
                    contcar_struct = read_contcar(dft_dir, fid)
                except Exception as exc:
                    print(f"  WARN raw source {filename} (id={fid}): {exc}")
                    status = "raw_missing"

            write_struct = struct  # canonical: the dft_structure_cif column
            if args.source == "traj":
                if traj_struct is not None:
                    write_struct = traj_struct
                else:
                    status = "raw_missing"
            elif args.source == "both" and traj_struct is not None:
                if not same_structure(traj_struct, struct):
                    summary["mismatch"] += 1
                    status = "mismatch"
                    print(f"  MISMATCH {filename}: csv CIF != traj[-1]")

            name = f"{stem}_dft.cif"
            if name in seen:
                summary["duplicates"] += 1
                name = f"{stem}_dft_{fid}.cif" if fid is not None else f"{stem}_dft_dup.cif"
            seen.add(name)

            out_path = out_dir / name
            try:
                write_cif(write_struct, out_path, symprec=args.symprec)
            except Exception as exc:
                print(f"  FAIL write {filename}: {exc}")
                summary["failed"] += 1
                continue

            manifest.append({
                "cif_file": str(out_path.relative_to(out_root)),
                "source_filename": filename,
                "source_tag": tag,
                "dft_folder_id": fid,
                "n_sites": len(write_struct),
                "formula": write_struct.composition.reduced_formula,
                "dft_energy_raw": row.get("dft_energy_raw", ""),
                "dft_energy_corrected": row.get("dft_energy_corrected", ""),
                "e_above_hull_dft_corrected": row.get("e_above_hull_dft_corrected", ""),
                "is_stable_dft": row.get("is_stable_dft", ""),
                "is_metastable_dft": row.get("is_metastable_dft", ""),
                "chgnet_energy": row.get("chgnet_energy", ""),
                "e_above_hull_chgnet": row.get("e_above_hull_chgnet", ""),
                "cross_check": status,
            })
            n_this += 1

        print(f"[{tag}] extracted {n_this} CIF files -> {out_dir}")
        summary["reports"].append({"report": str(report), "extracted": n_this})
        summary["extracted"] += n_this

    manifest_path = out_root / "dft_cif_manifest.csv"
    with open(manifest_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(manifest[0].keys()) if manifest else ["cif_file"])
        writer.writeheader()
        writer.writerows(manifest)

    with open(out_root / "dft_cif_extraction_summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    print()
    print(f"extracted : {summary['extracted']}")
    print(f"skipped   : {summary['skipped_empty']} (no DFT result)")
    print(f"failed    : {summary['failed']}")
    if args.source in {"traj", "both"}:
        print(f"mismatch  : {summary['mismatch']}")
    print(f"manifest  : {manifest_path}")
    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
